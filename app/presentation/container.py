from dependency_injector import containers, providers

from app.application.container import ApplicationContainer
from app.presentation.inbox_worker import InboxWorker
from app.presentation.inbox_writer import InboxWriter
from app.presentation.outbox_worker import OutboxWorker


class PresentationContainer(containers.DeclarativeContainer):
    config = providers.Configuration()
    application = providers.Container[ApplicationContainer](
        ApplicationContainer, config=config
    )
    outbox_worker = providers.Singleton[OutboxWorker](
        OutboxWorker, application.process_outbox_use_case
    )
    inbox_writer = providers.Singleton[InboxWriter](
        InboxWriter, application.write_to_inbox_use_case
    )
    inbox_worker = providers.Singleton[InboxWorker](
        InboxWorker, application.process_inbox_use_case
    )
