# GitHub Copilot Instructions for Cabici Project

## Project Context

This is the Cabici cycling race management application, currently undergoing a comprehensive modernization.

## 🚧 Active Modernization Project

**Critical:** This project is in active modernization from Django 4.2 + jQuery to Django 5.2 + React.

**Status (2026-10-11):** Phase 1 (Foundation) is complete — Django 5.2 / Python 3.14,
clean-install boot verified, black + ruff + mypy + coverage gated in CI on the
`modernization` branch. Work now starts at Phase 2.1 (API audit & planning). See
[MODERNIZATION_CHECKLIST.md](../MODERNIZATION_CHECKLIST.md) → "Phase 1 Exit Notes"
for verified state and carried-forward debt.

### Key Documents

- **[MODERNIZATION_README.md](../MODERNIZATION_README.md)** - Project overview
- **[MODERNIZATION_PLAN.md](../MODERNIZATION_PLAN.md)** - Detailed implementation plan
- **[MODERNIZATION_CHECKLIST.md](../MODERNIZATION_CHECKLIST.md)** - Task tracking
- **[MODEL_REVIEW.md](../MODEL_REVIEW.md)** - Model & API review (Phase 2 basis)
- **[TECHNICAL_ASSESSMENT.md](../TECHNICAL_ASSESSMENT.md)** - Current state analysis

### Development Strategy

- **All modernization work happens on `modernization` branch**
- **`master` branch stays stable for production**
- **Single deployment when complete** (not incremental)
- **No backward compatibility needed during development**
- **The existing `api.py` is being replaced, not extended** — see “API Rules” below

## Technology Stack

### Current (Legacy - Being Replaced)

- Django 4.2.23
- jQuery 3.3.1 + Bootstrap 3
- Django templates
- Token authentication

### Target (Under Development)

- Django 5.2
- React 18 + TypeScript
- Vite build tool
- JWT authentication
- Complete REST API

## Development Guidelines

### When Working on Backend (`races/` directory)

1. **Check current phase** in MODERNIZATION_CHECKLIST.md
2. **Follow Django 5.2 patterns** - Use modern conventions
3. **API-first approach** - Build REST endpoints, not template views
4. **Remove template code** - Templates are being eliminated
5. **Use JWT for API auth** - Not session auth (except admin)
6. **Do not add endpoints to `races/apps/cabici/api.py`** - it is frozen and
   scheduled for deletion; new work goes in the `api/` package (see API Rules)

### When Working on Frontend (Future `cabici-frontend/` directory)

1. **Use TypeScript** - All React code should be typed
2. **React Query for API state** - Use TanStack Query
3. **Tailwind or MUI for styling** - Not Bootstrap
4. **Component-based architecture** - Reusable components
5. **API client in `/src/api/`** - Centralized API calls

### Code Quality Standards

```bash
# Before committing, always run (or just `pre-commit run --all-files`):
black .                      # Format Python code
ruff check --fix .          # Lint and fix Python
mypy races                  # Type check
python bin/runtests.py      # Run tests (uses races/settings/testing.py)
coverage run bin/runtests.py && coverage report   # Coverage gate (floor 42%)
```

### Testing Requirements

- **Write tests for all new code**
- **Maintain >80% coverage**
- **API endpoints must have tests**
- **React components need component tests**

## Current Phase

Check [MODERNIZATION_CHECKLIST.md](../MODERNIZATION_CHECKLIST.md) for current phase and progress.

**Phases:**

1. Foundation & Django Upgrade (Weeks 1-4) — ✅ complete 2026-10-11
2. Backend API Rebuild (Weeks 5-12) — **current**; starts with a retirement pass
3. React Frontend Development (Weeks 13-26)
4. Integration & Deployment (Weeks 27-32)
5. Optimization (Weeks 33-38)

Phase 2 runs **2.0 Retirement Pass** (delete the out-of-date ingest pipelines and
the withdrawn AusCycling polling — ~2,400 lines) → **2.1 Model Hardening** →
**2.2 The Race-Day Contract** (the one frozen external contract, designed before
the general API). Findings it acts on (A1-A9 defects, B1-B9 integrity, C1-C12
structure) are numbered in [MODEL_REVIEW.md](../MODEL_REVIEW.md).

## Important Notes

### DO:

✅ Work on `modernization` branch
✅ Follow the modernization plan
✅ Write modern Django 5.2 code
✅ Build API endpoints, not template views
✅ Use type hints in Python
✅ Write comprehensive tests
✅ Check the plan before making architectural decisions

