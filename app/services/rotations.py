import hashlib
from itertools import product

from app.data_store import SOURCES, DataStore, read_json
from app.rotation_schemas import (
    AgriculturalRule, AlternativeSlot, CriterionCheck, PlannedSeason,
    RotationRequest, RotationResponse, RuleSet, Strategy,
)
from app.schemas import Source, Warning
from app.services.explore import explore, fingerprint


def load_rules(path):
    rules = RuleSet(**read_json(path))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    return rules, f"{rules.version}:{digest}"


def check(criterion, status, reason, rule=None):
    return CriterionCheck(
        criterion=criterion, status=status, reason=reason,
        rule_id=rule.rule_id if rule else None, source_url=rule.source_url if rule else None,
    )


def crop_break_check(rule, request, sequence):
    history = [item.crops for item in request.crop_history]
    seasons = history + [item.crops for item in sequence]
    if any("unknown" in item for item in history):
        return check(rule.criterion, "unknown", "Crop history contains an unknown season.", rule)
    for index in range(len(history), len(seasons)):
        for crop in set(seasons[index]) & set(rule.crops):
            previous = [i for i in range(index) if crop in seasons[i]]
            if previous and index - previous[-1] - 1 < rule.min_break_seasons:
                return check(rule.criterion, "fail", f"{crop} returns sooner than this rule permits.", rule)
            if not previous and len(history) < rule.min_break_seasons:
                return check(rule.criterion, "unknown", "More crop-history seasons are needed for this return interval.", rule)
    if request.repeats:
        cycle = [item.crops for item in sequence]
        for crop in rule.crops:
            positions = [i for i, crops in enumerate(cycle) if crop in crops]
            if positions and positions[0] + len(cycle) - positions[-1] - 1 < rule.min_break_seasons:
                return check(rule.criterion, "fail", f"{crop} returns too soon when the rotation repeats.", rule)
    return check(rule.criterion, "pass", "The supplied history and sequence meet this declared return-interval rule.", rule)


def agricultural_check(rule: AgriculturalRule, request, sequence):
    if rule.kind == "minimum_crop_break":
        return crop_break_check(rule, request, sequence)
    if rule.kind == "soil_ph_range":
        if request.soil.ph is None:
            return check(rule.criterion, "unknown", "A soil pH value is needed for this rule.", rule)
        matches = rule.minimum <= request.soil.ph <= rule.maximum
        status = "pass" if matches else "fail"
        return check(rule.criterion, status, f"The supplied pH was compared with this rule's {rule.minimum}-{rule.maximum} range.", rule)
    if request.water_supply == "unknown" or request.water_supply == "limited_irrigation":
        return check(rule.criterion, "unknown", "Irrigation capacity needs confirmation.", rule)
    status = "fail" if request.water_supply == "rainfall_only" else "pass"
    return check(rule.criterion, status, "This crop requires irrigation under the cited rule; no water-volume estimate is made.", rule)


def assess_strategy(store, request, sequence, strategy_id, rules):
    checks = []
    crops = {crop for season in sequence for crop in season.crops}
    supported = {crop.crop_id for crop in store.crops}
    excluded = crops & set(request.excluded_crops)
    status = "fail" if excluded else "pass"
    reason = f"Excluded crops occur: {', '.join(sorted(excluded))}." if excluded else "No explicitly excluded crops occur."
    checks.append(check("farmer_exclusions", status, reason))
    unsupported = crops - supported
    reference_status = "unknown" if unsupported else "pass"
    checks.append(check("crop_reference_coverage", reference_status,
                        "Some crops have no supplied species reference." if unsupported else "Species references are available; this is not local validation."))
    if any(len(season.crops) != 1 for season in sequence):
        checks.append(check("cropping_system", "unknown", "Automatic rules currently cover single-crop seasons, not mixtures or fallow."))
    dates_known = all(season.planting_date and season.harvest_date for season in sequence)
    calendar_status = "unknown"
    calendar_reason = "Planting and harvest dates are needed to check season overlap."
    if dates_known:
        overlaps = any(sequence[i].planting_date <= sequence[i - 1].harvest_date for i in range(1, 3))
        calendar_status = "fail" if overlaps else "pass"
        calendar_reason = "Planned seasons overlap." if overlaps else "The supplied season dates do not overlap."
    checks.append(check("calendar_overlap", calendar_status, calendar_reason))
    checks.append(check("growing_window_suitability", "unknown",
                        "Local maturity periods and season-specific climate/water rules are not supplied; historical context is descriptive."))
    covered = set()
    for rule in rules:
        relevant = crops & set(rule.crops)
        if relevant:
            covered.update(relevant)
            checks.append(agricultural_check(rule, request, sequence))
    if crops - covered or not rules:
        checks.append(check("agricultural_rule_coverage", "unknown", "Reviewed agricultural rules do not cover the full sequence."))
    if request.priority != "general":
        missing_priority = {
            "improve_soil": "Soil-benefit rules and locally relevant soil information are needed.",
            "conserve_water": "Seasonal crop-water requirements and an applicable water-balance method are needed.",
            "reduce_pests": "Crop/pest relationships and locally reviewed succession rules are needed.",
            "income": "Local prices, costs and market-access information are needed.",
        }
        checks.append(check("priority_evidence", "unknown",
                            missing_priority[request.priority]))
    statuses = {item.status for item in checks}
    feasibility = "unknown"
    if "fail" in statuses:
        feasibility = "infeasible"
    elif statuses == {"pass"}:
        feasibility = "feasible_for_declared_checks"
    return Strategy(
        strategy_id=strategy_id, sequence=sequence, feasibility_status=feasibility,
        checks=checks, explanations=[item.reason for item in checks],
    )


