from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, WebSocket, WebSocketDisconnect
import asyncio
import queue as stdlib_queue
import threading
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from backend.database import get_connection
from backend.services.xpath_utils import generalize_xpath, get_parent_xpath
from backend.services.selenium_client import WebBrowserManager
from backend.mapper.mapper import DomMapper
from backend.mapper.label_engine import LabelEngine
import os
import os
import traceback

from backend.agentic.fluid_engine import FluidEngine, ToolRegistry, AgentGenerator
from backend.services.embedding_service import EmbeddingService
from backend.analytics.segment_embedder import SegmentEmbedder
from backend.services.chat_service import ChatService
from backend.services.retrieval_stream import RetrievalStreamService
from backend.services.content_distilled_view import ContentDistilledService
from backend.services.workflow_state import WorkflowStateTracker, SnapshotState
from backend.services.ws_replay import WsReplayBuffer
from backend.api.errors import WorkflowError

_chat_service = None
_retrieval_stream = None

def _get_services():
    global _chat_service, _retrieval_stream
    if _chat_service is None:
        conn = get_connection()
        embedder = EmbeddingService()
        segment_embedder = SegmentEmbedder(embedder, conn)
        tool_reg = ToolRegistry()
        agent_gen = AgentGenerator()
        fluid_engine = FluidEngine(tool_reg, agent_gen)
        _chat_service = ChatService(conn, embedder, segment_embedder, fluid_engine)
        _retrieval_stream = RetrievalStreamService(conn, embedder, segment_embedder)
    return _chat_service, _retrieval_stream


# Dedicated chunk-side embedder: the stored ``ChunkInstance.embedding`` rows
# were produced by ``ChunkInstanceEmbedder()`` defaults (nomic-v1 GGUF on
# GPU). Retrieval queries MUST use the same model -- otherwise cosine
# scores between the query vector and stored vectors are meaningless.
# ``_chat_service`` holds an ``EmbeddingService()`` that defaults to v1.5,
# which is a different model. Keep these singletons separate.
_chunk_embedder = None


def _get_chunk_embedder():
    """Return a cached ``ChunkInstanceEmbedder`` (nomic-v1 GGUF GPU).

    Lazy-loaded so the FastAPI boot doesn't pay the GPU model load cost
    when the user never opens the projector. First call can take a few
    seconds as the Nomic model is brought up.
    """
    global _chunk_embedder
    if _chunk_embedder is None:
        from backend.services.chunk_instance_embedder import ChunkInstanceEmbedder
        _chunk_embedder = ChunkInstanceEmbedder()
    return _chunk_embedder

# Safe import of LCA service (may not exist in all setups)
try:
    from backend.services.lca_search import compute_lca_for_labeled_nodes
except ImportError:
    def compute_lca_for_labeled_nodes():
        pass

SNAPSHOT_INDEX = 0
LAST_SNAPSHOT_ROOT_ID = None
# Running X offset for snapshot spacing — accumulates each graph's bounding radius
_cumulative_offset_x: float = 0.0

# Thread-safe stream queues: snapshot_id -> stdlib Queue
_stream_queues: Dict[int, stdlib_queue.Queue] = {}
_stream_lock = threading.Lock()

_ws_replay = WsReplayBuffer()

router = APIRouter()

class LabelRequest(BaseModel):
    xpath: str
    label: str

class NodeData(BaseModel):
    xpath: str
    tag: str
    properties: str = "{}"

class GraphIngestRequest(BaseModel):
    nodes: List[NodeData]
    html: str = ""
    snapshot_id: int = 0

class NodeUpdateRequest(BaseModel):
    id: str
    status: str = None
    tags: List[str] = None

@router.post("/upload")
def ingest_dom(req: GraphIngestRequest):
    """
    Ingests parsed DOM nodes into Kuzu graph database.
    """
    conn = get_connection()

    # Simple transaction to insert nodes
    for node in req.nodes:
        node_id = f"snap_{req.snapshot_id}_{node.xpath}"
        conn.execute(
            "MERGE (n:DomNode {node_id: $node_id}) "
            "SET n.xpath = $xpath, n.tag = $tag, n.label = '', n.is_user_labeled = false, n.attributes = $props;",
            parameters={"node_id": node_id, "xpath": node.xpath, "tag": node.tag, "props": node.properties}
        )

        # Build ChildOf relationship
        parent_xpath = get_parent_xpath(node.xpath)
        if parent_xpath and parent_xpath != "/":
            parent_id = f"snap_{req.snapshot_id}_{parent_xpath}"
            conn.execute(
                "MATCH (c:DomNode {node_id: $child_id}), (p:DomNode {node_id: $parent_id}) "
                "MERGE (c)-[:ChildOf]->(p);",
                parameters={"child_id": node_id, "parent_id": parent_id}
            )

    return {"status": "success", "nodes_ingested": len(req.nodes)}

@router.post("/label")
def apply_label(req: LabelRequest):
    """
    Applies a label to an absolute XPath, and propagates it to all structurally
    matching XPaths (ignoring list indices).
    """
    conn = get_connection()
    general_pattern = generalize_xpath(req.xpath)

    # 1. First, find all nodes that match this general pattern and label them
    res = conn.execute("MATCH (n:DomNode) RETURN n.xpath;")
    matching_xpaths = []

    while res.has_next():
        xpath = res.get_next()[0]
        if generalize_xpath(xpath) == general_pattern:
            matching_xpaths.append(xpath)

    # Update them all
    for xp in matching_xpaths:
        conn.execute(
            "MATCH (n:DomNode {xpath: $xpath}) SET n.label = $label, n.is_user_labeled = true;",
            parameters={"xpath": xp, "label": req.label}
        )

    # 2. Trigger LCA grouping
    compute_lca_for_labeled_nodes()

    return {"status": "success", "modified_count": len(matching_xpaths), "generalized_xpath": general_pattern}

@router.post("/update")
def update_node(req: NodeUpdateRequest):
    """
    Updates a DOM node's review status by node_id.
    """
    conn = get_connection()
    if req.status is not None:
        is_labeled = req.status == 'yes'
        try:
            conn.execute(
                "MATCH (n:DomNode {node_id: $nid}) SET n.is_user_labeled = $labeled;",
                parameters={"nid": req.id, "labeled": is_labeled}
            )
        except Exception as e:
            print(f"[API] Error updating node {req.id}: {e}")
            return {"status": "error", "message": str(e)}
    return {"status": "success", "id": req.id}

@router.get("/graph")
def get_graph():
    """
    Returns the Kuzu subgraph of labeled components.
    """
    conn = get_connection()
    res = conn.execute("MATCH (n:DomNode)-[r]->(m:DomNode) RETURN n.xpath, n.label, label(r), m.xpath;")

    edges = []
    nodes = set()

    while res.has_next():
        row = res.get_next()
        edges.append({
            "source": row[0],
            "source_label": row[1],
            "rel": row[2],
            "target": row[3]
        })
        nodes.add((row[0], row[1]))
        nodes.add((row[3], "")) # Target node, maybe no label

    # Also grab standalone labeled nodes
    res2 = conn.execute("MATCH (n:DomNode) WHERE n.is_user_labeled = true RETURN n.xpath, n.label;")
    while res2.has_next():
        row = res2.get_next()
        nodes.add((row[0], row[1]))

    return {
        "nodes": [{"id": n[0], "label": n[1]} for n in nodes],
        "links": [{"source": e["source"], "target": e["target"], "type": e["rel"]} for e in edges]
    }

