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