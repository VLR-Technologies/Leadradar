import asyncio
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any

import httpx

from app.core.categories import BusinessCategory
from app.models.business import Business
from app.models.location import BoundingBox, ResolvedLocation
from app.normalizers.overture_business import normalize_overture_business
from app.providers.base import (
    MalformedProviderResponseError,
    ProviderNotConfiguredError,
    ProviderTimeoutError,
    ProviderUnavailableError,
)

_RELEASE_PATTERN = re.compile(r"^\d{4}-\d{2}-\d{2}\.\d+$")
QueryExecutor = Callable[
    [str, BoundingBox, tuple[str, ...], int, Path],
    list[dict[str, Any]],
]


class OvertureMapsProvider:
    """Query a bounded slice of public Overture Places GeoParquet with DuckDB."""

    name = "overture"
    display_name = "Overture Maps"

    def __init__(
        self,
        *,
        enabled: bool = True,
        release: str = "latest",
        stac_url: str = "https://stac.overturemaps.org/catalog.json",
        timeout_seconds: float = 45.0,
        extension_directory: str | Path = ".duckdb/extensions",
        client: httpx.AsyncClient | None = None,
        query_executor: QueryExecutor | None = None,
    ) -> None:
        self.enabled = enabled
        self.release = release.strip()
        self.stac_url = stac_url
        self.timeout_seconds = timeout_seconds
        self.overall_timeout_seconds = timeout_seconds
        self.extension_directory = Path(extension_directory).resolve()
        self.client = client
        self.query_executor = query_executor or _execute_duckdb_query
        self._resolved_release: str | None = None

    async def _release(self) -> str:
        if self._resolved_release:
            return self._resolved_release
        if self.release.casefold() != "latest":
            if not _RELEASE_PATTERN.fullmatch(self.release):
                raise ProviderNotConfiguredError("The configured Overture release is invalid.")
            self._resolved_release = self.release
            return self.release

        owns_client = self.client is None
        client = self.client or httpx.AsyncClient(timeout=self.timeout_seconds)
        try:
            response = await client.get(
                self.stac_url,
                headers={"User-Agent": "LeadRadar/0.2 (internal business discovery)"},
            )
            response.raise_for_status()
            payload = response.json()
        except httpx.TimeoutException as exc:
            raise ProviderTimeoutError("Overture release discovery timed out") from exc
        except (httpx.HTTPError, ValueError) as exc:
            raise ProviderUnavailableError("Overture release discovery failed") from exc
        finally:
            if owns_client:
                await client.aclose()

        latest = payload.get("latest") if isinstance(payload, dict) else None
        if not isinstance(latest, str) or not _RELEASE_PATTERN.fullmatch(latest):
            raise MalformedProviderResponseError(
                "Overture STAC catalog did not contain a valid latest release"
            )
        self._resolved_release = latest
        return latest

    async def discover(
        self,
        *,
        location: ResolvedLocation,
        category: BusinessCategory,
        limit: int,
    ) -> list[Business]:
        if not self.enabled:
            raise ProviderNotConfiguredError("Overture Maps is disabled.")
        if location.bounding_box is None:
            raise ProviderNotConfiguredError(
                f"Overture geographic bounds are not catalogued for {location.display_name}."
            )
        if not category.overture_categories:
            raise ProviderNotConfiguredError(
                f"Overture category mapping is unavailable for {category.label}."
            )

        release = await self._release()
        try:
            rows = await asyncio.wait_for(
                asyncio.to_thread(
                    self.query_executor,
                    release,
                    location.bounding_box,
                    category.overture_categories,
                    limit,
                    self.extension_directory,
                ),
                timeout=self.timeout_seconds,
            )
        except TimeoutError as exc:
            raise ProviderTimeoutError("Overture Places query timed out") from exc
        except ProviderNotConfiguredError:
            raise
        except Exception as exc:
            raise ProviderUnavailableError("Overture Places query failed") from exc

        if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
            raise MalformedProviderResponseError("Overture Places returned invalid rows")
        businesses = [
            normalize_overture_business(
                row,
                category=category.label,
                fallback_city=location.city,
                fallback_state=location.region,
                fallback_country=location.country,
            )
            for row in rows
        ]
        return [business for business in businesses if business.name != "Unnamed business"]


def _execute_duckdb_query(
    release: str,
    bounding_box: BoundingBox,
    categories: tuple[str, ...],
    limit: int,
    extension_directory: Path,
) -> list[dict[str, Any]]:
    try:
        import duckdb
    except ImportError as exc:
        raise ProviderNotConfiguredError("DuckDB is not installed.") from exc

    extension_directory.mkdir(parents=True, exist_ok=True)
    connection = duckdb.connect(
        database=":memory:",
        config={"extension_directory": str(extension_directory)},
    )
    try:
        connection.execute("INSTALL httpfs")
        connection.execute("LOAD httpfs")
        connection.execute("SET s3_region='us-west-2'")
        source = (
            "s3://overturemaps-us-west-2/release/"
            f"{release}/theme=places/type=place/*"
        )
        placeholders = ", ".join("?" for _ in categories)
        sql = f"""
            SELECT
                id,
                CAST(names AS JSON) AS names,
                CAST(categories AS JSON) AS categories,
                CAST(addresses AS JSON) AS addresses,
                CAST(phones AS JSON) AS phones,
                CAST(websites AS JSON) AS websites,
                CAST(emails AS JSON) AS emails,
                CAST(socials AS JSON) AS socials,
                operating_status,
                confidence,
                bbox.xmin AS longitude,
                bbox.ymin AS latitude
            FROM read_parquet('{source}', hive_partitioning=true)
            WHERE
                categories.primary IN ({placeholders})
                AND bbox.xmin BETWEEN ? AND ?
                AND bbox.ymin BETWEEN ? AND ?
                AND (operating_status IS NULL OR operating_status = 'open')
            ORDER BY confidence DESC NULLS LAST
            LIMIT ?
        """
        parameters = [
            *categories,
            bounding_box.xmin,
            bounding_box.xmax,
            bounding_box.ymin,
            bounding_box.ymax,
            limit,
        ]
        result = connection.execute(sql, parameters)
        columns = [item[0] for item in result.description]
        return [dict(zip(columns, row, strict=True)) for row in result.fetchall()]
    finally:
        connection.close()