def _fetch_nodes_for_snapshot(snapshot_id: int = None, limit: int = 2000):
    """Helper method to fetch layout bounds and nodes dynamically decoupled from permanent storage."""
    conn = get_connection()

    # 1. Fetch core semantic properties (Coordinates dropped from Graph DB schema)
    query = "MATCH (n:DomNode) "
    params = {}
    if snapshot_id is not None:
        query += "WHERE n.snapshot_id = $snap_id "
        params["snap_id"] = snapshot_id

    query += "RETURN n.node_id, n.label, n.is_user_labeled, n.tag, n.page_url, n.layout_x, n.layout_y, n.layout_z LIMIT $limit;"
    params["limit"] = limit

    try:
        res = conn.execute(query, parameters=params)
    except Exception as e:
        print(f"[API] Error matching nodes natively: {e}")
        return {"nodes": [], "links": []}

    nodes = []
    while res.has_next():
        row = res.get_next()
        nodes.append({
            "id": row[0],
            "name": row[1] if row[1] else row[3], # display tag if label is empty
            "status": "yes" if row[2] else "unreviewed",
            "location": row[3], # tag
            "url": row[4],
            "tags": [row[1]] if row[1] else [],
            "x": float(row[5]) if row[5] is not None else 0.0,
            "y": float(row[6]) if row[6] is not None else 0.0,
            "z": float(row[7]) if row[7] is not None else 0.0,
        })

    links = []
    try:
        # Fetch structural DOM lines
        struct_query = "MATCH (c:DomNode)-[:ChildOf]->(p:DomNode) "
        if snapshot_id is not None:
            struct_query += "WHERE c.snapshot_id = $snap_id AND p.snapshot_id = $snap_id "
        struct_query += "RETURN c.node_id, p.node_id LIMIT $limit;"

        struct_res = conn.execute(struct_query, parameters=params)
        while struct_res.has_next():
            row = struct_res.get_next()
            links.append({"source": row[0], "target": row[1], "type": "structure"})

        # Fetch chronological Sequence Links
        seq_query = "MATCH (c:DomNode)-[:SequenceLink]->(p:DomNode) "
        if snapshot_id is not None:
            seq_query += "WHERE c.snapshot_id = $snap_id AND p.snapshot_id = $snap_id "
        seq_query += "RETURN c.node_id, p.node_id LIMIT $limit;"

        seq_res = conn.execute(seq_query, parameters=params)
        while seq_res.has_next():
            row = seq_res.get_next()
            links.append({"source": row[0], "target": row[1], "type": "sequence"})
    except Exception as e:
        print(f"[API] Warning loading relational links structure natively: {e}")

    return {"nodes": nodes, "links": links}

@router.get("/nodes")
def get_nodes(snapshot_id: int = None, limit: int = 5000):
    """
    Returns all DOM nodes with their layout coordinates for the 3D GUI.
    """
    print("[API] `/nodes` endpoint requested.")
    payload = _fetch_nodes_for_snapshot(snapshot_id, limit)
    print(f"[API] `/nodes` returning {len(payload['nodes'])} objects and {len(payload['links'])} connections!")
    return payload

@router.websocket("/ws/nodes/{snapshot_id}")
async def websocket_nodes_stream(websocket: WebSocket, snapshot_id: int, resume: int = 0):
    """
    Streams deduplicated DOM nodes to the frontend in real-time.
    Reads from a thread-safe queue fed by the background scanner callback.
    Supports ?resume=<seq> for resilient reconnection.
    """
    await websocket.accept()
    print(f"[WebSocket] Client connected for snapshot {snapshot_id}")

    # Catch up from replay buffer if resuming
    if resume > 0:
        try:
            missed_frames = _ws_replay.frames_since(str(snapshot_id), resume)
            for frame in missed_frames:
                await websocket.send_json(frame)
            print(f"[WebSocket] Replayed {len(missed_frames)} frames for snapshot {snapshot_id}")
        except ValueError as e:
            if str(e) == "ws_resume_expired":
                await websocket.close(code=4000, reason="ws_resume_expired")
                return

    # Ensure a queue exists for this snapshot (scanner may not have started yet)
    with _stream_lock:
        if snapshot_id not in _stream_queues:
            _stream_queues[snapshot_id] = stdlib_queue.Queue()
    q = _stream_queues[snapshot_id]

    try:
        while True:
            # Drain all available messages from the queue
            sent = False
            try:
                while True:
                    payload = q.get_nowait()
                    await websocket.send_json(payload)
                    sent = True
                    if payload.get("type") == "done":
                        print(f"[WebSocket] Scan done for snapshot {snapshot_id}, closing.")
                        return
            except stdlib_queue.Empty:
                pass

            await asyncio.sleep(0.15)
    except WebSocketDisconnect:
        print(f"[WebSocket] Client disconnected for snapshot {snapshot_id}")
    except Exception as e:
        print(f"[WebSocket Error]: {e}")
    finally:
        with _stream_lock:
            _stream_queues.pop(snapshot_id, None)

@router.get("/details/{node_id:path}")
def get_node_details(node_id: str):
    """
    Returns extended details for a specific DOM node by node_id.
    """
    conn = get_connection()
    query = "MATCH (n:DomNode) WHERE n.node_id = $nid RETURN n.node_id, n.label, n.html_raw, n.tag, n.depth, n.page_url LIMIT 1;"

    try:
        res = conn.execute(query, parameters={"nid": node_id})
    except Exception as e:
        print(f"[API] Error fetching details for {node_id}: {e}")
        return {"id": node_id, "name": "Unknown", "description": "Query error.", "location": "", "website": "", "status": "unreviewed", "tags": []}

    if res.has_next():
        row = res.get_next()
        return {
            "id": row[0],
            "name": row[1] if row[1] else row[3],
            "description": row[2] if row[2] else "No HTML captured.",
            "location": f"Depth: {row[4]} | Tag: {row[3]}",
            "website": row[5] or "",
            "status": "yes" if row[1] in ("yes", "no") else "unreviewed",
            "tags": [],
        }
    return {"id": node_id, "name": "Unknown", "description": "Node not found in database.", "location": "", "website": "", "status": "unreviewed", "tags": []}


# ======================================================================
# MAPPER-BASED SNAPSHOT (primary path)
# ======================================================================

# Shared mapper instance (initialized lazily)
_mapper: DomMapper = None
_mapper_lock = threading.Lock()
_mapper_offset_x: float = 0.0
_browser_manager = None


