from app.schemas.base import ApiModel


class CategoryResponse(ApiModel):
    id: str
    label: str


class CategoriesResponse(ApiModel):
    categories: list[CategoryResponse]

