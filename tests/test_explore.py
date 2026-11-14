import copy

import pandas as pd
import pytest

from app.schemas import ExploreRequest
from app.services.explore import explore


def selection(**changes):
    body = {
        "location_id": "northern_gulu", "start_date": "2024-01-01", "end_date": "2024-01-31",
        "categories": ["rainfall", "temperature", "soil_wetness"], "interval": "monthly",
    }
    return body | changes


def test_known_rainfall_and_leap_year(client):
    for start, end, days, rain in [
        ("2024-01-01", "2024-01-31", 31, 39.59),
        ("2024-02-01", "2024-02-29", 29, 77.54),
    ]:
        response = client.post("/api/v1/explore", json=selection(start_date=start, end_date=end))
        assert response.status_code == 200
        point = response.json()["panels"][0]["series"][0]["points"][0]
        assert point["value"] == pytest.approx(rain)
        assert point["expected_days"] == days
        assert point["partial_calendar_month"] is False


def test_partial_months_are_filtered_before_aggregation(client):
    body = selection(location_id="central_masaka", start_date="2024-03-15", end_date="2024-04-10")
    result = client.post("/api/v1/explore", json=body).json()
    points = result["panels"][0]["series"][0]["points"]
    assert [p["expected_days"] for p in points] == [17, 10]
    assert all(p["partial_calendar_month"] for p in points)
    assert sum(p["value"] for p in points) == pytest.approx(208.13)
    assert points[0]["period_start"] == "2024-03-15"
    assert points[1]["period_end"] == "2024-04-10"


@pytest.mark.parametrize("changes,status", [
    ({"location_id": "not-supported"}, 404),
    ({"start_date": "2026-01-01", "end_date": "2026-02-01"}, 422),
    ({"end_date": "2023-01-01"}, 422),
    ({"categories": ["rainfall", "rainfall"]}, 422),
    ({"categories": ["crop"]}, 422),
    ({"categories": []}, 422),
    ({"unexpected": True}, 422),
    ({"start_date": "2023-01-01", "end_date": "2024-12-31", "interval": "daily"}, 422),
])
def test_invalid_selections(client, changes, status):
    response = client.post("/api/v1/explore", json=selection(**changes))
    assert response.status_code == status
    assert "error" in response.json()


def test_missing_days_and_zero_rain_are_distinct(client):
    store = copy.copy(client.app.state.store)
    frame = store.daily.copy()
    location = frame["sample_id"].eq("northern_gulu")
    zero_day = frame["date"].eq(pd.Timestamp("2024-01-01")) & location
    absent_day = frame["date"].eq(pd.Timestamp("2024-01-02")) & location
    frame.loc[zero_day, "rainfall_mm"] = 0
    store.daily = frame.loc[~absent_day]
    request = ExploreRequest(**selection(interval="daily"))
    result = explore(store, request)
    points = result.panels[0].series[0].points
    assert len(points) == 31
    assert points[0].value == 0
    assert points[1].value is None
    assert points[1].valid_days == 0
    assert result.statistics[0].value is None
    assert result.statistics[0].valid_days == 30
    assert any(w.code == "incomplete_data" for w in result.warnings)


def test_statistics_are_daily_weighted_and_variable_specific(client):
    store = copy.copy(client.app.state.store)
    store.daily = store.daily.copy()
    rows = store.daily["sample_id"].eq("northern_gulu")
    dates = store.daily["date"].between("2024-01-01", "2024-02-29")
    jan = store.daily["date"].dt.month.eq(1)
    store.daily.loc[rows & dates & jan, "temperature_mean_c"] = 10
    store.daily.loc[rows & dates & ~jan, "temperature_mean_c"] = 20
    one_day = store.daily["date"].eq(pd.Timestamp("2024-01-10"))
    store.daily.loc[rows & one_day, "surface_soil_wetness"] = float("nan")
    result = explore(store, ExploreRequest(**selection(end_date="2024-02-29")))
    stats = {s.metric_id: s for s in result.statistics}
    assert stats["temperature_mean_c"].value == pytest.approx((31 * 10 + 29 * 20) / 60, abs=0.0001)
    assert stats["surface_soil_wetness_mean"].value is None
    assert stats["root_zone_soil_wetness_mean"].value is not None


def test_repeated_requests_do_not_mutate_source_data(client):
    before = client.app.state.store.daily.copy(deep=True)
    first = client.post("/api/v1/explore", json=selection()).json()
    second = client.post("/api/v1/explore", json=selection()).json()
    assert first == second
    pd.testing.assert_frame_equal(before, client.app.state.store.daily)
    assert first["selected_location_geojson"]["geometry"]["coordinates"] == [32.299, 2.774]
    assert all(d["evidence_ids"] for d in first["descriptions"])
