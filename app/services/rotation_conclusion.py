from app.rotation_schemas import RotationConclusion


def conclude(store, request, baseline, alternatives):
    failures = [item for item in baseline.checks if item.status == "fail"]
    crops = {crop for season in baseline.sequence for crop in season.crops}
    known = {crop.crop_id: crop for crop in store.crops}
    missing = crops - set(known) - {"unknown"}
    steps = []
    assessed = [baseline, *alternatives]
    gaps = [item for strategy in assessed for item in strategy.checks if item.gap_type == "farmer_input"]
    if any(item.criterion.endswith("soil_ph") for item in gaps):
        steps.append("Add a measured soil pH to check your field.")
    if any(item.criterion == "calendar_overlap" or item.criterion.endswith("minimum_cycle_days") for item in gaps):
        steps.append("Add planting and harvest dates to finish the timing checks.")
    if failures:
        return RotationConclusion(title="Your starting plan needs a change", detail=failures[0].reason,
            tone="attention", next_steps=steps[:2])
    if missing:
        detail = "No saved reference for: " + ", ".join(sorted(missing)) + "."
        if "coffee" in missing:
            detail = "Choose Coffee — Arabica or Coffee — Robusta so we can use the correct reference."
        return RotationConclusion(title="Choose a referenced crop", detail=detail,
            tone="review", next_steps=["Edit the crops marked without a reference."])
    perennial_ids = [crop for crop in sorted(crops) if crop in known and not known[crop].rotation_candidate]
    perennials = [known[crop].crop_name for crop in perennial_ids]
    if perennials:
        context_checks = [item for item in baseline.checks if any(
            item.criterion in {f"{crop}_soil_ph", f"{crop}_historical_temperature"} for crop in perennial_ids)]
        all_passed = len(context_checks) == len(perennials) * 2 and all(item.status == "pass" for item in context_checks)
        detail = "Some crop-range checks still need data. Use a perennial growing plan rather than seasonal replacement."
        if all_passed:
            ph_source = "supplied pH" if request.soil.ph is not None else "area-estimated pH"
            detail = f"{', '.join(perennials)}: broad {ph_source} and past-temperature checks passed. Plan for harvest and ongoing care rather than seasonal replacement."
        needs = [step for step in steps if "pH" in step]
        return RotationConclusion(title="Use a perennial growing plan", tone="review",
            detail=detail, next_steps=[*needs, "Review the harvest cycle and any companion crops locally."])
    if alternatives:
        sequence = " → ".join(" + ".join(known[crop].crop_name for crop in season.crops) for season in alternatives[0].sequence)
        return RotationConclusion(title="An option to explore", tone="review",
            detail=f"{sequence}. It passes the available broad-range checks; crop order and seasonal water needs still need review.",
            next_steps=steps[:2])
    if crops <= {"unknown"} or not crops:
        return RotationConclusion(title="Add your starting crops", detail="Choose at least one known crop to explore a different plan.",
            tone="review", next_steps=["Edit your next seasons."])
    return RotationConclusion(title="No alternative passed the available checks", tone="review",
        detail="Review crop exclusions, pH and planned dates before changing this plan.", next_steps=steps[:2])
