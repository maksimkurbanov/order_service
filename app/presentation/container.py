from dependency_injector import containers, providers

from app.application.container import ApplicationContainer


class PresentationContainer(containers.DeclarativeContainer):
    config = providers.Configuration()
    application = providers.Container[ApplicationContainer](
        ApplicationContainer, config=config
    )
