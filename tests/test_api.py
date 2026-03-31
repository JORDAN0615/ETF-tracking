from app.repositories import (
    get_diffs,
    get_latest_crawl_run,
    get_snapshot,
    save_diffs,
    save_snapshot,
)
from app.models import Holding
from app.services.diff import build_diffs
import app.services.ingest as ingest_service
from app.services.ingest import ingest_latest_snapshot


def test_api_returns_holdings_and_diffs(client) -> None:
    previous = [
        Holding("2330", "台積電", "stock", 1000, 10.0),
        Holding("2454", "聯發科", "stock", 700, 7.0),
    ]
    current = [
        Holding("2330", "台積電", "stock", 1200, 12.0),
        Holding("2317", "鴻海", "stock", 600, 6.0),
    ]

    save_snapshot("00980A", "2026-03-27", previous)
    save_snapshot("00980A", "2026-03-28", current)
    save_diffs("00980A", "2026-03-28", build_diffs(previous, current))

    holdings_response = client.get("/etfs/00980A/holdings", params={"date": "2026-03-28"})
    assert holdings_response.status_code == 200
    assert len(holdings_response.json()["holdings"]) == 2
    assert holdings_response.json()["fetched_at"] is not None
    assert holdings_response.json()["holdings"][0]["quantity_lots"] == 1.2

    diffs_response = client.get("/etfs/00980A/diffs", params={"date": "2026-03-28"})
    assert diffs_response.status_code == 200
    diffs = diffs_response.json()["diffs"]
    assert {item["change_type"] for item in diffs} == {"add", "increase", "remove"}
    assert diffs[0]["quantity_delta_lots"] is not None


def test_list_etfs_includes_seeded_sources(client) -> None:
    response = client.get("/etfs")
    assert response.status_code == 200
    payload = response.json()
    tickers = {item["ticker"] for item in payload}
    assert {"00980A", "00981A", "00987A", "00991A", "00992A"} <= tickers
    assert "00994A" not in tickers
    assert "latest_fetched_at" in payload[0]
    assert "last_run_status" in payload[0]


def test_first_snapshot_has_no_diff_error(client) -> None:
    save_snapshot(
        "00980A",
        "2026-03-28",
        [Holding("2330", "台積電", "stock", 1000, 10.0)],
    )

    response = client.get("/etfs/00980A/diffs", params={"date": "2026-03-28"})
    assert response.status_code == 200
    assert response.json()["diffs"] == []


def test_index_shows_stale_message_and_unknown_fetched_at_for_old_data(client) -> None:
    save_snapshot(
        "00980A",
        "2026-02-28",
        [Holding("2330", "台積電", "stock", 1000, 10.0)],
        fetched_at=None,
    )

    response = client.get("/")
    assert response.status_code == 200
    html = response.text
    assert "資料日期：" in html
    assert "最後抓取時間：" in html
    assert "資料尚未更新，最新資料日期為 2026-02-28" in html


def test_detail_page_shows_all_diff_columns(client) -> None:
    previous = [Holding("2330", "台積電", "stock", 1000, 10.0)]
    current = [Holding("2330", "台積電", "stock", 1200, 12.0)]
    save_snapshot("00980A", "2026-03-27", previous)
    save_snapshot("00980A", "2026-03-28", current)
    save_diffs("00980A", "2026-03-28", build_diffs(previous, current))

    response = client.get("/etfs/00980A")
    assert response.status_code == 200
    html = response.text
    assert "張數變動" in html
    assert "張數變動 %" in html
    assert "+0.2 張" in html
    assert "權重變動 %" in html
    assert "目前權重" in html
    assert "台灣主動式 ETF 追蹤系統試作版" not in html


def test_index_and_detail_do_not_show_removed_00994a(client) -> None:
    index_response = client.get("/")
    assert index_response.status_code == 200
    assert "00994A" not in index_response.text

    response = client.get("/etfs/00994A")
    assert response.status_code == 404


def test_same_day_refresh_replaces_snapshot_atomically(monkeypatch) -> None:
    class StubAdapter:
        def fetch(self, source_url, source_config):
            return {"ok": True}

        def parse(self, raw_data, source_config):
            return (
                "2026-03-28",
                [
                    Holding("2330", "台積電", "stock", 1300, 13.0),
                    Holding("2317", "鴻海", "stock", 600, 6.0),
                ],
            )

    previous = [Holding("2330", "台積電", "stock", 1000, 10.0)]
    current = [Holding("2330", "台積電", "stock", 1200, 12.0)]
    save_snapshot("00980A", "2026-03-27", previous)
    save_snapshot("00980A", "2026-03-28", current)
    save_diffs("00980A", "2026-03-28", build_diffs(previous, current))

    monkeypatch.setattr(ingest_service, "get_adapter", lambda source_type: StubAdapter())
    result = ingest_latest_snapshot("00980A")

    assert result["status"] == "success"
    latest_holdings = [row["instrument_key"] for row in get_snapshot("00980A", "2026-03-28")]
    assert latest_holdings == ["2330", "2317"]
    assert len(get_diffs("00980A", "2026-03-28")) == 2


def test_failed_refresh_keeps_existing_snapshot_and_records_failure(monkeypatch) -> None:
    class BrokenAdapter:
        def fetch(self, source_url, source_config):
            raise RuntimeError("source timeout")

    previous = [Holding("2330", "台積電", "stock", 1000, 10.0)]
    current = [Holding("2330", "台積電", "stock", 1200, 12.0)]
    save_snapshot("00980A", "2026-03-27", previous)
    save_snapshot("00980A", "2026-03-28", current)
    save_diffs("00980A", "2026-03-28", build_diffs(previous, current))

    monkeypatch.setattr(ingest_service, "get_adapter", lambda source_type: BrokenAdapter())
    result = ingest_latest_snapshot("00980A")

    assert result["status"] == "failed"
    assert len(get_snapshot("00980A", "2026-03-28")) == 1
    assert get_diffs("00980A", "2026-03-28")[0]["instrument_key"] == "2330"
    latest_run = get_latest_crawl_run("00980A")
    assert latest_run["status"] == "failed"
    assert latest_run["error_message"] == "source timeout"
