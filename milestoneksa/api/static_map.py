# -*- coding: utf-8 -*-
import base64
from urllib.parse import urlencode

import frappe
from frappe import _

@frappe.whitelist()
def static_map_data_uri(lat: float, lng: float, zoom: int = 15, width: int = 640, height: int = 220, marker: str = "red-pushpin"):
    """Fetch OSM static map server-side and return as a data URI to avoid CSP host blocks."""
    try:
        lat = float(lat); lng = float(lng)
    except Exception:
        frappe.throw(_("Invalid coordinates."))

    # sanitize bounds
    if not (-90 <= lat <= 90 and -180 <= lng <= 180):
        frappe.throw(_("Coordinates out of range."))

    width  = max(100, min(int(width), 1024))
    height = max(100, min(int(height), 1024))
    zoom   = max(0,   min(int(zoom),   19))

    # cache key (12h)
    cache_key = f"mksa:staticmap:{lat:.5f}:{lng:.5f}:{zoom}:{width}x{height}:{marker}"
    cached = frappe.cache().get_value(cache_key)
    if cached:
        return {"data_uri": cached}

    # build OSM static map URL
    qs = urlencode({
        "center": f"{lat},{lng}",
        "zoom": zoom,
        "size": f"{width}x{height}",
        "markers": f"{lat},{lng},{marker}",
    })
    url = f"https://staticmap.openstreetmap.de/staticmap.php?{qs}"

    # fetch
    import requests
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    content_type = r.headers.get("Content-Type", "image/png")

    b64 = base64.b64encode(r.content).decode("ascii")
    data_uri = f"data:{content_type};base64,{b64}"

    # cache for 12 hours
    frappe.cache().set_value(cache_key, data_uri, expires_in_sec=60 * 60 * 12)
    return {"data_uri": data_uri}
