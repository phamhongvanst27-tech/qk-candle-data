import os
import requests
import json
from datetime import datetime, timezone

ALL_SYMBOLS = [
    "EURUSD",
    "GBPUSD",
    "USDJPY",
    "XAUUSD"
]

TIMEFRAMES = ["15min", "1h", "4h"]

SYMBOLS_PER_RUN = 2

API_KEY = os.environ["TWELVE_DATA_API_KEY"]


def ema(values, period):
    if len(values) < period:
        return None

    multiplier = 2 / (period + 1)
    result = sum(values[:period]) / period

    for value in values[period:]:
        result = (value - result) * multiplier + result

    return result


def get_api_symbol(symbol):
    # Forex
    if symbol != "XAUUSD":
        return symbol[:3] + "/" + symbol[3:]

    # Gold
    return "XAU/USD"


# Đọc dữ liệu cũ
try:
    with open("qk_scan.json", "r", encoding="utf-8") as f:
        old_scan = json.load(f)
        all_symbols_data = old_scan.get("symbols", {})
except (FileNotFoundError, json.JSONDecodeError):
    all_symbols_data = {}


# Chọn các cặp cần quét:
# 1. Ưu tiên cặp chưa có dữ liệu
# 2. Sau đó chọn cặp có updated_at cũ nhất

symbol_times = []

for symbol in ALL_SYMBOLS:

    symbol_data = all_symbols_data.get(symbol)

    if not symbol_data:
        symbol_times.append(
            (datetime.min.replace(tzinfo=timezone.utc), symbol)
        )
        continue

    updated_at = symbol_data.get("updated_at")

    try:
        update_time = datetime.fromisoformat(updated_at)
    except (ValueError, TypeError):
        update_time = datetime.min.replace(tzinfo=timezone.utc)

    symbol_times.append((update_time, symbol))


symbol_times.sort(key=lambda x: x[0])

symbols_to_scan = [
    symbol
    for _, symbol in symbol_times[:SYMBOLS_PER_RUN]
]


print("SCANNING:", symbols_to_scan)


# Quét lần lượt 2 cặp
for symbol_to_scan in symbols_to_scan:

    symbol_data = {}

    for timeframe in TIMEFRAMES:

        url = "https://api.twelvedata.com/time_series"

        params = {
            "symbol": get_api_symbol(symbol_to_scan),
            "interval": timeframe,
            "outputsize": 250,
            "apikey": API_KEY
        }

        try:
            response = requests.get(
                url,
                params=params,
                timeout=30
            )

            response.raise_for_status()

            result = response.json()

        except Exception as e:

            symbol_data[timeframe] = {
                "status": "error",
                "message": str(e)
            }

            continue


        if result.get("status") == "error" or "values" not in result:

            symbol_data[timeframe] = {
                "status": "error",
                "message": result.get("message", "No data")
            }

            continue


        candles = result["values"]
        candles.reverse()

        closes = [
            float(candle["close"])
            for candle in candles
        ]

        highs = [
            float(candle["high"])
            for candle in candles
        ]

        lows = [
            float(candle["low"])
            for candle in candles
        ]

        latest = candles[-1]

        symbol_data[timeframe] = {
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


    # Chỉ cập nhật thời gian sau khi quét xong cặp
    symbol_data["updated_at"] = datetime.now(
        timezone.utc
    ).isoformat()


    # Giữ dữ liệu cũ của các cặp khác
    # Chỉ thay cặp vừa quét
    all_symbols_data[symbol_to_scan] = symbol_data


# Tạo JSON mới
now = datetime.now(timezone.utc)

scan = {
    "version": now.strftime("%Y%m%d%H%M%S"),
    "updated_at": now.isoformat(),
    "total_symbols": len(all_symbols_data),
    "symbols": all_symbols_data
}


# Ghi file
with open(
    "qk_scan.json",
    "w",
    encoding="utf-8"
) as f:

    json.dump(
        scan,
        f,
        ensure_ascii=False,
        indent=2
    )


print(
    "QK SCAN DONE:",
    symbols_to_scan,
    "TOTAL:",
    len(all_symbols_data)
)
