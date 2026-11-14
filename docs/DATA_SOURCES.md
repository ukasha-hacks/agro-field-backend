# Data sources: origin, purpose and limits

The allowed resource list is the user's supplied Field Shift resource page:

https://www.spaceappschallenge.org/2026/challenges/adapting-farms-with-nasa-data/?tab=resources

The source page could not be fetched during data preparation or the latest verification attempt. The user supplied its resource text; that unchanged text is retained at `data/Field_Shift_Relevant_Data/provenance/user_supplied_resources.txt`. This limitation is recorded rather than claiming that the live page was successfully inspected. No third-party mirror supplied the dataset values.

| Listed resource | Local inputs | Why we use it | What it cannot establish |
| --- | --- | --- | --- |
| NASA POWER | Temperature, MERRA-2 wetness, humidity, wind and solar radiation in the daily CSV | Historical growing conditions; supporting meteorology | Farm soil fertility, actual crop yields, current weather or future conditions |
| GPM / IMERG | IMERG_PRECTOT rainfall, delivered through the listed NASA POWER service | Rainfall totals and historical variability | Measured rainfall on each farm, crop water requirement or irrigation demand by itself |
| FAO GAEZ | Maize soil/terrain suitability raster, legend and point extracts | Spatial soil/terrain reference for rain-fed maize under low inputs | Suitability for every crop, measured soil pH, or present-day soil health |
| FAO GAEZ's linked ECOCROP reference | Four species requirement records and their original FAO sheets | Temperature, annual rainfall, pH and broad maturity reference ranges | Locally validated crop calendars or a proven rotation |

ECOCROP is accessed through GAEZ's crop-reference links, rather than being an independently added source. FAO documents that integration at https://www.fao.org/land-water/resources/tools/databases/ecocrop/en. This distinction matters: ECOCROP is a legacy reference database, not a new NASA measurement product.

## Direct provider references

- NASA POWER: https://power.larc.nasa.gov/
- Download service: https://power.larc.nasa.gov/api/temporal/daily/point
- GPM/IMERG: https://gpm.nasa.gov/data
- GAEZ: https://gaez.fao.org/
- GAEZ soil/terrain catalogue: https://data.fao.org/catalog/iso/fd3fc7ff-07d3-477a-a905-c46dbecc9dcc
- ECOCROP entry in GAEZ: https://gaez.fao.org/pages/ecocrop-find-plant

The NASA raw responses, request URLs, retrieval dates, units and source metadata are under `provenance/nasa_raw/` and `provenance/nasa_manifest.json`. The GAEZ raster download URL and metadata are in `provenance/fao_map_download.json`. Original crop sheets and class descriptions are under `provenance/fao_sources/`. The source URLs are retained for attribution; the application never calls them.

## What stays separate

Farmer answers are user inputs, not downloaded observations. Agricultural rules must cite an applicable source and retain their review status. Test fixtures are synthetic, labelled test data and never returned as production measurements. Python packages are implementation dependencies, not additional agricultural datasets.

No unrelated soil, weather, boundary, price or crop-yield dataset is added. Further datasets require an explicit scope decision. `resources_scope.csv` records the remaining listed resources and why they were deferred, including entries whose supplied descriptions are limited to the United States.

The GAEZ map catalogue states CC-BY-NC-SA-4.0. Preserve attribution and the applicable source terms. No NASA or FAO endorsement is implied.
