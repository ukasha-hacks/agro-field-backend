> Stage 6 implementation update: local species-range checks may now return explicitly unvalidated `reference_only` options. This extends the original no-alternatives behavior below without declaring agricultural review complete. See [ROTATION_RULES.md](ROTATION_RULES.md) for the current formulas, selection order and remaining limits. Only existing resource files are used.

# Agro Field backend: complete implementation prompt

Version: 1.0 | Prepared: 14 November 2026

## 1. Your role and the required outcome

You are the Python developer implementing the Agro Field backend for the Field Shift: Adapting Farms with NASA Data challenge. Treat this document as the implementation brief. Build a small, understandable FastAPI application that implements the agreed workflow, uses downloaded datasets locally, and produces reproducible outputs.

The application has two connected functions:

1. **Explore conditions:** select a supported location, dates, and categories; receive graph data, map information, descriptive summaries, and a PDF report.
2. **Compare rotations:** combine additional farmer inputs with crop references, historical conditions, and documented agricultural rules to compare the existing plan with alternatives. Explain evidence, trade-offs, and missing information.

Preserve both functions. Offline source files do not mean mock API results, static screenshots instead of calculations, or removing the rotation workflow. Compute outputs from the supplied files. When evidence cannot support an agricultural conclusion, return an explicit provisional or insufficient-evidence result.

This document describes work to implement. It does not claim that a FastAPI backend already exists, that rotation rules are locally validated, or that the prototype has demonstrated field benefits.

## 2. Latest decisions that take precedence

- Use downloaded files as the data source. Do not call NASA, FAO, weather APIs, external AI services, or other data services during application startup, exploration, comparison, or PDF generation.
- Keep the complete agreed user experience. Only resource access is offline.
- The main explorer asks for location, dates, and categories. Farmer history and priorities belong to the separate rotation-comparison workflow.
- PDF export is essential, not an optional future feature.
- Historical exploration is primarily date filtering and linked graphs. Automatic playback is optional.
- Use four supported sample locations initially. Do not pretend the sample points represent every farm or the average of a district.
- Combine different units in aligned graph panels, not one shared vertical axis.
- Describe the soil time series as **modelled soil wetness**, not soil fertility, measured water content, or an overall soil-health score.
- Present crop requirements as reference data. No crop growth or crop yield time series is supplied.
- Prefer a small service and ordinary Python functions over unnecessary infrastructure.
- Do not add accounts, a database, a message queue, a GIS server, a language model, or machine learning to the first implementation.
- Do not replace missing agricultural knowledge with invented numbers, blanket succession rules, or a claim that NASA has recommended a rotation.

Offline data access does not necessarily mean the frontend can run without an internet connection. A fully offline browser, offline basemap, installation process, or downloadable app is a separate feature. The backend must run without external data calls once its dependencies and data files are installed.

## 3. What success looks like

The first complete milestone is:

**Select a location -> select dates and categories -> inspect historical graphs and a map -> read calculated descriptions -> download a matching PDF.**

The second milestone is the rotation endpoint and comparison report, including honest evidence gaps when the local agricultural rule set is incomplete.

The full challenge demonstration should show how NASA-derived environmental observations contribute to rotation assessment. An environmental dashboard alone is not the whole challenge solution.

## 4. Technology stack and responsibilities

| Technology | Responsibility | Why it is included |
| --- | --- | --- |
| Python 3.12 | Application and calculation language | One language for API, analysis, and reports |
| FastAPI | HTTP routes, OpenAPI documentation, lifecycle and errors | Clear request/response contracts |
| Pydantic, compatible with the chosen FastAPI release | Validate requests and serialize responses | Prevent unsupported selections and ambiguous payloads |
| Uvicorn | Run the ASGI application | Simple local development server |
| pandas | Read local CSV tables, filter dates, group and aggregate | Small historical datasets fit in memory |
| Matplotlib with a noninteractive backend | Generate report charts | No browser automation or external chart rendering service |
| ReportLab, using Platypus | Produce a multipage PDF | Local report generation with text, tables, and images |
| Python standard library | Paths, dates, JSON, hashing, logging, temporary buffers and configuration | Avoid extra libraries for simple tasks |
| pytest and HTTPX | Development tests and API checks | Verify calculations and the complete workflow |

Use mutually compatible, supported releases. Resolve and record the exact versions that are actually installed and tested. Do not invent a tested lock file or claim an installation passed before running it. A simple requirements file and a recorded tested environment are sufficient for this prototype.

No database is required: the source data is read-only, and requests do not need to be saved. No ORM, Redis, Celery, scikit-learn, TensorFlow, LangChain, external LLM, GeoServer, or PostGIS is needed.

Direct GeoTIFF processing with Rasterio is an optional extension. The core implementation can return sample-point GeoJSON and serve the supplied, clearly labelled reference map preview without installing a GIS stack. Do not misrepresent that preview as a georeferenced overlay.

## 5. Input dataset and installation

Use the supplied archive `Field_Shift_Relevant_Inputs_Outputs.zip`. Its extracted root is `Field_Shift_Relevant_Data/`.

The archive is a separate input artifact. This Markdown file does not embed its contents. If the archive is unavailable, ask for that exact input rather than generating replacement measurements or downloading unrelated data.

Extract it into the project under `data/Field_Shift_Relevant_Data/`. Keep the folder read-only during normal requests. Do not overwrite the original source files or precomputed outputs.

### 5.1 Authoritative files

