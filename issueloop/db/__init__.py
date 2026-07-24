from .base import TicketStoreBackend


def get_backend(kind: str = "local", **kwargs) -> TicketStoreBackend:
    if kind == "local":
        from .local_store import LocalStore
        return LocalStore(db_path=kwargs.get("path"))
    if kind == "supabase":
        from .supabase_store import SupabaseStore
        return SupabaseStore()
    raise ValueError(f"unknown database backend '{kind}' — expected 'local' or 'supabase'")