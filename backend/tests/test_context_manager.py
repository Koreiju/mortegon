import pytest
from backend.agentic.context_manager import ContextManager

def test_gather_context(clean_db):
    # We expect gather_context to actually pull notes or ontology objects
    clean_db.execute("CREATE (n:UserNote {note_id: 'n1', content: 'User says check out pricing page', source_url: 'http://test'})")
    
    mgr = ContextManager()
    mgr.store = clean_db # Assign the DB instance
    
    ctx = mgr.gather_context(["http://test"])
    
    # The current mock just returns "Consolidated context". TDD demands it fails.
    assert "pricing page" in ctx, "gather_context must query KuzuDB for UserNotes related to the URL"
    assert "http://test" in ctx

def test_chunk_context():
    mgr = ContextManager()
    # A long string with sentence breaks
    long_ctx = "This is sentence one. " * 500
    
    chunks = mgr.chunk_context(long_ctx, max_tokens=100) # Expecting ~100 words/tokens limit
    
    assert len(chunks) > 1, "ContextManager should split context based on max_tokens"
    assert all("This is sentence" in chunk for chunk in chunks)
