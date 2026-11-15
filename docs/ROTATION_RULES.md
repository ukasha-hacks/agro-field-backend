> Stage 7 update: the supplementary local files extend the catalog to ten crop choices and add explicit HWSD area-pH estimates. Original files remain unchanged. `reference_rule_coverage` now checks whether configured references cover every crop, separately from `succession_evidence`, which remains unvalidated. Missing farm answers, missing sources, missing observations and local-review gaps have different labels. See [DATA_SOURCES.md](DATA_SOURCES.md) for downloaded files and extraction details.

# Local reference checks and rotation evidence

The default configuration now enables reference-based options. It reads only the supplied local files. It does not fetch source URLs and does not mark the agricultural rules as reviewed.

## Files used

- `config/rotation_rules.json`: enables `soil_ph`, `minimum_cycle_days` and `historical_temperature` under `reference_checks`.
- `data/Field_Shift_Relevant_Data/inputs/crops/crop_reference_requirements.csv`: broad ECOCROP species ranges and original source URLs for maize, beans, groundnut and sorghum.
- `data/Field_Shift_Relevant_Data/inputs/environment/daily_environment_2016_2025.csv`: the selected sample point's historical daily mean temperature, delivered through NASA POWER.

All thresholds come directly from those existing crop records. The original download and checksum manifest are unchanged. Supplementary FAO sheets now add coffee, banana, sugarcane, vanilla and cotton. Cassava still has no supplied reference.

## Checks and formulas

| Check | Calculation | Missing or conflicting evidence |
| --- | --- | --- |
| Soil pH | absolute minimum <= farmer pH <= absolute maximum | Missing pH is unknown; outside the broad range flags a reference conflict |
| Minimum crop cycle | use harvest - planting + 1 when both dates exist; otherwise use supplied planned_days; compare with the saved minimum | Missing dates and duration are unknown; any period shorter than the minimum fails this check |
| Historical mean temperature | mean of all selected daily mean temperatures; compare with the saved absolute range | Any missing day leaves the mean unknown; a mean outside the range needs review, rather than proving the crop unsuitable |
| Calendar | each later planting date must follow the previous harvest date | Missing dates are unknown; overlap fails |
| Farmer exclusions | no excluded crop in the sequence | An excluded crop fails |

The historical temperature check passes only a comparison of a past-period mean with a broad species range. It cannot confirm crop-stage conditions, heat damage, a future planting window or local suitability. A minimum-cycle pass does not verify the variety, calendar or maturity date. Annual rainfall ranges are not used as seasonal water demand.

## How options are selected

1. Keep the farmer's starting plan and all its checks, including mixtures, fallow, unknowns and unsupported crops.
2. Enumerate three single-crop seasons from the five seasonal candidate crops after exclusions. Do not invent crops or planting dates.
3. Remove candidates with any failed declared check. At least one positive sourced range check is required; mere enumeration does not qualify a candidate.
4. In reference-only mode, sort by the number of distinct preferred crops, then the number of distinct crops, then keeping the starting crop first, then crop IDs for reproducibility. This is a transparent display heuristic, not a scientifically validated rotation rule.
5. Show up to two different crop combinations, each containing at least two species. Different permutations of the same crop set do not fill two cards. A repeated crop is not universally banned; no unsourced crop-break interval is introduced.
6. Label the result `reference_only`, with unknown feasibility and local review required. Explain passed checks, tradeoffs and all unresolved information.

This mode needs at least one named, referenced starting crop and a reference for every named starting crop. A planned season marked unknown returns needs_input and a named-season prompt before candidates are generated. Unknown crop history remains acceptable. Perennial references can pass species checks but cannot unlock annual replacement sequences. A fully unknown plan receives `needs_input`; an unreferenced system receives `insufficient_evidence`, not an automatic replacement with annual crops. Mixed referenced crops can explore single-crop ideas, but this does not validate the mixture or advise removing it.

If too few crop combinations remain, show fewer options and explain the empty slots. No yield, income, water saving, soil benefit, confidence percentage or agronomic ranking is calculated. Water supply and priority identify missing evidence; they do not silently alter temperature observations.

## Reviewed agricultural rules remain separate

`review_status` is still `pending` and `rules` is empty. Both the set and an individual rule must be `reviewed` before reviewed agricultural rules run. Never change those labels just to unlock alternatives.

Supported kinds remain `minimum_crop_break` (parameter `min_break_seasons`), `soil_ph_range` (`minimum`, `maximum`) and `requires_irrigation`. Each needs an ID, criterion, description, crops, source URL and applicability. Synthetic reviewed rules in tests are not production advice. When reviewed rules are configured, a provisional alternative requires a passed reviewed rule, not merely a passed reference check.

Set `reference_checks` to `[]` to disable exploratory reference options. Restart the backend after configuration changes: rules are loaded at startup. The rule version combines its declared version and file hash; crop/environment bytes are covered by the data version. Changes therefore produce a different assessment fingerprint.

## Test it

Use `examples/rotation.json`: it should return the original maize plan and two `reference_only` options. Add pH 4.2: only beans matches that broad pH range, so there are not enough species for diverse options. Add coffee or banana to a planned season: the baseline stays recorded and automatic replacements are withheld. These outcomes demonstrate honest file-based screening, not expert validation.
