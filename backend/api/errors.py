from typing import Optional
from fastapi.responses import JSONResponse

class WorkflowError(Exception):
    """Structured workflow error with HTTP status, code, and retryable flag (§14.2)."""

    def __init__(self, code: str, message: str, http_status: int,
                 retryable: bool = False, retry_after_ms: int = 0,
                 context: Optional[dict] = None):
        self.code = code
        self.message = message
        self.http_status = http_status
        self.retryable = retryable
        self.retry_after_ms = retry_after_ms
        self.context = context or {}

def register_workflow_error_handler(app):
    """FastAPI exception handler that emits the canonical error envelope."""
    @app.exception_handler(WorkflowError)
    async def handler(request, exc: WorkflowError):
        return JSONResponse(
            status_code=exc.http_status,
            content={"error": {"code": exc.code, "message": exc.message, "retryable": exc.retryable, "retry_after_ms": exc.retry_after_ms, "context": exc.context}}
        )


def register_slm_unavailable_handler(app):
    """Map a real SLM-backend failure to HTTP 503 (§8D.46: subsystem
    failures are LOUD — no silent stub fallback in production). The
    cascade halts; the client sees a retryable 503 rather than
    ``[stub-slm]`` text."""
    from backend.services.slm_client import SLMUnavailableError

    @app.exception_handler(SLMUnavailableError)
    async def slm_handler(request, exc: SLMUnavailableError):
        return JSONResponse(
            status_code=503,
            content={"error": {
                "code": "slm_unavailable",
                "message": str(exc),
                "retryable": True,
            }},
        )