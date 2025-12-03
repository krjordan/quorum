"""
Error handlers - Global exception handling
"""
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
import litellm
import logging

logger = logging.getLogger(__name__)


def setup_exception_handlers(app: FastAPI):
    """Setup global exception handlers"""

    @app.exception_handler(HTTPException)
    async def http_exception_handler(request: Request, exc: HTTPException):
        logger.warning(f"HTTP {exc.status_code}: {exc.detail}")
        return JSONResponse(
            status_code=exc.status_code,
            content={"detail": exc.detail}
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning(f"Validation error: {exc.errors()}")
        return JSONResponse(
            status_code=422,
            content={"detail": exc.errors()}
        )

    @app.exception_handler(litellm.exceptions.RateLimitError)
    async def rate_limit_handler(request: Request, exc: litellm.exceptions.RateLimitError):
        logger.warning(f"Rate limit hit: {exc}")
        return JSONResponse(
            status_code=429,
            content={"detail": "Rate limit exceeded. Please try again later."}
        )

    @app.exception_handler(litellm.exceptions.Timeout)
    async def timeout_handler(request: Request, exc: litellm.exceptions.Timeout):
        logger.error(f"Request timeout: {exc}")
        return JSONResponse(
            status_code=504,
            content={"detail": "Request timeout. Please try again."}
        )

    @app.exception_handler(litellm.exceptions.AuthenticationError)
    async def auth_error_handler(request: Request, exc: litellm.exceptions.AuthenticationError):
        logger.error(f"Authentication error: {exc}")
        return JSONResponse(
            status_code=401,
            content={"detail": "Invalid API key or authentication failed."}
        )

    @app.exception_handler(Exception)
    async def general_exception_handler(request: Request, exc: Exception):
        logger.error(f"Unhandled error: {exc}", exc_info=True)
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal server error"}
        )
