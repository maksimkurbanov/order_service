class ApplicationError(Exception):
    status_code: int = 400

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class EntityNotFoundError(ApplicationError):
    status_code = 404


class EntityBadDataError(ApplicationError):
    status_code = 403


class OperationFailedError(ApplicationError):
    status_code = 400
