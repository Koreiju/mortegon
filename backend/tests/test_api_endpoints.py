def test_serve_html(client, clean_db):
    res = client.get("/")
    assert res.status_code == 200
    assert "Orbit: Company Discovery" in res.text or "Graph-Analytic" in res.text or "<!DOCTYPE html>" in res.text

def test_upload_and_graph_fetch(client, clean_db):
    payload = {
        "nodes": [
            {"xpath": "/html", "tag": "html"},
            {"xpath": "/html/body", "tag": "body"}
        ],
        "html": "<html><body></body></html>"
    }
    
    # Ingest
    res = client.post("/api/upload", json=payload)
    assert res.status_code == 200
    assert res.json()["status"] == "success"
    assert res.json()["nodes_ingested"] == 2
    
    # Fetch Graph
    graph_res = client.get("/api/graph")
    assert graph_res.status_code == 200
    data = graph_res.json()
    assert "nodes" in data
    assert "links" in data
    
    # Assuming the nodes were inserted but no explicit relations mapped outside ChildOf yet,
    # nodes should still show up
    assert len(data["nodes"]) >= 2
