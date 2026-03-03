from contextlib import contextmanager
from contextvars import ContextVar

_DEFAULT_TENANT_ID = "default"
_current_tenant: ContextVar[str] = ContextVar("current_tenant", default=_DEFAULT_TENANT_ID)


def default_tenant_id() -> str:
    return _DEFAULT_TENANT_ID


def get_current_tenant() -> str:
    return _current_tenant.get() or _DEFAULT_TENANT_ID


def set_current_tenant(tenant_id: str):
    return _current_tenant.set((tenant_id or _DEFAULT_TENANT_ID).strip())


def reset_current_tenant(token) -> None:
    _current_tenant.reset(token)


@contextmanager
def tenant_scope(tenant_id: str):
    token = set_current_tenant(tenant_id)
    try:
        yield get_current_tenant()
    finally:
        reset_current_tenant(token)
