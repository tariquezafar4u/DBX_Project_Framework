"""OpenWeather API connector for the weather learning contract."""
from __future__ import annotations

import json
from datetime import datetime, timezone
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit, urlunsplit
from urllib.request import Request, urlopen

from dat_edip.contract_loader import DataContract


def fetch_weather_record(contract: DataContract, dbutils) -> dict:
    """Fetch one OpenWeather observation and map it to the contract columns."""
    source = contract.source
    if source.get("name") != "openweather":
        raise ValueError(
            f"Unsupported API source '{source.get('name')}' for product "
            f"'{contract.product_name}'"
        )
    if source.get("method", "GET").upper() != "GET":
        raise ValueError("OpenWeather connector supports GET requests only")

    auth = source.get("authentication", {})
    if auth.get("type") != "secret":
        raise ValueError("OpenWeather authentication must use a Databricks secret")
    scope = auth.get("scope")
    key = auth.get("key")
    if not scope or not key:
        raise ValueError("OpenWeather contract must define secret scope and key")

    api_key = dbutils.secrets.get(scope=scope, key=key)
    if not api_key:
        raise ValueError(f"Databricks secret '{scope}/{key}' is empty")

    endpoint = source.get("endpoint")
    if not endpoint:
        raise ValueError("OpenWeather contract must define an endpoint")
    params = dict(source.get("parameters", {}))
    params["appid"] = api_key
    parts = urlsplit(endpoint)
    query = "&".join(filter(None, (parts.query, urlencode(params))))
    request_url = urlunsplit((parts.scheme, parts.netloc, parts.path, query, parts.fragment))
    request = Request(request_url, headers={"Accept": "application/json"})

    try:
        with urlopen(request, timeout=30) as response:
            payload = json.load(response)
    except HTTPError as exc:
        raise RuntimeError(
            f"OpenWeather API returned HTTP {exc.code} {exc.reason}"
        ) from exc
    except URLError as exc:
        raise RuntimeError(f"Could not reach OpenWeather API: {exc.reason}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError("OpenWeather API returned invalid JSON") from exc

    if not isinstance(payload, dict):
        raise ValueError("OpenWeather API response must be a JSON object")
    if str(payload.get("cod", "200")) != "200":
        raise RuntimeError(
            f"OpenWeather API error {payload.get('cod')}: "
            f"{payload.get('message', 'unspecified error')}"
        )

    main = payload.get("main")
    weather_items = payload.get("weather")
    wind = payload.get("wind", {})
    if not isinstance(main, dict) or not isinstance(weather_items, list) or not weather_items:
        raise ValueError("OpenWeather response is missing main or weather data")
    weather = weather_items[0]
    if not isinstance(weather, dict) or not isinstance(wind, dict):
        raise ValueError("OpenWeather response contains malformed weather or wind data")
    timestamp = payload.get("dt")
    if timestamp is None:
        raise ValueError("OpenWeather response is missing observation timestamp")

    values = {
        "city": payload.get("name"),
        "temperature": main.get("temp"),
        "feels_like": main.get("feels_like"),
        "humidity": main.get("humidity"),
        "pressure": main.get("pressure"),
        "weather": weather.get("main"),
        "description": weather.get("description"),
        "wind_speed": wind.get("speed"),
        "observation_timestamp": datetime.fromtimestamp(
            int(timestamp), timezone.utc
        ).replace(tzinfo=None),
    }
    missing = [column for column in contract.column_names() if column not in values]
    if missing:
        raise ValueError(f"OpenWeather mapping does not define contract columns: {missing}")
    return {column: values[column] for column in contract.column_names()}
