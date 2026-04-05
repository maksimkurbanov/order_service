import asyncio

import sentry_sdk
import uvicorn
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from sentry_sdk.integrations.fastapi import FastApiIntegration

from app.application.container import ApplicationContainer
from app.application.exception_handlers import validation_exception_handler
from app.config import settings
from app.presentation.api import router
from app.presentation import api
from app.presentation.container import PresentationContainer


sentry_sdk.init(
    dsn=settings.SENTRY_DSN,
    traces_sample_rate=1.0,
    integrations=[FastApiIntegration()],
)


def build_api(container: ApplicationContainer):
    app = FastAPI()
    app.include_router(router)
    app.add_exception_handler(RequestValidationError, validation_exception_handler)
    container.wire(modules=[api])
    return app


async def main():
    presentation_container = PresentationContainer()
    presentation_container.config.from_pydantic(settings=settings, required=True)

    app = build_api(presentation_container.application)

    api_task = asyncio.create_task(
        uvicorn.Server(
            uvicorn.Config(app, host=settings.SERVER_HOST, port=settings.SERVER_PORT)
        ).serve()
    )

    await asyncio.gather(api_task)


if __name__ == "__main__":
    asyncio.run(main())
