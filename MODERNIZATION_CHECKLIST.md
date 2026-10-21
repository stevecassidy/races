# Django Modernization - Quick Reference Checklist

This is a condensed checklist version of the full modernization plan. Use this for quick tracking of progress.

**Development Approach:** Work happens on short-lived branches cut from
`modernization`, each landing as a reviewed pull request. `modernization` is the
integration branch and is never committed to directly. Production remains stable
on `master` until final deployment when complete. See
[MODERNIZATION_PLAN.md](MODERNIZATION_PLAN.md) → Branch Strategy for the loop and
naming convention.

> **Adopted 2026-10-12.** Phase 1 and the 2.0 retirement pass (`c6e89b0`) are
> already on `modernization` from before this rule existed. Everything from 2.1
> onward: branch → PR → review → merge.

## ✅ Phase 1: Foundation (Weeks 1-4)

### Django Upgrade
- [x] Create modernization branch (`git checkout -b modernization`)
- [x] Backup production database
- [x] Update requirements.txt: Django 5.2
- [x] Run migrations in test environment
- [x] Fix deprecation warnings
- [x] Update URL patterns (re_path → path)
- [x] Run full test suite

### Dependency Updates
- [x] Remove obsolete frontend packages (Bootstrap, jQuery, etc.)
- [x] Remove django-bootstrap-form
- [x] Remove django-pagination
- [x] Update django-allauth
- [x] Update django-cors-headers
- [x] Update djangorestframework
- [x] Update gunicorn, whitenoise
- [x] Pin all versions
- [x] Test application functionality

### Code Quality
- [x] Install and configure Black
- [x] Install and configure ruff
- [x] Set up pre-commit hooks
- [x] Configure GitHub Actions CI
- [x] Run formatters on codebase
- [x] Fix linting issues (legacy debt quarantined, see below)
- [x] Add mypy for type checking (shallow: `check_untyped_defs = false`)

### Phase 1 Exit Notes (2026-10-11)

Verified on a throwaway virtualenv built from `requirements/dev.txt`:

```bash
ruff check .                 # clean
black --check .              # clean
python bin/develop.py check  # no issues
python bin/develop.py makemigrations --check --dry-run   # no changes
mypy races                   # no issues (68 files)
python bin/runtests.py       # 49 tests, OK, 1 skipped
coverage report              # 44% (CI floor 42%)
```

What the phase actually uncovered and fixed (the branch did **not** boot on a
clean install before this):

1. `bootstrapform` was still in `INSTALLED_APPS` after the package was dropped →
   `ModuleNotFoundError` for CI, Docker and any new developer.
2. `debug_toolbar` was wired into the shared base settings but only installed in
   `dev.txt` → same failure for production settings.
3. `0001_initial` still imported `geoposition.fields` (submodule removed) → any
   `migrate` on a clean install crashed.
4. The vendored `GeopositionField` lost its descriptor, so in-memory instances
   held strings while reloaded ones held `Geoposition` (failing test).
5. `SECRET_KEY` was a committed literal; it now comes from the environment and
   production refuses to start without it.
6. CI only ran on `master`, so the modernization branch was untested.
7. The Docker image installed the dev toolchain and had no PostgreSQL driver.

Known gaps carried into Phase 2:

- Coverage 44% vs the >80% target; `forms.py`, `auscycling.py`, `feeds.py` and
  all management commands are at 0%.
- `races/apps/cabici/forms.py` is now imported by nothing (the template views
  that used it are gone) - port or delete.
- `races/apps/cabici/feeds.py` (iCal/Atom) is still unrouted - decide whether to
  expose it as an API endpoint or drop it. Note `item_link` reverses the removed
  `race` URL name, so it cannot be re-routed as-is (MODEL_REVIEW A3).
- ~~`usermodel.save_rider()` is a dead Strava social-auth callback~~ — deleted in
  Phase 2.0.
- Lint debt is quarantined by `per-file-ignores` in `pyproject.toml` for
  `races/ingest/*` (bare excepts that are load-bearing for scraper fallbacks) and
  `races/apps/cabici/tests/*` (star imports, unused locals). The `races/ingest/*`
  quarantine disappears when 2.0 deletes the scrapers; the tests one clears as
  those modules are rewritten.
- `TIME_ZONE = 'Europe/Helsinki'` in base settings for a NSW racing app -
  unresolved, needs an owner decision (changing it shifts displayed times).