| Relative path inside the data root | Purpose |
| --- | --- |
| `inputs/environment/daily_environment_2016_2025.csv` | Authoritative daily environmental table for filters, summaries, and custom periods |
| `inputs/maps/sample_locations.csv` | Supported IDs, names and coordinates |
| `inputs/maps/sample_locations.geojson` | Four sample points, with longitude before latitude |
| `inputs/crops/crop_reference_requirements.csv` | Four species-level crop references |
| `inputs/maps/gaez_map_metadata.json` | Baseline, scope, resolution, source and limitations of the maize map |
| `inputs/maps/gaez_maize_map_legend.csv` | Official class meanings and colors |
| `inputs/maps/gaez_v4_maize_soil_terrain_low_inputs.tif` | Optional native raster source; preserve it |
| `outputs/gaez_maize_point_reference.csv` | Already extracted maize reference classes at the four sample points |
| `previews/maize_soil_terrain_map.png` | Static reference map for display and PDF reports |
| `outputs/monthly_line_graphs_2016_2025.csv` | Precomputed monthly comparison/checking table |
| `outputs/historical_seasonal_patterns_2016_2025.csv` | Ten-year calendar-month averages for supported comparisons |
| `provenance/nasa_manifest.json` and `provenance/nasa_raw/` | Source requests, original responses, dates and units |
| `provenance/fao_sources/` | Downloaded crop sheets and map class metadata |
| `resources_scope.csv` | Included and deferred resources from the supplied challenge resource list |
| `validation_report.json` and `checksums.sha256` | Existing data preparation checks and integrity information |

The farmer input templates are empty templates. The rotation output template contains uncomputed values. Neither is evidence that an assessment has already been completed.

### 5.2 Verified dataset inventory

- Four locations; 1 January 2016 through 31 December 2025 inclusive.
- 14,612 daily location records; nine environmental variables.
- 480 precomputed monthly location records, 40 annual records, and 48 seasonal-average records.
- Four crop reference records: `maize`, `beans`, `groundnut`, and `sorghum`.
- One soil/terrain suitability reference map for rain-fed maize under low inputs; GAEZ v4 land-resource baseline 2010.
- No district polygons, actual farmer records, measured farm pH records, local market price series, yield histories, forecasts, or validated rotation outcomes.

| location_id, matching source sample_id | Display name | Latitude | Longitude |
| --- | --- | --- | --- |
| central_masaka | Masaka vicinity | -0.337 | 31.737 |
| eastern_mbale | Mbale vicinity | 1.080 | 34.175 |
| northern_gulu | Gulu vicinity | 2.774 | 32.299 |
| western_mbarara | Mbarara vicinity | -0.607 | 30.655 |

These coordinates are analyst-selected prototype points. Region names are navigation labels, not a statement of regional averaging. Do not interpolate four point series across Uganda, assign a nearest sample silently, or manufacture boundaries.

### 5.3 Raw environmental columns

The daily CSV contains `date`, `sample_id`, `region`, `latitude`, `longitude`, followed by:

| Raw column | Source parameter | Native daily unit | Default explorer use |
| --- | --- | --- | --- |
| temperature_mean_c | T2M | C | Temperature panel |
| temperature_min_c | T2M_MIN | C | Optional temperature-extreme line |
| temperature_max_c | T2M_MAX | C | Optional temperature-extreme line |
| rainfall_mm | IMERG_PRECTOT | mm/day; numerically equal to depth over each one-day interval | Rainfall panel |
| surface_soil_wetness | GWETTOP | Dimensionless 0-1 | Wetness panel |
| root_zone_soil_wetness | GWETROOT | Dimensionless 0-1 | Wetness panel |
| relative_humidity_percent | RH2M | % | Supporting data; not a first-screen category |
| wind_speed_2m_m_s | WS2M | m/s | Supporting data; not a first-screen category |
| solar_radiation_mj_m2_day | ALLSKY_SFC_SW_DWN | MJ/m2/day | Supporting data; not a first-screen category |

Read the solar units from the actual NASA metadata; do not assume kWh/m2/day. Do not sum temperature or wetness. Do not present the MERRA-2 wetness variables as SMAP measurements.

The metadata reports MERRA-2 and IMERG provenance for the relevant series and SYN1DEG provenance for radiation. Meteorological grid resolution is approximately 0.5 degrees latitude by 0.625 degrees longitude; IMERG is approximately 0.1 degrees. A point coordinate does not imply farm-scale resolution.

## 6. Simple application structure

Use one FastAPI application with thin routers and small service modules. Do not create microservices or a generic plugin framework.

| Project file or folder | Responsibility |
| --- | --- |
| `app/main.py` | Application creation, lifespan loading, CORS and exception handlers |
| `app/config.py` | Small configuration object using environment variables and pathlib |
| `app/schemas.py` | Request, response, warning, series and comparison models |
| `app/data_store.py` | Read and validate local files once; expose read-only data |
| `app/routers/catalog.py` | Health, metadata, locations, crops and map reference routes |
| `app/routers/analysis.py` | Exploration and rotation routes |
| `app/routers/exports.py` | PDF endpoint |
| `app/services/explore.py` | Filtering, aggregation and descriptive statistics |
| `app/services/describe.py` | Deterministic text generated from assessed metrics |
| `app/services/rotations.py` | Constraint checks, candidate evaluation and evidence states |
| `app/services/reports.py` | Report charts, map inclusion and PDF composition |
| `config/rotation_rules.json` | Versioned agricultural rules; initially honest about unreviewed/missing content |
| `tests/` | Calculation, contract, missing-data and PDF tests |
| `data/Field_Shift_Relevant_Data/` | Extracted input files |
| `README.md` | Installation, run commands, data setup, limitations and examples |

If a router becomes trivial, combining it with another is acceptable. Keep calculations independent of HTTP so the API and PDF call the same functions.

