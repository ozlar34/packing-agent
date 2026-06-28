# ruff: noqa
# Weather MCP server (Milestone B) — stdio transport, decision 5.
#
# The ADK agent spawns this file as a subprocess via McpToolset and calls
# get_weather over MCP. Run standalone for debugging:
#     uv run python -m app.weather_server      (speaks MCP over stdin/stdout)
#
# SECURITY (§6.1 — data minimization at the tool boundary): this tool receives
# ONLY destination + dates. It never sees the profile, medications, or
# preferences, and must never log or transmit them. Open-Meteo is keyless, so
# "no secrets in repo" stays trivially true.

import json
import urllib.error
import urllib.parse
import urllib.request

from mcp.server.fastmcp import FastMCP

mcp = FastMCP("weather")

_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
_FORECAST_URL = "https://api.open-meteo.com/v1/forecast"
_DAILY_VARS = "temperature_2m_max,temperature_2m_min,precipitation_probability_max,weathercode,windspeed_10m_max"
_HTTP_TIMEOUT = 10  # seconds

# WMO weather-code groups (Open-Meteo `weathercode`) we branch on.
_DRIZZLE_RAIN = set(range(51, 68)) | {80, 81, 82, 95, 96, 99}  # drizzle/rain/showers/thunder
_SNOW = {71, 73, 75, 77, 85, 86}
_CLEAR = {0, 1}


def _get_json(url: str, params: dict) -> dict:
    """GET a URL with query params and return parsed JSON (stdlib only, keyless)."""
    qs = urllib.parse.urlencode(params)
    req = urllib.request.Request(
        f"{url}?{qs}", headers={"User-Agent": "packing-agent/0.1 (capstone demo)"}
    )
    with urllib.request.urlopen(req, timeout=_HTTP_TIMEOUT) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _geocode(destination: str) -> tuple[float, float] | None:
    """Resolve a free-text place name to (latitude, longitude), or None."""
    data = _get_json(
        _GEOCODE_URL, {"name": destination, "count": 1, "language": "en", "format": "json"}
    )
    results = data.get("results") or []
    if not results:
        return None
    return results[0]["latitude"], results[0]["longitude"]


def _fetch_daily(lat: float, lon: float, start_date: str, end_date: str) -> dict:
    """Fetch the daily forecast, normalized to the §4.3 fields.

    Open-Meteo's forecast window is only ~16 days out, so a trip further ahead
    can't be forecast directly. In that case we fall back to the next 7 days at
    the SAME location — a near-term, destination-specific proxy — so the demo's
    "change the destination, the list changes" still holds for any date.
    """
    base = {"latitude": lat, "longitude": lon, "daily": _DAILY_VARS, "timezone": "auto"}
    try:
        data = _get_json(_FORECAST_URL, {**base, "start_date": start_date, "end_date": end_date})
        usable = data.get("daily", {}).get("temperature_2m_max")
    except urllib.error.HTTPError:
        # Out-of-range dates come back as HTTP 400 — fall through to the proxy.
        usable = None
    if not usable:
        data = _get_json(_FORECAST_URL, {**base, "forecast_days": 7})
    return data["daily"]


def _summary_bucket(mean_max_c: float) -> str:
    """Map a representative high temperature (°C) to a §4.3 coarse bucket."""
    if mean_max_c >= 30:
        return "hot"
    if mean_max_c >= 22:
        return "warm"
    if mean_max_c >= 12:
        return "mild"
    if mean_max_c >= 4:
        return "cold"
    return "freezing"


def _precip_label(max_prob: float) -> str:
    """Map the peak daily precipitation probability (%) to a §4.3 label."""
    if max_prob >= 60:
        return "likely"
    if max_prob >= 25:
        return "possible"
    return "none"


def _conditions(codes: list[int], max_prob: float, max_wind: float) -> list[str]:
    """Derive §4.3 notable conditions from weather codes + precip + wind."""
    code_set = set(codes)
    conds: list[str] = []
    if code_set & _DRIZZLE_RAIN or max_prob >= 60:
        conds.append("rain")
    if code_set & _SNOW:
        conds.append("snow")
    if max_wind >= 35:  # km/h
        conds.append("wind")
    if code_set & _CLEAR and max_prob < 40:
        conds.append("sun")
    return conds


@mcp.tool()
def get_weather(destination: str, start_date: str, end_date: str) -> dict:
    """Get the weather forecast for a destination over a date range.

    Args:
        destination: Free-text place name, e.g. "Reykjavik, Iceland".
        start_date: Trip start, ISO YYYY-MM-DD.
        end_date: Trip end, ISO YYYY-MM-DD.

    Returns:
        A §4.3 weather response: {destination, start_date, end_date, summary,
        temp_c_min, temp_c_max, precipitation, conditions[]} where summary is one
        of hot | warm | mild | cold | freezing.
    """
    # Neutral fallback so the packing list always generates even if Open-Meteo is
    # unreachable or the place can't be resolved — weather never hard-fails the run.
    result = {
        "destination": destination,
        "start_date": start_date,
        "end_date": end_date,
        "summary": "mild",
        "temp_c_min": 12,
        "temp_c_max": 20,
        "precipitation": "none",
        "conditions": [],
    }

    try:
        coords = _geocode(destination)
        if coords is None:
            return result
        daily = _fetch_daily(coords[0], coords[1], start_date, end_date)

        highs = daily["temperature_2m_max"]
        lows = daily["temperature_2m_min"]
        probs = daily.get("precipitation_probability_max") or [0]
        codes = daily.get("weathercode") or []
        winds = daily.get("windspeed_10m_max") or [0]

        mean_max = sum(highs) / len(highs)
        max_prob = max(p for p in probs if p is not None) if any(p is not None for p in probs) else 0
        max_wind = max(w for w in winds if w is not None) if any(w is not None for w in winds) else 0

        result.update(
            {
                "summary": _summary_bucket(mean_max),
                "temp_c_min": round(min(lows)),
                "temp_c_max": round(max(highs)),
                "precipitation": _precip_label(max_prob),
                "conditions": _conditions([c for c in codes if c is not None], max_prob, max_wind),
            }
        )
    except Exception:
        # Swallow network/parse errors and keep the neutral fallback. We
        # deliberately do NOT log the payload (§6.3 — no sensitive data in logs;
        # there's none here, but the tool stays quiet by policy).
        return result

    return result


if __name__ == "__main__":
    mcp.run(transport="stdio")
