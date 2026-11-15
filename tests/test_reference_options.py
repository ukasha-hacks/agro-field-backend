import copy

import pytest

from app.rotation_schemas import RotationRequest
from app.services.rotations import compare_rotations
from tests.test_rotations import rotation_body


def compare(client, body):
    return compare_rotations(client.app.state.store, RotationRequest(**body))


def test_ph_ranges_are_read_from_the_local_catalog(client):
    body = rotation_body()
    body["soil"]["ph"] = 4.2
    result = compare(client, body)
    assert result.baseline.feasibility_status == "infeasible"
    maize = next(c for c in client.app.state.store.crops if c.crop_id == "maize")
    check = next(c for c in result.baseline.checks if c.criterion == "maize_soil_ph")
    assert check.status == "fail" and check.source_url == maize.source_url
    assert f"{maize.soil_ph_absolute_min:g}-{maize.soil_ph_absolute_max:g}" in check.reason
    # Only beans has a broad pH range including 4.2; one crop cannot make two diverse options.
    assert result.alternatives == []


@pytest.mark.parametrize("ph, expected", [(4.5, "pass"), (8.5, "pass"), (8.6, "fail"), (None, "unknown")])
def test_species_ph_boundaries_and_missing_values(client, ph, expected):
    body = rotation_body()
    body["soil"]["ph"] = ph
    body["soil"]["use_area_estimate"] = False
    result = compare(client, body)
    assert next(c.status for c in result.baseline.checks if c.criterion == "maize_soil_ph") == expected


def test_a_short_planned_cycle_blocks_that_crop(client):
    body = rotation_body()
    body["baseline_sequence"][0].update(planting_date="2027-03-01", harvest_date="2027-04-29")
    result = compare(client, body)
    check = next(c for c in result.baseline.checks if c.criterion == "maize_minimum_cycle_days")
    assert check.status == "fail"  # 60 days, below the saved maize minimum of 65.
    for option in result.alternatives:
        assert option.sequence[0].crops == ["beans"]


def test_supported_mixture_can_explore_but_is_not_declared_valid(client):
    body = rotation_body()
    body["baseline_sequence"][0]["crops"] = ["groundnut", "beans"]
    body["baseline_sequence"][1]["crops"] = ["beans", "groundnut"]
    body["baseline_sequence"][2]["crops"] = ["maize"]
    result = compare(client, body)
    assert result.status == "reference_only" and len(result.alternatives) == 2
    assert result.baseline.sequence[0].crops == ["groundnut", "beans"]
    assert next(c.status for c in result.baseline.checks if c.criterion == "cropping_system") == "unknown"
    assert all(any("not advice to replace" in text for text in option.tradeoffs) for option in result.alternatives)


@pytest.mark.parametrize("crop", ["coffee", "unreferenced-banana", "cassava"])
def test_unreferenced_or_entirely_unknown_systems_are_not_replaced(client, crop):
    body = rotation_body()
    for season in body["baseline_sequence"]:
        season["crops"] = [crop]
    result = compare(client, body)
    assert result.status == "insufficient_evidence" and result.alternatives == []
    assert result.baseline.sequence[0].crops == [crop]


def test_preferences_exclusions_and_repeatable_selection(client):
    body = rotation_body()
    body.update(excluded_crops=["groundnut"], preferred_crops=["sorghum"])
    result = compare(client, body)
    assert result.alternatives
    assert "sorghum" in {crop for season in result.alternatives[0].sequence for crop in season.crops}
    assert all("groundnut" not in season.crops for option in result.alternatives for season in option.sequence)
    assert result.model_dump() == compare(client, body).model_dump()


def test_chart_topic_does_not_change_reference_screening(client):
    body = rotation_body()
    original = compare(client, body)
    body["exploration"]["categories"] = ["rainfall"]
    result = compare(client, body)
    assert result.alternatives == original.alternatives
    assert any(source.source_id == "nasa_power_merra2" for source in result.sources)


def test_missing_temperature_is_not_silently_averaged(client):
    store = copy.copy(client.app.state.store)
    store.daily = store.daily.copy()
    selected = (store.daily.sample_id == "northern_gulu") & (store.daily.date.dt.year == 2024)
    store.daily.loc[store.daily.index[selected][0], "temperature_mean_c"] = float("nan")
    body = rotation_body()
    body["soil"]["use_area_estimate"] = False
    result = compare_rotations(store, RotationRequest(**body))
    assert result.alternatives == []  # pH and dates also missing, so no positive range evidence.
    assert next(c.status for c in result.baseline.checks if c.criterion == "maize_historical_temperature") == "unknown"


def test_reference_checks_can_be_disabled_without_unlocking_reviewed_rules(client):
    store = copy.copy(client.app.state.store)
    store.rules = store.rules.model_copy(update={"reference_checks": []})
    result = compare_rotations(store, RotationRequest(**rotation_body()))
    assert result.status == "insufficient_evidence" and not result.alternatives
    assert store.rules.review_status == "pending" and store.rules.reviewed_rules() == []


def test_a_reference_pass_does_not_substitute_for_a_reviewed_rule_pass(client):
    store = copy.copy(client.app.state.store)
    rule = {
        "rule_id": "synthetic-ph", "description": "Synthetic reviewed pH rule",
        "criterion": "synthetic_ph", "kind": "soil_ph_range", "crops": ["maize", "beans", "groundnut", "sorghum"],
        "minimum": 5, "maximum": 8, "source_url": "https://example.invalid/fixture",
        "applicability": "Tests only", "review_status": "reviewed",
    }
    from app.rotation_schemas import RuleSet
    store.rules = RuleSet(version="fixture", review_status="reviewed", notes="Tests only",
                          reference_checks=["historical_temperature"], rules=[rule])
    result = compare_rotations(store, RotationRequest(**rotation_body()))
    assert any(c.status == "pass" and c.rule_id.startswith("reference:") for c in result.baseline.checks if c.rule_id)
    assert result.status == "insufficient_evidence" and not result.alternatives