### DON'T:

❌ Add new template views (we're removing them)
❌ Add endpoints to the legacy `races/apps/cabici/api.py` (it is frozen, then deleted)
❌ Use `fields = '__all__'` on a serializer
❌ Use jQuery or Bootstrap 3 (being replaced)
❌ Make changes to `master` branch (except critical fixes)
❌ Add features that aren't in the plan (discuss first)
❌ Skip tests
❌ Use deprecated Django patterns

## File Organization

### Backend Structure

```
races/
  apps/
    cabici/
      models.py           # merged domain models (usermodel.py folded in, Phase 2.0)
      services/           # domain operations: ingest, results, pointscore,
                          # officials, membership, exports
      api/\                # REST API (new structure)
        routers.py        # /api/v1/ wiring
        serializers/      # DRF serializers
        views/            # API ViewSets
        filters/          # django-filter FilterSets
        permissions.py
        pagination.py
      tests/              # Test files
```

### Frontend Structure (To Be Created)

```
cabici-frontend/
  src/
    api/              # Generated + hand-written API client
    components/       # Reusable components
    features/         # Feature modules
      clubs/
      races/
      riders/
    hooks/            # Custom hooks
    pages/            # Page components
```

## API Rules

The pre-existing `races/apps/cabici/api.py` was built ad-hoc for the jQuery
screens and is **replaced, not extended** (rationale and evidence:
[MODEL_REVIEW.md](../MODEL_REVIEW.md)). When building the new API:

- **The race-day contract is frozen.** The external race-day entry application
  (not in this repo) authenticates with a DRF token, downloads
  `GET /clubs/<slug>/riders.xlsx`, and posts `POST /api/raceresults/` with
  `{race, entries[], riders[]}` expecting `{message, errors, ridermap}`. It is
  the app's only rider-creation path. Reproduce it compatibly until it is
  formally retired — do **not** treat it as free to redesign.
- **Contract-first.** Define the resource, filters and payload shapes in the
  OpenAPI spec before implementing; the React client is generated from it.
- **Never `fields = '__all__'`.** Declare read and write shapes explicitly.
- **One identifier per concept.** A rider is `Rider.id` everywhere (the old API
  used `Rider.id`, `User.id` and a display string interchangeably under the same
  key names).
- **Filters are filters.** Use `django-filter` FilterSets + search/ordering
  backends, not per-view query params like `?select=future` or `?count=10`.
- **Domain operations are actions**, backed by `services/`, wrapped in
  `transaction.atomic()`, permission-checked, and tested for their failure paths.
- **No 500s for expected client errors.** Unknown email → 401, missing Rider →
  403, bad payload → 400, duplicate → 409.
- **Single tenant.** WMCC is the only client club. Do not design generic
  multi-club RBAC; permissions answer “is this an official of the club that owns
  this object?”.
- **Retired subsystems.** The ingest pipelines and AusCycling membership polling
  are deleted in Phase 2.0. Never add new code that reaches for them; the
  replacement membership provider is TBD.

### API Pattern

```python
from rest_framework import viewsets, filters
from rest_framework.decorators import action

class RaceViewSet(viewsets.ModelViewSet):
    queryset = Race.objects.select_related('club', 'location').all()
    serializer_class = RaceSerializer
    permission_classes = [CanManageClub]
    filterset_class = RaceFilter
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'location__name']

    @action(detail=True, methods=['post'])
    def upload_results(self, request, pk=None):
        # delegates to services.results; atomic; returns typed errors
        pass
```

## Authentication

### For API Endpoints

- Use JWT authentication (`djangorestframework-simplejwt`)
- Include `Authorization: Bearer <token>` header
- Session auth only for admin panel

### For React Frontend

- Store JWT in memory or httpOnly cookie
- Implement token refresh
- Redirect to login on 401

## Questions or Unclear?

1. Check [MODERNIZATION_PLAN.md](../MODERNIZATION_PLAN.md) for detailed guidance
2. Review [TECHNICAL_ASSESSMENT.md](../TECHNICAL_ASSESSMENT.md) for current state
3. Look at existing code patterns in the modernization branch
4. When in doubt, follow Django and React best practices

## Useful Commands

```bash
# Development
python bin/develop.py runserver
python bin/runtests.py
python bin/develop.py makemigrations
python bin/develop.py migrate

# Code quality
black .
ruff check --fix .
mypy races
pre-commit run --all-files

# React (when available)
npm run dev
npm test
npm run build
```

---

**Remember:** We're building a modern, maintainable application. Quality over speed!
