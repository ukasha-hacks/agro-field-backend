# Understanding the Agro Field backend

A practical guide to the code, the formulas and the reasons behind the design

Prepared for Ukasha Katuntu, 15 November 2026. This guide follows the actual FastAPI code and the downloaded local archive. It explains what to say in a demonstration and what the prototype cannot yet establish.

### The main idea

Agro Field calculates historical summaries and checks declared constraints. It does not train a model to predict the next crop, forecast weather or estimate farm income. Reviewed agricultural rules remain empty and pending review. Configured local species checks now support reference-only options alongside the starting plan and evidence gaps.

The archive contains 14,612 daily records across four sample points near Gulu, Mbale, Masaka and Mbarara, covering 2016 through 2025. One point in each broad region keeps the first demonstration manageable. This is not a representative sample of every farm or district.

### The small set of moving parts

| Part | Job | Why it is here |
| --- | --- | --- |
| FastAPI | Receives requests and sends responses | One clear API for the frontend |
| Pydantic | Validates dates and farmer inputs | Rejects ambiguous or invalid requests |
| pandas | Filters and groups daily rows | Repeatable historical calculations |
| Explicit rules | Checks supported constraints | A reason can accompany each check |
| Matplotlib and ReportLab | Draw charts and build PDFs | A portable record of the same evidence |

### A good sentence for your talk

We combine a small local archive of NASA-derived records with farmer answers, then show the historical evidence, the checks we can perform and the information that still needs local review.

## Follow one request through the API

The entry point is app/main.py. At startup, its lifespan function loads DataStore and the rule configuration into application memory. Requests reuse those loaded objects. No NASA or FAO request runs during normal analysis.

| Endpoint | What it returns |
| --- | --- |
| GET /health | Whether the app and local store started |
| GET /api/v1/locations | Four supported sample points |
| GET /api/v1/crops | The four species reference records |
| GET /api/v1/metadata | Coverage, source and method information |
| POST /api/v1/explore | Historical panels, statistics and explanations |
| POST /api/v1/rotation-comparisons | Baseline checks, possible alternatives and gaps |
| POST /api/v1/exports/pdf | A freshly calculated historical or combined report |

### A real example request

```
{
  "location_id": "eastern_mbale",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "categories": ["rainfall", "temperature", "soil_wetness"],
  "interval": "monthly"
}
```

Pydantic checks the structure first. Dates must be ordered, categories must be supported and unique, and daily views are limited to 366 days. The service then checks that the location exists and the dates fall inside the downloaded archive. Invalid input returns a clear JSON error, not a fabricated result.

The exploration service selects one location, creates the complete calendar of requested days, and reindexes the source rows onto it. A missing row therefore remains an expected day. Only then does the service group rows into months or individual days.

## Understand the historical formulas

### Expected days and coverage

Expected days = end date minus start date in days, plus 1

Coverage = valid daily values / expected calendar days

Date differences use whole calendar days. Both end dates count. The full 2024 period has 366 expected days because 2024 is a leap year. Coverage is calculated separately for each variable. The API rounds coverage fractions to four decimal places and returns both day counts.

### Rainfall adds daily depths

Rainfall total R = sum of the selected daily rainfall depths

The daily rainfall column stores one-day depths in millimetres. The monthly graph adds only the selected days in that month. For the Mbale 2024 sample, the annual total is 1,984.87 mm and April totals 298.04 mm. All 366 selected days are present. These are historical grid estimates, not a farm rain gauge.

### Temperature and wetness use daily means

Mean x = sum of all selected daily values / number of selected days

Here x can be daily mean air temperature, surface wetness or root-zone wetness. Temperature is in degrees Celsius. Each wetness measure is a 0 to 1 model index. A wetness value of 0.5 does not mean the soil is 50 percent water or halfway to fertile.

These formulas produce a displayed value only when every expected daily value for that measure is present. Otherwise the API returns null and explains the day coverage.

## Handle missing days and partial months correctly

### Missing is different from zero

Zero rainfall is a real observation and must stay zero. A missing daily record is unknown. The backend never fills it with zero or silently drops it from an average. The same strict completeness rule applies to chart points and selected-period statistics.

| Teaching example | Coverage | What the API shows |
| --- | --- | --- |
| Daily rainfall values 0 and 10 | 2 of 2 days | Total 10 mm |
| Daily rainfall values 0, missing, 10 | 2 of 3 days | Unavailable total |
| Daily temperatures 10 and 20 | 2 of 2 days | Mean 15 degrees Celsius |
| Daily temperatures 10, missing, 20 | 2 of 3 days | Unavailable mean |

These four rows are labelled teaching examples, not observations from the local archive. The code rounds calculated values to four decimal places; a report may show fewer decimals for reading.

### Filter before grouping

