# Requirements layout

This project uses a split dependency layout for clarity and reproducibility:

- `base.txt` — shared runtime dependencies used in both dev and production
- `dev.txt` — local development, debugging and code quality tooling
- `production.txt` — deployment/runtime requirements

Typical installs:

- Local dev: `python3 -m pip install -r requirements/dev.txt`
- Production: `python3 -m pip install -r requirements/production.txt`
- The Docker image installs `production.txt`, so nothing in `dev.txt` ships to
  the deployed container.

Notes:

- `races/settings/development.py` enables `django-debug-toolbar`; it is a
  development-only dependency and is deliberately absent from `base.txt` and
  `production.txt`. CI installs `dev.txt`.
- `vcrpy` backs the (currently disabled) ingest tests in
  `races/apps/cabici/tests/testingest.py`, using the cassettes in
  `fixtures/vcr_cassettes`.
- `psycopg[binary]` is only in `production.txt` because the deployed stack runs
  on PostgreSQL; `bin/develop.py` uses SQLite.
- Code quality tools (black, ruff, mypy, coverage, pre-commit) are pinned here
  and configured in `pyproject.toml`. Run `pre-commit install` once so they
  execute on commit.
- The former `django-geoposition` submodule is gone; the lat/long field now
  lives in `races/apps/cabici/geoposition.py`.
