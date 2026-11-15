# Development stages

Each stage is a cumulative branch so the last stage contains the earlier work. Use main for the current backend and matching frontend. Stage branches retain the earlier implementation.

| Branch | Scope | Status |
| --- | --- | --- |
| stage/01-foundation | Local data loading, validation, catalog and map references | Complete; 3 tests passed |
| stage/02-exploration | Daily/monthly analysis, summaries and replay data | Complete; 16 tests passed |
| stage/03-pdf-export | Local charts and matching PDF export | Complete; 19 tests passed |
| stage/04-rotation-comparison | Evidence-aware comparison and combined reports | Complete implementation; 36 tests passed |
| stage/05-readable-pdf | Embedded DM Sans, report layout and backend learning guide | Complete; 37 tests passed |
| stage/06-local-rules | Local species-range checks and explicit reference-only options | Complete; 53 tests passed |

The repository was empty when implementation began; each tested stage was published separately. Testing uses Python 3.12.14 with the dependency versions in requirements files. The environment emits two upstream HTTPX/TestClient and AnyIO deprecation warnings; all checks pass.

Stage 2 adds strict selection validation, daily calendar reindexing, partial-month aggregates, daily-weighted statistics and deterministic evidence-linked descriptions. Source references and their selection rationale are in docs/DATA_SOURCES.md.

Stage 3 exports through the same exploration service, embeds locally shipped fonts, and includes the static GAEZ reference map with its baseline. All three pages of examples/gulu-2024-report.pdf were rendered and visually reviewed. Report tests also cover invalid client-calculated payloads and an absent optional map.

Stage 4 validates farmer history and three-season plans, keeps the baseline visible, and supports versioned agricultural rules with explicit review status. Production rules remain pending: the default comparison returns insufficient evidence and explains the two unfilled alternative slots. Synthetic reviewed rules exercise the engine only in tests. No field suitability, yield, income or soil improvement is claimed.

Final verification covers all 43 original source-file checksums, startup/exploration/PDF export with network connections blocked, validation failures and missing optional maps. A real Uvicorn HTTP check verified health, exploration (Gulu 2024 rainfall: 1686.04 mm) and a four-page combined PDF. All four combined-report pages were rendered and visually reviewed. The API contract is saved in docs/openapi.json.

Stage 5 changes presentation only. It bundles DM Sans regular and bold under the SIL Open Font License, uses those fonts for PDF text and Matplotlib labels, and improves table spacing, wetness labels, dates and source page breaks. Statistics, endpoints, source files, agricultural rules and analysis identifiers retain their existing meaning. The regenerated combined sample has five pages, all rendered and visually reviewed. A new test checks actual embedded font data as well as the plain wetness units. All 37 backend tests pass. The learning guide in docs/BACKEND_GUIDE.md explains strict coverage, daily weighting, candidate selection and the pending-rule limitation with worked examples.

## Stage 6: local reference-based options

Enabled pH, minimum-cycle and historical-temperature checks from the existing crop/environment CSVs. No original data bytes or source URLs changed. Added reference_only response status, distinct exploratory crop combinations, explanations and source links. Reviewed agricultural rules stay pending; unsupported starting systems are retained without automatic replacement. The PDF carries the same label and evidence gaps. Paired frontend: stage/07-local-options.

Validation: 53 backend tests pass, covering boundary pH, dates, mixtures, unsupported crops, missing temperature, display-topic independence, preferences, exclusions, deterministic output, reference mode disabled, original file checksums and offline requests. These checks validate the software, not agronomic outcomes.

## Stage 7: downloaded references and clear conclusions

Added six FAO crop sheets, explicit perennial handling, and four HWSD v2.0 topsoil pH estimates from FAO-linked archives. Original source files are unchanged. Corrected whole-sequence reference coverage and separated unvalidated succession evidence. Added explicit gap types and a concise shared conclusion for the API, frontend and PDF. A measured pH takes priority; estimates can be disabled and never become farm measurements. Paired frontend: stage/08-clear-rotation-answer.

Validation: 70 backend tests pass, including all ten crop choices, original and new source integrity, soil-row provenance, measured-pH precedence, estimate opt-out, missing data, cotton duration, actual date checks, perennial safety and offline requests.

## Stage 8: complete plan inputs

Paired with frontend stage/09-plan-input-checks. Unknown planned crops now return needs_input, the affected season numbers and no premature alternatives. Unknown past crops remain valid. Optional planned_days lets farmers check minimum crop duration without inventing dates. Supplied date pairs take priority; known overlaps fail even when another season has no dates. Fallow is recorded without pretending crop-reference coverage passed. Reviewed agronomic rules remain pending.

Validation: 82 backend tests pass, including minimum-cycle boundaries, date precedence, partial calendar overlaps, incomplete plans, fallow, original source integrity and offline operation.

## Stage 9: deployed frontend access

The default CORS list now includes https://agrofields.vercel.app and local Next.js development on localhost or 127.0.0.1. Explicit CORS_ORIGINS values still replace the defaults, with surrounding spaces and trailing slashes removed. The README records both Vercel environment settings and connection checks. The existing GET/POST and Content-Type policy is retained.

Validation: 88 backend tests pass. New checks cover real catalog responses, JSON submission preflight, other origins and configured-origin normalization. The matching frontend production smoke also passes against this backend, including historical graphs, rotation assessments and a combined PDF.