**Phase 2 planning outcome (2026-10-11):** a full review of the model and API
layers was carried out as part of closing Phase 1, then revised the same day
after an owner briefing. It found **nine** live model defects, nine integrity
gaps and twelve structural issues, and concluded that the existing API should be
rebuilt rather than adapted — with one exception, the race-day upload contract,
which has an external client. Four defects are resolved by retiring the code they
live in. See [MODEL_REVIEW.md](MODEL_REVIEW.md); the task lists below reflect it.

Briefing facts that changed the plan:

- All **ingest pipelines are out of date** → deleted in 2.0, not repaired
- **AusCycling membership polling is withdrawn**, pending a new provider →
  deleted in 2.0; membership categories to be redesigned around the new system
- **WMCC is the only client club** → no multi-tenancy design; the hardcoded
  pointscale becomes data rather than a bug
- The **race-day entry app is the only rider-creation path**, and it is external
  to this repo → its contract is frozen until it is retired

## ✅ Phase 2: Backend API Rebuild (Weeks 5-12)

Each numbered section below is its own branch and PR: e.g.
`chore/phase2.1-model-constraints`, `feature/phase2.2-vendor-raceday`,
`feature/phase2.3-api-contract`. Split further when a section is too large to
review in one sitting.

> **Decisions (2026-10-11, third revision):**
> 1. `api.py` is **scrapped, not adapted**.
> 2. A **retirement pass comes first**: the ingest pipelines, the withdrawn
>    AusCycling polling, the dead import paths **and the unreachable export views**
>    are deleted, not repaired — resolves four model defects by removal.
> 3. **WMCC is the only client club** — do not design for multi-tenancy.
> 4. **The React race-day app is vendored into `frontend/`; deployment is
>    same-origin** (Django serves both builds, so **CORS is deleted**).
> 5. **Cutover deploys new API + `apps/web` + `apps/raceday` together.**
>    Angular retires at cutover alongside them — no phased withdrawal. The old
>    Angular interface (`payload.riders`, display-string `rider`) is not carried
>    forward; the new API uses the correct keys (`newriders[]`, `riderid`) natively.
>    DRF token auth goes at cutover with Angular.
> 6. D1/D2 are **React-only, not live** — no hotfix, no urgency. **A9 is the one
>    live production bug.** A8 and the rest of the membership track are
>    **deferred** pending the AusCycling provider spec (2026-10-21).
>
> Evidence: [MODEL_REVIEW.md](MODEL_REVIEW.md).

### 2.0 Retirement Pass (Week 5) — ✅ complete

Landed in two commits: `c6e89b0` on `modernization`, then the remainder on
`chore/phase2.0-finish-retirement`. **3,463 Python lines removed** (3,037 + 426).

- [x] Delete `races/ingest/` + commands `ingest`, `csvingest`, `harvestclubs`,
      `loadusers`, `wmccimport` (out-of-date pipelines, 1,029 lines)
- [x] Delete the withdrawn AusCycling polling: `auscycling.py`,
      `validate_memberships.py`, `Club.validate_membership()`, the 3 `Club`
      credential fields and 2 `Membership` validation fields (closes C9)
- [x] Delete `Race.load_excel_results()` + its 4 tests (`c6e89b0`, closes A5/A6)
- [x] Delete the dead import/parse paths in `usermodel.py` — `save_rider()`,
      `parse_img_members()` + `IMG_MAP`, `RiderManager.update_from_tidyhq_spreadsheet()`
      and its helper `find_user()`, and `RaceResult.pointscores()` (closes **A4**)
      — *finished on the branch, not in `c6e89b0`*
- [x] Delete dead schema: `RacePrototype`, `Club.icalurl`, `Club.icalpatterns`
      (closes C4); delete `Club.ingest_race_list()` and
      `RaceCourseManager.find_location()` (orphaned once `ingest_by_module` went),
      then collapse the two now-empty managers `ClubManager`/`RaceCourseManager`
      (Django's default manager suffices; `makemigrations --check` confirms no
      migration needed)
- [x] Delete dead tests: `testingest.py`, `imgsampledict.py`, 7 VCR cassettes
      (closes A7)
- [x] Delete the three unreachable export views in `views.py`
      (`club_riders_csv_view`, `ClubRidersExcelView`, `RaceSummarySpreadsheet`)
