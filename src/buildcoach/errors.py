"""Actionable input failures. These are not step verdicts."""


class InputError(Exception):
    """A session, image, or kit file cannot be checked."""

    def __init__(self, category: str, message: str, path: str | None = None) -> None:
        super().__init__(message)
        self.category = category
        self.message = message
        self.path = path

    def to_dict(self) -> dict:
        body = {
            "schema_version": "1.0.0",
            "ok": False,
            "error_category": self.category,
            "message": self.message,
        }
        if self.path is not None:
            body["path"] = self.path
        return body
