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

## Downloaded reference update, 15 November 2026

The live challenge page is still inaccessible to the retrieval tool. The existing user-supplied resource list names FAO GAEZ; FAO confirms that ECOCROP is integrated with GAEZ. The new files use that same source route, not an unrelated crop guide.

Six additional species references were downloaded from original FAO ECOCROP sheets: Arabica coffee (749), Robusta coffee (750), Musa acuminata banana (7848), sugarcane (1884), vanilla (2131), and cotton (1160). Raw HTML, retrieval time, exact URLs and SHA-256 values are in `supplemental/fao_crop_sheets/` and `supplemental/crop_download_manifest.json`. Sugarcane's life span is absent from its data sheet, so its original FAO crop-view description is also saved and cited. Life span and candidate eligibility are explicit: perennial crops are assessed but never generated as seasonal replacements; the cotton sheet includes annual and perennial life spans, so its broad cycle is checked for the declared seasonal plan. No local cultivar, market or succession validation is implied.

GAEZ's FAO soil reference links to HWSD. The FAO HWSD page, https://www.fao.org/land-water/resources/tools/databases/hwsd/en, directly links the HWSD2 database and raster archives. The downloaded files are **HWSD v2.0**, not the v2.2 release mentioned in newer GAEZ news. Their URLs and hashes are retained in `supplemental/soil_download_manifest.json`.

Only four sample-point estimates are needed at runtime. The raster cell containing each point selects its mapping unit. From the database, the extraction keeps the 0–20 cm layer and selects the component with the highest SHARE, breaking ties by SEQUENCE. No arithmetic pH average is used. Raw selected database rows and point coordinates are retained in `soil_selected_rows.json`; compact runtime values are in `soil_points.json`.

| Point | Mapping unit | Topsoil pH in water |
| --- | --- | --- |
| Masaka | 27533 | 5.5 |
| Mbale | 27569 | 6.7 |
| Gulu | 27473 | 5.1 |
| Mbarara | 27475 | 5.1 |

These are mapped estimates at approximately 1 km, not measurements from the farmer's field. A dominant mapped component may occupy less than half the mapping unit. A supplied measured pH takes precedence. A user can disable the estimate with `soil.use_area_estimate: false`. An estimated pH outside a crop range requests measurement rather than rejecting the crop as if the pH were certain.

Preparation scripts are `scripts/download_crop_references.py` and `scripts/download_soil_references.py`. Install their preparation-only dependencies with `python -m pip install -r scripts/requirements-data.txt`. Global ZIP/MDB files stay in an ignored preparation cache; source rows and all runtime inputs are committed. The API never fetches them at runtime. Original archive files and checksums remain unchanged.
