from dependency_injector import containers, providers

from app.application.create_order import CreateOrderUseCase
from app.application.get_order import GetOrderUseCase
from app.application.process_payment_callback import ProcessPaymentCallbackUseCase
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
    ](ProcessPaymentCallbackUseCase, unit_of_work=infrastructure_container.unit_of_work)