## 7. Startup, configuration and data integrity

Use FastAPI lifespan to load the CSV/JSON resources once per process. For the small prototype, run one application worker initially.

Configuration:

- `DATA_DIR`: extracted data root; default to a project-relative directory, never an author-specific scratch path.
- `CORS_ORIGINS`: explicit allowed frontend origins; document a local development example.
- `APP_ENV`: development or production-style error handling; do not add a settings service.

Determine `data_version` from the checksum manifest or a stable hash of the files actually used. Keep `methods_version` and `rules_version` as explicit strings. Do not change results invisibly when changing source data or rules.

At startup, verify required file existence, required columns, supported location IDs, unique `(sample_id, date)` keys, parseable dates and numeric values, and the stated coverage. Treat missing numeric cells as missing values. Do not convert them to zero.

Check nonnegative rainfall, finite numbers, wetness within 0-1, and minimum <= mean <= maximum temperature where all values exist. Invalid nonmissing values and duplicate daily keys are data errors, not something to silently repair.

Stop startup with an actionable local error if core files are absent or malformed. Missing optional map preview/reference assets may disable that component with a structured warning while exploration remains available. Expose feature availability through metadata. No network fallback.

## 8. Shared API conventions

- Base path: `/api/v1` except `/health`, `/docs`, and `/openapi.json`.
- JSON input/output uses snake_case. Use declared response models.
- Dates are ISO `YYYY-MM-DD` date strings. All source daily intervals use UTC. User-facing generation timestamps can display Africa/Kampala with an explicit zone; never shift UTC daily records into invented local-date observations.
- `start_date` and `end_date` are inclusive, with start <= end.
- `location_id` is an exact supported ID. Unknown IDs return 404. Free-form district names and arbitrary coordinate analysis are outside this version.
- Reject unknown request fields and unsupported enum values. Return 422 for invalid selections and date ranges.
- Keep JSON numbers numeric; missing values are null, never NaN or Infinity. Zero rainfall is valid.
- Use warning objects with `code`, `message`, and optional `field`. Warnings are data limitations, not hidden exceptions.
- A business result of insufficient evidence is HTTP 200 with an explicit assessment status. It is not a server failure.
- Use a consistent error object for validation, not found, known component unavailability and unexpected server errors: `error.code`, `error.message`, and `error.details` as a list. Include the field path in validation details. Avoid stack traces and absolute file paths in public errors.
- No authentication or user storage in this local, read-only prototype. Do not collect farmer names, phone numbers or account credentials.

## 9. Endpoint inventory

| Method | Endpoint | Returns |
| --- | --- | --- |
| GET | `/health` | Process and loaded-data readiness |
| GET | `/api/v1/metadata` | Coverage, categories, methods, sources and available features |
| GET | `/api/v1/locations` | Supported location list |
| GET | `/api/v1/locations.geojson` | Four-point GeoJSON FeatureCollection |
| GET | `/api/v1/crops` | Four crop reference records with limitations |
| GET | `/api/v1/map-layers` | Available map references, baseline, legend and preview links |
| GET | `/api/v1/map-layers/{layer_id}/preview` | Whitelisted static reference PNG |
| POST | `/api/v1/explore` | Filtered series, statistics, descriptions and selected-point GeoJSON |
| POST | `/api/v1/rotation-comparisons` | Baseline/alternative assessments and evidence gaps |
| POST | `/api/v1/exports/pdf` | PDF bytes for an exploration and optional rotation assessment |

Do not add a separate replay API, report job queue, live data endpoint, or arbitrary file download endpoint.

### 9.1 GET /health

Return `status: ok`, `data_loaded: true`, application version, and data version when core data has loaded. This is readiness to serve the documented features, not proof of agronomic validity. Do not return `rotation_validated: true` because the API process is running.

### 9.2 GET /api/v1/metadata

Return the available date range, UTC time convention, supported categories and series, units, aggregation definitions, interval choices, known limitations and source records. Include feature availability for exploration, PDFs, map references and reviewed rotation scoring.

The date range for this pack is 2016-01-01 through 2025-12-31. Derive and verify it from the files.

### 9.3 GET /api/v1/locations and /locations.geojson

The list contains ID, display name, navigation region, latitude, longitude, coverage and `spatial_scope: gridded_point_sample`.

The GeoJSON route returns the same four locations as Point features in EPSG:4326. Coordinate order is `[longitude, latitude]`. It contains location metadata, not fabricated district conditions.

### 9.4 GET /api/v1/crops

Return all four reference records, mapping blank cells to null and the source's `False` string to a Boolean false for local-variety validation. Preserve source IDs and URLs. Include an explanation that rainfall limits are annual, crop-cycle ranges are broad, and these references are not locally validated variety recommendations.

Do not put crop IDs into the environmental category enum. Crop details are a separate panel/tab, not a time-series measurement.

### 9.5 GET /api/v1/map-layers and map preview

Use `gaez_maize_soil_terrain_low_inputs` as the whitelisted layer ID. Return its name, crop, management, water-supply assumption, land-resource baseline, native raster extent, resolution, legend, source and limitations.

Return the preview URL only if its supplied PNG exists. Serve it with `image/png`. Reject unknown layer IDs with 404; never concatenate a client-provided path into DATA_DIR.

Important: the supplied preview PNG contains labels, margins and a legend. It is a reference illustration, **not** an image that may be stretched onto its geographic bbox as a raster overlay. Set `image_role: reference_preview_not_georeferenced_overlay`. The bbox describes the source GeoTIFF only.

