from backend.database import get_connection

def compute_lca_for_labeled_nodes():
    """
    Iterates over currently labeled nodes and attempts to find structural LCAs 
    by walking up their paths. In a full graph implementation, this leverages
    Kuzu relationships.
    """
    conn = get_connection()
    
    # Get all uniquely labeled elements
    res = conn.execute("MATCH (n:DomNode) WHERE n.is_user_labeled = true RETURN n.xpath, n.label;")
    labeled_nodes = []
    while res.has_next():
        row = res.get_next()
        labeled_nodes.append((row[0], row[1]))
        
    if not labeled_nodes:
        return
        
    # Example logic: For each label group, find a common ancestor
    labels = set(l for _, l in labeled_nodes)
    
    for label in labels:
        xpaths = [x for x, l in labeled_nodes if l == label]
        if len(xpaths) < 2:
            continue
            
        common_path = xpaths[0]
        # Very crude string-based LCA for demo purposes
        for xp in xpaths[1:]:
            parts1 = common_path.split("/")
            parts2 = xp.split("/")
            common_parts = []
            for p1, p2 in zip(parts1, parts2):
                if p1 == p2:
                    common_parts.append(p1)
                else:
                    break
            common_path = "/".join(common_parts)
            
        if common_path and common_path != "":
            # Ensure this LCA node exists in DB
            # And add LcaLinkTo relationships from the children to this LCA
            for xp in xpaths:
                conn.execute(
                    "MATCH (c:DomNode {xpath: $child}), (p:DomNode {xpath: $parent}) "
                    "MERGE (c)-[:LcaLinkTo]->(p);",
                    parameters={"child": xp, "parent": common_path}
                )
