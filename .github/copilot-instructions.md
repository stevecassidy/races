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

- **One branch per change, merged by pull request.** Nothing is committed or
  pushed directly to `modernization`
- **`modernization` is the integration branch** — it only advances by merging
  reviewed PRs
- **`master` stays stable for production** (critical fixes go via a `hotfix/*`
  branch and a PR to `master`)
- **Single deployment when complete** (not incremental)
- **No backward compatibility needed during development**
- **The existing `api.py` is being replaced, not extended** — see “API Rules” below

### Branch & Review Workflow

Every unit of work — normally one checklist section, often less — gets its own
short-lived branch off `modernization` and a PR back into it. The owner reviews
and merges.

```bash
# start from an up-to-date integration branch
git checkout modernization && git pull

# one branch per change: feature/ | fix/ | chore/ | refactor/ | docs/, named for the plan section
git checkout -b chore/phase2.1-model-constraints

# keep the gates green before pushing
ruff check . && black --check . && mypy races && python bin/runtests.py

git push -u origin HEAD        # then open a PR targeting modernization
```

Rules:

- **The assistant proposes work and stops at "PR ready for review"** — it does
  not merge, close, or push to `modernization`/`master`, and does not open the
  PR until asked to.
- Branch names carry the plan section (e.g. `feature/phase2.3-race-day-contract`)
  so history maps back to the checklist.
- Small, reviewable PRs: one logical change per commit, and the PR description
  states what is *behavioural* rather than mechanical.
- CI must be green before review is requested; rebase onto `modernization` if it
  has moved. Force-push only to your own feature branch, never to
  `modernization`.
- Deleting code is fine; changing model semantics, points maths, membership
  categories or API contracts is flagged prominently for review.

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

### When Working on Frontend (`frontend/` — monorepo, decided 2026-10-11)

Two React apps live in this repo under a pnpm workspace root:
`frontend/apps/raceday` (vendored from `stevecassidy/cabici-raceday-react` — the
offline, race-day entry app and the only way riders are created today) and
`frontend/apps/web` (the SPA replacing the Django template views). Both consume
`frontend/packages/api-client`.

1. **Never hand-write API types or calls** - import them from
   `packages/api-client`, generated from the server's OpenAPI schema. This is the
   control that prevents a repeat of D1/D2 (a hand-maintained payload key
   silently lost rider data across two repos)
2. **TypeScript** - all React code is typed
3. **Stack is fixed by the vendored app** - React 18 + Vite + **MUI** +
   react-hook-form + axios + Vitest. Not Bootstrap; not Tailwind
4. **TanStack Query for server state** - introduce in `apps/web` first; do not
   break `apps/raceday`'s offline `localStorage` + delta-sync behaviour
5. **Keep the two apps as separate deployables** - race day is high-stakes
6. **Changing an endpoint shape means changing the schema first**, then
   regenerating, then fixing both apps in the same commit

### Code Quality Standards

```bash
# Before committing, always run (or just `pre-commit run --all-files`):
black .                      # Format Python code
ruff check --fix .          # Lint and fix Python
mypy races                  # Type check
python bin/runtests.py      # Run tests (uses races/settings/testing.py)
coverage run bin/runtests.py && coverage report   # Coverage gate (floor 42%)
```

### Commit & PR attribution

Assistant attribution must name the model **actually running**. Check it rather
than assuming:

```bash
env | grep -E '^PI_MODEL=|^PI_PROVIDER='
```

- Footer form, in commit messages and PR bodies:

  ```
  Assisted by: <model name> (<PI_MODEL> via <PI_PROVIDER>)
  ```

- **Do not** use a `Co-Authored-By:` trailer for the assistant — GitHub resolves
  it to a real account, so it means inventing an identity and an email address.
- **Never** name a model that is not the one in the session. Attributing work to
  the wrong model is a factual error in the permanent record, not a courtesy.

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
the withdrawn AusCycling polling — 2,742 measured lines) → **2.1 Model Hardening** →
**2.2 Vendor & audit the race-day React app** (it moves into `frontend/`, and its
upload path currently loses data — D1/D2/D3) → 2.3 Resource model & OpenAPI
contract for **both** clients → 2.4 Auth (JWT same-origin, CORS deleted, token
auth kept until Angular retires) → 2.5 CRUD →
2.6 Docs → 2.7 Tests + delete `api.py`. Findings it acts on (A1-A9 and D1-D4
defects, B1-B9 integrity, C1-C12 structure) are numbered in
[MODEL_REVIEW.md](../MODEL_REVIEW.md).