- [x] Final dependency set: `icalendar`, `ngram`, `beautifulsoup4`/`bs4`,
      `requests`, `vcrpy`, `pytz`, `python-dateutil`, `pyexcel`, `pyexcel-xls`,
      `openpyxl`, `django-cors-headers` all out; `base.txt` is now Django,
      djangorestframework, django-allauth, django-anymail, tzdata, setuptools

#### Correction — an earlier "verified" claim in this section was false

The first version of this section asserted each dropped dependency was *"verified
used only by code deleted in this pass"*. It wasn't, for two of them:

- `find_location()` was **kept** while `ngram` was dropped from `base.txt` —
  `ruff` even flagged the resulting `F821` mid-session, and I fixed the import in
  the code but never reconciled `base.txt` or this bullet.
- `parse_img_members()` was deleted *in my working tree* and then **silently
  reverted**: while wrestling with `models.py` I ran `git checkout -- .`, which
  also restored `usermodel.py`, and I never re-applied those deletions before
  committing. So `c6e89b0` shipped with ~345 lines of dead `usermodel.py` code and
  `bs4` still genuinely imported.

The result: CI failed on undeclared `ngram`/`bs4`, and it passed locally only
because both lingered in `.venv`. **You restored both to `base.txt` to unblock CI
(`bs4==0.0.2`, a stub that does not pin `beautifulsoup4`) — the right short-term
move; the dependency was correct, the code was wrong.** Deleting the dead code on
this branch is what makes dropping them honest, verified from pristine
environments rather than by grep reasoning: 38-package dev venv → 45 tests OK;
18-package prod venv → `check` clean.

Two process notes for the PR workflow this is the first change under: a green
`black --check`/lint gate on a *freshly created* venv would have caught both
undeclared deps, and marking a checklist item `[x]` before its commit exists is
how this slipped — the bullets are now stated as landed only where they are.

- [ ] **Keep, move to `services/` in 2.1/2.5**: pointscore score/tally/recalculate,
      `tally_pointscores`, `fix_small_races`, official allocation, promotion and
      performance reports, `classification`

### 2.1 Model Hardening (Weeks 5-6)
- [x] A1: `PointScore.score()` now reads its own `points` / `smallpoints` /
      `smallthreshold` / `participation` fields, so a series is database-driven
      and a second club can run its own scale. Behaviour is identical for the
      shipped defaults — the pre-existing `test_create` still passes unchanged,
      including the reason strings, and `test_score_uses_configured_scale` /
      `test_default_scale_matches_legacy_values` cover both directions
      (`fix/phase2.1-pointscore-config`)
- [x] A1b: deleted the decorative `PointScore.method` field (only WMCC ever
      existed in code; LACC was a retired scraper) — migration `0018`
- [ ] **Residual hardcode from A1:** the tiny-field rule (`numberriders < 6`,
      winner gets 3) is now the documented module constants `TINY_RACE_FIELD` /
      `TINY_RACE_POINTS`, but unlike the other four values it has **no**
      `PointScore` field. Making it configurable needs a migration plus
      admin/UI work — worth deciding before a second club onboards.
- [x] A2: membership categories are now the AusCycling set — `Ride`, `Club`,
      `Race`, with `Club` and `Race` entitling the holder to race and `Ride`
      not. Replaces the previously inverted tuple (value/label swapped, so admin
      writes were invisible to the filters) and re-maps stored data in one
      migration (`0019`): `race`→`Race` (6,076 rows), `ride`+`non-riding`→`Ride`
      (116+96), verified forward **and** reverse against a copy of the dev
      database with all 6,288 rows accounted for. `Membership.allows_racing`
      expresses the entitlement; `RACING_CATEGORIES` replaces the single-literal
      filters (`Club.statistics()` now counts both racing categories)
      (`fix/phase2.1-membership-categories`)
- [x] **A9 — the one live production bug:** `grade_change == "y"` vs the boolean
      both clients send → in-race grade changes have never applied in production;
      also missing from the GET response so downloads reset it. Fixed both ends:
      `_truthy()` accepts the JSON boolean (and the legacy `"y"`), and the
      serializer exposes `grade_change` as `grade != usual_grade`
      (`fix/phase2.1-grade-change`)
