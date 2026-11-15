# Agro Field backend

A small FastAPI backend for exploring historical environmental data and comparing crop-rotation evidence. Source data is downloaded once and read locally. There are no live NASA, FAO, weather or AI calls.

## Run locally

Use Python 3.12. From the repository root:

```bash
python -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python -m uvicorn app.main:app --reload
```

On Windows, activate with `.venv\Scripts\activate` instead. Open http://127.0.0.1:8000/docs.

The included `data/Field_Shift_Relevant_Data/` folder contains the local inputs and source records. `DATA_DIR` can point to another extracted copy of the same dataset. Dependency installation needs connectivity; normal application requests do not.

## Current stage

Use `main` in both repositories for the current matching implementation. Tested stage branches remain available. The backend includes local data, historical exploration, reference-based rotation checks and DM Sans PDF reports. To get the complete implementation:

```bash
git clone --branch main https://github.com/ukasha-hacks/agro-field-backend.git
cd agro-field-backend
```

The rotation endpoint is implemented, but the supplied agricultural rule set is pending review. Its default maize example now returns **reference_only** options from saved species ranges, with explicit gaps. These are ideas for local review, not validated crop advice. Unsupported systems still return insufficient evidence. See [rotation rules and current limits](docs/ROTATION_RULES.md).

The [source guide](docs/DATA_SOURCES.md) records challenge-listed resources, local file provenance, reasons for use and limitations.

## Explore a location

```bash
curl -X POST http://127.0.0.1:8000/api/v1/explore \
  -H 'Content-Type: application/json' \
  --data-binary @examples/explore.json
```

Select a supported `location_id`, inclusive dates, unique categories (`rainfall`, `temperature`, `soil_wetness`), and `daily` or `monthly`. Daily views support up to 366 days. Monthly views support the entire 2016-2025 archive.

The API returns aligned panel data, units, statistics, concise descriptions and point geometry. Monthly requests filter daily observations first, so a partial-month request never receives an entire month's rainfall. Missing observations stay null; real zero rainfall stays zero. Statistics use daily weighting. Monthly minimum/maximum temperatures are extremes, not averaged daily minima/maxima.

The frontend can implement a year selector and month cursor from one response; no replay API or live data calls are needed. A source's grid resolution remains unchanged when zooming the map.

## Export a report

```bash
curl -X POST http://127.0.0.1:8000/api/v1/exports/pdf \
  -H 'Content-Type: application/json' \
  --data-binary @examples/export.json \
  --output agro-field-report.pdf
```

The report recomputes through the same exploration service. It includes statistics, charts, descriptions, source records, limitations and the supplied static map reference. DM Sans regular and bold are bundled and embedded, including chart labels. Tables use plain wetness units, readable dates and daily coverage. The font license and source are in [assets/fonts/dm-sans](assets/fonts/dm-sans/README.md). Export never downloads map tiles, images or fonts. Invalid export requests return JSON errors, not a PDF.

The map preview labels all four locations; the report identifies the chosen location in text. It is not an animated weather map or a newly highlighted district. When the optional image is absent, export still works with coordinates and an explicit note.

A generated [Gulu 2024 sample report](examples/gulu-2024-report.pdf) is included for review.

For the request flow, formulas, worked examples, rule checks and presentation questions, read [Understanding the backend](docs/BACKEND_GUIDE.md).

## Compare rotations

```bash
curl -X POST http://127.0.0.1:8000/api/v1/rotation-comparisons \
  -H 'Content-Type: application/json' \
  --data-binary @examples/rotation.json
```

This separate workflow accepts crop history, a three-season baseline, water availability, priorities, exclusions/preferences and optional soil information. The baseline stays visible even when it has a failed or unknown check. Reference-based alternatives use saved pH, minimum crop-cycle and historical-temperature checks. They remain unvalidated for crop succession, seasonal water needs and priority outcomes. The endpoint explains unfilled comparison slots. A planned season marked Not sure returns `needs_input` and a direct crop-choice prompt before alternatives are considered. Optional `planned_days` checks the saved minimum cycle; exact planting/harvest dates take priority when both are supplied.

