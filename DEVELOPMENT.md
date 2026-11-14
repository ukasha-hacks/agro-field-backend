# Development stages

Each stage is a cumulative branch so the last stage contains the earlier work. Main is left untouched until repository integration is explicitly completed.

| Branch | Scope | Status |
| --- | --- | --- |
| stage/01-foundation | Local data loading, validation, catalog and map references | Complete locally; 3 tests passed |
| stage/02-exploration | Daily/monthly analysis, summaries and replay data | Complete; 16 tests passed |
| stage/03-pdf-export | Local charts and matching PDF export | Complete; 19 tests passed |
| stage/04-rotation-comparison | Evidence-aware comparison and combined reports | Planned |

The repository was empty. Main contains a branch guide; each tested stage is published separately. Stage 1 was tested on Python 3.12.14 with the dependency versions in requirements files. The environment emits upstream HTTPX/TestClient and AnyIO deprecation warnings; the catalog checks pass.

Stage 2 adds strict selection validation, daily calendar reindexing, partial-month aggregates, daily-weighted statistics and deterministic evidence-linked descriptions. Source references and their selection rationale are in docs/DATA_SOURCES.md.

Stage 3 exports through the same exploration service, embeds locally shipped fonts, and includes the static GAEZ reference map with its baseline. All three pages of examples/gulu-2024-report.pdf were rendered and visually reviewed. Report tests also cover invalid client-calculated payloads and an absent optional map.