If a user selects 15 March to 10 April, the March point contains 17 days and the April point contains 10 days. The backend does not substitute full-month rainfall. Both points are labelled partial calendar months, even if their selected days are complete.

### Weight a whole period by its days

Daily weighted test example = (31 × 10 + 29 × 20) / 60 = 14.8333 degrees Celsius

This is the synthetic example in the tests: 31 January days at 10 degrees and 29 February days at 20 degrees. Averaging the two monthly means would give 15, which weights unequal months equally. The backend calculates from the selected daily rows instead.

Lowest temperature uses the lowest daily minimum. Highest temperature uses the highest daily maximum. When an extreme repeats, the first chronological date is shown. These values do not establish crop damage without crop-stage thresholds and local evidence.

## Read the farmer inputs and rule checks

The rotation request includes the historical selection plus crop history and exactly three planned seasons. The baseline is what the farmer would normally grow. It stays visible even when a check fails or information is missing.

| Input | Why the backend needs it |
| --- | --- |
| Past crops in order | A crop-break rule needs previous seasons |
| Three planned seasons | A fixed sequence makes the prototype easy to compare |
| Water supply and one priority | Expresses the farmer’s situation and the evidence needed |
| Preferred and excluded crops | Constrains choices and orders eligible options |
| Optional soil pH, texture and carbon | Supplies local information that wetness cannot infer |
| Optional planting and harvest dates | Allows a season-overlap check |

The string unknown means the farmer is not sure. An empty crop list means fallow. They are different. Mixed crops and fallow remain recordable, but the present automatic rules do not establish their feasibility. A crop may not appear in both preferred and excluded lists.

### Three simple rule types

Rules must be marked reviewed at both the rule-set level and the individual-rule level. Pending rules are ignored. Each active rule carries a source URL and a stated applicability. Code support alone is not agricultural validation.

Soil pH check passes only inside the bounds supplied by an applicable reviewed rule

The bounds a and b come from that reviewed rule. The code does not turn a species reference range into a locally validated rule automatically. Missing pH returns unknown.

Crop break = the current season index minus the previous occurrence index minus 1

A minimum crop-break rule compares this gap with its declared requirement. Repeating rotations also need the end-to-start gap checked. An irrigation rule distinguishes rainfall-only, limited, reliable and unknown supply; it does not calculate water volumes.

## Understand candidate selection and evidence gaps

### The search is deliberately small

Four available crops across three single-crop seasons give 64 combinations

The engine enumerates the available crop catalogue after exclusions. With four crops and three single-crop seasons there are 64 combinations. If a supported single-crop baseline matches one of them, that baseline is skipped, leaving 63 candidate sequences. This is a limited prototype search, not the full set of farming possibilities.

| Check result | Meaning |
| --- | --- |
| pass | This declared check is met |
| fail | A declared constraint is violated |
| unknown | An input, rule or applicable method is missing |

Any failed check makes a candidate infeasible. Unknown checks keep its local suitability unknown. A provisional candidate under reviewed rules needs at least one passed reviewed check. Reference-only options use a separate, explicitly labelled path described below. The result must remain provisional and show the gaps. The current code always leaves the growing-window check unknown.

### Preferences are not an agronomic score

Preference matches = count of planned crop occurrences in the farmer’s preferred set

For each season, I is 1 if its crop is preferred and 0 otherwise. Eligible candidates are ordered by these matches, then the first two are kept. This is not a soil health, water, income or resilience score. Priority-specific checks explain missing evidence instead of awarding invented points.

### How local references now support exploratory options

The config enables three reference checks while reviewed agricultural rules remain pending. For each referenced crop, the engine compares supplied pH with its saved absolute pH range, inclusive planned days with the saved minimum cycle, and the selected past temperature mean with the saved broad temperature range. Any missing temperature day makes that historical mean unknown. The mean is context, not a forecast or a crop-stage heat check.

At least one sourced range check must pass, and no declared check may fail, before a candidate can be displayed. The reference-only display order favors distinct preferred crops, more distinct crops and then the starting crop first, with alphabetical ties. Different crop sets give visibly different options; this is not a proven benefit of diversity or a validated crop succession. Reviewed-rule ordering above remains unchanged.

The normal maize example returns `reference_only` with two options. All remain unknown for local suitability. An unreferenced crop such as coffee or banana is recorded but blocks replacing that growing system automatically. A pH conflict, short dates, missing observations or tight exclusions can leave fewer options. The original files contain only maize, beans, groundnut and sorghum; no outside references are added.

See [the exact checks, formulas and selection procedure](ROTATION_RULES.md).

## Connect the calculations to the report and version IDs

The PDF endpoint accepts selections and farmer answers, not client-calculated statistics. It calls the same exploration service again and runs the rotation service when requested. The exploration inside a combined rotation request must match the report selection. This keeps a report from mixing two different places or periods.