- [ ] A3: fix or drop `Race`/`Rider.get_absolute_url()` (admin "View on site" 500s)
- [ ] **Membership — DEFERRED (owner decision, 2026-10-21), pending the
      AusCycling provider spec.** The earlier split into "track (a) local
      verification — do now" and "track (b) provider integration — blocked" is
      withdrawn: with no authoritative source of membership data there is
      nothing to verify against, so building the storage/API now risks rework
      when the provider's data model lands. Deferred together: **A8**
      (`member_category` / `verifiedMemberDate` on upload), membership as a
      resource, `Rider.current_membership` (**C10**), and the verification
      semantics. Settled and staying: the `Ride`/`Club`/`Race` categories (A2,
      migration `0019`). Production continues without verification and the React
      app's flow stays unfinished — an accepted trade-off. When the spec lands:
      capture the provider category set, define the `MembershipSource` seam, and
      never put a provider client secret in a model field again (C9)
- [ ] Unique constraints: `Club.slug`, `ClubRole.name`, `Membership(rider, club,
      category, date)`, `ClubGrade(rider, club)`, `UserRole(user, club, role)`,
      `PointscoreTally(pointscore, rider)` — `Race.hash` moot after 2.0
- [ ] Replace the `ClubGrade.save()` Python uniqueness override with a constraint
- [ ] Conditional uniqueness for bib numbers, then delete the "increment to avoid
      clash" workaround in `api.py` (the others went with 2.0)
- [ ] Indexes on `Race(date, status)` and pointscore ordering columns
- [ ] Verify no duplicate data against a production copy before applying
- [x] C1: `usermodel.py` merged into `models.py` and deleted; the six
      function-level circular imports are gone. No migration required
      (`refactor/phase2.1-merge-models`)
- [x] C2 (results slice): the race-day upload moved out of `api.py` into
      `races/apps/cabici/services/results.py`. `upload_results(payload)` owns the
      transaction and the race row lock and returns a typed `ResultUpload`
      (`ridermap` / `errors` / `deleted` / `created`); the view is now only the
      HTTP projection (debug dump, 400 mapping, response shape). Rejected
      payloads return 400 rather than the old 500. Direct service tests added
      (`refactor/phase2.1-services-results`)
- [x] C2 (pointscore slice): `score`, `get_points`/`get_smallpoints`,
      `tally`/`tally_helpers`, `recalculate`, `tally_pointscores` and
      `fix_small_races` moved into `services/pointscore.py` and removed from the
      models. `recalculate`, `tally`, `tally_race` and `fix_small_races` now own
      their transaction. Callers updated: the upload service, the `pointscore`
      management command and the pointscore tests. `current()`, `tabulate()` and
      `audit()` stay on the model as read accessors
      (`refactor/phase2.1-services-pointscore`)
- [ ] C2 (remaining slices): `services/officials.py` (allocation, promotion,
      performance reports), `services/exports.py` (deferred until wanted). Move
      the logic outright and update callers
- [ ] C3: **simplified** — permissions answer "official of the owning club?";
      keep the schema, do not build a general RBAC engine
- [ ] C5/C6: structure `Race.grading` (the per-race grade set the entry screen
      renders); resolve `place` 0-vs-NULL and `dob` 1970-01-01 sentinels; give
      `Rider.commissaire` a real boolean or drop its `"0"` sentinel
- [ ] C8: make `Rider.updated` delta tracking explicit
- [ ] C11/C12: eliminate N+1 paths and normalise `Club.statistics()`

### 2.2 Monorepo: Vendor the Race-Day App (Week 6)

**Cutover deploys both React apps together.** `apps/web` replaces the Django views;
`apps/raceday` replaces Angular at cutover with no phased withdrawal.
- [ ] **Do not vendor Angular as a buildable app** (Angular 8 in CI is cost with no
      benefit, and a third race-day implementation invites "which is live?")
- [ ] **Extract Angular's wire semantics into `docs/raceday-contract.md`** — the
      `_buildUploadPayload()` field list (`payload.riders`) and the
      `getRider(e.riderid)` download mapping — so the spec does not depend on a
      sibling checkout surviving
- [ ] **Design the upload/download semantics cleanly for the React app** (no legacy
      shapes needed)
- [ ] `git subtree add --prefix=frontend/apps/raceday stevecassidy/cabici-raceday-react main`
      (preserve history — the blame is the D1/D2 provenance evidence)
