from typing import Dict, List, Optional

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

_STATUS_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
}


def _error_body(code: str, message: str, fields: Optional[Dict[str, List[str]]] = None) -> Dict:
    body: dict = {"error": {"code": code, "message": message}}
    if fields:
        body["error"]["fields"] = fields
    return body


def register_error_handlers(app: FastAPI) -> None:
    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        fields: Dict[str, List[str]] = {}
        for e in exc.errors():
            field = str(e["loc"][-1]) if len(e["loc"]) > 1 else "body"
            fields.setdefault(field, []).append(e["msg"])
        return JSONResponse(
            status_code=422,
            content=_error_body("VALIDATION_ERROR", "Validation failed", fields),
        )

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, exc: HTTPException):
        code = _STATUS_CODES.get(exc.status_code, "HTTP_ERROR")
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(code, str(exc.detail)),
        )

    @app.exception_handler(Exception)
    async def server_error(request: Request, exc: Exception):
        """Never leak internal exception details to clients."""
        return JSONResponse(
            status_code=500,
            content=_error_body("SERVER_ERROR", "An unexpected error occurred"),
        )
