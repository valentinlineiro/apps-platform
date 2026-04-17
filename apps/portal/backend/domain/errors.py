class ForbiddenError(Exception):
    def __init__(self, code: str = "forbidden"):
        super().__init__(code)
        self.code = code


class NotFoundError(Exception):
    def __init__(self, code: str = "not_found"):
        super().__init__(code)
        self.code = code


class ValidationError(Exception):
    """
    errors may be:
      - dict[field_name, message]  → field-level validation
      - str                        → top-level error message
    """
    def __init__(self, errors: dict | str):
        super().__init__(str(errors))
        self.errors = errors
