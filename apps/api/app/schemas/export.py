from typing import Annotated

from pydantic import Field

from app.schemas.base import ApiModel
from app.schemas.business import BusinessResponse


class ExportBusinessesRequest(ApiModel):
    businesses: Annotated[list[BusinessResponse], Field(min_length=1, max_length=500)]
    search_label: Annotated[str | None, Field(max_length=160)] = None

