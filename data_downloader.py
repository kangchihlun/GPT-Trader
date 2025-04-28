import os
import time
import pandas as pd
import datetime
from binance import Client
from datetime import datetime

# ====== 配置區 =======
BINANCE_API_KEY = 'ah5EJSKZk1b6p2ywX5NNI0zrPeNiSBLm25gz63XEPnryD9VnLhH3j5BI5EQjGScT'
BINANCE_API_SECRET = 'WxvX45ImBEuZWJJznKdtDfYylAah92rUU1EguFULUEPlTpPna21geKshzj4yiCf7'
SYMBOL = "BTCUSDT"  # 你要下載的幣種
SAVE_DIR = "./data/"
os.makedirs(SAVE_DIR, exist_ok=True)

INTERVALS = {
    '1w': Client.KLINE_INTERVAL_1WEEK,
    '1d': Client.KLINE_INTERVAL_1DAY,
    '1h': Client.KLINE_INTERVAL_1HOUR,
    '15m': Client.KLINE_INTERVAL_15MINUTE
}

START_DATE = int(datetime.strptime("2022-01-01", "%Y-%m-%d").timestamp())*1000
END_DATE = int(datetime.now().timestamp())*1000

# ====== 初始化 Binance 客戶端 =======
client = Client(api_key=BINANCE_API_KEY, api_secret=BINANCE_API_SECRET)

# ====== 工具函數 =======
def download_klines(symbol, interval, start_str, end_str):
    print(f"開始下載 {symbol} {interval} K線...")
    all_klines = []
    while True:
        temp_klines = client.get_klines(symbol=symbol, interval=interval, startTime=start_str, endTime=end_str, limit=1000)
        if not temp_klines:
            break
        all_klines.extend(temp_klines)

        last_close_time = temp_klines[-1][6]  # 關閉時間 (結束時間戳，單位ms)
        start_str = last_close_time

        if len(temp_klines) < 1000:
            break
        time.sleep(0.5)  # 小小間隔避免 API 被限速
    return all_klines

def klines_to_df(klines):
    df = pd.DataFrame(klines, columns=[
        'open_time', 'open', 'high', 'low', 'close', 'volume',
        'close_time', 'quote_asset_volume', 'number_of_trades',
        'taker_buy_base', 'taker_buy_quote', 'ignore'
    ])
    df['timestamp'] = pd.to_datetime(df['open_time'], unit='ms')
    df = df[['timestamp', 'open', 'high', 'low', 'close', 'volume']]
    df = df.astype({'open':'float', 'high':'float', 'low':'float', 'close':'float', 'volume':'float'})
    return df

# ====== 主下載流程 =======
for label, interval in INTERVALS.items():
    klines = download_klines(SYMBOL, interval, START_DATE, END_DATE)
    df = klines_to_df(klines)
    save_path = os.path.join(SAVE_DIR, f"{SYMBOL}_{label}.csv")
    df.to_csv(save_path, index=False)
    print(f"✅ 已儲存到: {save_path}")

print("✨ 所有K線資料下載完成！")
