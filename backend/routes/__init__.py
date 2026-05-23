# BrokerOS Routes Package
from .auth import router as auth_router, users_router
from .clients import router as clients_router
from .cases import router as cases_router
from .lenders import router as lenders_router
from .commissions import router as commissions_router
from .notes import router as notes_router, cases_notes_router
from .documents import router as documents_router
from .dashboard import router as dashboard_router
from .ai import router as ai_router

__all__ = [
    "auth_router",
    "users_router",
    "clients_router",
    "cases_router",
    "lenders_router",
    "commissions_router",
    "notes_router",
    "cases_notes_router",
    "documents_router",
    "dashboard_router",
    "ai_router",
]
