import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException

logger = logging.getLogger(__name__)


class ApiError(Exception):
    def __init__(self, status: int, code: str, message: str, details=None):
        self.status = status
        self.code = code
        self.message = message
        self.details = details or []


def error_response(status, code, message, details=None):
    body = {"error": {"code": code, "message": message, "details": details or []}}
    return JSONResponse(status_code=status, content=body)


def install_error_handlers(app: FastAPI):
    @app.exception_handler(ApiError)
    async def application_error(request: Request, error: ApiError):
        return error_response(error.status, error.code, error.message, error.details)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, error: RequestValidationError):
        details = []
        for item in error.errors():
            field = ".".join(str(part) for part in item["loc"])
            details.append({"field": field, "message": item["msg"]})
        return error_response(422, "invalid_request", "Check the request fields.", details)

    @app.exception_handler(HTTPException)
    async def http_error(request: Request, error: HTTPException):
        return error_response(error.status_code, "http_error", str(error.detail))

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, error: Exception):
        logger.error("Request failed: %s %s (%s)", request.method, request.url.path, type(error).__name__)
        return error_response(500, "internal_error", "The request could not be completed.")
