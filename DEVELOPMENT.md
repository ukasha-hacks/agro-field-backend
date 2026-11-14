# Development stages

Each stage is a cumulative branch so the last stage contains the earlier work. Stages 1-3 have also been merged into main. Stage 4 is published separately for review.

| Branch | Scope | Status |
| --- | --- | --- |
| stage/01-foundation | Local data loading, validation, catalog and map references | Complete; 3 tests passed |
| stage/02-exploration | Daily/monthly analysis, summaries and replay data | Complete; 16 tests passed |
| stage/03-pdf-export | Local charts and matching PDF export | Complete; 19 tests passed |
| stage/04-rotation-comparison | Evidence-aware comparison and combined reports | Complete implementation; 36 tests passed |

The repository was empty when implementation began; each tested stage was published separately. Testing uses Python 3.12.14 with the dependency versions in requirements files. The environment emits two upstream HTTPX/TestClient and AnyIO deprecation warnings; all checks pass.

Stage 2 adds strict selection validation, daily calendar reindexing, partial-month aggregates, daily-weighted statistics and deterministic evidence-linked descriptions. Source references and their selection rationale are in docs/DATA_SOURCES.md.

Stage 3 exports through the same exploration service, embeds locally shipped fonts, and includes the static GAEZ reference map with its baseline. All three pages of examples/gulu-2024-report.pdf were rendered and visually reviewed. Report tests also cover invalid client-calculated payloads and an absent optional map.

Stage 4 validates farmer history and three-season plans, keeps the baseline visible, and supports versioned agricultural rules with explicit review status. Production rules remain pending: the default comparison returns insufficient evidence and explains the two unfilled alternative slots. Synthetic reviewed rules exercise the engine only in tests. No field suitability, yield, income or soil improvement is claimed.

Final verification covers all 43 original source-file checksums, startup/exploration/PDF export with network connections blocked, validation failures and missing optional maps. A real Uvicorn HTTP check verified health, exploration (Gulu 2024 rainfall: 1686.04 mm) and a four-page combined PDF. All four combined-report pages were rendered and visually reviewed. The API contract is saved in docs/openapi.json.
