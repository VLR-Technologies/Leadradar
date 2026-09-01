from fastapi import APIRouter

from app.api.routes import businesses, calls, categories, locations

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(categories.router)
api_router.include_router(locations.router)
api_router.include_router(businesses.router)
api_router.include_router(calls.router)
