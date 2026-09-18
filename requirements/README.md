# Requirements layout

This project now uses a split dependency layout for clarity and reproducibility:

- `base.txt` — shared runtime dependencies used in both dev and production
- `dev.txt` — local development and debugging tools
- `production.txt` — deployment/runtime requirements

Typical installs:

- Local dev: `python3 -m pip install -r requirements/dev.txt`
- Production: `python3 -m pip install -r requirements/production.txt`

Notes:
- The local `./django-geoposition/` checkout remains pinned as a direct dependency because the app uses the custom `GeopositionField` model field.
- `django-debug-toolbar`, `vcrpy`, and `django-webtest` are intentionally kept out of production to avoid shipping tooling packages.
- Whitenoise is included in both dev and production because it is used by the app’s static file handling in both environments.
