import hashlib
from itertools import product

from app.data_store import SOURCES, DataStore, read_json
from app.rotation_schemas import (
    AgriculturalRule, AlternativeSlot, CriterionCheck, PlannedSeason,
    RotationRequest, RotationResponse, RuleSet, Strategy,
)
from app.schemas import Source, Warning
from app.services.explore import explore, fingerprint
from app.services.reference_checks import (
    assess_references, can_explore_references, choose_reference_options, historical_temperature,
)
from app.services.rotation_conclusion import conclude


def load_rules(path):
    rules = RuleSet(**read_json(path))
    digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    return rules, f"{rules.version}:{digest}"


def check(criterion, status, reason, rule=None):
    gap = None
    if status == "unknown":
        gap = "local_review"
        if criterion in {"calendar_overlap", "crop_history"} or "needed for this rule" in reason:
            gap = "farmer_input"
        if criterion == "crop_reference_coverage":
            gap = "missing_reference"
    return CriterionCheck(
        criterion=criterion, status=status, reason=reason,
        rule_id=rule.rule_id if rule else None, source_url=rule.source_url if rule else None,
        gap_type=gap,
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


def assess_strategy(store, request, sequence, strategy_id, rules, mean_temperature=None):
    checks = []
    crops = {crop for season in sequence for crop in season.crops}
    supported = {crop.crop_id for crop in store.crops}
    excluded = crops & set(request.excluded_crops)
    status = "fail" if excluded else "pass"
    reason = f"Excluded crops occur: {', '.join(sorted(excluded))}." if excluded else "No explicitly excluded crops occur."
    checks.append(check("farmer_exclusions", status, reason))
    unsupported = crops - supported
    reference_status = "unknown" if unsupported else "pass"
    reference_reason = "Species references are available for every named crop."
    if unsupported:
        reference_reason = f"No local species reference for: {', '.join(sorted(unsupported - {'unknown'}))}."
        if unsupported == {"unknown"}:
            reference_reason = "Choose a crop for each season marked Not sure."
    checks.append(check("crop_reference_coverage", reference_status, reference_reason))
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
    reference_checks = assess_references(store, request, sequence, mean_temperature)
    checks.extend(reference_checks)
    if store.rules.reference_checks:
        covered = {crop for crop in crops if all(
            any(item.rule_id == f"reference:{crop}:{kind}" for item in reference_checks)
            for kind in store.rules.reference_checks)}
        missing = crops - covered
        covered_status = "unknown" if missing or not crops else "pass"
        reason = "Local reference checks cover every crop in the sequence. This does not validate crop order."
        if missing or not crops:
            reason = f"Reference checks cannot cover: {', '.join(sorted(missing)) or 'an empty crop sequence'}."
        item = check("reference_rule_coverage", covered_status, reason)
        if covered_status == "unknown":
            item.gap_type = "missing_reference"
        checks.append(item)
    perennial = [crop.crop_name for crop in store.crops if crop.crop_id in crops and not crop.rotation_candidate]
    if perennial:
        checks.append(check("perennial_management", "unknown", f"{', '.join(perennial)}: review as standing perennial crops, not replacements every season."))
    covered = set()
    for rule in rules:
        relevant = crops & set(rule.crops)
        if relevant:
            covered.update(relevant)
            checks.append(agricultural_check(rule, request, sequence))
    if crops - covered or not rules:
        checks.append(check("succession_evidence", "unknown", "Crop-order effects on pests, nutrients and water have not been validated by the downloaded references."))
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
    available = sorted(crop.crop_id for crop in store.crops if crop.rotation_candidate and crop.crop_id not in request.excluded_crops)
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
    uses_temperature = "historical_temperature" in store.rules.reference_checks
    mean_temperature = historical_temperature(store, request.exploration) if uses_temperature else None
    baseline = assess_strategy(store, request, request.baseline_sequence, "existing_rotation", rules, mean_temperature)
    reference_mode = not rules and can_explore_references(store, request)
    counts = {"evaluated": 0, "rejected": 0, "unknown": 0, "eligible": 0}
    eligible = []
    for sequence in candidate_sequences(store, request):
        assessed = assess_strategy(store, request, sequence, "candidate", rules, mean_temperature)
        counts["evaluated"] += 1
        if assessed.feasibility_status == "infeasible":
            counts["rejected"] += 1
        elif assessed.feasibility_status == "unknown":
            counts["unknown"] += 1
            # Reference ideas and reviewed comparisons have different evidence gates.
            has_pass = any(c.rule_id and c.status == "pass" and
                           (reference_mode or not c.rule_id.startswith("reference:")) for c in assessed.checks)
            if (rules or reference_mode) and has_pass:
                eligible.append(assessed)
                counts["eligible"] += 1
        else:
            counts["eligible"] += 1
            eligible.append(assessed)
    preferred = set(request.preferred_crops)
    eligible.sort(key=lambda item: -sum(crop in preferred for season in item.sequence for crop in season.crops))
    alternatives = choose_reference_options(eligible, request, mean_temperature) if reference_mode else eligible[:2]
    for index, alternative in enumerate(alternatives, 1):
        alternative.strategy_id = f"alternative_{index}"
    missing = sorted({item.reason for strategy in [baseline, *alternatives] for item in strategy.checks if item.status == "unknown"})
    if not rules:
        missing.insert(0, "No reviewed agricultural rules are configured; species references alone do not validate rotations.")
    status = "insufficient_evidence"
    if alternatives:
        status = "provisional" if missing else "assessed"
        if reference_mode:
            status = "reference_only"
    elif not rules and baseline.feasibility_status != "infeasible":
        coverage = any(item.criterion == "reference_rule_coverage" and item.status == "pass" for item in baseline.checks)
        has_evidence = any(item.rule_id and item.status == "pass" for item in baseline.checks)
        if coverage and has_evidence:
            status = "reference_only"
    if not rules and not reference_mode and store.rules.reference_checks:
        missing.insert(0, "Seasonal replacement options need known seasonal crops. Unreferenced crops and standing perennial systems are not replaced automatically.")
    slot_reason = "No additional adequately supported alternative is available."
    perennial_plan = any(item.criterion == "perennial_management" for item in baseline.checks)
    if perennial_plan:
        slot_reason = "Seasonal replacement options do not apply to the standing perennial crops in this plan."
    elif reference_mode:
        slot_reason = "No further distinct crop combination passed the local reference checks. Check your exclusions, pH, planned dates and missing observations; unsupported crops are not added."
    slots = [AlternativeSlot(strategy_id=f"alternative_{i}", reason=slot_reason)
             for i in range(len(alternatives) + 1, 3)]
    sources = list(context.sources)
    sources.append(SOURCES[2])
    area_soil = store.location(request.exploration.location_id).soil_reference
    if request.soil.ph is None and request.soil.use_area_estimate and area_soil:
        sources.append(Source(source_id="fao_hwsd", name="FAO HWSD v2.0 topsoil reference", url=area_soil.source_url,
            period="Soil inventory, 0-20 cm layer", limitations=area_soil.method + "; " + area_soil.resolution))
    if store.rules.reference_checks:
        if uses_temperature and not any(source.source_id == SOURCES[0].source_id for source in sources):
            sources.append(SOURCES[0])
        used_crops = {crop for strategy in [baseline, *alternatives] for season in strategy.sequence for crop in season.crops}
        for crop in store.crops:
            if crop.crop_id not in used_crops:
                continue
            sources.append(Source(
                source_id=f"reference:{crop.crop_id}", name=f"{crop.crop_name} species reference",
                url=crop.source_url, period="Supplied local ECOCROP reference",
                limitations="Broad species ranges; not locally validated varieties or succession rules.",
            ))
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
        conclusion=conclude(store, request, baseline, alternatives),
        selection_method=("local_species_reference_checks_then_preferences_and_distinct_crop_sets; not agronomic ranking"
                          if status == "reference_only" else "constraint_checks_then_explicit_crop_preferences; no agronomic overall score"),
    )