- [ ] pnpm workspaces root under `frontend/`; Node pinned; apps stay **two
      separate deployables** (raceday is offline-first and high-stakes)
- [ ] `frontend/packages/api-client` (generated, 2.3) + `frontend/apps/web`
      skeleton for the Phase 3 SPA
- [ ] **Mount `apps/raceday` on a subpath** (`/raceday/`) — required by
      same-origin and **not configured today**: no `base` in `vite.config.ts`, no
      `basename` on `BrowserRouter`, a catch-all `<Route path="*">`, and a PWA
      service worker whose scope must be narrowed to the subpath
- [ ] Frontend CI workflow (`install --frozen-lockfile`, lint, `tsc --noEmit`,
      `vitest run`, `build`) on `frontend/**`; path filters on the Python workflow
- [ ] Carry over `PROJECT_CONTEXT.md`; refresh `.devcontainer` (still Python 3.10)

**Client-side fixes (React-only, so not urgent)**
- [ ] **D1:** app sends `newriders`, `api.py:654` reads `riders` → rider
      creations are silently dropped, HTTP 200, `ridermap {}`. Restore the Angular
      mapping
- [ ] **D2:** app maps entries by `String(entry.rider)` where the API returns a
      display string (ID is `riderid`) → downloads always return an empty sheet.
      Angular used `e.riderid`
- [ ] **D4:** surface the server's `errors[]` to the race director (currently
      discarded by `EntryService.uploadEntries()`)
- [ ] Regression tests for all of the above through the **real HTTP boundary** —
      their absence is why D1/D2 survived both suites

**Server-side fixes (affect the deployed Angular app)**
- [x] **D3 (server half) — permissions + atomicity:** `RaceResultPermission`
      requires an official of the race's club (reads stay open; guarded against a
      User with no Rider), `post()` is `@transaction.atomic` with the race row
      locked and per-row savepoints, and a rejected duplicate is reported rather
      than dropped silently (`fix/phase2.1-grade-change`)
- [ ] **D3 (server half) — explicit overwrite contract:** the upload still
      replaces all results for a race. The confirmation flag / `If-Match` version
      contract belongs with the new results endpoint in 2.2/2.5, where both
      clients' shapes are designed — a required flag would break the deployed
      Angular app
- [ ] **A8 — deferred with the membership track:** honour `member_category` +
      `verifiedMemberDate` once the AusCycling provider spec lands
- [ ] **Preserve the offline contract:** full paginated load + `localStorage`
      cache + `?changed=<unix>` merge-by-`rider.id`. Load-bearing at the
      velodrome; `?updated_after=` must keep all three and not silently drop
      deleted riders

### 2.3 Resource Model & API Contract (Week 7)
- [ ] Derive remaining resources from the domain (not from the old views)
- [ ] One consistent public identifier per concept (rider = `Rider.id` everywhere)
- [ ] Explicit read/write serializer shapes; never `fields='__all__'`
- [ ] `django-filter` FilterSets replacing `?select=` / `?count=` / `?prefix=` /
      `?changed=` (delta sync becomes `?updated_after=` + `ETag`)
- [ ] Domain operations as explicit actions (`POST /races/bulk/`,
      `POST /pointscores/{id}/recalculate/`,
      `POST /clubs/{slug}/officials/allocate/`)
- [ ] Publish OpenAPI before implementing; generate the TypeScript client into
      `frontend/packages/api-client` and consume it from **both** apps (the control
      that prevents a repeat of D1/D2)
- [ ] Contract test in CI covering served schema ↔ generated client ↔ raceday
      upload payload

### 2.4 Authentication & Same-Origin Wiring (Week 8)
- [ ] Install djangorestframework-simplejwt; JWT access + refresh endpoints
- [ ] Register / password reset / profile endpoints
- [ ] allauth → JWT; session auth for `/admin/` only
- [ ] Fix carried-over defects: unknown email → 401 not 500; user without a Rider
      must not 500
- [ ] **Token storage settled by same-origin:** access in memory, refresh in an
      httpOnly SameSite cookie, with CSRF protection on cookie-authenticated
      writes. Bearer-in-`localStorage` is off the table
- [ ] **Delete CORS entirely** (not scope it): `corsheaders` app, `CorsMiddleware`,
      the 3 `CORS_*` settings, and `django-cors-headers` from `base.txt`