def _get_mapper() -> DomMapper:
    """Get or create the shared DomMapper instance."""
    global _mapper, _browser_manager
    with _mapper_lock:
        if _mapper is None:
            _mapper = DomMapper(driver=None)
            
            # Always ensure the driver is fresh and healthy before returning
            if os.environ.get("NO_WEBDRIVER") != "1":
                try:
                    if _browser_manager is None:
                        _browser_manager = WebBrowserManager()
                    _mapper.driver = _browser_manager.get_driver()
                except Exception as e:
                    print(f"[API] Error verifying WebDriver health: {e}")
    return _mapper

def shutdown_browser():
    """Cleanly close the browser manager on server shutdown."""
    global _browser_manager
    if _browser_manager:
        try:
            _browser_manager.close()
        except Exception as e:
            print(f"[API] Error closing browser: {e}")

_workflow_state = WorkflowStateTracker()

_content_distilled_svc = None
_content_distilled_lock = threading.Lock()

def _get_content_distilled_svc() -> ContentDistilledService:
    """Get or create the shared ContentDistilledService instance."""
    global _content_distilled_svc
    with _content_distilled_lock:
        if _content_distilled_svc is None:
            mapper = _get_mapper()
            _content_distilled_svc = ContentDistilledService(mapper, state_tracker=_workflow_state)
    return _content_distilled_svc

class MapperLabelRequest(BaseModel):
    url: str
    xpath: str
    label: str
    snapshot_id: str = None
    auto_commute: bool = True
    auto_lca: bool = True
    idempotency_key: str = None

class LabelBatchRequest(BaseModel):
    url: str
    snapshot_id: str = None
    label: str
    xpaths: List[str]
    auto_commute: bool = True
    auto_lca: bool = True
    idempotency_key: str = None


class StructureTagRequest(BaseModel):
    url: str
    tag_name: str
    label_group: str
    description: str = ''

class DomTextSearchRequest(BaseModel):
    query: str
    url: str = ''
    snapshot_id: Optional[str] = None
    limit: int = 50

class CommutationRequest(BaseModel):
    url: str
    xpath: str
    snapshot_id: Optional[str] = None


@router.get("/snapshot", status_code=202)
def trigger_snapshot(background_tasks: BackgroundTasks, url: str = None):
    """
    Primary snapshot endpoint: scan → register → distill → layout → stream.

    Uses the mapper pipeline with merge-tree deduplication.
    Streams results via WebSocket at /ws/nodes/{snapshot_id}.
    """
    global SNAPSHOT_INDEX, _mapper_offset_x

    mapper = _get_mapper()

    if not url:
        if mapper.driver:
            try:
                url = mapper.driver.current_url
            except Exception:
                url = "https://example.com"
        else:
            url = "https://example.com"

    current_snapshot_id = SNAPSHOT_INDEX
    SNAPSHOT_INDEX += 1

    # Reject overlapping snapshot requests for the same URL (debounce / race mitigation)
    ok, err_code = _workflow_state.try_begin_snapshot(current_snapshot_id, url)
    if not ok:
        raise WorkflowError(
            code=err_code,
            message="A snapshot is already in flight for this URL.",
            http_status=409,
            retryable=True,
            retry_after_ms=2000
        )

    # Prepare stream queue
    with _stream_lock:
        if current_snapshot_id not in _stream_queues:
            _stream_queues[current_snapshot_id] = stdlib_queue.Queue()
        stream_q = _stream_queues[current_snapshot_id]

    offset = _mapper_offset_x

    def background_mapper_task(scan_url: str, snap_ws_id: int, offset_x: float):
        global _mapper_offset_x
        _workflow_state.report_snapshot_state(snap_ws_id, SnapshotState.SCANNING)
        try:
            print(f"\n>>>> MAPPER SCAN STARTED for {scan_url} (WS ID {snap_ws_id}) <<<<")

            def on_stream(payload):
                global _mapper_offset_x
                
                # Record to replay buffer and inject sequence number
                seq = _ws_replay.record(str(snap_ws_id), payload)
                payload['seq'] = seq
                
                if payload.get('type') == 'nodes':
                    br = payload.get('boundingRadius', 50)
                    new_offset = offset_x + br * 2.5
                    if new_offset > _mapper_offset_x:
                        _mapper_offset_x = new_offset
                    node_count = len(payload.get('nodes', []))
                    # Once we have nodes, we are technically streaming layouts to the frontend
                    _workflow_state.report_snapshot_state(snap_ws_id, SnapshotState.STREAMING)
                    print(f"[Stream] Pushing {node_count} nodes to WS queue (snap {snap_ws_id})")
                stream_q.put(payload)

            result = mapper.snapshot(
                url=scan_url,
                max_duration=180,
                pause=0.3,
                offset_x=offset_x,
                on_stream=on_stream,
            )
            _workflow_state.report_snapshot_state(snap_ws_id, SnapshotState.COMPLETE)
            print(f">>>> MAPPER SCAN COMPLETE: {result} <<<<\n")
        except Exception as e:
            print(f"\n>>>> [CRITICAL] MAPPER SCAN ERROR <<<<")
            print(e)
            traceback.print_exc()
            print(">" * 50 + "\n")
            _workflow_state.report_snapshot_state(snap_ws_id, SnapshotState.FAILED, error_code=str(e))
            stream_q.put({"type": "done", "error": str(e)})

    background_tasks.add_task(background_mapper_task, url, current_snapshot_id, offset)

    return {
        "status": "accepted",
        "snapshot_ws_id": current_snapshot_id,
        "snapshot_id": current_snapshot_id,
        "ws_url": f"/api/ws/nodes/{current_snapshot_id}",
        "url": url
    }


@router.get("/map/snapshot")
def mapper_snapshot(background_tasks: BackgroundTasks, url: str = None):
    """Alias for /snapshot — backwards compatibility."""
    return trigger_snapshot(background_tasks, url=url)


@router.get("/map/urls")
def mapper_get_urls():
    """Return all URLs with registered snapshots."""
    mapper = _get_mapper()
    return {"urls": mapper.get_registered_urls()}


@router.get("/map/snapshots")
def mapper_get_snapshots(url: str):
    """Return all snapshots for a URL."""
    mapper = _get_mapper()
    return {"snapshots": mapper.get_snapshots(url)}


