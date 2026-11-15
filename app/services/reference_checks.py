"""Broad species checks from the supplied files, separate from reviewed agronomy."""

from app.rotation_schemas import CriterionCheck
from app.services.explore import aggregate, selected_days


def historical_temperature(store, exploration):
    days = selected_days(store, exploration)
    return aggregate(days["temperature_mean_c"], "mean")


def reference_check(crop, kind, status, reason):
    return CriterionCheck(
        criterion=f"{crop.crop_id}_{kind}", status=status, reason=reason,
        rule_id=f"reference:{crop.crop_id}:{kind}", source_url=crop.source_url,
        gap_type=("farmer_input" if kind in {"soil_ph", "minimum_cycle_days"} else "missing_observation") if status == "unknown" else None,
    )


def assess_references(store, request, sequence, mean_temperature):
    enabled = set(store.rules.reference_checks)
    crops = {name for season in sequence for name in season.crops}
    checks = []
    for crop in store.crops:
        if crop.crop_id not in crops:
            continue
        name = crop.crop_name
        if "soil_ph" in enabled:
            low, high = crop.soil_ph_absolute_min, crop.soil_ph_absolute_max
            ph = request.soil.ph
            area_soil = store.location(request.exploration.location_id).soil_reference
            estimated = ph is None and request.soil.use_area_estimate and area_soil is not None
            if estimated:
                ph = area_soil.ph
            status = "unknown"
            if ph is not None:
                status = "pass" if low <= ph <= high else "fail"
                if estimated and status == "fail":
                    status = "unknown"
            reason = f"{name}: the saved species pH range is {low:g}-{high:g}. "
            reason += "Add a measured soil pH to compare it." if ph is None else f"Your supplied pH is {ph:g}. This is a broad reference check."
            if estimated:
                reason = f"{name}: the HWSD area estimate is pH {ph:g} (0-20 cm); the saved species range is {low:g}-{high:g}. This is a mapped soil estimate, not a farm test."
                if status == "unknown":
                    reason += " Measure farm pH before ruling this crop out."
            checks.append(reference_check(crop, "soil_ph", status, reason))
        if "minimum_cycle_days" in enabled:
            if not crop.rotation_candidate:
                item = reference_check(crop, "minimum_cycle_days", "unknown",
                    f"{name} is perennial. Its published cycle is not a planting-to-first-harvest or replanting schedule; a perennial management plan is needed.")
                item.gap_type = "local_review"
                checks.append(item)
        if "minimum_cycle_days" in enabled and crop.rotation_candidate:
            seasons = [season for season in sequence if crop.crop_id in season.crops]
            lengths = [
                (season.harvest_date - season.planting_date).days + 1
                for season in seasons if season.planting_date and season.harvest_date
            ]
            status = "unknown"
            reason = f"{name}: the saved species cycle is {crop.crop_cycle_days_min}-{crop.crop_cycle_days_max} days. "
            if any(days < crop.crop_cycle_days_min for days in lengths):
                status = "fail"
                reason += "A planned season is shorter than the published minimum."
            elif len(lengths) == len(seasons):
                status = "pass"
                reason += "The planned periods reach the minimum; local variety maturity is still unverified."
            else:
                reason += "Add planting and harvest dates to check the minimum."
            checks.append(reference_check(crop, "minimum_cycle_days", status, reason))
        if "historical_temperature" in enabled:
            low, high = crop.temperature_c_absolute_min, crop.temperature_c_absolute_max
            within = mean_temperature is not None and low <= mean_temperature <= high
            status = "pass" if within else "unknown"
            reason = f"{name}: the saved broad temperature range is {low:g}-{high:g} °C. "
            if mean_temperature is None:
                reason += "The selected period has missing temperature days; no mean was calculated."
            else:
                reason += f"The selected past period averaged {mean_temperature:.2f} °C. "
                reason += "That mean is within the range." if within else "That mean is outside the range; seasonal review is needed."
            reason += " This does not test heat extremes, crop stages or future growing conditions."
            item = reference_check(crop, "historical_temperature", status, reason)
            if status == "unknown" and mean_temperature is not None:
                item.gap_type = "local_review"
            checks.append(item)
    return checks


def can_explore_references(store, request):
    known = {crop.crop_id for crop in store.crops if crop.rotation_candidate}
    recorded = {crop for season in request.baseline_sequence for crop in season.crops} - {"unknown"}
    # Do not silently replace an unreferenced crop or perennial system with annual crops.
    return bool(store.rules.reference_checks and recorded and recorded <= known)


def choose_reference_options(candidates, request, mean_temperature):
    preferred = set(request.preferred_crops)
    starting = set(request.baseline_sequence[0].crops)
    baseline = tuple(tuple(season.crops) for season in request.baseline_sequence)

    def order(strategy):
        crops = [season.crops[0] for season in strategy.sequence]
        return (-len(set(crops) & preferred), -len(set(crops)), crops[0] not in starting, tuple(crops))

    options = []
    combinations = set()
    for candidate in sorted(candidates, key=order):
        crops = tuple(season.crops[0] for season in candidate.sequence)
        combination = frozenset(crops)
        # These are visibly different ideas, not repeated cards for reordered crops.
        if len(combination) < 2 or combination in combinations or tuple((c,) for c in crops) == baseline:
            continue
        combinations.add(combination)
        passed = [item for item in candidate.checks if item.rule_id and item.status == "pass"]
        candidate.explanations = [
            "Every crop in this option has a reference in the supplied local files.",
            f"{len(passed)} published-range checks passed. Read the checks for the values and source links; these do not validate a rotation.",
            "Shown for crop variety and your stated preferences, not as an agronomic ranking. The order of crops has not been validated.",
        ]
        temperature_checks = [item for item in passed if item.criterion.endswith("_historical_temperature")]
        if mean_temperature is not None and len(temperature_checks) == len(combination):
            candidate.explanations.insert(1, f"The selected past period averaged {mean_temperature:.2f} °C, within these crops' broad temperature ranges. This is past context, not a future suitability check.")
        candidate.tradeoffs = [
            "Single-crop seasons only; this is not advice to replace an existing crop mixture.",
            "Confirm succession, local variety, planting windows and water needs with a local adviser.",
        ]
        ph_checks = [item for item in candidate.checks if item.criterion.endswith("_soil_ph")]
        both_passed = len(temperature_checks) == len(combination) and len(ph_checks) == len(combination) and all(item.status == "pass" for item in ph_checks)
        candidate.summary = "Some broad crop-range checks passed; open the checks for the limits."
        if both_passed:
            ph_source = "Supplied pH" if request.soil.ph is not None else "Area-estimated pH"
            candidate.summary = f"{ph_source} and past temperature fit these crops' broad ranges."
        candidate.next_step = "Confirm planting dates, crop order and water needs."
        options.append(candidate)
        if len(options) == 2:
            break
    return options
