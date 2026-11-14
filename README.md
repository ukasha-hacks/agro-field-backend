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

Stages 1-3 provide local data loading, historical exploration, calculated descriptions and PDF export. Rotation comparisons follow on the final branch. Metadata reports which features are currently implemented.

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

The report recomputes through the same exploration service. It includes statistics, charts, descriptions, source records, limitations and the supplied static map reference. It never downloads map tiles, images or fonts. Invalid export requests return JSON errors, not a PDF.

The map preview labels all four locations; the report identifies the chosen location in text. It is not an animated weather map or a newly highlighted district. When the optional image is absent, export still works with coordinates and an explicit note.

A generated [Gulu 2024 sample report](examples/gulu-2024-report.pdf) is included for review.

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