- [ ] **allauth links must resolve into the SPA** — password reset and email
      confirmation are absolute template links today; needs allauth URL/adapter
      config (previously untasked)
- [ ] **Flatpage disposition:** `FlatpageFallbackMiddleware` + the `/` flatpage back
      the current home page; with `/` owned by the SPA, expose pages as a resource
      or reorder the middleware
- [ ] Migrate `frontend/apps/raceday` off `AUTH_HEADER_PREFIX = 'Token'` and its
      `localStorage` token storage
- [ ] **Delete DRF token auth at cutover alongside Angular.** Neither app needs
      legacy token auth — both use JWT from day one (refresh in httpOnly cookie).

### 2.5 Core CRUD Implementation (Weeks 9-10)
- [ ] ViewSets + routers under `/api/v1/` (no hand-wired URL pairs)
- [ ] Serializers with explicit fields; write shapes separated from read shapes
- [ ] `select_related` / `prefetch_related` on every queryset
- [ ] Pagination on every list endpoint
- [ ] Permission classes applied uniformly
- [ ] `transaction.atomic()` around every multi-row write
- [ ] Custom actions for domain operations, backed by services

### 2.6 API Documentation (Week 11)
- [ ] Install drf-spectacular; annotate every view/action
- [ ] Generate OpenAPI schema + interactive docs at `/api/docs/`
- [ ] Create Postman collection from the schema
- [ ] Regenerate the TypeScript client from the final spec
- [ ] Write API usage guide

### 2.7 Test Suite Rebuild & Retirement of api.py (Week 12)
- [ ] Per-resource endpoint tests (CRUD, filters, pagination, permissions, errors)
- [ ] Service-layer tests for the race-day upload, bulk create, allocation,
      pointscore recalculation
- [ ] Contract test: generated TS types match the served schema
- [ ] Achieve >80% coverage; ratchet `fail_under` (42 → 60 → 80)
- [ ] **Delete `api.py`** and its hand-wired URL pairs in one commit

## ✅ Phase 3: React Frontend (Weeks 13-28)

### Initial Setup
- [ ] Decide on frontend architecture
- [ ] Create React project with Vite + TypeScript
- [ ] Set up project structure
- [ ] Configure ESLint + Prettier
- [ ] Install core dependencies
- [ ] Set up routing
- [ ] Configure environment variables

### Core Dependencies
```bash
- [ ] npm install react-router-dom
- [ ] npm install @tanstack/react-query
- [ ] npm install axios
- [ ] npm install zustand
- [ ] npm install react-hook-form
- [ ] npm install zod
- [ ] npm install tailwindcss (or MUI)
```

### Authentication (Weeks 15-16)
- [ ] Create API client
- [ ] Implement login form
- [ ] Implement logout
- [ ] Implement registration
- [ ] Password reset flow
- [ ] Protected routes
- [ ] User profile page
- [ ] Auth state management

### Layout & Navigation (Week 16)
- [ ] Main layout component
- [ ] Navigation bar
- [ ] Footer
- [ ] Responsive design
- [ ] Loading states
- [ ] Error boundaries

### Club Features (Weeks 17-18)
- [ ] Club list page
- [ ] Club detail page
- [ ] Club dashboard
- [ ] Club members page
- [ ] Club statistics
- [ ] Club search/filter

### Race Features (Weeks 19-20)
- [ ] Race list page
- [ ] Race detail page
- [ ] Race creation form
- [ ] Race edit form
- [ ] Race officials management
- [ ] Bulk race creation
- [ ] Race filtering/search
- [ ] Race calendar view

### Rider Features (Weeks 21-22)
- [ ] Rider list page
- [ ] Rider detail page
- [ ] Rider search
- [ ] Rider autocomplete component
- [ ] Rider profile editor
- [ ] Rider grade management

### Results & Pointscores (Weeks 23-24)
- [ ] Result upload UI
- [ ] Result display
- [ ] Excel file handling
- [ ] Pointscore list
- [ ] Pointscore detail
- [ ] Pointscore audit view

### Advanced Features (Weeks 25-26)
- [ ] File upload with drag-drop
- [ ] Google Maps integration
- [ ] Email composition
- [ ] Export functionality
- [ ] Advanced filtering
- [ ] Calendar integration

