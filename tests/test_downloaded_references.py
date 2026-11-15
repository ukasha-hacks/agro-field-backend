import copy
import hashlib
import json

import pytest

from app.rotation_schemas import RotationRequest
from app.services.rotations import compare_rotations
from tests.test_rotations import rotation_body


def test_downloaded_crop_sheets_match_their_manifest(client):
    root = client.app.state.store.root / "supplemental"
    manifest = json.loads((root / "crop_download_manifest.json").read_text())
    for source in manifest["sources"]:
        assert source["url"].startswith("https://ecocrop.apps.fao.org/")
        assert hashlib.sha256((root / source["local_file"]).read_bytes()).hexdigest() == source["sha256"]


def test_soil_extract_matches_real_selected_database_rows(client):
    root = client.app.state.store.root / "supplemental"
    selected = json.loads((root / "soil_selected_rows.json").read_text())
    for record in selected:
        point, row = record["point"], record["database_row"]
        location = client.app.state.store.location(point["sample_id"])
        soil = location.soil_reference
        assert soil.ph == round(row["PH_WATER"], 2)
        assert (soil.latitude, soil.longitude) == (location.latitude, location.longitude)
        assert soil.mapping_unit_id == row["HWSD2_SMU_ID"]
        assert soil.component_share_percent == row["SHARE"]
        assert soil.depth_cm == (row["TOPDEP"], row["BOTDEP"]) == (0, 20)
    assert any(source["source_id"] == "fao_hwsd" for source in client.get('/api/v1/metadata').json()['sources'])


@pytest.mark.parametrize("crop", ["maize", "beans", "groundnut", "sorghum", "cotton", "coffee_arabica", "coffee_robusta", "sugarcane", "vanilla", "banana"])
def test_every_catalog_crop_gets_real_reference_coverage_and_a_conclusion(client, crop):
    body = rotation_body()
    for season in body["baseline_sequence"]:
        season["crops"] = [crop]
    result = client.post("/api/v1/rotation-comparisons", json=body).json()
    checks = {item["criterion"]: item for item in result["baseline"]["checks"]}
    assert checks["reference_rule_coverage"]["status"] == "pass"
    assert checks[f"{crop}_soil_ph"]["status"] == "pass"
    assert checks[f"{crop}_historical_temperature"]["status"] == "pass"
    assert checks["succession_evidence"]["status"] == "unknown"
    assert checks["succession_evidence"]["gap_type"] == "local_review"
    assert "agricultural_rule_coverage" not in checks
    assert result["conclusion"]["title"] and result["conclusion"]["detail"]
    if crop in {"coffee_arabica", "coffee_robusta", "sugarcane", "vanilla", "banana"}:
        assert result["status"] == "reference_only"
        assert result["alternatives"] == []
        assert result["conclusion"]["title"] == "Use a perennial growing plan"
        assert "checks passed" in result["conclusion"]["detail"]


def test_measured_ph_overrides_the_area_estimate(client):
    body = rotation_body()
    body["soil"]["ph"] = 4.2
    result = client.post("/api/v1/rotation-comparisons", json=body).json()
    item = next(c for c in result["baseline"]["checks"] if c["criterion"] == "maize_soil_ph")
    assert item["status"] == "fail" and "supplied pH is 4.2" in item["reason"]
    assert not any(source["source_id"] == "fao_hwsd" for source in result["sources"])


def test_area_estimate_can_be_disabled_and_missing_ph_is_a_farmer_input_gap(client):
    body = rotation_body()
    body["soil"]["use_area_estimate"] = False
    result = client.post("/api/v1/rotation-comparisons", json=body).json()
    item = next(c for c in result["baseline"]["checks"] if c["criterion"] == "maize_soil_ph")
    assert item["status"] == "unknown" and item["gap_type"] == "farmer_input"
    assert any("measured soil pH" in text for text in result["conclusion"]["next_steps"])


def test_uncertain_area_ph_does_not_reject_a_crop_as_if_it_was_measured(client):
    store = copy.copy(client.app.state.store)
    store.locations = dict(store.locations)
    original = store.locations["northern_gulu"]
    soil = original.soil_reference.model_copy(update={"ph": 4.2})
    store.locations[original.location_id] = original.model_copy(update={"soil_reference": soil})
    result = compare_rotations(store, RotationRequest(**rotation_body()))
    item = next(c for c in result.baseline.checks if c.criterion == "maize_soil_ph")
    assert item.status == "unknown" and "mapped soil estimate" in item.reason
    assert result.baseline.feasibility_status != "infeasible"


def test_cotton_uses_its_downloaded_minimum_cycle(client):
    body = rotation_body()
    body["baseline_sequence"][0].update(crops=["cotton"], planting_date="2027-03-01", harvest_date="2027-06-01")
    result = client.post("/api/v1/rotation-comparisons", json=body).json()
    item = next(c for c in result["baseline"]["checks"] if c["criterion"] == "cotton_minimum_cycle_days")
    assert item["status"] == "fail" and "150-200" in item["reason"]
    assert result["conclusion"]["tone"] == "attention"


def test_all_known_dates_make_timing_checks_real_instead_of_unconditionally_unknown(client):
    body = rotation_body()
    periods = [("2027-01-01", "2027-04-30"), ("2027-05-01", "2027-08-31"), ("2027-09-01", "2027-12-31")]
    for season, (start, end) in zip(body["baseline_sequence"], periods):
        season.update(planting_date=start, harvest_date=end)
    result = client.post("/api/v1/rotation-comparisons", json=body).json()
    checks = {item["criterion"]: item for item in result["baseline"]["checks"]}
    assert checks["calendar_overlap"]["status"] == "pass"
    assert checks["maize_minimum_cycle_days"]["status"] == "pass"
    assert not any("timing" in step for step in result["conclusion"]["next_steps"])
