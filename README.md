# Taiwan Active ETF Tracker Prototype

最小可驗證概念版本，目標是追蹤 1 檔台灣主動式 ETF 的公開持股資料，存成每日 snapshot，並比較前後日差異。
目前已將資料來源抽成 adapter，依投信官方來源分流抓取與解析。

## Setup

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

## API

- `GET /etfs`
- `POST /etfs/{ticker}/fetch`
- `POST /refresh`
- `POST /etfs/{ticker}/refresh`
- `GET /etfs/{ticker}`
- `GET /etfs/{ticker}/holdings?date=YYYY-MM-DD`
- `GET /etfs/{ticker}/diffs?date=YYYY-MM-DD`

## Source Adapter

- `nomura_etfweb`: 野村官方 `Fund/GetFundAssets` API
- `unified_ezmoney`: 統一投信 ETF 頁面內嵌 `DataAsset` 資料
- `fhtrust_etf_html`: 復華投信 ETF 詳情頁的官方持股表
- `tsit_etf_detail`: 台新投信 ETF 詳情頁的官方持股表
- `capital_portfolio`: 群益投信 ETF `portfolio` 頁的官方持股表

首頁會顯示 ETF 名稱、資料日期、最後成功抓取時間、最近一次抓取狀態，以及依公開持股差異推估出的新增 / 加碼 / 減碼 / 剔除清單。
