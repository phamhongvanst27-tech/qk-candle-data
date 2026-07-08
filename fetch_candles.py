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

API_KEY = os.environ["TWELVE_DATA_API_KEY"]


def ema(values, period):
    if len(values) < period:
        return None

    multiplier = 2 / (period + 1)
    result = sum(values[:period]) / period

    for value in values[period:]:
        result = (value - result) * multiplier + result

    return result


# Đọc dữ liệu cũ
try:
    with open("qk_scan.json", "r", encoding="utf-8") as f:
        old_scan = json.load(f)
        all_symbols_data = old_scan.get("symbols", {})
except (FileNotFoundError, json.JSONDecodeError):
    all_symbols_data = {}


# Tìm cặp chưa có dữ liệu
symbol_to_scan = None

for symbol in ALL_SYMBOLS:
    if symbol not in all_symbols_data:
        symbol_to_scan = symbol
        break


# Nếu đã đủ 4 cặp, tìm cặp có thời gian cập nhật cũ nhất
if symbol_to_scan is None:

    oldest_time = None

    for symbol in ALL_SYMBOLS:

        symbol_data = all_symbols_data.get(symbol, {})

        symbol_updated_at = symbol_data.get("updated_at")

        if symbol_updated_at is None:
            symbol_to_scan = symbol
            break

        try:
            update_time = datetime.fromisoformat(symbol_updated_at)
        except (ValueError, TypeError):
            symbol_to_scan = symbol
            break

        if oldest_time is None or update_time < oldest_time:
            oldest_time = update_time
            symbol_to_scan = symbol


print("SCANNING:", symbol_to_scan)


# Quét cặp được chọn
symbol_data = {}


for timeframe in TIMEFRAMES:

    url = "https://api.twelvedata.com/time_series"

    params = {
        "symbol": symbol_to_scan[:3] + "/" + symbol_to_scan[3:],
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


# Ghi thời gian cập nhật riêng cho từng cặp
symbol_data["updated_at"] = datetime.now(
    timezone.utc
).isoformat()


# Lưu cặp vừa quét vào dữ liệu chung
all_symbols_data[symbol_to_scan] = symbol_data


# Tạo file JSON mới
scan = {

    "version": datetime.now(
        timezone.utc
    ).strftime("%Y%m%d%H%M%S"),

    "updated_at": datetime.now(
        timezone.utc
    ).isoformat(),

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
    symbol_to_scan,
    "TOTAL:",
    len(all_symbols_data)
)
