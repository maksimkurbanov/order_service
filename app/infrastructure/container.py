from typing import Callable

from dependency_injector import containers, providers
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    AsyncSession,
    AsyncEngine,
)

from app.infrastructure.http_clients import CatalogServiceClient
from app.infrastructure.unit_of_work import UnitOfWork
from app.utils import logging


log = logging.get_logger(__name__)


class InfrastructureContainer(containers.DeclarativeContainer):
    config = providers.Configuration()
    async_engine = providers.Singleton[AsyncEngine](
        create_async_engine, config.POSTGRES_CONNECTION_STRING
    )
    session_factory: Callable[..., AsyncSession] = providers.Factory(
        async_sessionmaker,
        async_engine,
        expire_on_commit=False,
    )
    unit_of_work = providers.Singleton[UnitOfWork](
        UnitOfWork, session_factory=session_factory
    )
    catalog_client = providers.Singleton[CatalogServiceClient](CatalogServiceClient)
