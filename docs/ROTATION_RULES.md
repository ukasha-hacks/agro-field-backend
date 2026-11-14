# Rotation comparisons and their current limits

The supplied species references do not contain a locally validated rotation model. Therefore `config/rotation_rules.json` starts with `review_status: pending` and no rules. The working endpoint returns the farmer's baseline, actual historical context, check results and missing information. It does not select the first two generated sequences and call them recommendations.

## Request behavior

Use `examples/rotation.json` for the complete request structure. It is an example request, not a real farmer record. Crop history is ordered from older to newer. The baseline contains three planned seasons; unknown names, mixed cropping and fallow are retained. Crop names are normalized to lowercase and surrounding spaces removed. `unknown` must appear alone in an unknown season.

Planting/harvest dates describe a proposed plan and may be in the future. The nested exploration request selects historical evidence only. No future weather is supplied. Missing planting dates leave calendar checks unknown.

## Checks implemented now

- Explicit farmer exclusions, reference availability and planned-season overlap.
- A documented schema for reviewed crop-return, pH-range and irrigation-requirement rules.
- Candidate enumeration for four single-crop choices across three seasons, with duplicates and exclusions removed.
- A return-interval rule can inspect crop history and, when `repeats` is true, the last-to-first transition.
- Source IDs, rule versions and a request fingerprint are included.
- Missing information stays unknown. No overall agricultural score, predicted yield, market return or water saving is generated.

## Supported rule kinds

| Kind | Required parameter | Meaning |
| --- | --- | --- |
| minimum_crop_break | min_break_seasons | Number of intervening seasons required before a crop returns; not a number of years or a crop-family rule |
| soil_ph_range | minimum, maximum | Compare the farmer-supplied pH with an applicable sourced range |
| requires_irrigation | No numeric threshold | Check declared water supply; limited/unknown irrigation capacity remains unknown |

Every rule also needs rule_id, description, criterion, crops, source_url, applicability and review_status. Both the rule set and the individual rule must be reviewed before it affects agricultural checks. Review labels are assertions made by whoever maintains the file, not automatic proof of expert review. Do not change them merely to unlock alternatives.

Use the challenge's permitted resource sources. A new source requires an explicit scope decision. No source URL is fetched during a request.

## Important remaining work

Growing-window suitability always remains unknown in this implementation because local maturity, crop-stage climate and water parameters were not supplied. Priority outcomes also remain unquantified. Adding a reviewed rule can support a **partial, provisional** comparison; it does not enable a validated recommendation or a complete farm simulation. Such partial alternatives must have at least one applicable reviewed rule pass and no failed declared check. They are ordered only by explicit crop-preference overlap, with a stable tie order; that is not an agronomic best-to-worst ranking.

The default configuration returns no alternatives and two explained unfilled slots. Agricultural rules, calibration and local review remain substantive work before a competition demonstration can claim supported rotation advice. The environmental explorer and PDF export work independently of that gap.

Synthetic reviewed rules occur only in tests to exercise the engine. They are not production data or agricultural recommendations.
