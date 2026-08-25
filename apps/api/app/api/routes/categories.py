from fastapi import APIRouter

from app.core.categories import list_categories
from app.schemas.category import CategoriesResponse, CategoryResponse

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("", response_model=CategoriesResponse)
async def get_categories() -> CategoriesResponse:
    return CategoriesResponse(
        categories=[
            CategoryResponse(id=category.id, label=category.label)
            for category in list_categories()
        ]
    )