The native raster includes neighboring territory. It is not an official Uganda outline. Its class codes 1-7 indicate progressively lower suitability, class 8 means not suitable, and class 9 means water. Preserve the supplied legend. The layer applies to maize soil/terrain suitability under the stated conditions, not to all crops or current farm soil health.

## 10. Exploration request

POST `/api/v1/explore` accepts:

```json
{
  "location_id": "northern_gulu",
  "start_date": "2024-01-01",
  "end_date": "2024-12-31",
  "categories": ["rainfall", "temperature", "soil_wetness"],
  "interval": "monthly"
}
```

Required: location_id, start_date, end_date, categories. Interval defaults to monthly. Categories must be a nonempty list of unique values from `rainfall`, `temperature`, `soil_wetness`. Preserve request order when producing panels. Interval is `daily` or `monthly`; do not silently downsample a daily request.

A daily request is limited to 366 calendar days to keep the screen and PDF readable. Longer daily requests receive 422 with a suggestion to select monthly. Monthly requests may cover the entire supplied range. Return the applied interval explicitly.

Reject dates outside the supplied coverage instead of silently clipping them. This service does not provide forecasts or accept future dates for environmental exploration.

No farm ID, crop history, soil test, irrigation answer or priority is required for this endpoint.

## 11. Filtering, aggregation and missing-data rules

The daily CSV is the calculation source. Filter by location and inclusive dates first, then group into calendar months. Never use a full precomputed monthly total for a request covering only part of that month.

For every series point return:

- `period_start` and `period_end`: actual dates included in that point, clipped to the request.
- `value`: numeric result or null.
- `expected_days`: count of selected calendar days in that period.
- `valid_days`: valid observations for this particular variable.
- `coverage_fraction`: valid_days / expected_days; this is data completeness, not scientific confidence.
- `partial_calendar_month`: true for a monthly point that covers less than a full calendar month; false for daily points.

Daily points have identical start/end dates, expected_days = 1 and valid_days either 0 or 1. Retain expected calendar dates even if observations are missing.

### 11.1 Series definitions

| Category | series_id | Daily value | Monthly value | Public unit |
| --- | --- | --- | --- | --- |
| rainfall | rainfall_total_mm | One-day rainfall depth | Sum of selected daily depths | mm; interval is stated separately |
| temperature | temperature_mean_c | Daily mean | Average of selected daily means | degC |
| temperature | temperature_minimum_c | Daily minimum | Lowest selected daily minimum | degC |
| temperature | temperature_maximum_c | Daily maximum | Highest selected daily maximum | degC |
| soil_wetness | surface_soil_wetness | Daily surface wetness | Average of selected daily values | dimensionless_index |
| soil_wetness | root_zone_soil_wetness | Daily root-zone wetness | Average of selected daily values | dimensionless_index |

Include the temperature-extreme series in the API, but mark them hidden-by-default for the frontend/PDF. Their monthly meaning is an extreme, not an average daily minimum/maximum.

Return a value only when valid_days equals expected_days for that series point. Otherwise return null and an incomplete-data warning. Do not interpolate, forward-fill, turn missing rainfall into zero, or allow an all-null sum to become zero.

For a request from 15 March to 10 April, the two monthly points cover 15-31 March and 1-10 April. They are partial months but can each have complete data for their selected days. Distinguish partial calendar periods from missing observations.

Compute whole-period statistics from daily records, not the unweighted average of monthly averages. Apply the same completeness rule to each statistic. Keep valid-day counts visible when a result is unavailable.

Use full precision for calculations. Serialize measured values to at most four decimal places; round presentation separately. Do not introduce false precision into explanatory text.

### 11.2 Period statistics

- Rainfall: selected-period total, daily mean, highest daily depth and its date when the necessary data is complete. Do not label highest daily rainfall as highest monthly rainfall.
- Temperature: average daily mean, minimum daily minimum, maximum daily maximum, and corresponding dates for extremes.
- Wetness: average surface/root-zone indices and their observed daily ranges.
- For tied extrema, return the earliest date and state that additional ties may exist, or return a consistently bounded list; choose and document the simple earliest-date approach.

Do not compare totals from unequal-duration partial months as if they identify a wettest or driest full month. An optional full-month comparison should use only complete calendar months with complete observations.

## 12. Exploration response and descriptions

Define an `ExploreResponse` with these top-level fields:

| Field | Content |
| --- | --- |
| analysis_id | Stable fingerprint of normalized request, data_version and methods_version; not a persisted database ID |
| request | Validated selections actually applied |
| location | Name, ID, coordinates and spatial-scope statement |
| panels | One panel per selected category; each has title, axis labels, series definitions and points |
| statistics | Numeric whole-period metrics, units, definitions and coverage |
| descriptions | Short deterministic sentences with evidence references |
| selected_location_geojson | One selected Point feature for map focus |
| map_references | Relevant static layer metadata/preview links; clear temporal distinction |
| sources | Source records used in this particular response |
| warnings | Coverage, scale, historical-data and other material limitations |
| data_version / methods_version | Reproducibility identifiers |

Each panel has `category`, `title`, `x_axis_label`, `y_axis_label`, and `series`. Each series has `series_id`, `label`, `unit`, `aggregation`, `visible_by_default`, and `points`.

The frontend renders interactive graphs; the backend supplies values and labels. Rainfall, temperature and wetness use separate aligned panels. Surface/root-zone wetness share a 0-1 index axis. All panels share dates, but not units. Hover/click highlighting is frontend behavior.

### 12.1 Deterministic descriptive text

Use templates populated from statistics, not a generative AI call. Each sentence should reference the metric or series IDs used to produce it. Describe selected-period rainfall, average temperature and wetness clearly. Explain missing results when needed.

