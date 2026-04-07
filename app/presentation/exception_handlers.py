from fastapi import Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.application.exceptions import ApplicationError


async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = exc.errors()
    error_messages = []
    for error in errors:
        field = error["loc"][-1]
        msg = error["msg"]
        error_messages.append(f"Invalid input for field '{field}': {msg}")

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={"message": "Invalid request", "details": error_messages},
    )


async def application_exception_handler(request: Request, exc: ApplicationError):
    return JSONResponse(
        status_code=exc.status_code,
        content={"message": "Invalid request", "detail": str(exc)},
    )