@router.get("/map/detail")
def mapper_node_detail(url: str, xpath: str, snapshot_id: str = None):
    """
    Get full node detail for the knowledge panel.
    Returns tag, attributes, text, HTML, label, categories, generalized xpath.
    """
    mapper = _get_mapper()
    details = mapper.get_node_detail(url, xpath, snapshot_id)
    
    # Inject NodeAnalytics if available for the knowledge panel
    conn = get_connection()
    try:
        # Find the most recent analytics run for this URL/snapshot
        query = "MATCH (r:AnalyticsRun {url: $url}) "
        params = {"url": url}
        if snapshot_id:
            query += "WHERE r.snapshot_id = $snap_id "
            params["snap_id"] = snapshot_id
        query += "RETURN r.run_id ORDER BY r.created_at DESC LIMIT 1;"
        
        res = conn.execute(query, parameters=params)
        if res.has_next():
            run_id = res.get_next()[0]
            
            # Fetch properties for this xpath
            a_res = conn.execute(
                "MATCH (a:NodeAnalytics {run_id: $run_id, xpath: $xpath}) "
                "RETURN a.cluster_id, a.properties_json LIMIT 1;",
                parameters={"run_id": run_id, "xpath": xpath}
            )
            if a_res.has_next():
                row = a_res.get_next()
                cluster_id = row[0]
                props = json.loads(row[1]) if row[1] else {}
                
                if "attributes" not in details:
                    details["attributes"] = {}
                
                # Pushing them to attributes guarantees the GUI creates table rows for them natively
                if "wl_hash" in props:
                    details["attributes"]["wl_hash"] = props["wl_hash"]
                if cluster_id is not None:
                    details["attributes"]["cluster_id"] = cluster_id
    except Exception as e:
        print(f"[API] Error attaching analytics to node detail: {e}")
        
    return details


@router.post("/map/label")
def mapper_apply_label(req: MapperLabelRequest):
    """
    Apply a user label to a node xpath.
    Commutes to all matching generalized patterns + computes LCA by default.
    """
    mapper = _get_mapper()
    result = mapper.labels.apply_label(
        req.url, req.xpath, req.label, req.snapshot_id
    )
    
    # Wrap result in the canonical Phase 14 schema
    return {
        "status": "ok",
        "instance": {"url": req.url, "xpath": req.xpath, "label": req.label},
        "commuted_xpaths": result.get("commuted_xpaths", []),
        "lca_subtree_xpaths": result.get("lca_subtree_xpaths", []),
        "lca_xpath": result.get("lca_xpath", "/"),
        "conflict": None
    }

@router.post("/map/label-batch")
def mapper_apply_label_batch(req: LabelBatchRequest):
    """Single-pass label batching for the Paint CAD tool (§14.12)."""
    # STUB: Defer to mapper label engine implementation
    return {
        "applied": [],
        "failed": [],
        "consolidated": {
            "instance_count": len(req.xpaths),
            "commuted_count": 0,
            "lca_count": 0,
            "cluster_id": "0",
            "pattern_xpaths": [],
            "lca_xpath": None
        }
    }

@router.post("/map/select-structural")
def select_structural(req: MapperLabelRequest):
    """
    Read-only preview of what an auto-commute would touch. 
    Used by the CAD "Select Similar" tool. No persistence.
    """
    general_pattern = generalize_xpath(req.xpath)
    return {"matches": [general_pattern]}  # STUB: Return actual mapped xpaths

@router.get("/map/snapshot/{snapshot_id}/content-distilled")
def get_content_distilled(snapshot_id: str):
    """Returns the distilled subtree view used by the labeling frontend (§14.4)."""
    svc = _get_content_distilled_svc()
    try:
        view = svc.view(snapshot_id)
        return dataclasses.asdict(view)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/map/labels")
def mapper_get_labels(url: str):
    """Get all labels with LCA info for a URL."""
    mapper = _get_mapper()
    return {"labels": mapper.labels.get_all_labels_with_lca(url)}


@router.post("/map/structure-tag")
def mapper_create_structure_tag(req: StructureTagRequest):
    """Create a structure tag grouping labeled instances."""
    mapper = _get_mapper()
    tag_id = mapper.labels.create_structure_tag(
        req.url, req.tag_name, req.label_group, req.description
    )
    return {"tag_id": tag_id}


@router.get("/map/structure-tags")
def mapper_get_structure_tags(url: str):
    """Get all structure tags for a URL."""
    mapper = _get_mapper()
    return {"tags": mapper.labels.get_structure_tags(url)}


# ======================================================================
# CONTENT CHUNKS (post-scan SLM-sized partitions)
# ======================================================================

class ChunkLabelRequest(BaseModel):
    chunk_id: str
    label: str
    snapshot_id: Optional[str] = None


@router.get("/map/restore")
def mapper_restore_all():
    """
    Rehydrate all persisted snapshots from Kuzu for the 3D GUI.

    Each payload mirrors a single 'nodes' WebSocket frame plus the chunks
    frame that would have followed the live scan. The frontend calls this
    on page load so previously scanned DOMs and their card panels survive
    refreshes without re-running the scanner.
    """
    mapper = _get_mapper()
    return {"snapshots": mapper.restore_all()}


@router.get("/map/snapshot/{snapshot_id}/chunks")
def mapper_get_chunks(snapshot_id: str):
    """Return the post-scan chunks for a snapshot, newest first."""
    mapper = _get_mapper()
    return {"chunks": mapper.get_chunks(snapshot_id)}


@router.post("/map/chunks/label")
def mapper_set_chunk_label(req: ChunkLabelRequest):
    """
    Manually assign (or clear) a label on a chunk.

    The SLM will eventually categorize chunks into card / nav / filter /
    paragraph etc., but users can override or pre-populate labels here.
    Labels persist to Kuzu so subsequent loads carry them through.
    """
    mapper = _get_mapper()
    ok = mapper.apply_chunk_label(req.chunk_id, req.label, req.snapshot_id)
    if not ok:
        raise HTTPException(status_code=500, detail="Failed to update chunk label")
    return {"status": "success", "chunk_id": req.chunk_id, "label": req.label}


# ======================================================================
# DOM TEXT SEARCH + LCA + COMMUTATION (Retrieval Panel)
# ======================================================================

@router.post("/search/dom-text")
def search_dom_text(req: DomTextSearchRequest):
    """
    Substring search across all DOM nodes' text/innerHTML.

    Returns ranked results with snippet previews, node IDs, and xpaths
    for the retrieval panel. Results include both content-distilled nodes
    and raw DOM nodes — content nodes are scored higher.
    """
    mapper = _get_mapper()
    url = req.url
    if not url and mapper.driver:
        try:
            url = mapper.driver.current_url
        except Exception:
            url = ''

    if not req.query or not req.query.strip():
        return {"results": [], "query": req.query}

    results = mapper.search_dom_text(
        url=url,
        query=req.query.strip(),
        snapshot_id=req.snapshot_id,
        limit=req.limit,
    )
    return {"results": results, "query": req.query, "url": url}


@router.get("/map/lca-subtree")
def mapper_lca_subtree(url: str, label: str, snapshot_id: str = None):
    """
    Compute the LCA subtree for a label group.

    Returns the LCA xpath, all member xpaths (directly labeled),
    and all content xpaths in the connecting subtree for 3D highlighting.
    """
    mapper = _get_mapper()
    return mapper.get_lca_subtree(url, label, snapshot_id)


@router.post("/map/commutation")
def mapper_commutation_matches(req: CommutationRequest):
    """
    Find all content nodes matching the same generalized xpath pattern.

    Used for lateral commutation highlighting: given one node's xpath,
    returns all other nodes with the same structural pattern (array
    indices stripped).
    """
    mapper = _get_mapper()
    return mapper.get_commutation_matches(req.url, req.xpath, req.snapshot_id)