Do not invent causal explanations, declare crop damage, label an arbitrary wetness threshold as drought, claim a long-term trend from two endpoints, or promise yields/profits.

Historical averages are optional comparison lines. If implemented, compare only full calendar months with complete observations against the corresponding calendar-month average over 2016-2025 at the same sample. Label this a ten-year historical average, not a 30-year climate normal. The comparison average includes the selected year when it belongs to that reference period; document that choice. Do not compare a partial-month total with a full-month average.

## 13. Historical replay behavior

No separate replay server or simulation is required. The frontend selects a year/date range through `/explore` and moves a local month cursor over the returned points.

The initial interface can select a year, move a month slider, and use previous/next-month buttons. Selecting a month updates the selected-date marker and the values in a panel next to the map. Automatic play/pause is optional and should not cause one API call per animation frame.

Default to the latest complete year present in the data, 2025 for this pack. The visible label must state historical replay and the selected month/year.

The selected point may be green to mean selected. Do not let that green marker imply healthy soil, low risk or crop suitability. If a future feature maps an environmental value, it needs a measurement legend and the observation period.

Changing the replay year changes the displayed history. It must not silently change a rotation assessment's reference period. Rotation comparison uses the explicit historical reference dates in its own request.

## 14. Rotation-comparison request

POST `/api/v1/rotation-comparisons` is separate from exploration. Use this logical request structure:

```json
{
  "exploration": {
    "location_id": "northern_gulu",
    "start_date": "2016-01-01",
    "end_date": "2025-12-31",
    "categories": ["rainfall", "temperature", "soil_wetness"],
    "interval": "monthly"
  },
  "crop_history": [
    {"season_label": "previous season", "crops": ["maize"]},
    {"season_label": "current season", "crops": ["maize"]}
  ],
  "baseline_sequence": [
    {"season": 1, "crops": ["maize"], "planting_date": null, "harvest_date": null},
    {"season": 2, "crops": ["maize"], "planting_date": null, "harvest_date": null},
    {"season": 3, "crops": ["maize"], "planting_date": null, "harvest_date": null}
  ],
  "water_supply": "rainfall_only",
  "priority": "improve_soil",
  "excluded_crops": [],
  "preferred_crops": [],
  "soil": {"ph": null, "texture": null, "organic_carbon_percent": null}
}
```

This is an illustrative request structure, not a real farmer record or a recommendation to grow maize repeatedly.

Rules:

- `exploration` is required and uses the same local historical coverage rules as the explorer. It selects environmental context, not future weather.
- `crop_history` is an ordered list from older to newer. Require at least the latest known crop or an explicit unknown. Earlier history is optional.
- `baseline_sequence` is required and contains exactly three future season entries in order. Do not infer a farmer's intended plan by repeating the current crop silently.
- Support arrays of crops to represent mixed cropping. An empty array means fallow. A reserved `unknown` value represents an unknown history entry. Unknown or mixed baseline systems must be retained and identified as outside supported rules when appropriate.
- Future planning dates may be supplied here even though exploration dates are historical. They do not authorize future environmental observations. Reject harvest-before-planting when both dates are present. Missing dates leave calendar checks unknown.
- `water_supply`: rainfall_only, limited_irrigation, reliable_irrigation, unknown.
- `priority`: improve_soil, conserve_water, reduce_pests, income, general. This is a preference, not a substitute for evidence supporting a score.
- Soil measurements are optional. Validate pH within 0-14 and organic carbon within 0-100 percent if supplied. Unknown remains null.
- Exclusions/preferences can be empty. Do not fabricate prices or seasonal water needs.
- This request is not stored. It needs no farm identifier or personal information for the prototype.

Use catalog IDs for recognized crop choices. Preserve unrecognized baseline/history crop names as supplied text with an unsupported-reference warning; do not discard the farmer's baseline. Generated alternative crops must come from the supported candidate catalog and applicable reviewed rules.

## 15. Rotation engine: simple, explainable and evidence-aware

Implement this as ordinary Python functions. No trained model is justified by this pack: it contains environmental series and reference ranges, not labelled outcomes showing which rotations succeeded on these farms.

### 15.1 Rule file

Create a small, versioned `rotation_rules.json`. Separate documented agricultural rules from user constraints and application configuration.

A rule needs: ID, description, crops/systems covered, criterion, operation/threshold or permitted transition, unit when relevant, source reference, applicability notes, and review status. Do not mark rules reviewed merely because an AI wrote them. The initial file may contain no reviewed agricultural rules, with an explicit `review_status: pending`.

User exclusions and supplied dates can be checked immediately. Crop-family return intervals, seasonal water needs, pest-break effects, residue contributions and soil benefits require appropriate sourced parameters. The crop reference file alone does not establish all of them.

### 15.2 Candidate generation and feasibility

For four single-crop candidates across three seasons, enumerate at most 4^3 = 64 sequences. Use the standard library; no solver is needed. This enumeration count does not include fallow, mixtures, multiple fields or alternative planting dates. Keep those extensions out of automatic generation initially.

Always evaluate and display the supplied baseline. For alternatives, apply explicit farmer exclusions and documented sequence constraints. Remove exact duplicates of the baseline and one another. Do not add a universal ban on repeating a crop or crop family unless the relevant sourced rule supports it.

Each check returns `pass`, `fail`, or `unknown`, plus a reason, rule/source IDs, and relevant observations. A missing measurement is unknown, not fail. A failed hard constraint can exclude an alternative. Missing critical evidence prevents calling a candidate feasible or recommended.

Dates and maturity must be checked using locally applicable crop-duration information. The source's broad species cycle range must not become an invented Uganda planting calendar. When a sequence is meant to repeat, also check the last-to-first transition if a documented rule supports that check.

