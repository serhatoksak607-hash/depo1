import base64
import json
import urllib.request
from typing import Any


def _auth_header(config: dict) -> dict[str, str]:
    auth_type = str(config.get("auth_type") or "bearer").strip().lower()
    if auth_type == "basic":
        username = str(config.get("username") or "").strip()
        password = str(config.get("password") or "").strip()
        if not username or not password:
            return {}
        raw = f"{username}:{password}".encode("utf-8")
        return {"Authorization": "Basic " + base64.b64encode(raw).decode("ascii")}
    token = str(config.get("token") or "").strip()
    if token:
        return {"Authorization": f"Bearer {token}"}
    return {}


def _normalize_items(payload: Any) -> list[dict]:
    if isinstance(payload, dict):
        if isinstance(payload.get("items"), list):
            payload = payload.get("items")
        elif isinstance(payload.get("data"), list):
            payload = payload.get("data")
        elif isinstance(payload.get("vehicles"), list):
            payload = payload.get("vehicles")
    if not isinstance(payload, list):
        return []
    out: list[dict] = []
    for row in payload:
        if not isinstance(row, dict):
            continue
        plate = str(
            row.get("plate")
            or row.get("plaka")
            or row.get("vehiclePlate")
            or row.get("vehicle_plate")
            or ""
        ).strip().upper()
        lat = row.get("lat", row.get("latitude"))
        lon = row.get("lon", row.get("lng", row.get("longitude")))
        speed = row.get("speed", row.get("hiz"))
        ts = row.get("timestamp", row.get("time", row.get("last_update")))
        if not plate:
            continue
        out.append(
            {
                "plate": plate,
                "lat": float(lat) if lat not in {None, ""} else None,
                "lon": float(lon) if lon not in {None, ""} else None,
                "speed": float(speed) if speed not in {None, ""} else None,
                "timestamp": str(ts or "").strip() or None,
                "raw": row,
            }
        )
    return out


def fetch_arvento_positions(config: dict) -> list[dict]:
    base_url = str(config.get("base_url") or "").strip().rstrip("/")
    endpoint = str(config.get("vehicles_endpoint") or "").strip()
    if not base_url or not endpoint:
        return []
    url = endpoint if endpoint.startswith("http") else f"{base_url}/{endpoint.lstrip('/')}"
    req = urllib.request.Request(url, method="GET")
    req.add_header("Accept", "application/json")
    for k, v in _auth_header(config).items():
        req.add_header(k, v)
    timeout_sec = int(config.get("timeout_sec") or 20)
    with urllib.request.urlopen(req, timeout=timeout_sec) as resp:
        body = resp.read().decode("utf-8", errors="ignore")
    payload = json.loads(body) if body else {}
    return _normalize_items(payload)
