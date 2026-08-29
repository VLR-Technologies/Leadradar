"""Build LeadRadar's bundled India city search index from GeoNames.

Source: https://download.geonames.org/export/dump/cities5000.zip
License: Creative Commons Attribution 4.0 (https://creativecommons.org/licenses/by/4.0/)
Attribution: GeoNames (https://www.geonames.org/)
"""

import io
import json
import re
import urllib.request
import zipfile
from datetime import UTC, datetime
from pathlib import Path

BASE_URL = "https://download.geonames.org/export/dump"
OUTPUT = Path(__file__).resolve().parents[1] / "app" / "data" / "india_cities.json"
LATIN_NAME = re.compile(r"^[\w .,'()\-/]+$", re.ASCII)
COMMON_ALIASES = {
    "Bengaluru": ("Bangalore",),
    "Chennai": ("Madras",),
    "Gurgaon": ("Gurugram",),
    "Kochi": ("Cochin",),
    "Kolkata": ("Calcutta",),
    "Mumbai": ("Bombay",),
    "Thiruvananthapuram": ("Trivandrum",),
    "Vadodara": ("Baroda",),
    "Varanasi": ("Benares", "Banaras"),
    "Visakhapatnam": ("Vizag",),
}


def download(name: str) -> bytes:
    request = urllib.request.Request(
        f"{BASE_URL}/{name}",
        headers={"User-Agent": "LeadRadar location index builder/0.2"},
    )
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def code_names(raw: bytes, *, columns: int) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in raw.decode("utf-8").splitlines():
        fields = line.split("\t")
        if len(fields) >= columns and fields[0].startswith("IN."):
            values[fields[0]] = fields[1]
    return values


def aliases(name: str, ascii_name: str, raw_aliases: str) -> list[str]:
    candidates = [ascii_name, *COMMON_ALIASES.get(name, ())]
    candidates.extend(raw_aliases.split(","))
    seen = {name.casefold()}
    result: list[str] = []
    for candidate in candidates:
        cleaned = " ".join(candidate.split()).strip()
        key = cleaned.casefold()
        if (
            not cleaned
            or key in seen
            or len(cleaned) > 80
            or not LATIN_NAME.fullmatch(cleaned)
        ):
            continue
        seen.add(key)
        result.append(cleaned)
        if len(result) >= 12:
            break
    return result


def main() -> None:
    admin1 = code_names(download("admin1CodesASCII.txt"), columns=2)
    admin2 = code_names(download("admin2Codes.txt"), columns=2)
    archive = zipfile.ZipFile(io.BytesIO(download("cities5000.zip")))
    source_name = next(name for name in archive.namelist() if name.endswith(".txt"))
    records: list[dict[str, object]] = []
    for line in archive.read(source_name).decode("utf-8").splitlines():
        fields = line.split("\t")
        if len(fields) < 19 or fields[8] != "IN":
            continue
        name = fields[1].strip()
        state_code = f"IN.{fields[10]}"
        district_code = f"{state_code}.{fields[11]}" if fields[11] else ""
        records.append(
            {
                "id": int(fields[0]),
                "name": name,
                "aliases": aliases(name, fields[2], fields[3]),
                "latitude": float(fields[4]),
                "longitude": float(fields[5]),
                "state": admin1.get(state_code, fields[10]),
                "district": admin2.get(district_code) if district_code else None,
                "population": int(fields[14] or 0),
            }
        )
    records.sort(key=lambda value: (-int(value["population"]), str(value["name"])))
    payload = {
        "source": "GeoNames cities5000",
        "sourceUrl": f"{BASE_URL}/cities5000.zip",
        "license": "CC BY 4.0",
        "attribution": "GeoNames (https://www.geonames.org/)",
        "generatedAt": datetime.now(UTC).isoformat(),
        "recordCount": len(records),
        "cities": records,
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    print(f"Wrote {len(records)} India city records to {OUTPUT}")


if __name__ == "__main__":
    main()