### 15.3 Use of environmental data

The immediate, supported output is historical environmental context for the chosen location and period. Per-crop growing-window screening is enabled only when dates, relevant crop durations and interpretable thresholds exist.

If historical screening is implemented later, apply the same seasonal window to the available historical years, handle year-boundary windows explicitly, and flag incomplete windows rather than reading unavailable 2026 data after December 2025. A pass rate is the proportion of historical windows meeting the declared rules, not a crop survival probability or a forecast.

Do not compare annual ECOCROP rainfall limits with a month's rainfall or relabel them seasonal crop water needs. Do not infer irrigation demand from rainfall alone. Do not assign maize's GAEZ map rating to other crops. Broad crop temperature ranges are not automatically validated daily damage thresholds.

### 15.4 Comparison and optional ranking

The first implementation should show criterion-level checks, reasons and gaps. Do not require a numerical overall score to make the comparison useful.

Preserve the planned multi-criteria ranking capability as a small extension: enable it only when criteria definitions, normalization, direction, and sufficient comparable evidence are documented. A weighted sum can use weights summing to one, with the priority profile and weights shown to the user. Any score means preference alignment, not predicted success, yield or soil improvement.

Do not renormalize each option over a different subset of available criteria; that can reward missing data. Use a common assessed criterion set, disclose exclusions, and withhold ranking if critical criteria are unavailable. Check whether modest weight changes alter the ordering substantially before calling a ranking stable.

Without reviewed agronomic rules, return an insufficient-evidence assessment with the baseline, environmental context, missing inputs and unassessed candidate slots. Do not present the first two enumerated sequences as the best alternatives. Do not manufacture demonstrated benefits to fill three cards.

### 15.5 Rotation response

Return `assessment_id`, `status`, `baseline`, `alternatives`, `unfilled_alternative_slots`, `environmental_context`, `priority`, `rules_version`, `criteria`, `missing_information`, `sources`, and `warnings`.

Statuses:

- `assessed`: the declared checks required for this comparison have enough evidence; this still does not establish field validation or guaranteed outcomes.
- `provisional`: partial comparison is useful, but material checks remain unknown; no definitive recommendation.
- `insufficient_evidence`: information/rules do not support meaningful rotation evaluation.

Each strategy includes its sequence, feasibility status, criterion checks, explanations, evidence references, supported potential benefits, trade-offs, and local-review needs. Unsupported benefit values remain null with an explanation. `alternatives` contains up to two actually assessed/provisional strategies. Return fewer than two when necessary and give reasons for the unfilled slots.

Unknown source coverage is not HTTP 500. The frontend should be able to render evidence gaps as part of the product.

## 16. PDF export: required in the first complete explorer milestone

POST `/api/v1/exports/pdf` accepts:

```json
{
  "exploration": {
    "location_id": "northern_gulu",
    "start_date": "2024-01-01",
    "end_date": "2024-12-31",
    "categories": ["rainfall", "temperature", "soil_wetness"],
    "interval": "monthly"
  },
  "rotation": null
}
```

For a combined report, `rotation` is a full RotationRequest. Require its nested exploration request to match the top-level exploration selections; otherwise return 422. This avoids silently combining different places or periods.

Recompute through the same exploration/comparison services. Do not accept client-supplied calculated series, score values, descriptions, arbitrary HTML, image URLs or filesystem paths. No persisted analysis ID lookup is needed. This is a synchronous, small report endpoint, not an asynchronous job system.

Return PDF bytes with `Content-Type: application/pdf` and an attachment filename built from validated location/date values. Return an ordinary structured JSON error if validation or rendering fails; never return an error page disguised as a PDF.

### 16.1 Report contents

1. Agro Field title, selected location and coordinates, selected dates, interval and historical-data label.
2. A compact numeric summary with units and data completeness.
3. One legible line-chart panel per selected environmental category; same values as the API. Use the default visible series, with optional temperature extremes only if deliberately requested through a later explicit feature.
4. The supplied GAEZ reference map preview with its own baseline/maize-only caption, plus a separate text statement identifying the selected location. It already labels the four sample locations. Do not claim it is a date-specific environmental map or that it newly highlights the chosen point.
5. Descriptions and material missing-data warnings.
6. Rotation assessment and gaps only when a rotation request was supplied. A provisional report must retain that status prominently.
7. Sources, data/method/rule versions, generation timestamp, and spatial/temporal limitations.

Use a straightforward A4 layout with readable charts, tables that wrap, page numbers, and additional pages when needed. Do not squeeze all content onto one page or put a long daily series into an unreadable miniature plot.

Use local Matplotlib images and ReportLab Platypus. No remote fonts, tiles or images are fetched. Use in-memory buffers or request-local temporary files with cleanup. Configure a noninteractive backend before rendering. Avoid shared pyplot figures; create/close each figure explicitly. Serialize chart rendering with a small lock if needed because concurrent rendering should not rely on Matplotlib global state being thread-safe.

If the optional reference map PNG is absent, the PDF can still export with a labelled coordinates table and explicit map-unavailable note. Do not substitute a blank coordinate scatter and call it a geographic basemap. Report component availability before the user exports.

## 17. Descriptive endpoints, not hidden external services

Keep all main processing local and deterministic:

1. Validate the request.
2. Look up the location.
3. Filter and aggregate the in-memory daily table.
4. Calculate statistics and data completeness.
5. Generate short descriptions from those results.
6. Attach selected-point geometry, source records and relevant static map references.
7. Return typed JSON, or pass that same result to the PDF renderer.

For a rotation request, add the baseline, applicable rules, candidate generation/checks and evidence-aware comparison between steps 5 and 6.

