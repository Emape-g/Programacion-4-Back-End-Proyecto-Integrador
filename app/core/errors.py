from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


_STATUS_CODES = {
    400: "BAD_REQUEST",
    401: "UNAUTHORIZED",
    403: "FORBIDDEN",
    404: "NOT_FOUND",
    409: "CONFLICT",
    422: "UNPROCESSABLE_ENTITY",
    429: "TOO_MANY_REQUESTS",
    500: "INTERNAL_SERVER_ERROR",
}


def _body(detail: str, code: str | None = None, field: str | None = None) -> dict:
    return {"detail": detail, "code": code, "field": field}


async def http_exception_handler(request: Request, exc: HTTPException) -> JSONResponse:
    detail = exc.detail
    code = None
    field = None

    if isinstance(detail, dict):
        code = detail.get("code")
        field = detail.get("field")
        detail = detail.get("detail") or detail.get("message") or str(detail)

    if code is None:
        code = _STATUS_CODES.get(exc.status_code, "ERROR")

    return JSONResponse(
        status_code=exc.status_code,
        content=_body(str(detail), code, field),
        headers=getattr(exc, "headers", None),
    )


async def validation_exception_handler(
    request: Request, exc: RequestValidationError,
) -> JSONResponse:
    first = exc.errors()[0] if exc.errors() else {}
    field = ".".join(str(p) for p in first.get("loc", []) if p != "body") or None
    return JSONResponse(
        status_code=422,
        content=_body(
            detail=first.get("msg", "Validation error"),
            code="VALIDATION_ERROR",
            field=field,
        ),
    )


def register_exception_handlers(app: FastAPI) -> None:
    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