def candidate_sequences(store, request):
    available = sorted(crop.crop_id for crop in store.crops if crop.crop_id not in request.excluded_crops)
    baseline = tuple(tuple(season.crops) for season in request.baseline_sequence)
    for crops in product(available, repeat=3):
        if tuple((crop,) for crop in crops) == baseline:
            continue
        yield [PlannedSeason(
            season=i + 1, crops=[crop], planting_date=request.baseline_sequence[i].planting_date,
            harvest_date=request.baseline_sequence[i].harvest_date,
        ) for i, crop in enumerate(crops)]


def compare_rotations(store: DataStore, request: RotationRequest) -> RotationResponse:
    context = explore(store, request.exploration)
    rules = store.rules.reviewed_rules()
    baseline = assess_strategy(store, request, request.baseline_sequence, "existing_rotation", rules)
    counts = {"evaluated": 0, "rejected": 0, "unknown": 0, "eligible": 0}
    eligible = []
    for sequence in candidate_sequences(store, request):
        assessed = assess_strategy(store, request, sequence, "candidate", rules)
        counts["evaluated"] += 1
        if assessed.feasibility_status == "infeasible":
            counts["rejected"] += 1
        elif assessed.feasibility_status == "unknown":
            counts["unknown"] += 1
            # Partial options need reviewed evidence, not just a position in enumeration.
            has_pass = any(c.rule_id and c.status == "pass" for c in assessed.checks)
            if rules and has_pass:
                eligible.append(assessed)
        else:
            counts["eligible"] += 1
            eligible.append(assessed)
    preferred = set(request.preferred_crops)
    eligible.sort(key=lambda item: -sum(crop in preferred for season in item.sequence for crop in season.crops))
    alternatives = eligible[:2]
    for index, alternative in enumerate(alternatives, 1):
        alternative.strategy_id = f"alternative_{index}"
    missing = sorted({item.reason for strategy in [baseline, *alternatives] for item in strategy.checks if item.status == "unknown"})
    if not rules:
        missing.insert(0, "No reviewed agricultural rules are configured; species references alone do not validate rotations.")
    status = "insufficient_evidence"
    if alternatives:
        status = "provisional" if missing else "assessed"
    slots = [AlternativeSlot(strategy_id=f"alternative_{i}", reason="No additional adequately supported alternative is available.")
             for i in range(len(alternatives) + 1, 3)]
    sources = list(context.sources)
    sources.append(SOURCES[2])
    for rule in rules:
        sources.append(Source(
            source_id=f"rule:{rule.rule_id}", name=rule.description, url=rule.source_url,
            period="Configured agricultural reference", limitations=rule.applicability,
        ))
    warnings = [Warning(code="rotation_evidence_limits", message=(
        "Comparison is not a yield forecast or locally validated recommendation. "
        "Growing-window checks and priority outcomes remain unassessed without the required evidence."
    ))]
    return RotationResponse(
        assessment_id=fingerprint(request, store.version, store.rules_version), status=status,
        baseline=baseline, alternatives=alternatives, unfilled_alternative_slots=slots,
        environmental_context=context, priority=request.priority, rules_version=store.rules_version,
        criteria=sorted({item.criterion for item in baseline.checks}), missing_information=missing,
        sources=sources, warnings=warnings, candidate_counts=counts,
    )
