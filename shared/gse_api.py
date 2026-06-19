"""
Functions to query the GSE ArcGIS REST API for POD → cabina primaria lookups.
"""

import httpx

GSE_URL = (
    "https://mappe.gse.it/srvf/rest/services/TIAD2/POD_AC_2025/"
    "FeatureServer/13/query"
)


def get_cabina_primaria_sync(pod: str) -> str | None:
    """Synchronous version — calls the GSE ArcGIS API directly."""
    try:
        resp = httpx.get(
            GSE_URL,
            params={
                "f": "json",
                "outFields": "COD_AC",
                "returnGeometry": "false",
                "where": f"COD_POD = '{pod}'",
            },
            timeout=10,
        )
    except httpx.RequestError:
        return None

    if resp.status_code not in (200, 304):
        return None

    try:
        data = resp.json()
    except ValueError:
        return None

    if "error" in data:
        return None

    features = data.get("features")
    if not features:
        return None

    return features[0].get("attributes", {}).get("COD_AC")


async def get_cabina_primaria(pod: str) -> str | None:
    """Async version — call from async handlers without blocking."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                GSE_URL,
                params={
                    "f": "json",
                    "outFields": "COD_AC",
                    "returnGeometry": "false",
                    "where": f"COD_POD = '{pod}'",
                },
            )
    except httpx.RequestError:
        return None

    if resp.status_code not in (200, 304):
        return None

    try:
        data = resp.json()
    except ValueError:
        return None

    if "error" in data:
        return None

    features = data.get("features")
    if not features:
        return None

    return features[0].get("attributes", {}).get("COD_AC")