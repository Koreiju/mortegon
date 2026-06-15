import pytest
from backend.ontology.cypher_engine import CypherEngine

def test_lca_trickle_up_path(clean_db):
    # Insert a fake graph
    clean_db.execute("CREATE (n:DomNode {node_id: 'n1', xpath: '/html/body/div', tag: 'div', label: '', depth: 0})")
    clean_db.execute("CREATE (n:DomNode {node_id: 'n2', xpath: '/html/body/div/a[1]', tag: 'a', label: '', depth: 1})")
    clean_db.execute("CREATE (n:DomNode {node_id: 'n3', xpath: '/html/body/div/a[2]', tag: 'a', label: '', depth: 1})")

    # Relationships
    clean_db.execute("MATCH (c:DomNode {xpath: '/html/body/div/a[1]'}), (p:DomNode {xpath: '/html/body/div'}) CREATE (c)-[:ChildOf]->(p)")
    clean_db.execute("MATCH (c:DomNode {xpath: '/html/body/div/a[2]'}), (p:DomNode {xpath: '/html/body/div'}) CREATE (c)-[:ChildOf]->(p)")

    path = CypherEngine.get_trickle_up_lca_path(
        ['/html/body/div/a[1]', '/html/body/div/a[2]'],
        conn=clean_db,
    )

    assert len(path) == 1
    assert path[0] == '/html/body/div'

    # Validate LinkTo was created in DB
    res = clean_db.execute("MATCH (n)-[r:LcaLinkTo]->(m) RETURN count(r)")
    assert res.has_next()
    assert res.get_next()[0] == 2
