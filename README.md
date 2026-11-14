# Agro Field backend

Implementation is being developed and tested on cumulative stage branches:

1. `stage/01-foundation` — local data, validation, catalog and map references.
2. `stage/02-exploration` — historical filters, graphs and descriptions.
3. `stage/03-pdf-export` — local charts and PDF reports.
4. `stage/04-rotation-comparison` — evidence-aware comparisons and combined reports.

Each branch has its own README and DEVELOPMENT.md. The final branch will contain all earlier stages. Main stays a branch guide; no application code is merged here automatically.

The runtime uses downloaded local data without live NASA or FAO calls. Dataset attribution and limitations are retained alongside the code.