### Testing (Weeks 27-28)
- [ ] Unit tests for utilities
- [ ] Component tests
- [ ] Integration tests
- [ ] E2E tests (Playwright)
- [ ] Accessibility audit
- [ ] Performance testing
- [ ] Mobile testing

## ✅ Phase 4: Integration & Deployment (Weeks 29-33)

### Backend Cleanup
- [ ] Remove all Django template files
- [ ] Remove jQuery and static assets
- [ ] Remove frontend URL patterns
- [ ] Remove template views
- [ ] Update settings (remove TEMPLATES config)
- [ ] Remove frontend middleware
- [ ] Update INSTALLED_APPS
- [ ] Final code cleanup
- [ ] **URL space is reassigned, not just cleaned up** (same-origin): `/` →
      `apps/web`, `/raceday/` → `apps/raceday`, `/admin/`, `/api/`. The current `/`
      is `HomePage`, a Django `ListView`

#### Template reachability (analysed during Phase 1, delete in this phase)

`races/templates/` (a `TEMPLATES DIRS` entry) shadows the same-named files in
`races/apps/cabici/templates/`, so the app copies below are unreachable and can
 go with the rest of the template layer:

- `cabici/templates/account/{login,signup,password_reset,password_change,settings,delete}.html`
  and the pinax-era `password_reset_token*.html`, `email_confirmation_sent.html`,
  `email_confirmed.html`, `password_reset_sent.html`, `_login_sidebar.html`,
  `_signup_sidebar.html` — none of these template names exist in allauth 65
- `cabici/templates/account/email/{invite_user,password_reset,password_change}*.txt`
  (allauth uses `password_reset_key_*`)
- `cabici/templates/pagination/*` (django-pagination removed), `test.html`,
  `theme_bootstrap/*` (uses `{% load staticfiles %}`, gone in Django 4.0),
  `cabici/templates/_account_bar.html`
- `races/templates/registration/*` — Django auth views that are no longer routed
- 3.3 MB of `cabici/static/` (bootstrap, bootstrap-select, bootstrap-datetimepicker,
  datepicker, jQuery)

Still live until the React app replaces them: `cabici/templates/index.html`
(`HomePage`), `site_base.html`, `_messages.html`, `404/500.html`,
`flatpages/default.html`, `races/templates/account/*` (allauth login/reset flow,
still the only way officials sign in until JWT lands) and
`races/templates/rest_framework/api.html`.

### Integration Testing
- [ ] Full end-to-end testing
- [ ] Cross-browser testing
- [ ] Mobile device testing
- [ ] Performance testing
- [ ] Load testing
- [ ] Security audit
- [ ] Accessibility testing
- [ ] Fix all critical issues

### Production Deployment
- [ ] **Multi-stage Dockerfile** — add a Node stage (`pnpm install
      --frozen-lockfile && pnpm -r build`) and copy both `dist` trees into the
      Python image; today it is `python:3.14-alpine` with no Node
- [ ] **`.dockerignore` must exclude `node_modules`** (verified absent today)
- [ ] **Resolve the static-storage/manifest trap:** Vite content-hashes already;
      `CompressedManifestStaticFilesStorage` re-hashes and does **not** rewrite
      `index.html`, breaking asset URLs → use
      `whitenoise.storage.CompressedStaticFilesStorage`
- [ ] **CI smoke test for that trap:** `collectstatic` against a real build, then
      assert every `src`/`href` in the emitted `index.html` resolves to a
      collected file
- [ ] SPA catch-all routing for both apps, ordered after `/admin/` and `/api/`,
      with `404`/`500` handling that does not assume the template layer
- [ ] `STATICFILES_DIRS` gains both builds; review `ALLOWED_HOSTS` / `SECURE_*` /
      `CSRF_TRUSTED_ORIGINS` for one-origin operation
- [ ] Final database backup before deployment
- [ ] Set up monitoring (Sentry — already a dependency of `apps/raceday`)
- [ ] Deploy Django (one image, one cutover); run migrations
- [ ] Smoke test all critical functionality
- [ ] Update DNS/CORS settings — ~~eliminated by same-origin~~
- [ ] **Angular retirement is a separate, later step, not part of the cutover:**
      define `apps/raceday` exit criteria (parity with Angular's 11 components,
      D1/D2/D4 fixed, A8/A9 honoured, offline behaviour verified), retire it only
      after a race or two on the new app, and only then delete the legacy API
      surface and DRF token auth

