import shutil
import socket
import hashlib

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.data_store import CROP_FILE, DAILY_FILE, LOCATION_FILE, DataStore
from app.main import create_app
from tests.test_explore import selection


def test_downloaded_files_match_the_original_manifest(client):
    root = client.app.state.store.root
    for line in (root / "checksums.sha256").read_text().splitlines():
        expected, name = line.split("  ", 1)
        assert hashlib.sha256((root / name).read_bytes()).hexdigest() == expected, name


@pytest.mark.parametrize("problem", ["duplicate", "negative_rain", "temperature_order", "infinity", "bad_crop_flag"])
def test_invalid_source_data_fails_startup(client, tmp_path, problem):
    original = client.app.state.store.root
    for name in [DAILY_FILE, LOCATION_FILE, CROP_FILE]:
        destination = tmp_path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original / name, destination)
    frame = pd.read_csv(tmp_path / DAILY_FILE)
    if problem == "duplicate":
        frame = pd.concat([frame, frame.iloc[:1]])
    elif problem == "negative_rain":
        frame.loc[0, "rainfall_mm"] = -1
    elif problem == "temperature_order":
        frame.loc[0, "temperature_mean_c"] = 999
    elif problem == "infinity":
        frame.loc[0, "rainfall_mm"] = float("inf")
    else:
        crops = pd.read_csv(tmp_path / CROP_FILE, dtype={"local_variety_validated": "string"})
        crops.loc[0, "local_variety_validated"] = "maybe"
        crops.to_csv(tmp_path / CROP_FILE, index=False)
    frame.to_csv(tmp_path / DAILY_FILE, index=False)
    with pytest.raises(ValueError):
        DataStore(tmp_path)


def test_malformed_optional_map_does_not_block_data(client, tmp_path):
    original = client.app.state.store.root
    for name in [DAILY_FILE, LOCATION_FILE, CROP_FILE, "inputs/maps/gaez_maize_map_legend.csv"]:
        destination = tmp_path / name
        destination.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(original / name, destination)
    (tmp_path / "inputs/maps/gaez_map_metadata.json").write_text("not JSON")
    store = DataStore(tmp_path)
    assert store.map_layers == []
    assert any(w.code == "map_unavailable" for w in store.warnings())


def test_startup_exploration_and_export_need_no_network(client, monkeypatch):
    def no_connection(*args, **kwargs):
        raise AssertionError("The local-data backend attempted a network connection")

    monkeypatch.setattr(socket, "create_connection", no_connection)
    monkeypatch.setattr(socket.socket, "connect", no_connection)
    settings = Settings.from_environment()
    with TestClient(create_app(settings)) as offline_client:
        assert offline_client.get("/health").status_code == 200
        body = selection(categories=["rainfall"])
        assert offline_client.post("/api/v1/explore", json=body).status_code == 200
        report = offline_client.post("/api/v1/exports/pdf", json={"exploration": body})
        assert report.status_code == 200
        assert report.content.startswith(b"%PDF-")