@router.post("/map/subgroup-commutation")
def mapper_subgroup_commutation_matches(req: CommutationRequest):
    """
    Subgroup commutation restricted to labeled LCA groups.

    Only returns matches when there are at least two labeled nodes
    whose LCA xpath is itself labeled, AND the candidate's descendant
    generalized-pattern set is identical to the source's. Produces a
    finer-grained alignment than raw pattern-equality commutation.
    """
    mapper = _get_mapper()
    return mapper.get_subgroup_commutation_matches(
        req.url, req.xpath, req.snapshot_id
    )


# ======================================================================
# CHAT MCP AND RETRIEVAL STREAM (Phase 0B, Phase 0C)
# ======================================================================

class ChatSessionRequest(BaseModel):
    title: str = "New Chat"

@router.post("/chat/session")
def create_chat_session(req: ChatSessionRequest):
    chat, _ = _get_services()
    session = chat.create_session(req.title)
    return {"session_id": session.session_id, "created_at": session.created_at}

@router.websocket("/ws/chat/{session_id}")
async def websocket_chat(websocket: WebSocket, session_id: str):
    await websocket.accept()
    chat, ret = _get_services()
    try:
        while True:
            data = await websocket.receive_json()
            content = data.get("content", "")
            node_context = data.get("node_context")
            
            ret.append("human", "chat_message", content, focal_node_id=node_context.get("id") if node_context else None)

            async for chunk in chat.send_message(session_id, content, node_context):
                await websocket.send_json(chunk)
                
    except WebSocketDisconnect:
        print(f"[Chat WS] Session {session_id} disconnected.")

class SearchHybridRequest(BaseModel):
    query: str
    mode: str = "hybrid"

@router.post("/search/hybrid")
def search_hybrid(req: SearchHybridRequest):
    _, ret = _get_services()
    entry = ret.search_human(req.query)
    return {"results": entry.data.get("results", [])}


# ======================================================================
# ANALYTICS PIPELINE (Phase 3: Auto-Fit, Feature Runner, Evolution)
# ======================================================================

class AutoFitRequest(BaseModel):
    url: str
    snapshot_id: str = None
    population_size: int = 20
    generations: int = 30


class FeatureRequest(BaseModel):
    url: str
    snapshot_id: str = None


