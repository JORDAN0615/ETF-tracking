from __future__ import annotations

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.db import init_db
from app.main import app
from app.repositories import seed_default_data


@pytest.fixture(autouse=True)
def clean_db(tmp_path) -> None:
    db_path = tmp_path / "test_etf_tracking.db"
    previous = os.environ.get("ETF_TRACKING_DB_PATH")
    previous_scheduler = os.environ.get("ETF_TRACKING_DISABLE_SCHEDULER")
    os.environ["ETF_TRACKING_DB_PATH"] = str(db_path)
    os.environ["ETF_TRACKING_DISABLE_SCHEDULER"] = "1"
    init_db()
    seed_default_data()
    yield
    if previous is None:
        os.environ.pop("ETF_TRACKING_DB_PATH", None)
    else:
        os.environ["ETF_TRACKING_DB_PATH"] = previous
    if previous_scheduler is None:
        os.environ.pop("ETF_TRACKING_DISABLE_SCHEDULER", None)
    else:
        os.environ["ETF_TRACKING_DISABLE_SCHEDULER"] = previous_scheduler


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def fixtures_dir() -> Path:
    return Path(__file__).resolve().parent / "fixtures"