Use normal synchronous route functions for the small blocking data/report work, or explicitly offload that work if using async routes. Do not block the event loop with a large synchronous render inside an async handler. Start with the simpler synchronous handlers.

## 18. Safeguards and deliberately excluded scope

- No scheduled or per-request source downloads. The local dataset version remains fixed until an explicit maintenance update outside this API.
- No arbitrary user file uploads or arbitrary URL fetching.
- No external basemap requests during PDF generation. Frontend basemap selection is separate; this backend returns point geometry and the supplied reference preview.
- No district polygons or district-wide environmental claims from four points.
- No current-weather labels on 2016-2025 data and no projections beyond the supplied date range.
- No fabricated farmer testimony, field-trial results, prices, nitrogen contributions, yield gains, or water savings.
- Preserve source attribution and the map's stated CC-BY-NC-SA-4.0 terms. Do not claim that an application code license changes source-data rights.
- Log route, duration and error category as needed; avoid dumping farmer request bodies or full source tables into logs.
- Keep CORS explicit and local file serving whitelisted. This is sufficient for the prototype; do not introduce a new authentication project.

## 19. Meaningful tests and acceptance checks

Use a small synthetic fixture for edge cases and the supplied dataset for a few verified reference checks. Label fixtures as test data and keep them out of production responses. Do not add hundreds of tests that simply mirror internal functions.

### Data and calculation tests

- Unknown location -> 404; invalid category, duplicate categories, malformed/reversed dates and out-of-range environmental dates -> 422.
- Daily selection over 366 days -> 422 with a monthly-view suggestion.
- A real zero-rain day remains zero. Missing rain remains null and does not become a valid sum.
- Missing days remain in the expected calendar; incomplete aggregate values are null with valid/expected counts.
- February 2024 has 29 days; source calendar/date grouping is correct.
- Means use daily weighting, not an unweighted average of unequal-length months.
- Temperature monthly extrema use min/max of the correct daily source columns.
- Different variables have independent coverage counts.
- GeoJSON coordinate order is longitude, latitude.
- Source crop-validation strings become booleans correctly; do not use bool('False').

Verified numerical examples from the supplied daily CSV:

| Location | Inclusive dates | Expected days | Rainfall total |
| --- | --- | --- | --- |
| northern_gulu | 2024-01-01 to 2024-01-31 | 31 | 39.59 mm |
| northern_gulu | 2024-02-01 to 2024-02-29 | 29 | 77.54 mm |
| central_masaka | 2024-03-15 to 2024-04-10 | 27 | 208.13 mm |

For the Masaka partial-period example, verify two correctly clipped monthly points whose totals sum to 208.13 mm. Do not return the full March and April monthly totals. Test a suitable numeric tolerance instead of binary floating-point equality.

### Rotation tests

- Baseline stays visible even if it fails an exclusion or lacks reference coverage.
- Missing soil or crop-duration data produces unknown checks, not failure or invented values.
- Candidate duplicates and the baseline duplicate are removed.
- Explicit excluded crops do not appear in returned alternatives.
- No reviewed agronomic rules -> insufficient_evidence with specific gaps and no invented best alternatives.
- Mixed/unknown histories are preserved with clear limits.
- Unsupported priorities do not produce fabricated economic or water scores.
- A historical window crossing beyond the last available year is not filled with future observations.

### End-to-end and report tests

- One request selects Gulu, 2024, and all three categories and returns correct panel labels, series, units, warnings and source records.
- The same selection generates an actual readable PDF with matching statistics, selected categories, local map reference and source information.
- PDF begins with the expected PDF header, has correct content type/attachment behavior, and contains extractable location/date text.
- Render a sample PDF and visually review every page for clipped text, overlapping labels and readable legends before calling PDF export complete.
- A combined provisional rotation report retains its warnings and evidence status.
- Requests succeed with outbound networking unavailable after dependencies and files are installed. No application path attempts a source download.
- Repeated calls do not mutate the shared source table or leak report buffers/figures.

## 20. Impact, creativity, validity, relevance and presentation

These are design goals and evaluation questions, not claims that the backend alone proves a competition result.

| Dimension | Backend contribution | Evidence to gather outside backend implementation |
| --- | --- | --- |
| Impact | Readable local context, understandable comparisons and shareable PDF | Whether intended users can complete the workflow and explain trade-offs; longer field evaluation for agronomic outcomes |
| Creativity | Historical date exploration, consistent period comparisons and explainable preference-aware assessment where evidence exists | A demonstration showing a concrete decision becoming clearer |
| Validity | Correct aggregation, sources, supported spatial scope, reproducibility and explicit unknowns | Agricultural review of the actual rules and representative scenarios |
| Relevance | NASA-derived conditions contribute to the crop/rotation assessment, with local information where available | A demonstration connecting environmental evidence to the declared checks |
| Presentation | Stable typed outputs, aligned units, concise descriptions and coherent PDF export | Clear frontend, accessible labels and a concise project narrative |

Do not add decorative scores or a complex model simply to appear innovative. Do not claim a local pilot, expert endorsement, demonstrated water savings or improved soil without evidence. Distinguish working software, reference screening, local review, and field validation.

## 21. Implementation order

### Step 1: foundation

Create the project, resolve compatible dependencies, configure DATA_DIR, load the supplied files, implement schemas and catalog/health routes, and document local setup. No live source client.

### Step 2: complete exploration

Implement inclusive filtering, daily/monthly points, partial-period handling, completeness, statistics, deterministic descriptions, map references and `/explore`. Run calculation and contract checks.

### Step 3: finish the first end-to-end milestone