### What the report includes

The report contains period statistics, graphs, a separate static maize map reference, the baseline and evidence gaps when supplied, source notes and version identifiers. DM Sans regular and bold fonts are bundled and embedded. Matplotlib uses the same local fonts for chart labels. The original static map is a separate source image.

Days present is valid daily values out of expected selected days. Wetness uses / 1 rather than the raw dimensionless_index field name. Lowest and highest values have readable dates. A missing optional map produces an explicit note and coordinates, while the historical export still works.

### Why the IDs matter

The data version is the first 16 hexadecimal characters of a SHA-256 digest over selected local input paths and their bytes. The methods version is a declared code version. The rules version combines its declared version and the first 12 hexadecimal characters of its file hash.

An analysis ID uses the first 24 hexadecimal characters of a hash of canonical JSON containing the validated request, data version and methods version. A rotation assessment adds the rules version. These are compact reproducibility identifiers, not confidence scores or proof of scientific correctness.

Identical inputs and versions produce the same analysis ID. PDF bytes can still differ because the report records its generation time and its typography can change without changing the analysis. The PDF includes Africa/Kampala time. Preserve the source, method and rule records when reproducing a result.

### What is cached

The backend holds its validated local tables in process memory. The frontend separately caches successful read-only results for five minutes, bounded to 20 entries; catalogue fetches use one-hour server revalidation. Failed responses and PDF blobs are not cached by the browser helper. The browser still needs the running app and backend.

## Separate the seasonal view from the backend assessment

The new seasonal section is calculated in the frontend from the existing monthly exploration response. It requests the full 2016–2025 archive only while expanded. It does not introduce a live data service, a forecast or a new backend risk endpoint.

### A calendar window calculation

March to May rainfall window in year y = March + April + May rainfall

Only a year with all three complete calendar months enters the calculation. September to November uses the corresponding three months. Monthly history averages the complete corresponding months across the available years. Each table cell shows its real number of complete years.

Window archive average = sum of complete yearly window totals / complete years

Below-average count B = number of complete years below that window’s archive mean

Here I is 1 when a complete year’s window total is below the archive average, and 0 otherwise. A total equal to the average does not count as below average.

For the Gulu sample, March to May averages 442.893 mm across 2016–2025. September to November averages 503.492 mm. In each window, five of the ten complete years fall below its own average. An independent sum from the daily CSV matches the frontend result.

This means below the sample’s ten-year archive average. It is not a drought diagnosis, a crop stress threshold or a standard planting calendar for all Uganda. Northern rainfall patterns can differ from the central and southern pattern. The current data cannot determine bare-field dates or crop damage.

### Keep the report period clear

The main charts and PDF retain the dates the user selected. The expanded seasonal view is labelled as a separate full-archive comparison. Its on-screen calculations are not silently added to the selected-period PDF. No scenario slider, NDVI layer, SMAP measurement or crop-water balance has been added.

## Explain the system confidently in the presentation

### A short explanation you can say aloud

A farmer selects one of four sample areas and a past period. Our backend reads the local daily records, checks the calendar and calculates totals, averages and extremes with complete-day coverage. The farmer adds crop history, water supply and a starting rotation. The rule engine shows the checks it can perform and the evidence it still needs. The PDF keeps those selections, results and sources together for a conversation with a local adviser.

### Questions you should be ready to answer

| Question | A clear answer |
| --- | --- |
| Why NASA data | It gives a consistent historical record at the sample points. Local observations still matter. |
| Why four areas | One sample per broad region and a common ten-year period keep the prototype focused. They are not representative of all farms. |
| Why no best crop score | Seasonal water needs, reviewed local rules and local outcome evidence are missing. A number would overstate what is known. |
| Is wetness a soil health score | No. It is a 0 to 1 model index. Nutrients, pH and organic carbon need different evidence. |
| Have farmers benefited yet | No measured yield, income or water-saving result is claimed. A pilot will test usefulness and comprehension. |

### Run and read the code

```
python -m uvicorn app.main:app --reload
python -m pytest -q
```

Read app/main.py, then app/data_store.py, app/services/explore.py and app/services/rotations.py. Follow app/routers/exports.py into app/services/reports.py for the PDF. Review docs/DATA_SOURCES.md and docs/ROTATION_RULES.md before making an agricultural claim.

[Backend source and source guide](https://github.com/ukasha-hacks/agro-field-backend/tree/stage/05-readable-pdf)

[Frontend seasonal calculation and methods](https://github.com/ukasha-hacks/agro-fields-frontend/tree/stage/05-evidence-and-guidance)

[NASA POWER documentation](https://power.larc.nasa.gov/docs/methodology/)

[FAO GAEZ and linked crop references](https://gaez.fao.org/)
