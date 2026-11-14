# Development stages

Each stage is a cumulative branch so the last stage contains the earlier work. Main is left untouched until repository integration is explicitly completed.

| Branch | Scope | Status |
| --- | --- | --- |
| stage/01-foundation | Local data loading, validation, catalog and map references | Complete locally; 3 tests passed |
| stage/02-exploration | Daily/monthly analysis, summaries and replay data | Planned |
| stage/03-pdf-export | Local charts and matching PDF export | Planned |
| stage/04-rotation-comparison | Evidence-aware comparison and combined reports | Planned |

The repository was empty. Main contains a branch guide; each tested stage is published separately. Stage 1 was tested on Python 3.12.14 with the dependency versions in requirements files. The environment emits upstream HTTPX/TestClient and AnyIO deprecation warnings; the catalog checks pass.
