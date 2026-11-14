# Field Shift: relevant inputs and outputs for the Uganda prototype

This pack contains downloaded environmental data, extracted crop reference data, a modelled soil/terrain map, and calculated graph tables. All external data comes from resources named in your supplied challenge resource list: NASA POWER, GPM/IMERG, and FAO GAEZ. ECOCROP is accessed through the GAEZ platform's crop-reference links. No third-party mirror data, external district boundaries, invented farmer records, or invented rotation scores are included.

## What is ready

| Part | Included | Use |
| --- | --- | --- |
| Environmental inputs | 14,612 daily records, nine variables, four locations, 2016-2025 | Understand historical growing conditions |
| Crop inputs | Four species reference records: maize, common bean, groundnut and sorghum | Compare crop temperature, annual rainfall, pH and growth-cycle reference ranges |
| Map inputs | Four sample points and one GAEZ v4 soil/terrain suitability GeoTIFF for rain-fed maize under low inputs | Select a location and display a documented modelled suitability layer |
| Graph outputs | 480 monthly rows, 40 annual rows, 48 seasonal-pattern rows | Draw historical line graphs |
| Point-map outputs | December 2025 environmental point GeoJSON and maize map values sampled at the four points | Show labelled historical values at selectable points |
| Farmer inputs | Four empty CSV templates and a JSON input schema | Collect information that satellites cannot provide |
| Rotation output | A three-strategy JSON structure with uncomputed values | Define the eventual comparison response without inventing advice |

## Open these first

1. `inputs/maps/sample_locations.geojson`: four selectable points.
2. `outputs/monthly_line_graphs_2016_2025.json`: monthly values ready for an API/frontend.
3. `inputs/crops/crop_reference_requirements.csv`: extracted crop-reference inputs.
4. `inputs/maps/gaez_v4_maize_soil_terrain_low_inputs.tif`: the spatial soil/terrain layer.
5. `farmer_inputs/`: collect actual farmer information.
6. `input_output_dictionary.csv`: field definitions and availability.
7. `resources_scope.csv`: every listed resource and why it was included or deferred.

The `previews` folder demonstrates graphs and the thematic map using the included values. These are examples of presentation, not forecasts or crop recommendations.

## 1. Downloaded environmental inputs

Source: NASA POWER daily point API. Rainfall is the IMERG parameter delivered through NASA POWER, rather than a separate download of GPM granules. Temperature, humidity, wind and wetness have MERRA-2 provenance; solar radiation has SYN1DEG provenance in the returned NASA metadata.

| Variable | Source parameter | Units | Monthly calculation |
| --- | --- | --- | --- |
| Mean air temperature | T2M | degrees C | Average daily mean temperatures |
| Minimum air temperature | T2M_MIN | degrees C | Lowest daily minimum in the month |
| Maximum air temperature | T2M_MAX | degrees C | Highest daily maximum in the month |
| Rainfall | IMERG_PRECTOT | mm/day | Sum of daily one-day depths, reported in mm/month |
| Surface wetness | GWETTOP | dimensionless 0-1 | Average |
| Root-zone wetness | GWETROOT | dimensionless 0-1 | Average |
| Relative humidity | RH2M | percent | Average |
| Wind at 2 metres | WS2M | m/s | Average |
| Solar radiation | ALLSKY_SFC_SW_DWN | MJ/m2/day | Average daily radiation |

The first six variables are sufficient for the initial environmental dashboard. Humidity, wind and radiation are supporting inputs for a later, documented water-use model. This pack does not calculate evapotranspiration or crop irrigation requirements.

Wetness is a modelled relative-saturation index. It is not laboratory soil moisture, soil pH, nutrient content or a soil-health score. No separate SMAP observations are included. NASA POWER's meteorological grid is approximately 0.5 degrees latitude by 0.625 degrees longitude; IMERG rainfall is approximately 0.1 degrees. The coordinates do not imply farm-scale precision.

### Location coverage

| Sample ID | Vicinity | Latitude | Longitude |
| --- | --- | --- | --- |
| central_masaka | Masaka | -0.337 | 31.737 |
| eastern_mbale | Mbale | 1.080 | 34.175 |
| northern_gulu | Gulu | 2.774 | 32.299 |
| western_mbarara | Mbarara | -0.607 | 30.655 |

These are analyst-selected prototype points inherited from the earlier prototype, not official district centroids or actual farm boundaries. The region labels are navigation labels. A sample does not represent the average of its district or region. For another farm, request data at that farm's actual coordinates.

## 2. Crop reference inputs

The four records were extracted directly from FAO ECOCROP data sheets linked through GAEZ. Each record carries its source URL and ECOCROP identifier. Original downloaded HTML is retained in `provenance/fao_sources`.

Available fields include optimal/absolute temperature ranges, optimal/absolute annual rainfall ranges, optimal/absolute soil pH ranges, broad crop-cycle length, and soil texture/drainage descriptions where supplied.

Important distinctions:

- Rainfall ranges are **annual rainfall**, not crop-season water requirements. Do not compare them directly with one month's rainfall or relabel them seasonal water demand.
- Crop-cycle ranges cover different cultivars and environments. They are not Uganda-specific maturity dates or a validated planting calendar.
- Blank source descriptions remain blank. Nitrogen fixation amounts, pest-break benefits, residue production and local market profitability have not been fabricated.
- These records support reference screening. They do not validate a rotation or guarantee yield.
- ECOCROP is a legacy reference database; the FAO platform notes it was discontinued around 2015. Local review remains necessary.

## 3. Map inputs and outputs

The GAEZ v4 raster is **soil and terrain suitability for rain-fed maize under low-input management**. It is approximately 1 km resolution, referenced to GAEZ v4's land-resource baseline, not a present-day farm measurement or an assessment for every crop.

The supplied rectangular study window covers the Uganda area and neighboring territory. It is not clipped to an official Uganda boundary. No district or region polygons are supplied, because a verified boundary dataset was not obtained from the named resources during this extraction. You can select the four points immediately. Administrative area highlighting needs a separately verified boundary source within your permitted resources.

Use `gaez_maize_map_legend.csv` to interpret native class codes. Lower class numbers represent higher suitability for classes 1-7; class 8 means not suitable; class 9 means water. Do not interpret the codes as a 1-10 soil-health score. The class captions and colors come from FAO metadata and the original raster palette.

The output uses Int16 with nodata -9 so the source's out-of-range Byte nodata setting is not silently clamped onto a valid class. Pixel values are preserved. The four point extracts were checked against the original remote raster.

## 4. Farmer inputs to collect

These are empty templates, not downloaded observations:

| Template | Information to collect |
| --- | --- |
| farmer_profile_template.csv | Actual location, water supply, main priority, preferred/excluded crops, budget, equipment and market constraints |
| crop_history_template.csv | Crop order, varieties, planting/harvest dates and observed problems |
| soil_measurements_template.csv | pH, organic carbon, texture, drainage, date and source, if known |
| local_crop_validation_template.csv | Locally relevant maturity periods, seasonal water needs, crop family, nitrogen-fixing status, markets and agricultural review |

Allow unknown soil values. Do not replace missing measurements with NASA wetness values. Annual rainfall requirements do not fill the seasonal-water fields.

## 5. Presenting the outputs

- Location selection: select a point, then filter all time series by `sample_id`.
- Rainfall line graph: X = month; Y = `rainfall_total_mm`.
- Temperature line graph: X = month; Y = `temperature_mean_c`; optional lines for the monthly minimum and maximum have their distinct extreme-value meaning.
- Wetness line graph: X = month; Y = surface/root-zone wetness, displayed as indices from 0 to 1.
- Use separate panels for different units. Do not sum temperatures or wetness.
- Use annual totals and annual means from `annual_line_graphs_2016_2025.csv` to compare years.
- Use the seasonal-pattern table to show a typical month averaged over the available ten years. Label it a **2016-2025 historical average**, not a 30-year climate normal.
- Point-map GeoJSON is labelled December 2025. It is historical, not current weather.
- Display map suitability separately from changing environmental observations because they have different dates, resolutions and meanings.

## 6. Rotation outputs that still need computation

`rotation_comparison_output_template.json` defines three slots: the existing rotation, alternative 1 and alternative 2. Crop sequences, planting windows, benefits and trade-offs are null because the farmer's actual rotation, local crop evidence and agricultural rules have not been supplied. This is an output contract, not a completed recommendation.

A responsible next stage is to populate farmer inputs, validate crop varieties locally, define explainable rotation rules and compare options. Yield increases, profits, erosion reduction and soil improvement cannot be inferred from the downloaded series alone.

## Sources and verification

The official challenge resource page could not be fetched in this session. Your attached resource-list text is preserved unchanged as the source-selection record. No mirror was substituted. Download URLs, retrieval times, NASA metadata, FAO map metadata and original crop sheets are retained under `provenance`.

- NASA POWER: https://power.larc.nasa.gov/
- NASA daily API documentation: https://power.larc.nasa.gov/docs/services/api/temporal/daily/
- GPM/IMERG: https://gpm.nasa.gov/data
- FAO GAEZ: https://gaez.fao.org/
- GAEZ soil/terrain catalogue: https://data.fao.org/catalog/iso/fd3fc7ff-07d3-477a-a905-c46dbecc9dcc
- ECOCROP entry in GAEZ: https://gaez.fao.org/pages/ecocrop-find-plant
- FAO's ECOCROP integration description: https://www.fao.org/land-water/resources/tools/databases/ecocrop/en

Credit NASA POWER, MERRA-2, GPM IMERG and SYN1DEG for the environmental series, and FAO/IIASA for GAEZ. The GAEZ soil/terrain catalogue states CC-BY-NC-SA-4.0; retain its attribution and terms when reusing that layer. This pack does not grant a different license over downloaded source datasets.

`validation_report.json` records data checks. `checksums.sha256` supports integrity checks on the finished files. All graph aggregates require complete daily coverage for the relevant variable. Missing values would remain blank/null rather than becoming zeros.