For a combined PDF, send an export request with `exploration` and the full `rotation` request. Their exploration selections must match. The report retains reference-only/provisional/insufficient-evidence labels and the missing-information list.

Use [the combined request](examples/export-with-rotation.json) with the PDF endpoint above. The [earlier-stage combined Gulu report](examples/gulu-2024-comparison.pdf) is retained for comparison. Run the combined request to generate a current reference-only report.

## Endpoints

| Method | Path | Purpose |
| --- | --- | --- |
| GET | /health | Local data readiness |
| GET | /api/v1/metadata | Coverage, units and feature availability |
| GET | /api/v1/locations | Four supported sample locations |
| GET | /api/v1/locations.geojson | Point GeoJSON |
| GET | /api/v1/crops | Species references and their limitations |
| GET | /api/v1/map-layers | Reference map metadata and legend |
| GET | /api/v1/map-layers/{layer_id}/preview | Whitelisted local PNG |
| POST | /api/v1/explore | Filtered graph series, statistics and descriptions |
| POST | /api/v1/rotation-comparisons | Evidence-aware rotation assessment |
| POST | /api/v1/exports/pdf | Matching exploration/combined PDF |

Errors use `error.code`, `error.message`, and `error.details`. Bad selections return 422, unknown IDs return 404, and insufficient agricultural evidence is a normal 200 response with an explicit assessment status.

## Configuration

| Variable | Default | Purpose |
| --- | --- | --- |
| DATA_DIR | Project-relative data folder | Local dataset root |
| CORS_ORIGINS | http://localhost:3000,http://localhost:5173 | Explicit frontend origins, comma separated |
| APP_ENV | development | Environment label |

## Data limits

- Four gridded sample locations near Masaka, Mbale, Gulu and Mbarara; these are not district averages or farm measurements.
- Historical coverage: 2016-2025. No current weather or forecasts.
- Wetness is a modelled 0-1 index, not soil fertility or a soil test.
- Crop rainfall requirements are annual; they do not establish seasonal irrigation demand.
- The map is a maize-only, low-input, rain-fed soil/terrain reference with a 2010 baseline. Its preview includes neighboring land and is not a georeferenced overlay.

## Tests

```bash
python -m pip install -r requirements-dev.txt
python -m pytest
```

See [the implementation brief](docs/BACKEND_BRIEF.md) for the full contract and [DEVELOPMENT.md](DEVELOPMENT.md) for stage progress.

## Sources and credits

Environmental series: NASA POWER, MERRA-2, GPM IMERG and SYN1DEG. Crop references: FAO GAEZ/ECOCROP. Maize map: FAO/IIASA GAEZ v4, with source catalogue terms recorded as CC-BY-NC-SA-4.0. Preserve the source records and attribution in the included dataset. No application license changes those dataset terms.

See [DATA_SOURCES.md](docs/DATA_SOURCES.md) for the challenge resource link, direct provider references, why each input is used, and the GAEZ/ECOCROP relationship.

AI assistance was used to implement and test this prototype. No agricultural review or field impact is claimed.

## Complete reference checks

The catalog now includes maize, beans, groundnut, sorghum, cotton, Arabica coffee, Robusta coffee, banana (Musa acuminata), sugarcane and vanilla. Supplementary FAO crop sheets and four HWSD topsoil estimates are saved locally with raw selected rows, source URLs, retrieval dates and hashes. See [the source update](docs/DATA_SOURCES.md).

Measured pH overrides the area estimate. Use `soil.use_area_estimate: false` to leave missing pH unknown. Planting and harvest dates must come from the farmer; the API does not invent a calendar. The response includes one concise conclusion and explicit gap types. Reference coverage is distinct from validated crop order. Perennial systems receive their own conclusion instead of seasonal replacement advice. The combined PDF uses the same conclusion as the interface.
