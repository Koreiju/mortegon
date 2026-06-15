"""Domain-specific id types (typing.NewType).

At runtime every identifier here IS a ``str`` — no overhead, no
wrapping. The point is **static analysis**: mypy / pyright treat
``ConceptId`` and ``WorkspaceId`` as distinct types, so a function
that expects a ``WorkspaceId`` rejects a ``ConceptId`` at the type
check layer. This catches the common swapped-argument bug
(``ge.list_concepts(workspace_id=concept.concept_id)``) before it
reaches the database.

Sites that don't yet annotate with these types keep working — the
NewTypes are gradually-adoptable. New / refactored signatures should
prefer them; legacy ``str``-typed code can be updated piecemeal.

Naming convention: each id type ends with ``Id`` and corresponds to
a record class in the domain. Workspaces aren't records but they
behave as ids in every API surface.
"""

from __future__ import annotations

from typing import NewType


# Concept-graph identifiers. ConceptId is the most common — used as
# foreign key in ConceptEdge, as the lookup key in GraphEditor, and
# as the parameter-card id in every agent path. EdgeId is the Kuzu
# edge id. WorkspaceId is the routing key across REST + WS queues.
ConceptId = NewType("ConceptId", str)
EdgeId = NewType("EdgeId", str)
WorkspaceId = NewType("WorkspaceId", str)

# Parameter card id is structurally a ConceptId — wrapping it in its
# own NewType lets a function signature say "this argument must be a
# parameter card id specifically" rather than "any concept id". The
# constructor accepts the underlying ConceptId without a cast.
ParameterCardId = NewType("ParameterCardId", str)

# Chunk id in the projector: snapshot-emitted chunks use bare integer
# ids stringified; graph-output chunks use composite
# ``graph__<wid>__<cid>__<sid>``. The NewType captures "this string is
# a chunk-id, not a concept-id" — important because they coexist in
# the same dicts (LayoutFrame.coords).
ChunkId = NewType("ChunkId", str)

# Idempotency key — UUID-ish string supplied by the client. Distinct
# type so the cache lookup signature is unambiguous about what kind
# of string is expected.
IdempotencyKey = NewType("IdempotencyKey", str)


__all__ = [
    "ConceptId",
    "EdgeId",
    "WorkspaceId",
    "ParameterCardId",
    "ChunkId",
    "IdempotencyKey",
]
