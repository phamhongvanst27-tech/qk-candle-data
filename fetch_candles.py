import os
import requests
import json
from datetime import datetime, timezone

SYMBOLS = [
   "EURUSD",
    "GBPUSD",
    "USDJPY",
    "USDCAD",
    "AUDUSD",
    "XAUUSD",
    "USOIL"
]

TIMEFRAMES = ["15min", "1h", "4h"]

API_KEY = os.environ["TWELVE_DATA_API_KEY"]


def ema(values, period):
    if len(values) < period:
        return None

    multiplier = 2 / (period + 1)
    result = sum(values[:period]) / period

    for value in values[period:]:
        result = (value - result) * multiplier + result

    return result


scan = {
    "version": datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S"),
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "total_symbols": len(SYMBOLS),
    "symbols": {}
}

for symbol in SYMBOLS:
    scan["symbols"][symbol] = {}

    for timeframe in TIMEFRAMES:
        url = "https://api.twelvedata.com/time_series"

        params = {
            "symbol": symbol[:3] + "/" + symbol[3:],
            "interval": timeframe,
            "outputsize": 250,
            "apikey": API_KEY
        }

        response = requests.get(url, params=params, timeout=30)
        result = response.json()

        if result.get("status") == "error" or "values" not in result:
            scan["symbols"][symbol][timeframe] = {
                "status": "error",
                "message": result.get("message", "No data")
            }
            continue

        candles = result["values"]
        candles.reverse()

        closes = [float(candle["close"]) for candle in candles]
        highs = [float(candle["high"]) for candle in candles]
        lows = [float(candle["low"]) for candle in candles]

        latest = candles[-1]

        scan["symbols"][symbol][timeframe] = {
            "status": "ok",
            "datetime": latest["datetime"],
            "open": float(latest["open"]),
            "high": float(latest["high"]),
            "low": float(latest["low"]),
            "close": float(latest["close"]),
            "ema50": ema(closes, 50),
            "ema200": ema(closes, 200),
            "recent_high_20": max(highs[-20:]),
            "recent_low_20": min(lows[-20:])
        }

with open("qk_scan.json", "w", encoding="utf-8") as f:
    json.dump(scan, f, ensure_ascii=False, indent=2)

print("QK SCAN DONE")
