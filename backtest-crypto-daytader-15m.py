import pandas as pd
import openai
import matplotlib.pyplot as plt
import numpy as np
from datetime import datetime, timedelta
import pytz
import os
import time

# region parameters
# ====== 配置部分 =======
openai.api_key = os.getenv("OPEN_AI_API_KEY")

DATA_DIR = "./data/"  # 放置日線/小時線/15分鐘線的資料夾
RESULT_DIR = "./backtest_results/"
os.makedirs(RESULT_DIR, exist_ok=True)

START_DATE = datetime.strptime("2024-01-01", "%Y-%m-%d")
END_DATE = datetime.strptime("2024-06-30", "%Y-%m-%d")

TRADING_START_HOUR = 20  # UTC+8
TRADING_END_HOUR = 5

capital = 10000  # 初始資金
position = 0     # 持倉量
entry_price = 0
balance_history = [capital]
log_lines = []
# endregion

# ====== 工具函數 =======
def load_data():
    day_df = pd.read_csv(os.path.join(os.getcwd(), DATA_DIR, "BTCUSDT_1d.csv"), parse_dates=['timestamp'])
    week_df = pd.read_csv(os.path.join(DATA_DIR, "BTCUSDT_1w.csv"), parse_dates=['timestamp'])
    hour_df = pd.read_csv(os.path.join(DATA_DIR, "BTCUSDT_1h.csv"), parse_dates=['timestamp'])
    min15_df = pd.read_csv(os.path.join(DATA_DIR, "BTCUSDT_15m.csv"), parse_dates=['timestamp'])
    return day_df, week_df, hour_df, min15_df

def ask_gpt4(trend_context, now_price):
    prompt = f"""
你是專業的比特幣當沖操盤手，請依據以下資料判斷現在是否為進場或出場的好時機：

【周線、日線、4小時線、15分鐘線資訊】:
{trend_context}

【當前價格】:{now_price}

請回答：
1. 建議操作：（買入/賣出/持有/觀望）
2. 主要原因（人類能理解的走勢邏輯）
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

def in_trading_session(ts):
    local_time = ts.tz_convert('Asia/Taipei')
    if TRADING_START_HOUR <= local_time.hour or local_time.hour < TRADING_END_HOUR:
        return True
    return False

if __name__ == "__main__":
    # ====== 主程式 =======
    day_df, week_df, hour_df, min15_df = load_data()

    min15_df['timestamp'] = pd.to_datetime(min15_df['timestamp']).dt.tz_localize('UTC')
    hour_df['timestamp'] = pd.to_datetime(hour_df['timestamp']).dt.tz_localize('UTC')
    day_df['timestamp'] = pd.to_datetime(day_df['timestamp']).dt.tz_localize('UTC')
    week_df['timestamp'] = pd.to_datetime(week_df['timestamp']).dt.tz_localize('UTC')

    min15_df = min15_df.set_index('timestamp')

    for ts, row in min15_df.iterrows():
        if not (START_DATE.timestamp() <= ts.value/1000**3 <= END_DATE.timestamp()):
            continue
        if not in_trading_session(ts):
            continue
        
        now_price = row['close']

        # 取出走勢背景
        week_data = week_df[week_df['timestamp'] <= ts].tail(26) # 半年周線
        day_data = day_df[day_df['timestamp'] <= ts].tail(180)   # 半年日線
        hour_data = hour_df[hour_df['timestamp'] <= ts].tail(100) # 本周小時線
        min15_data = min15_df[min15_df.index <= ts].tail(96)     # 當日15分鐘線

        trend_context = f"周線資料:{week_data.to_dict()}\n日線資料:{day_data.to_dict()}\n小時線資料:{hour_data.to_dict()}\n15分鐘資料:{min15_data.to_dict()}"

        # 問 GPT-4 目前策略
        gpt_answer = ask_gpt4(trend_context, now_price)
        if gpt_answer is None:
            continue
        
        print(ts.strftime("%Y-%m-%d %H:%M:%S"), gpt_answer)
        # 解析指令
        action = None
        reason = ""

        if "買入" in gpt_answer:
            action = "buy"
        elif "賣出" in gpt_answer:
            action = "sell"
        else:
            action = "hold"

        reason = gpt_answer

        # 模擬交易邏輯
        if action == "buy" and position == 0:
            position = capital / now_price
            entry_price = now_price
            log_lines.append(f"{ts} - 買入 - 價格: {now_price:.2f} - {reason}")

        elif action == "sell" and position > 0:
            capital = position * now_price
            position = 0
            log_lines.append(f"{ts} - 賣出 - 價格: {now_price:.2f} - {reason}")

        balance = capital if position == 0 else position * now_price
        balance_history.append(balance)
        time.sleep(30) # to avoid openai api rate limit

    # ====== 儲存與分析 =======
    # 交易日誌
    with open(os.path.join(RESULT_DIR, "trading_log.txt"), "w", encoding="utf-8") as f:
        for line in log_lines:
            f.write(line + "\n")

    # 資金曲線
    pd.DataFrame({'equity': balance_history}).to_csv(os.path.join(RESULT_DIR, "equity_curve.csv"))

    # 畫圖
    plt.plot(balance_history)
    plt.title('Equity Curve')
    plt.xlabel('Trade Steps')
    plt.ylabel('Balance')
    plt.grid()
    plt.savefig(os.path.join(RESULT_DIR, "equity_curve.png"))
    plt.show()

    # 計算夏普比率
    returns = np.diff(balance_history) / balance_history[:-1]
    sharpe_ratio = np.mean(returns) / np.std(returns) * np.sqrt(252 * 6.5 * 4)  # 每天交易約6.5小時、每小時4根15分K
    print(f"夏普比率(Sharpe Ratio): {sharpe_ratio:.2f}")