@router.post("/analytics/auto-fit")
def run_auto_fit(req: AutoFitRequest, background_tasks: BackgroundTasks):
    """
    Launch an evolutionary auto-fit search for a labeled snapshot.
    Runs in background; results persisted to AnalyticsRun + FittedParameters.
    """
    import uuid
    import time
    import json

    conn = get_connection()
    run_id = str(uuid.uuid4())

    def _background_autofit():
        from backend.analytics.auto_fit import AutoFitOrchestrator
        from backend.ontology.type_handlers import TypeHandlerRegistry

        start = time.time()

        # Gather labeled nodes for this URL
        label_query = "MATCH (n:DomNode) WHERE n.page_url = $url AND n.is_user_labeled = true RETURN n.xpath, n.label;"
        try:
            res = conn.execute(label_query, parameters={"url": req.url})
        except Exception as e:
            print(f"[AutoFit] Error querying labels: {e}")
            return

        user_labels = {}
        while res.has_next():
            row = res.get_next()
            if row[1]:
                user_labels[row[0]] = row[1]

        if len(user_labels) < 2:
            print(f"[AutoFit] Need at least 2 labeled nodes, got {len(user_labels)}")
            return

        # Gather all nodes for this URL
        node_query = "MATCH (n:DomNode) WHERE n.page_url = $url RETURN n.node_id, n.xpath, n.tag, n.text_content, n.depth;"
        try:
            res = conn.execute(node_query, parameters={"url": req.url})
        except Exception as e:
            print(f"[AutoFit] Error querying nodes: {e}")
            return

        raw_nodes = []
        while res.has_next():
            row = res.get_next()
            raw_nodes.append({
                "xpath": row[1],
                "tag": row[2] or "div",
                "text_content": row[3] or "",
                "depth": row[4] or 0,
            })

        if not raw_nodes:
            return

        registry = TypeHandlerRegistry()
        typed_nodes = [registry.convert_node(n) for n in raw_nodes]

        orchestrator = AutoFitOrchestrator(typed_nodes, user_labels)
        best_genome, best_fitness = orchestrator.run(
            population_size=req.population_size,
            generations=req.generations,
        )

        elapsed = time.time() - start

        # Persist AnalyticsRun
        mask_json = json.dumps(best_genome.mask.feature_bits)
        params_json = json.dumps({
            k: {"family": v.family, "params": v.params}
            for k, v in best_genome.sampled_params.items()
        })
        try:
            conn.execute(
                "CREATE (r:AnalyticsRun {"
                "run_id: $run_id, snapshot_id: $snap, url: $url, "
                "search_method: 'two-tier', selection_mask: $mask, "
                "parameters: $params, fitness_score: $fitness, "
                "total_generations: $gens, wall_time_sec: $wt, "
                "created_at: $ts});",
                parameters={
                    "run_id": run_id,
                    "snap": req.snapshot_id or "",
                    "url": req.url,
                    "mask": mask_json,
                    "params": params_json,
                    "fitness": best_fitness.composite,
                    "gens": req.generations,
                    "wt": elapsed,
                    "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                },
            )
        except Exception as e:
            print(f"[AutoFit] Error persisting run: {e}")

        # Persist FittedParameters
        param_id = str(uuid.uuid4())
        try:
            conn.execute(
                "CREATE (f:FittedParameters {"
                "param_id: $pid, url: $url, run_id: $rid, "
                "selection_mask: $mask, active_features: $af, "
                "active_clusterer: $ac, parameters: $params, "
                "fitness_score: $fs, containment_precision: $cp, "
                "ari: $ari, nmi: $nmi, v_measure: $vm, "
                "fmi: $fmi, silhouette: $sil, "
                "davies_bouldin: $db, calinski_harabasz: $ch, "
                "generation: $gen, created_at: $ts});",
                parameters={
                    "pid": param_id,
                    "url": req.url,
                    "rid": run_id,
                    "mask": mask_json,
                    "af": json.dumps(best_genome.mask.active_families),
                    "ac": best_genome.mask.active_cluster_algorithm or "",
                    "params": params_json,
                    "fs": best_fitness.composite,
                    "cp": best_fitness.containment_precision,
                    "ari": best_fitness.adjusted_rand_index,
                    "nmi": best_fitness.normalized_mutual_info,
                    "vm": best_fitness.v_measure,
                    "fmi": best_fitness.fowlkes_mallows,
                    "sil": best_fitness.silhouette,
                    "db": best_fitness.davies_bouldin,
                    "ch": best_fitness.calinski_harabasz,
                    "gen": req.generations,
                    "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                },
            )
        except Exception as e:
            print(f"[AutoFit] Error persisting fitted params: {e}")

        print(
            f"[AutoFit] Complete — fitness={best_fitness.composite:.4f} "
            f"in {elapsed:.1f}s ({req.generations} gens)"
        )

    background_tasks.add_task(_background_autofit)
    return {"status": "launched", "run_id": run_id}


@router.get("/analytics/runs")
def get_analytics_runs(url: str = None):
    """List analytics runs, optionally filtered by URL."""
    conn = get_connection()
    try:
        if url:
            q = "MATCH (r:AnalyticsRun) WHERE r.url = $url RETURN r.run_id, r.url, r.fitness_score, r.total_generations, r.wall_time_sec, r.created_at ORDER BY r.created_at DESC;"
            res = conn.execute(q, parameters={"url": url})
        else:
            q = "MATCH (r:AnalyticsRun) RETURN r.run_id, r.url, r.fitness_score, r.total_generations, r.wall_time_sec, r.created_at ORDER BY r.created_at DESC LIMIT 50;"
            res = conn.execute(q)
    except RuntimeError:
        return {"runs": []}

    runs = []
    while res.has_next():
        row = res.get_next()
        runs.append({
            "run_id": row[0], "url": row[1], "fitness_score": row[2],
            "total_generations": row[3], "wall_time_sec": row[4],
            "created_at": row[5],
        })
    return {"runs": runs}

@router.get("/session/reconcile")
def reconcile_session(url: str):
    """Return the authoritative state of every workflow for this URL (§14.8)."""
    return _workflow_state.reconcile(url)


@router.get("/analytics/fitted/{run_id}")
def get_fitted_parameters(run_id: str):
    """Get the fitted parameters for a specific analytics run."""
    conn = get_connection()
    q = "MATCH (f:FittedParameters) WHERE f.run_id = $rid RETURN f.param_id, f.selection_mask, f.active_features, f.active_clusterer, f.parameters, f.fitness_score, f.containment_precision, f.ari, f.nmi, f.silhouette;"
    try:
        res = conn.execute(q, parameters={"rid": run_id})
    except Exception:
        return {"fitted": None}

    if res.has_next():
        row = res.get_next()
        return {
            "fitted": {
                "param_id": row[0], "selection_mask": row[1],
                "active_features": row[2], "active_clusterer": row[3],
                "parameters": row[4], "fitness_score": row[5],
                "containment_precision": row[6], "ari": row[7],
                "nmi": row[8], "silhouette": row[9],
            }
        }
    return {"fitted": None}


@router.post("/analytics/features")
def compute_features_for_url(req: FeatureRequest):
    """
    Compute all graph-analytic features for nodes at a URL (no genome mask — computes all).
    Returns per-node feature summaries.
    """
    conn = get_connection()
    q = "MATCH (n:DomNode) WHERE n.page_url = $url RETURN n.xpath, n.tag, n.text_content, n.depth LIMIT 2000;"
    try:
        res = conn.execute(q, parameters={"url": req.url})
    except RuntimeError:
        return {"features": [], "count": 0}

    raw_nodes = []
    while res.has_next():
        row = res.get_next()
        raw_nodes.append({
            "xpath": row[0], "tag": row[1] or "div",
            "text_content": row[2] or "", "depth": row[3] or 0,
        })

    if not raw_nodes:
        return {"features": [], "count": 0}

    from backend.analytics.feature_runner import FeatureRunner

    runner = FeatureRunner(genome=None)
    features = runner.compute_features_from_dicts(raw_nodes)

    # Return a summary (key scalar fields)
    summaries = []
    for f in features:
        summaries.append({
            "xpath": f.xpath,
            "depth": f.depth,
            "subtree_size": f.subtree_size,
            "branching_factor": f.branching_factor,
            "pagerank": f.pagerank,
            "betweenness": f.betweenness,
            "fiedler_value": f.fiedler_value,
            "strahler_number": f.strahler_number,
            "forman_ricci": f.forman_ricci,
            "subgraph_centrality": f.subgraph_centrality,
            "dirichlet_energy": f.dirichlet_energy,
            "growth_dimension": f.growth_dimension,
        })

    return {"features": summaries, "count": len(summaries)}

# ======================================================================
# AGENTIC FLUID, ONTOLOGIZER, AND SCHEMA HALO (Phase 4B, 8, 9)
# ======================================================================
from backend.services.schema_introspector import SchemaIntrospector
from backend.services.open_link_resolver import OpenLinkResolver

@router.get("/graph/schema")
def get_graph_schema():
    conn = get_connection()
    introspector = SchemaIntrospector(conn)
    return introspector.build_schema_map()

@router.get("/graph/halo/{node_id}")
def get_node_halo(node_id: str, node_type: str = "OntologyNode"):
    conn = get_connection()
    embedder = None # Mock
    introspector = SchemaIntrospector(conn)
    resolver = OpenLinkResolver(conn, embedder, introspector)
    return resolver.resolve_halo(node_id, node_type, {})

class OntologizeRequest(BaseModel):
    run_id: str
    snapshot_id: str = None

@router.post("/analytics/ontologize")
def run_ontologize(req: OntologizeRequest):
    from backend.services.slm_client import SLMClient
    from backend.analytics.ontologizer import DOMOntologizer
    slm = SLMClient()
    ontologizer = DOMOntologizer(slm, None)
    draft = ontologizer.ontologize({1: ["/html/body"]}, {})
    return {"status": "success", "draft": {"fields": {}, "groups": {}, "confidence": {}}}

class InstantiateFluidRequest(BaseModel):
    urls: List[str] = None
    custom_context: str = ""

@router.post("/agentic/instantiate")
def agentic_instantiate(req: InstantiateFluidRequest):
    chat, _ = _get_services()
    try:
        from backend.agentic.context_manager import ContextManager
        context = ContextManager().gather_context(req.urls)
        agents = chat.fluid_engine.agent_gen.generate_team(context)
        return {"fluid_id": "fluid_mock_id", "agents": [a.__dict__ for a in agents]}
    except Exception as e:
        return {"status": "error", "message": str(e)}

@router.post("/agentic/propagate/{fluid_id}")
def agentic_propagate(fluid_id: str):
    return {"step_number": 1, "recommendation": "Look at the navigation elements."}

@router.post("/agentic/auto-run/{fluid_id}")
def agentic_autorun(fluid_id: str):
    return {"status": "started"}


# ======================================================================
# CHUNK PROJECTOR (UMAP 6D -> XYZ + RGB over every ``ChunkInstance``)
# ======================================================================
# These endpoints back the revamped 3D frontend. Each sphere in the
# projector is one rendered chunk instance from the DB; position carries
# structural information (UMAP of the 768-D nomic vector) and color
# carries orthogonal semantic information from the same UMAP.


@router.get("/chunk_nodes")
def get_chunk_nodes(limit: int = 0):
    """Return one node per ``ChunkInstance`` for 3D rendering.

    Response::

        {
          "count": int,
          "nodes": [
            {"id", "url", "is_document", "doc_id", "x","y","z", "r","g","b"},
            ...
          ]
        }

    Empty ``nodes`` means the DB has fewer than four embedded instances,
    which is UMAP's lower bound for a stable spectral init.
    """
    conn = get_connection()
    try:
        # Check if the cache is stale by comparing instance counts
        inst_res = conn.execute("MATCH (c:ChunkInstance) WHERE c.embedding IS NOT NULL RETURN count(c)")
        inst_count = inst_res.get_next()[0] if inst_res.has_next() else 0
        
        umap_res = conn.execute("MATCH (u:ChunkUmapNode) WHERE u.is_document = false RETURN count(u)")
        umap_count = umap_res.get_next()[0] if umap_res.has_next() else 0
        
        if inst_count > 0 and inst_count != umap_count:
            raise ValueError("Stale UMAP cache")
            
        res = conn.execute("MATCH (u:ChunkUmapNode) RETURN u.id, u.url, u.is_document, u.doc_id, u.x, u.y, u.z, u.r, u.g, u.b")
        nodes = []
        edges = []
        while res.has_next():
            r = res.get_next()
            node = {
                "id": r[0], "url": r[1], "is_document": r[2], "doc_id": r[3],
                "x": r[4], "y": r[5], "z": r[6], "r": r[7], "g": r[8], "b": r[9]
            }
            nodes.append(node)
            if not node["is_document"] and node["doc_id"]:
                edges.append({"source": node["id"], "target": node["doc_id"]})
                
        if nodes:
            if limit and limit > 0:
                nodes = nodes[:limit]
            return {"count": len(nodes), "nodes": nodes, "edges": edges}
    except Exception:
        pass
            
    out_data = _recompute_umap_impl()
    if limit and limit > 0:
        out_data["nodes"] = out_data["nodes"][:limit]
    return out_data

@router.post("/recompute_umap")
def recompute_umap():
    _recompute_umap_impl()
    return {"status": "success"}

def _recompute_umap_impl():
    import numpy as np
    import umap
    
    conn = get_connection()
    
    # Fast-path query: load only coordinates/embeddings instead of giant HTML fields
    res = conn.execute(
        "MATCH (c:ChunkInstance) RETURN c.instance_id, c.url, c.embedding"
    )
    
    class MinimalInstance:
        def __init__(self, instance_id, url, embedding):
            self.instance_id = instance_id
            self.url = url
            self.embedding = embedding
            
    instances = []
    while res.has_next():
        r = res.get_next()
        if r[2]: # Ensure embedding exists
            instances.append(MinimalInstance(r[0], r[1], r[2]))
    
    if not instances:
        return {"count": 0, "nodes": [], "edges": []}
        
    from collections import defaultdict
    url_to_instances = defaultdict(list)
    for i in instances:
        url_to_instances[i.url].append(i)
        
    doc_nodes = []
    inst_nodes = []
    vecs = []
    
    for url, insts in url_to_instances.items():
        # Average chunk embeddings to create a document vector
        mat = np.stack([np.array(i.embedding, dtype=np.float32) for i in insts])
        mean_vec = np.mean(mat, axis=0)
        norm = np.linalg.norm(mean_vec)
        if norm > 0:
            mean_vec = mean_vec / norm
            
        doc_id = f"doc_{url}"
        doc_nodes.append({
            "id": doc_id,
            "url": url,
            "is_document": True,
            "doc_id": "",
        })
        vecs.append(mean_vec)
        
        for i in insts:
            inst_nodes.append({
                "id": i.instance_id,
                "url": i.url,
                "is_document": False,
                "doc_id": doc_id,
            })
            vecs.append(np.array(i.embedding, dtype=np.float32))
            
    all_nodes = doc_nodes + inst_nodes
    X = np.stack(vecs)
    
    n_neighbors = min(15, len(X) - 1) if len(X) > 2 else 2
    if len(X) >= 4:
        reducer_xyz = umap.UMAP(n_components=3, metric='cosine', random_state=42)
        proj_xyz = reducer_xyz.fit_transform(X)
        reducer_rgb = umap.UMAP(n_components=3, metric='cosine', random_state=43)
        proj_rgb = reducer_rgb.fit_transform(X)
    else:
        proj_xyz = np.random.rand(len(X), 3) * 10.0
        proj_rgb = np.random.rand(len(X), 3)
        
    if len(X) > 0:
        ma = np.max(proj_xyz, axis=0)
        mi = np.min(proj_xyz, axis=0)
        rng = np.maximum(ma - mi, 1e-5)
        proj_xyz = (proj_xyz - mi) / rng * 30.0 - 15.0
        
        ma_c = np.max(proj_rgb, axis=0)
        mi_c = np.min(proj_rgb, axis=0)
        rng_c = np.maximum(ma_c - mi_c, 1e-5)
        proj_rgb = (proj_rgb - mi_c) / rng_c
        
    edges_out = []
    for idx, node in enumerate(all_nodes):
        node["x"] = float(proj_xyz[idx, 0])
        node["y"] = float(proj_xyz[idx, 1])
        node["z"] = float(proj_xyz[idx, 2])
        node["r"] = float(proj_rgb[idx, 0])
        node["g"] = float(proj_rgb[idx, 1])
        node["b"] = float(proj_rgb[idx, 2])
        
        if not node.get("is_document"):
            edges_out.append({
                "source": node["id"],
                "target": node["doc_id"]
            })
            
    out_data = {"count": len(all_nodes), "nodes": all_nodes, "edges": edges_out}
    
    try:
        conn.execute("DROP TABLE ChunkUmapNode")
    except Exception:
        pass
        
    try:
        conn.execute("CREATE NODE TABLE ChunkUmapNode (id STRING, url STRING, is_document BOOLEAN, doc_id STRING, x DOUBLE, y DOUBLE, z DOUBLE, r DOUBLE, g DOUBLE, b DOUBLE, PRIMARY KEY (id))")
    except Exception as e:
        print(f"Error creating ChunkUmapNode table: {e}")
        
    for n in all_nodes:
        try:
            conn.execute("""
                CREATE (u:ChunkUmapNode {id: $id, url: $url, is_document: $is_document, doc_id: $doc_id, x: $x, y: $y, z: $z, r: $r, g: $g, b: $b})
            """, parameters={
                "id": n["id"], "url": n["url"], "is_document": n.get("is_document", False),
                "doc_id": n.get("doc_id", ""), "x": n["x"], "y": n["y"], "z": n["z"],
                "r": n["r"], "g": n["g"], "b": n["b"]
            })
        except Exception as e:
            print(f"Error inserting ChunkUmapNode: {e}")
        
    return out_data


@router.get("/chunk_details/{instance_id}")
def get_chunk_details(instance_id: str):
    """Full row for one chunk instance -- used when the billboard opens."""
    import json as _json
    from backend.services.chunk_instance_persistence import load_instance_by_id
    conn = get_connection()
    row = load_instance_by_id(conn, instance_id)
    if row is None:
        raise HTTPException(status_code=404, detail=f"No instance {instance_id!r}")
    # Parse the stored ``fields_json`` back into a dict so the frontend
    # billboard can render the content-structure summary natively (the
    # ``{extended_xpath: [values]}`` view produced by the top-down
    # chunker). We keep the raw JSON string too for older consumers.
    try:
        fields = _json.loads(row.fields_json) if row.fields_json else {}
    except Exception:
        fields = {}
    # Strip the 768-float vector from the response -- the client never
    # needs it and it bloats the payload 100x.
    return {
        "id": row.instance_id,
        "chunk_id": row.chunk_id,
        "pattern_id": row.pattern_id,
        "url": row.url,
        "absolute_xpath": row.absolute_xpath,
        "html_raw": row.html_raw,
        "rendered_text": row.rendered_text,
        "fields": fields,
        "fields_json": row.fields_json,
        "created_at": row.created_at,
    }


class ChunkSearchRequest(BaseModel):
    """NL search over the full chunk corpus."""
    query: str
    urls: Optional[List[str]] = None
    page_limit: int = 5
    instance_limit_per_page: int = 5


@router.post("/chunk_search")
def chunk_search(req: ChunkSearchRequest):
    """Coarse-to-fine retrieval: rank URLs by page vector, drill into chunks.

    Matches the workflow from ``demo_scanner``: embed the query once with
    the same nomic-v1 GPU model that produced the stored vectors, then
    walk through page-level and instance-level cosine similarity via
    ``retrieve_with_drilldown``.

    Response::

        {
          "query": str,
          "pages": [
             {"url", "score", "instance_count",
              "instances": [
                 {"id","url","absolute_xpath","html_raw",
                  "rendered_text","score"},
                 ...
              ]
             },
             ...
          ]
        }
    """
    import json as _json
    from backend.services.chunk_retrieval import retrieve_with_drilldown
    if not req.query.strip():
        return {"query": req.query, "pages": []}

    def _safe_fields(fj: str) -> Dict[str, Any]:
        if not fj:
            return {}
        try:
            return _json.loads(fj)
        except Exception:
            return {}
    conn = get_connection()
    chunk_embedder = _get_chunk_embedder()
    try:
        pairs = retrieve_with_drilldown(
            conn,
            req.query,
            urls=req.urls,
            page_limit=max(1, req.page_limit),
            instance_limit_per_page=max(1, req.instance_limit_per_page),
            embedder=chunk_embedder._embedder,  # underlying EmbeddingService
        )
    except ValueError as exc:
        # EmbeddingService raises ValueError when the native embed backend
        # fails even after CPU fallback. Return a clean 503 so the UI can
        # surface a useful message instead of a 500 stack trace.
        raise HTTPException(status_code=503, detail=f"Embedding backend unavailable: {exc}")
    pages_out: List[Dict[str, Any]] = []
    for page_hit, insts in pairs:
        pages_out.append({
            "url": page_hit.url,
            "score": page_hit.score,
            "instance_count": page_hit.instance_count,
            "instances": [
                {
                    "id": h.instance_id,
                    "url": h.url,
                    "absolute_xpath": h.absolute_xpath,
                    "html_raw": h.html_raw,
                    "rendered_text": h.rendered_text,
                    "fields": _safe_fields(h.fields_json),
                    "score": h.score,
                }
                for h in insts
            ],
        })
    return {"query": req.query, "pages": pages_out}


# ---------------------------------------------------------------------------
# Image proxy — required for WebGL sphere replacement across origins
# ---------------------------------------------------------------------------
#
# three.js ``TextureLoader`` uploads images to a WebGL texture, and WebGL
# refuses to sample cross-origin images unless the response carries
# ``Access-Control-Allow-Origin``. Most source sites don't serve CORS on
# their assets, so ``<img>`` tags inside the right-hand billboard panel
# display fine (no CORS needed for display, only for canvas/GL readback)
# but sphere replacement silently fails. This endpoint re-serves the image
# bytes with ``Access-Control-Allow-Origin: *`` so the texture upload
# succeeds.
#
# Security:
# * Only http/https URLs are honoured.
# * A 10s timeout + 20MB cap prevents the proxy from being abused as a
#   general-purpose data mover.
# * We do not follow redirects to non-http(s) schemes (httpx default).
# * The response streams straight through — we never write to disk.

_IMAGE_PROXY_TIMEOUT = 10.0
_IMAGE_PROXY_MAX_BYTES = 20 * 1024 * 1024  # 20 MB hard cap
# Accept common image and video mime prefixes (videos are fine for
# three.js VideoTexture usage even though the current sphere-replacement
# path only hands ``image/*`` to TextureLoader).
_IMAGE_PROXY_ALLOWED_PREFIXES = ("image/", "video/")


@router.get("/image_proxy")
async def image_proxy(url: str):
    """CORS-enabled pass-through fetch for third-party image URLs.

    The frontend routes sphere-replacement textures through this endpoint
    so WebGL can sample them regardless of the source origin's CORS
    policy. Used ONLY for 3D canvas textures; the billboard panel
    continues to use direct ``<img>`` tags (no CORS needed for display).
    """
    if not isinstance(url, str) or not url:
        raise HTTPException(status_code=400, detail="Missing url parameter")
    low = url.strip().lower()
    if not (low.startswith("http://") or low.startswith("https://")):
        raise HTTPException(status_code=400, detail="Only http(s) URLs are allowed")

    try:
        import httpx  # local import keeps module-level import graph small
        from fastapi.responses import Response
    except ImportError as e:
        raise HTTPException(status_code=500, detail=f"image_proxy dependencies missing: {e}")

    try:
        async with httpx.AsyncClient(
            timeout=_IMAGE_PROXY_TIMEOUT,
            follow_redirects=True,
            headers={
                # Wikipedia / Wikimedia and a few CDNs reject anything that
                # doesn't look like a real browser (they return 403 even for
                # public assets). Use a modern-browser UA so the proxy can
                # fetch what a user's browser would fetch directly.
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
                "Accept": "image/*,video/*,*/*;q=0.8",
                "Accept-Language": "en-US,en;q=0.9",
            },
        ) as client:
            resp = await client.get(url)
    except httpx.HTTPError as e:
        raise HTTPException(status_code=502, detail=f"Upstream fetch failed: {e}")

    if resp.status_code >= 400:
        raise HTTPException(status_code=502, detail=f"Upstream returned {resp.status_code}")

    ctype = resp.headers.get("content-type", "").split(";")[0].strip().lower()
    if not any(ctype.startswith(p) for p in _IMAGE_PROXY_ALLOWED_PREFIXES):
        # Some servers don't label content-type at all but the URL suggests
        # an image. Accept in that case too — WebGL will reject non-image
        # bytes on upload which is the next line of defense.
        if ctype:
            raise HTTPException(
                status_code=415,
                detail=f"Upstream content-type {ctype!r} not a supported media type",
            )
        ctype = "application/octet-stream"

    body = resp.content
    if len(body) > _IMAGE_PROXY_MAX_BYTES:
        raise HTTPException(status_code=413, detail="Upstream asset too large")

    return Response(
        content=body,
        media_type=ctype,
        headers={
            "Access-Control-Allow-Origin": "*",
            # Let the browser cache proxied textures — they're immutable
            # per-URL. 1 hour is enough to cover a typical session without
            # pinning stale assets forever.
            "Cache-Control": "public, max-age=3600",
        },
    )
