"""Trusted backend persistence adapters."""

from app.db.supabase import (
    PersistenceResult,
    SupabaseClient,
    SupabasePersistenceError,
    SupabasePersistenceService,
    is_persistable_lead,
)

__all__ = [
    "PersistenceResult",
    "SupabaseClient",
    "SupabasePersistenceError",
    "SupabasePersistenceService",
    "is_persistable_lead",
]
