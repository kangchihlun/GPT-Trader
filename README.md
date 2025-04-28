# CryptoDayTrader

## 專案簡介

本專案是一套基於 Binance 歷史 K 線數據與 GPT-4 策略判斷的比特幣當沖回測系統。  
包含兩大功能：
- 自動下載 BTCUSDT 多週期歷史 K 線數據
- 以 GPT-4 模擬交易決策，進行回測並產生資金曲線與交易日誌

---

## 環境需求

- Python 3.8+
- 依賴套件：
  - pandas
  - numpy
  - matplotlib
  - openai
  - python-binance
  - pytz

安裝依賴：
```bash
pip install pandas numpy matplotlib openai python-binance pytz
```

---

## 使用步驟

### 1. 下載歷史數據

執行 `data_downloader.py`，自動下載 BTCUSDT 的 1週、1日、1小時、15分鐘 K 線數據，並儲存於 `./data/` 資料夾。

```bash
python data_downloader.py
```

> 預設會下載自 2022-01-01 至今的資料。  
> 若需更改下載區間，請修改 `START_DATE` 與 `END_DATE`。

### 2. 設定 OpenAI API 金鑰

請將你的 OpenAI API 金鑰寫入 `.env` 檔案或設定環境變數 `OPEN_AI_API_KEY`。

### 3. 執行回測

執行主回測腳本：

```bash
python backtest-crypto-dayytader.py
```

- 回測期間預設為 2024-01-01 ~ 2024-06-30
- 交易時段為台北時間每日 20:00 ~ 次日 05:00
- 初始資金 10,000 USDT

---

## 輸出結果

![](image/photo_2025-04-28_10-02-06.jpg)



回測結束後，結果將儲存於 `./backtest_results/` 資料夾：

- `trading_log.txt`：每筆交易的時間、價格、GPT-4 回答與理由
- `equity_curve.csv`：資金曲線數據
- `equity_curve.png`：資金曲線圖
- 終端機會顯示夏普比率（Sharpe Ratio）

---

## 注意事項

- `data_downloader.py` 內建 Binance API Key，建議更換為你自己的金鑰。
- 回測腳本會頻繁呼叫 OpenAI GPT-4 API，請注意 API 費用與速率限制。
- 若需更改回測參數（如資金、期間、交易時段），請直接修改 `backtest-crypto-dayytader.py` 內對應變數。

---

如需更詳細的說明或遇到問題，歡迎提 issue！
