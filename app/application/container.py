from dependency_injector import containers, providers

from app.application.create_order import CreateOrderUseCase
from app.application.get_order import GetOrderUseCase
from app.application.process_inbox import ProcessInboxUseCase
from app.application.process_outbox import ProcessOutboxUseCase
from app.application.process_payment_callback import ProcessPaymentCallbackUseCase
from app.application.write_to_inbox import WriteToInboxUseCase
from app.infrastructure.container import InfrastructureContainer


class ApplicationContainer(containers.DeclarativeContainer):
    config = providers.Configuration()
    infrastructure_container = providers.Container(
        InfrastructureContainer,
        config=config,
    )

    create_order_use_case = providers.Singleton[CreateOrderUseCase](
        CreateOrderUseCase,
        unit_of_work=infrastructure_container.unit_of_work,
        catalog_client=infrastructure_container.catalog_client,
        payments_client=infrastructure_container.payments_client,
    )

    get_order_use_case = providers.Singleton[GetOrderUseCase](
        GetOrderUseCase, unit_of_work=infrastructure_container.unit_of_work
    )

    process_payment_callback_use_case = providers.Singleton[
        ProcessPaymentCallbackUseCase
    ](
        ProcessPaymentCallbackUseCase,
        unit_of_work=infrastructure_container.unit_of_work,
    )

    process_outbox_use_case = providers.Singleton[ProcessOutboxUseCase](
        ProcessOutboxUseCase,
        unit_of_work=infrastructure_container.unit_of_work,
        kafka_producer=infrastructure_container.kafka_producer,
        notifications_client=infrastructure_container.notifications_client,
        max_retries=infrastructure_container.outbox_max_retries,
    )
    write_to_inbox_use_case = providers.Singleton[WriteToInboxUseCase](
        WriteToInboxUseCase,
        unit_of_work=infrastructure_container.unit_of_work,
        kafka_consumer=infrastructure_container.kafka_consumer,
    )
    process_inbox_use_case = providers.Singleton[ProcessInboxUseCase](
        ProcessInboxUseCase,
        unit_of_work=infrastructure_container.unit_of_work,
    )
