from backend.database import get_connection
from backend.services.xpath_utils import generalize_xpath

class CypherEngine:
    @staticmethod
    def bulk_apply_ontology_label(absolute_xpath: str, label: str, conn=None) -> None:
        """
        Takes an absolute XPath and generalizes it. Then uses Cypher to update
        all DOM nodes matching the generalized path with the new ontology label.
        """
        if conn is None:
            conn = get_connection()
        generalized = generalize_xpath(absolute_xpath)

        res = conn.execute("MATCH (n:DomNode) RETURN n.xpath;")
        to_update = []
        while res.has_next():
            xp = res.get_next()[0]
            if generalize_xpath(xp) == generalized:
                to_update.append(xp)

        for xp in to_update:
            conn.execute(
                "MATCH (n:DomNode {xpath: $xpath}) SET n.label = $label, n.is_user_labeled = true;",
                parameters={"xpath": xp, "label": label}
            )

    @staticmethod
    def get_trickle_up_lca_path(base_xpaths: list[str], conn=None) -> list[str]:
        """
        Performs a message-passing algorithm via Cypher to find Least Common Ancestor nodes
        by crawling up the `ChildOf` relationships.
        """
        if not base_xpaths:
            return []

        if conn is None:
            conn = get_connection()

        try:
            xpath_array = "[" + ", ".join([f"'{x}'" for x in base_xpaths]) + "]"
            query = f"""
                MATCH (n:DomNode)-[:ChildOf*1..20]->(p:DomNode)
                WHERE n.xpath IN {xpath_array}
                WITH p.xpath as ancestor, count(DISTINCT n.xpath) as descendants
                WHERE descendants = {len(base_xpaths)}
                RETURN ancestor
                ORDER BY size(ancestor) DESC
                LIMIT 1
            """
            res = conn.execute(query)
            if res.has_next():
                lca_xpath = res.get_next()[0]

                for xp in base_xpaths:
                    conn.execute(
                        "MATCH (c:DomNode {xpath: $child}), (p:DomNode {xpath: $parent}) "
                        "MERGE (c)-[:LcaLinkTo]->(p);",
                        parameters={"child": xp, "parent": lca_xpath}
                    )
                return [lca_xpath]
        except Exception as e:
            print(f"[Cypher Engine Warning]: {e}")

        return []
