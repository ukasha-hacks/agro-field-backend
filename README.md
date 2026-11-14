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

Stage 1 provides health, metadata, locations, point GeoJSON, crop references and the reference-map preview. Exploration, PDF exports and rotation comparisons are the following stages. Metadata reports which features are currently implemented.

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

AI assistance was used to implement and test this prototype. No agricultural review or field impact is claimed.