Implement PDF rendering through the same services, verify content and page layout, and demonstrate location -> selections -> JSON/graphs/map data -> PDF. This milestone requires no farmer questionnaire or agronomic score.

### Step 4: rotation comparison

Implement the separate request/response, baseline preservation, rule schema, candidate generator and pass/fail/unknown evaluation. Integrate available documented agricultural parameters. When they are insufficient, return useful context and specific evidence gaps instead of a fabricated ranking. Add the comparison to combined PDFs.

### Step 5: integrate and prepare the demonstration

Connect the frontend, check selected-date behavior, test source consistency and offline data operation, collect usability feedback where possible, and identify what the working rotation module can actually substantiate.

Do not call the full challenge solution complete merely because the explorer works. Equally, do not block the explorer/PDF milestone while awaiting field evidence that it does not need.

## 22. Optional extensions after the core works

- Local play/pause replay animation.
- Calendar-month historical-average comparison lines with the rules above.
- Reviewed weighted multi-criteria ranking and sensitivity checks.
- More supported locations after an explicit approved offline data update.
- Verified administrative boundaries from permitted sources.
- Direct GeoTIFF rendering/sampling using Rasterio, preserving class values and source CRS.
- Crop timeline overlays when planting dates and local durations exist; distinguish proposed scenarios from actual historical crop records.
- Documented evapotranspiration/water-balance modelling with the required coefficients and assumptions.
- Translation, audio, saved accounts, database persistence, multiple fields, production hosting and fully offline frontend packaging.

These are optional extensions, not justification for postponing a working simple backend. No automatic expansion without a specific need.

## 23. Deliverables and completion reporting

When asked to implement this brief, deliver:

- A runnable FastAPI project with the documented routes and typed contracts.
- Dependency/setup instructions and an explicit tested Python/dependency environment.
- Local-data setup instructions, with no author-specific file paths.
- Meaningful tests and their actual results.
- Sample exploration request, rotation request and PDF export request.
- A rendered and reviewed sample PDF.
- Accurate notes on working features, disabled components, agricultural evidence gaps and optional work.

Do not report tests, installations, expert reviews, field impacts or runtime success that were not observed. Finish the authorized implementation without repeatedly asking about ordinary reversible coding choices. Resolve ambiguities using the simple defaults in this brief, and document any material change.

## 24. Reference documentation

These references support implementation and interpretation. They are not runtime API dependencies or permission to add unrelated datasets.

| Reference | URL |
| --- | --- |
| FastAPI request bodies | https://fastapi.tiangolo.com/tutorial/body/ |
| FastAPI response models | https://fastapi.tiangolo.com/tutorial/response-model/ |
| FastAPI lifespan loading | https://fastapi.tiangolo.com/advanced/events/ |
| FastAPI CORS | https://fastapi.tiangolo.com/tutorial/cors/ |
| FastAPI tests | https://fastapi.tiangolo.com/tutorial/testing/ |
| Pydantic models | https://docs.pydantic.dev/latest/concepts/models/ |
| pandas time grouping reference | https://pandas.pydata.org/docs/reference/api/pandas.DataFrame.resample.html |
| Matplotlib rendering backends | https://matplotlib.org/stable/users/explain/figure/backends.html |
| ReportLab documentation | https://docs.reportlab.com/reportlab/userguide/ch1_intro/ |
| Optional Rasterio usage | https://rasterio.readthedocs.io/en/stable/quickstart.html |
| NASA POWER resource | https://power.larc.nasa.gov/ |
| NASA POWER hydrology interpretation | https://power.larc.nasa.gov/docs/methodology/data/sources_hydrology/ |
| NASA MERRA-2 wetness definitions | https://gs6101-gmao.gsfc.nasa.gov/gmao-products/merra-2/faq_merra-2/ |
| GPM/IMERG resource | https://gpm.nasa.gov/data |
| FAO GAEZ resource | https://gaez.fao.org/ |
| FAO GAEZ maize soil/terrain catalogue | https://data.fao.org/catalog/iso/fd3fc7ff-07d3-477a-a905-c46dbecc9dcc |
| FAO explanation of ECOCROP integration | https://www.fao.org/land-water/resources/tools/databases/ecocrop/en |

The supplied archive preserves the resource-selection text, direct source records and crop URLs. Use those records to attribute actual inputs. No new source download is needed to implement this local-data prototype.

## 25. Local operation and example verification

The following commands describe the expected developer workflow after implementing the project. They are not evidence that implementation or tests have already run.

From the project root, create an isolated environment, install the project's tested requirements, extract the supplied archive under `data/`, and run:

```bash
python -m uvicorn app.main:app --reload
```

Open `http://127.0.0.1:8000/docs` to inspect and exercise the typed contracts. Use `/health` to confirm the local data loaded, `/api/v1/locations` to obtain supported IDs, and `/api/v1/metadata` to discover categories and coverage. Dependency installation may need connectivity; serving this dataset after installation must not.

Example exploration request:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/explore \
  -H 'Content-Type: application/json' \
  -d '{"location_id":"northern_gulu","start_date":"2024-01-01","end_date":"2024-12-31","categories":["rainfall","temperature","soil_wetness"],"interval":"monthly"}'
```

For PDF export, place the complete export request shown in section 16 in a local `export-request.json`, then run:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/exports/pdf \
  -H 'Content-Type: application/json' \
  --data-binary @export-request.json \
  --output agro-field-report.pdf
```

Check the HTTP status and content type before treating the downloaded body as a PDF; an invalid request returns JSON. After implementing the test suite, run `python -m pytest`. Record which checks actually passed and visually inspect the sample PDF. A passing data-preparation report from the archive is not a substitute for application tests.
