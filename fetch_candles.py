import os
import requests
import json
from datetime import datetime, timezone

SYMBOLS = [
    "EURUSD", "GBPUSD", "USDJPY", "USDCHF",
    "USDCAD", "AUDUSD", "NZDUSD", "EURGBP",
    "EURJPY", "GBPJPY", "AUDJPY", "CADJPY",
    "CHFJPY", "EURAUD", "GBPAUD", "EURCAD"
]

TIMEFRAMES = ["15min", "1h", "4h"]

API_KEY = os.environ["TWELVE_DATA_API_KEY"]

data = {
    "updated_at": datetime.now(timezone.utc).isoformat(),
    "symbols": {}
}

for symbol in SYMBOLS:
    data["symbols"][symbol] = {}

    for timeframe in TIMEFRAMES:
        url = "https://api.twelvedata.com/time_series"

        params = {
            "symbol": symbol,
            "interval": timeframe,
            "outputsize": 250,
            "apikey": API_KEY
        }

        response = requests.get(url, params=params)
        result = response.json()

        data["symbols"][symbol][timeframe] = result

with open("candles.json", "w", encoding="utf-8") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print("DONE")
