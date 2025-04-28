import os
import time
import pandas as pd
import openai
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
import pytz

# ====== 配置 =======
openai.api_key = "你的 OpenAI API KEY"

DATA_DIR = "./btc_data/"
RESULT_DIR = "./backtest_asia/"
os.makedirs(RESULT_DIR, exist_ok=True)

START_DATE = "2024-01-01"
END_DATE = "2024-06-30"

capital = 10000  # 初始資金
position = 0
entry_price = 0
balance_history = [capital]
log_lines = []

# 每日亞洲交易時段 UTC+8
TRADING_START_HOUR = 6
TRADING_END_HOUR = 21

# ====== 工具函數 =======
def load_data():
    day_df = pd.read_csv(os.path.join(DATA_DIR, "BTCUSDT_1d.csv"), parse_dates=['timestamp'])
    week_df = pd.read_csv(os.path.join(DATA_DIR, "BTCUSDT_1w.csv"), parse_dates=['timestamp'])
    hour_df = pd.read_csv(os.path.join(DATA_DIR, "BTCUSDT_1h.csv"), parse_dates=['timestamp'])
    return day_df, week_df, hour_df

def ask_gpt4(trend_context, now_price):
    prompt = f"""
你是頂級的比特幣短線交易員。
請根據以下走勢資料，針對今天亞洲時段（UTC+8的6點到21點）給出交易規劃：

【周線、日線、小時線資料】:
{trend_context}

【當前價格】:{now_price}

請輸出：
1. 今日大方向（偏多/偏空/盤整）
2. 關鍵支撐位置
3. 關鍵壓力位置
4. 進場策略（例如：回踩支撐站穩做多 / 突破壓力回踩站穩做多）
5. 思考邏輯（為什麼這樣設定）
"""
    try:
        response = openai.ChatCompletion.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0
        )
        return response['choices'][0]['message']['content']
    except Exception as e:
        print(f"OpenAI API error: {e}")
        return None

def in_asia_session(ts):
    local_time = ts.tz_convert('Asia/Taipei')
    return TRADING_START_HOUR <= local_time.hour < TRADING_END_HOUR

def parse_strategy(gpt_text):
    direction = "none"
    support = None
    resistance = None

    if "偏多" in gpt_text:
        direction = "long"
    elif "偏空" in gpt_text:
        direction = "short"

    # 嘗試抽取支撐/壓力數字
    import re
    support_match = re.search(r'支撐.*?(\d{4,6})', gpt_text)
    resistance_match = re.search(r'壓力.*?(\d{4,6})', gpt_text)

    if support_match:
        support = float(support_match.group(1))
    if resistance_match:
        resistance = float(resistance_match.group(1))

    return direction, support, resistance

# ====== 主程式 =======
day_df, week_df, hour_df = load_data()

day_df['timestamp'] = pd.to_datetime(day_df['timestamp']).dt.tz_localize('UTC')
week_df['timestamp'] = pd.to_datetime(week_df['timestamp']).dt.tz_localize('UTC')
hour_df['timestamp'] = pd.to_datetime(hour_df['timestamp']).dt.tz_localize('UTC')
hour_df = hour_df.set_index('timestamp')

direction = "none"
support = None
resistance = None

for ts, row in hour_df.iterrows():
    if not (START_DATE <= ts.strftime("%Y-%m-%d") <= END_DATE):
        continue
    if not in_asia_session(ts):
        continue

    now_price = row['close']

    # 每天6:00 重新規劃今日交易計畫
    local_time = ts.tz_convert('Asia/Taipei')
    if local_time.hour == 6 and local_time.minute == 0:
        week_data = week_df[week_df['timestamp'] <= ts].tail(26)
        day_data = day_df[day_df['timestamp'] <= ts].tail(180)
        hour_data = hour_df[hour_df.index <= ts].tail(48)

        trend_context = f"周線資料:{week_data.to_dict()}\n日線資料:{day_data.to_dict()}\n小時線資料:{hour_data.to_dict()}"

        gpt_answer = ask_gpt4(trend_context, now_price)
        if gpt_answer:
            direction, support, resistance = parse_strategy(gpt_answer)
            log_lines.append(f"{ts} - 今日盤勢規劃:\n{gpt_answer}\n")
        else:
            direction, support, resistance = "none", None, None

    # ====== 交易邏輯 ======
    # 做多邏輯
    if direction == "long" and support and now_price < support * 1.005 and position == 0:
        position = capital / now_price
        entry_price = now_price
        log_lines.append(f"{ts} - 買入 - 價格: {now_price:.2f}")

    # 做空邏輯
    elif direction == "short" and resistance and now_price > resistance * 0.995 and position == 0:
        position = -capital / now_price
        entry_price = now_price
        log_lines.append(f"{ts} - 賣出 - 價格: {now_price:.2f}")

    # 平倉條件 (收盤時強制平倉)
    if local_time.hour == 20 and local_time.minute == 0:
        if position != 0:
            capital += position * now_price
            log_lines.append(f"{ts} - 平倉 - 價格: {now_price:.2f}")
            position = 0

    # 更新帳戶資金
    balance = capital if position == 0 else capital + position * (now_price - entry_price)
    balance_history.append(balance)

# ====== 儲存與分析 =======
with open(os.path.join(RESULT_DIR, "trading_log.txt"), "w", encoding="utf-8") as f:
    for line in log_lines:
        f.write(line + "\n")

pd.DataFrame({'equity': balance_history}).to_csv(os.path.join(RESULT_DIR, "equity_curve.csv"))

# 畫資金曲線
plt.plot(balance_history)
plt.title('Equity Curve - Asia Session')
plt.xlabel('Steps')
plt.ylabel('Balance')
plt.grid()
plt.savefig(os.path.join(RESULT_DIR, "equity_curve.png"))
plt.show()

# 計算夏普比率
returns = np.diff(balance_history) / balance_history[:-1]
sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252 * 10)  # 亞洲時段每天大約10根1hK
print(f"夏普比率(Sharpe Ratio): {sharpe_ratio:.2f}")