### Documentation
- [ ] API documentation
- [ ] Component documentation
- [ ] Deployment guide
- [ ] Developer onboarding
- [ ] User guide
- [ ] Troubleshooting guide

## ✅ Phase 5: Optimization (Weeks 34-38)

### Django Optimization
- [ ] Implement Django 5.x features
- [ ] Add database indexes
- [ ] Optimize queries (select_related, prefetch_related)
- [ ] Set up Redis caching
- [ ] Add API caching
- [ ] Implement rate limiting

### Frontend Optimization
- [ ] Code splitting
- [ ] Lazy loading
- [ ] Image optimization
- [ ] Bundle size optimization
- [ ] Service worker
- [ ] Optimistic updates

### Security
- [ ] Security audit
- [ ] Rate limiting
- [ ] API throttling
- [ ] Update CORS policies
- [ ] CSP headers
- [ ] Dependency security scan

### Monitoring
- [ ] Set up Sentry
- [ ] Configure logging
- [ ] Application metrics
- [ ] Uptime monitoring
- [ ] Performance dashboards
- [ ] User analytics

---

## Critical Path Items

These items are blocking for subsequent work:

1. ⚠️ **Create Development Branch** - All work happens here, production stays stable
2. ⚠️ **Django 5.2 Upgrade** - Must complete before API work
3. ⚠️ **API Authentication** - Must complete before frontend development
4. ⚠️ **Complete API Endpoints** - Must complete before frontend can be fully functional
5. ⚠️ **Testing Infrastructure** - Should be in place early
6. ⚠️ **Integration Testing** - Must complete before production deployment

---

## Quick Reference: Key Commands

### Backend
```bash
# Run the full suite (canonical runner, uses races/settings/testing.py)
python bin/runtests.py

# Coverage, with the pyproject.toml gate
coverage run --rcfile=pyproject.toml bin/runtests.py && coverage report

# Run development server
python bin/develop.py runserver

# Migrations (development settings)
python bin/develop.py makemigrations
python bin/develop.py migrate
python bin/develop.py makemigrations --check --dry-run

# Quality gates (run before pushing)
black .
ruff check --fix .
ruff check . && black --check . && mypy races

# Or all of them
pre-commit run --all-files
```

Against **production** settings (`bin/production.py`) requires `DJANGO_SECRET_KEY`
in the environment — it refuses to start without one, so use `bin/develop.py` for
local work.

### Frontend (pnpm workspaces, from `frontend/`)
```bash
cd frontend
pnpm install                                  # all workspaces

pnpm --filter @cabici/raceday dev             # dev server for one app
pnpm --filter @cabici/web dev

pnpm -r build                                 # production builds for both
pnpm -r test                                  # vitest across workspaces
pnpm -r lint
pnpm -r type-check

# Regenerate the API client from the served schema
pnpm --filter @cabici/api-client generate
```

Package names are tentative until 2.2 vendors the app; the commands are the
shape the monorepo decision implies (same-origin serving, no CORS).

### Docker
```bash
# Build and run
docker-compose up -d

# View logs
docker-compose logs -f web

# Run commands in container
docker-compose exec web python manage.py shell
```

---

## Weekly Milestones

- **Week 4:** Django 5.2 running in development ✅
- **Week 8:** 50% of API endpoints complete
- **Week 12:** Full API with documentation
- **Week 16:** React authentication working
- **Week 20:** Major features implemented
- **Week 24:** Feature-complete frontend
- **Week 28:** All tests passing
- **Week 31:** Integration testing complete
- **Week 32:** Production deployment ✅
- **Week 38:** Post-deployment optimization complete

---

## Success Criteria

- [ ] All tests passing (>80% coverage)
- [ ] API response time <200ms
- [ ] Frontend loads in <2s
- [ ] Lighthouse score >90
- [ ] Zero critical vulnerabilities
- [ ] 99.9% uptime
- [ ] User satisfaction >4/5

---

## Rollback Plans

### If Django upgrade fails:
1. Continue on the existing branch
2. Review migration issues
3. Fix and retry on a branch, merged by PR

### If API development has issues:
1. Fix issues before frontend integration
2. No impact on production

### If React deployment fails:
1. Rollback to previous Docker image
2. Restore database backup if needed
3. Fix issues and redeploy

---

*Use this checklist alongside the full MODERNIZATION_PLAN.md document*