**Each numbered section lands as its own branch + PR.** Note that **2.0 already
merged directly into `modernization` (`c6e89b0`) before this workflow was
adopted**; everything from 2.1 onward goes through review.

## Important Notes

### DO:

✅ Propose a branch off `modernization` and a PR for each change
✅ Run the gates locally (`ruff`, `black --check`, `mypy`, tests) before pushing
✅ Follow the modernization plan
✅ Write modern Django 5.2 code
✅ Build API endpoints, not template views
✅ Use type hints in Python
✅ Write comprehensive tests
✅ Check the plan before making architectural decisions

### DON'T:

❌ Commit or push directly to `modernization` — branch and open a PR
❌ Merge a PR, or approve work on your own behalf — the owner reviews and merges
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

### Frontend Structure (monorepo)

```
frontend/
  package.json          # pnpm workspaces root
  packages/
    api-client/         # GENERATED from the OpenAPI schema - the only sanctioned
                        # way to call the API
    ui/                 # shared components (only with a real 2nd consumer)
  apps/
    raceday/            # vendored offline entry app (apps/raceday): the upload path
    web/                # new SPA replacing the Django views
```

## API Rules

The pre-existing `races/apps/cabici/api.py` was built ad-hoc for the jQuery
screens and is **replaced, not extended** (rationale and evidence:
[MODEL_REVIEW.md](../MODEL_REVIEW.md)). When building the new API:

- **Angular is deployed; the React app is not.** The race-day entry app in
  production is the **Angular 8** app (`cabici-raceday`). The React rewrite
  (`frontend/apps/raceday`, vendored into this repo) is **unfinished** and
  predates the server work. So the new results endpoint **must keep accepting
  what Angular sends unchanged**, and **DRF token auth stays alive until Angular
  is deliberately retired after cutover** — it is not deleted when the React app
  is vendored.
- **The race-day upload path is the highest-risk surface in the app.** The React
  client posts `{race, entries[], newriders[]}` while `api.py` reads
  `data["riders"]` (D1: rider creations silently lost) and returns `rider` as a
  display string where the client expects an ID (D2: downloads always come back
  empty); the server also has **no permission class and no transaction**, so any
  authenticated user can replace a race's results and a mid-request failure
  leaves them half-populated (D3). D1/D2 are React-only, so not live — **D3's
  server half and A9 (`grade_change` compared to `"y"` while both clients send a
  boolean, so in-race grade changes have never applied in production) are real.**
  Fix with regression tests that exercise the **real HTTP boundary**, and treat
  the Angular `entry.service.ts` as the reference implementation of the wire
  format.
- **Offline is a hard API constraint.** `apps/raceday` does a full paginated rider
  load, caches it in `localStorage`, and refreshes with `?changed=<unix>`, merging
  by rider ID. Any replacement (`?updated_after=`) must preserve all of that and
  must not silently drop deleted riders.
- **Offline is a requirement.** `apps/raceday` does a full paginated rider load,
  caches it in `localStorage`, and refreshes with `?changed=<unix>`, merging by
  rider ID. Any replacement (`?updated_after=`) must preserve all of that.
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
  are deleted in Phase 2.0. Never add new code that reaches for them.
- **Membership has two tracks.** Local, at-the-track verification (storing a
  verified date, honouring `member_category`/`verifiedMemberDate` on upload) is
  **unblocked and goes first** — the React app already ships that flow and the
  server ignores it, so production currently has no verification at all. Provider
  integration is **blocked** on the new AusCycling API's spec; design the seam so
  it supplements local verification rather than rewriting it, and never put a
  provider client secret in a model field.
- **Same-origin deployment.** Django serves both SPA builds via WhiteNoise, so
  **there is no CORS** — do not reintroduce `corsheaders` or `CORS_*` settings.
  Refresh token in an httpOnly SameSite cookie, access token in memory; never
  bearer-in-`localStorage`. `apps/raceday` mounts on a subpath (`/raceday/`).

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
