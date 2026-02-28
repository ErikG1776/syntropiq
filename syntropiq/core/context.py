import uuid
from contextvars import ContextVar


request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)


def generate_request_id() -> str:
    return str(uuid.uuid4())


def set_request_id(request_id: str):
    request_id_var.set(request_id)


def get_request_id() -> str | None:
    return request_id_var.get()
