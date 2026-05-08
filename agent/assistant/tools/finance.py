import httpx
from langchain_core.tools import tool

_HEADERS = {"User-Agent": "VoiceAgent/1.0", "Accept": "application/json"}
_TIMEOUT = 15


def _get(url: str) -> dict:
    try:
        with httpx.Client(timeout=_TIMEOUT, follow_redirects=True) as client:
            r = client.get(url, headers=_HEADERS)
            r.raise_for_status()
            return {"ok": True, "data": r.json()}
    except Exception as e:
        return {"ok": False, "error": str(e)}


@tool
def get_exchange_rate(base: str = "USD", targets: list[str] | None = None) -> dict:
    """Get current exchange rates between currencies.

    Args:
        base: Base currency code, e.g. "USD", "EUR", "GBP" (default: "USD").
        targets: Target currency codes (default: EUR, GBP, JPY, CAD, AUD, CNY, INR, CHF).

    Returns:
        dict with rates, timestamp, and source.
    """
    if targets is None:
        targets = ["EUR", "GBP", "JPY", "CAD", "AUD", "CNY", "INR", "CHF"]

    res = _get(f"https://api.exchangerate-api.com/v4/latest/{base.upper()}")
    if not res["ok"]:
        return {"error": res["error"]}

    data = res["data"]
    if not isinstance(data, dict):
        return {"error": f"Invalid API response structure: expected dict, got {type(data).__name__}"}

    all_rates = data.get("rates")
    if not isinstance(all_rates, dict):
        return {"error": "API response missing 'rates' field or malformed"}

    filtered = {t: all_rates[t] for t in targets if t in all_rates}
    missing = [t for t in targets if t not in all_rates]

    result = {
        "base": base.upper(),
        "rates": filtered,
        "date": data.get("date"),
        "source": "exchangerate-api.com (v4 free)",
        "note": "Rates are mid-market — local exchange bureaus may differ.",
    }
    if missing:
        result["not_found"] = missing

    return result
