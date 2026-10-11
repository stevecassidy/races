# Django Application Modernization Plan

## Executive Summary

This document outlines a comprehensive plan to modernize the Cabici racing application from its current state (Django 4.2 with jQuery-based templates) to a modern architecture with Django 5.x backend API and React frontend. **The work will be done on a development branch with a single production deployment when complete.**

**Development Approach:**
The current production application remains stable while modernization work happens in parallel on a development branch. Once all phases are complete and tested, the new version will be deployed to production. This allows for more aggressive refactoring without concern for intermediate states or maintaining backward compatibility during development.

**Current State (as delivered on `master`):**
- Django 4.2.23
- Python 3.11
- Template-based frontend with Bootstrap 3
- jQuery 3.3.1 with various plugins
- Partial REST API implementation
- Mixed class-based and function-based views
- SQLite dev / PostgreSQL production
- Docker deployment

**State on the `modernization` branch (after Phase 1, 2026-10-11):**
- Django 5.2, Python 3.14, all versions pinned in `requirements/{base,dev,production}.txt`
- Template views stripped down to `HomePage`; ~61 legacy templates and 3.3 MB of
  Bootstrap/jQuery static assets remain for Phase 4
- Partial REST API in a single 829-line `api.py` (token auth, no routers)
  — **decided 2026-10-11: scrapped and rebuilt from scratch in Phase 2**, see
  [`MODEL_REVIEW.md`](MODEL_REVIEW.md)
- PostgreSQL driver + production dependency set in the Docker image
- Black / ruff / mypy / coverage / pre-commit / CI in place

**Target State:**
- Django 5.2 (latest stable)
- Python 3.14
- API-only backend: versioned DRF API (`/api/v1/`) generated from a published
  OpenAPI contract
- React SPA frontend
- Modern authentication (JWT + session for admin only)
- Comprehensive API documentation and a generated TypeScript client
- Improved test coverage
- Modern deployment practices

---

## Development Workflow

### Branch Strategy

`modernization` is the **integration** branch. It only moves by merging reviewed
pull requests — no direct commits, from anyone.

```
master (production)
  └── modernization (integration: PRs merged in, never committed to directly)
       ├── chore/phase2.1-model-constraints
       ├── docs/phase2-planning-notes
       ├── feature/phase2.3-race-day-contract
       ├── feature/phase2.5-core-crud
       └── ... one short-lived branch per unit of work
```

**The loop for every change:**

```bash
git checkout modernization && git pull
git checkout -b <type>/<plan-section-slug>   # feature/ | fix/ | chore/ | refactor/ | docs/
# ... small, focused commits ...
ruff check . && black --check . && mypy races && python bin/runtests.py
git push -u origin HEAD                       # open a PR targeting modernization
```

**Key Points:**

- One PR per checklist section, or smaller if the section is large — reviewable
  beats convenient
- The assistant prepares the branch, summarises the diff, and **stops at "ready
  for review"**; the owner reviews and merges
- CI must pass before review is requested; rebase onto `modernization` if it has
  moved; force-push only to your own feature branch
- Branch names reference the plan section so `git log` maps back to the checklist
- `master` remains untouched and production-ready; critical fixes go through a
  `hotfix/*` branch and a PR to `master`
- No need to maintain backward compatibility during development
- Breaking changes are fine **inside a reviewed PR** — review is where the risk
  gets accepted, not at deploy time
- Single merge to master when complete and tested

> History note: Phase 1 and the 2.0 retirement pass (`c6e89b0`) were committed
> directly to `modernization` before this workflow was adopted. From 2.1 onward,
> everything lands as a PR.

### Development Environment

Developers work on short-lived branches cut from `modernization`, with:
- Local Django development server
- Local React development server (Vite)
- SQLite or local PostgreSQL for development
- Freedom to experiment and refactor — nothing reaches `modernization` until the
  PR is reviewed and CI is green

### Testing Strategy

**During Development:**
- Unit tests run on every commit and every PR (CI)
- Integration tests for completed features
- No need to test against production environment

**Before Deployment:**
- Comprehensive integration testing
- Full end-to-end testing
- Performance and load testing
- Security audit
- User acceptance testing (optional)

### Deployment

**Single Cutover Approach:**
1. Complete all phases as merged PRs on the integration branch
2. Full integration testing
3. Merge `modernization` → `master`
4. Deploy to production
5. Monitor and support

**Rollback Plan:**
- Keep previous Docker image
- Database backup before deployment
- Can revert to previous version if needed

---

## Phase 1: Foundation & Django Upgrade

**Goal:** Update Django and dependencies, establish modern patterns, maintain current functionality

### 1.1 Django Version Upgrade (Week 1-2)

**Tasks:**
- [x] Update Django 4.2.23 → Django 5.2
- [x] Update Python dependencies in requirements.txt
- [x] Address deprecation warnings
- [x] Update URL patterns from `re_path` to `path` with converters
- [x] Test all existing functionality
- [x] Update Django REST Framework to latest version

**Breaking Changes to Address:**
- `django.utils.translation` → use `gettext_lazy` consistently
- Update middleware configuration if needed
- Check for removed features in Django 5.x
- Update settings for new defaults

**Success Criteria:**
- All tests pass with Django 5.2
- No deprecation warnings
- Database migrations successful
- Development environment functional

### 1.2 Modernize Dependencies (Week 2-3)

**Tasks:**
- [x] Remove obsolete packages (frontend being replaced):
  - Bootstrap, jQuery libraries (no longer needed)
  - `django-bootstrap-form` (not needed for API)
  - `django-pagination` (use Django's built-in)
  - `webtest/webob` (if not essential for testing)
  - Review need for `pinax-webanalytics`
- [x] Update third-party packages:
  - django-allauth (latest)
  - django-cors-headers (latest)
  - djangorestframework (latest)
  - gunicorn (latest)
  - whitenoise (latest)
- [x] Pin all package versions for reproducibility

**Success Criteria:**
- All dependencies up to date
- Security vulnerabilities resolved
- requirements.txt properly versioned
- Unnecessary frontend dependencies removed

### 1.3 Code Quality & Standards (Week 3-4)

**Tasks:**
- [x] Set up pre-commit hooks
- [x] Configure Black for code formatting
- [x] Configure ruff or flake8 for linting
- [x] Add mypy for type checking
- [x] Run formatters on existing codebase
- [x] Add GitHub Actions / CI pipeline for testing

**Success Criteria:**
- [x] Consistent code formatting
- [x] CI/CD pipeline running tests
- [x] Linting integrated into workflow

### 1.4 Phase 1 Exit Summary (2026-10-11)

Phase 1 is complete. The branch now installs and boots from a clean virtualenv,
and CI gates every push to `modernization` and PRs against it with: `ruff`,
`black --check`, `manage.py check`, `makemigrations --check`, `mypy` and the test
suite under `coverage` (floor 42%, measured 44%).

Tooling configuration lives in `pyproject.toml`; `.pre-commit-config.yaml` runs
the same tools locally from `requirements/dev.txt`. Black is set to
`line-length = 120` and both tools exclude
`races/apps/cabici/migrations/` (machine-generated history).

Two structural fixes were needed before any of that worked, because the branch
had been left in a state where **only the original author's virtualenv could run
it**: dangling `bootstrapform`/`debug_toolbar` app registrations for packages that
had been removed from the requirements files, and a `0001_initial` migration that
still imported the deleted `django-geoposition` submodule. See
`MODERNIZATION_CHECKLIST.md` → "Phase 1 Exit Notes" for the full list, the
verification commands, and the debt carried into Phase 2 (including the
`api.py` review findings and the unresolved `TIME_ZONE` question).

**Definition of done for Phase 2 entry:** nothing outstanding. Phase 2 was
replanned as a result of this review: it starts at **2.0 Model Hardening** and
rebuilds the API rather than extending `api.py` — see
[`MODEL_REVIEW.md`](MODEL_REVIEW.md).

---

## Phase 2: Backend API Rebuild

**Goal:** Replace the ad-hoc API with a complete, documented, contract-first REST
API built on the existing models — and retire the subsystems that no longer
match how the application is used.

**Decision (2026-10-11): the existing `api.py` is scrapped, not adapted.**
It was assembled ad-hoc to support specific jQuery front-end capabilities and is
idiosyncratic in ways a typed React client cannot absorb: per-view query
vocabularies instead of filters (`?select=future`, `?count=N`, `?prefix=`), three
different meanings for `rider`/`riderid` across serializers, `fields='__all__'`
writes, an unpermissioned and non-transactional result uploader, no schema, no
versioning, no refresh auth, and 5 of 13 models unexposed. Adapting it would
touch ~100% of the file while inheriting every inconsistency.

**The race-day client is in-house, and it moves in — but it is not the deployed
one.** The race-day entry application is the app's **only way to add riders**
today, and the system doing that today is the **Angular 8 app** (old, reliable, in
production). It was rewritten in React 18 in a separate repo
(`stevecassidy/cabici-raceday-react`) which is **unfinished and predates the
server-side work**. The decision is to **vendor the React app into this repo**
alongside the SPA that will replace the Django views, and to deploy **same-origin**
(Django serves both builds) for now.

So the contract is **co-designed for the future and compatibility-bound in the
present**: the new API must keep satisfying **Angular unchanged**, which is what
buys the whole of Phases 2–3 their safety — the deployed system keeps running and
Angular's retirement becomes a clean deletion rather than a migration. Token auth
cannot be deleted at vendoring time for the same reason: Angular uses it.

Reading the actual clients produced the review's most valuable findings, and the
briefing corrected their severity:

- **D1/D2 are React-only** (it sends `newriders` where the server reads `riders`,
  and maps downloads by `entry.rider` where the server returns a display string).
  **Not live — Angular gets both right.** They are fix-on-vendoring work, and
  Angular is therefore the reference implementation for the wire format.
- **A9 is the one live production bug:** `api.py:821` compares `grade_change` to
  `"y"` while **both** clients send a boolean, so in-race grade changes have never
  applied in production.
- **D3's server half is real regardless of client:** the upload endpoint has no
  permission class and no transaction, so any authenticated user can replace a
  race's results and a mid-request failure leaves it half-populated.
- **A8 is the unblocked membership work everyone assumed was blocked:** the React
  app already ships a complete manual at-the-track membership verification flow
  sending `verifiedMemberDate`, and the server ignores it entirely. With
  AusCycling polling withdrawn, production has **no verification at all** and the
  interim design is sitting in an unfinished client.

This is also why the API is contract-first with a **generated** client:
hand-maintained wire formats across two repos, with every layer mocking the layer
beneath it, is exactly how D1 survived both test suites.

Details, reproduction and remediation: 2.2 and
[`MODEL_REVIEW.md`](MODEL_REVIEW.md).

**Domain context** (owner briefings, 2026-10-11) — none of it visible from the
server code alone, all of it reflected in the plan below:

- The **ingest pipelines are out of date** (club scrapers, iCal ingestion,
  historical imports). Nothing is maintained there.
- **AusCycling membership polling has been withdrawn**, pending a new API
  provider.
- **WMCC is the only client club**, and the pointscore is a WMCC-specific thing —
  which is why its scale is hardcoded.
- **Membership categories must be redesigned** around AusCycling's new membership
  system.
- **The race-day client is an in-house React app**, and it is being brought into
  this repo.

Full evidence — nine model defects (A1–A9), four client/contract defects (D1–D4),
nine integrity gaps (B1–B9) and twelve structural findings (C1–C12):
[`MODEL_REVIEW.md`](MODEL_REVIEW.md).

**Sequencing rationale:** retire first (it shrinks every later estimate), then
harden the models (the API surface follows the domain, and A1/A2/A8 change API
responses if deferred), then vendor and audit the race-day client (its real shapes
are inputs to the contract), then design the contract for both clients, then build
the rest.

### 2.0 Retirement Pass (Week 5) ✅ complete

Delete before rebuilding. Landed as `c6e89b0` on `modernization` plus
`chore/phase2.0-finish-retirement`, which finished the part the first commit
missed. **3,463 Python lines removed** (3,037 + 426), 11 dependencies, 7 VCR
cassettes, 7 model fields.

- [x] **Ingest pipelines** — `races/ingest/` entirely (lacc, penrith, waratahs,
      csvingest = 384 lines) and the commands `ingest`, `csvingest`,
      `harvestclubs`, `loadusers`, `wmccimport` (645 lines) *(fact 1)*
- [x] **Withdrawn AusCycling polling** — `auscycling.py` (169),
      `validate_memberships.py` (136), `Club.validate_membership()` (~70 lines in
      `models.py`), and the fields `Club.auscycling_client_id` / `_client_secret`
      / `_club_id`, `Membership.last_validated` / `validation_error` *(fact 2;
      also closes **C9**, the plaintext secret)*
- [x] **`Race.load_excel_results()`** + its 4 tests *(closes **A5**, **A6**)* —
      `c6e89b0`
- [x] **Dead import/parse paths in `usermodel.py`** — `save_rider()`
      (unregistered Strava callback), `parse_img_members()` + `IMG_MAP`,
      `RiderManager.update_from_tidyhq_spreadsheet()` (the tidyhq app went in
      `f5d37e4`) and its helper `find_user()`, `RaceResult.pointscores()`
      *(closes **A4**)* — **finished on the branch: these were reverted by a stray
      `git checkout -- .` and never re-applied before `c6e89b0`**
- [x] **Dead schema** — `RacePrototype`, `Club.icalurl`, `Club.icalpatterns`
      *(closes **C4**)*
- [x] **Orphaned ingest helpers** — `Club.ingest_race_list()` (lost its only
      caller when `ingest_by_module` went) and
      `RaceCourseManager.find_location()` (called only from there)
- [x] **Now-empty managers** — `ClubManager` and `RaceCourseManager` collapsed to
      `pass` and then removed entirely; Django's default manager suffices, and
      `makemigrations --check` confirms no migration is required
- [x] **Unreachable export views** in `views.py` — `club_riders_csv_view`,
      `ClubRidersExcelView`, `RaceSummarySpreadsheet`: all three already unrouted
      on this branch (master had 3 such routes), and the React client fetches
      riders as JSON, never XLS
- [x] **Dead tests and fixtures** — `tests/testingest.py`, `imgsampledict.py`, the
      7 VCR cassettes in `fixtures/vcr_cassettes/` *(closes **A7**)*
- [x] **Dependencies** — `base.txt` is now Django, djangorestframework,
      django-allauth, django-anymail, tzdata, setuptools. Dropped: `icalendar`,
      `ngram`, `beautifulsoup4`, `requests`, `vcrpy`, `pytz`,
      `python-dateutil`, `pyexcel`, `pyexcel-xls`, `openpyxl`,
      `django-cors-headers`
- [ ] **Keep, relocate into `services/`** in 2.1/2.5 (real domain rules):
      `PointScore.score()`/`tally()`/`recalculate()`, `Race.tally_pointscores()`,
      `fix_small_races()`, `Club.allocate_officials()`/`promotion()`/
      `performancereport()`, `Rider.classification()`

**Success Criteria — met:** 3,463 fewer Python lines; `manage.py check`,
`makemigrations --check` and the suite green with the dead tests removed (45
tests, 1 pre-existing skip); no reference to any retired module remains in
`races/`.

> **Process correction.** The first version of this section claimed every dropped
> dependency was "verified used only by code deleted in this pass". That was false
> for `ngram` (still imported by the *kept* `find_location()`) and for `bs4` (the
> `usermodel.py` deletions had been silently reverted). Both surfaced as CI
> failures on undeclared modules, hidden locally because the packages lingered in
> `.venv`; the owner restored them to unblock CI. The dead code is now genuinely
> gone, so both go back out — and verification is by **pristine-environment
> install**, not grep reasoning: 38-package dev venv → 45 tests OK, 18-package
> prod venv → `check` clean. See
> [`MODEL_REVIEW.md`](MODEL_REVIEW.md) → Correction.

### 2.1 Model Hardening (Weeks 5-6)

Prerequisite for serializers. Referenced items are the findings in
[`MODEL_REVIEW.md`](MODEL_REVIEW.md).

**Defects (A4–A7 gone with 2.0):**
- [ ] A1: make `PointScore.score()` read its own `points` / `smallpoints` /
      `smallthreshold` / `participation` fields instead of the hardcoded WMCC
      constants; wire up `get_points()` / `get_smallpoints()`; add a test with a
      non-default configuration. Behaviour is unchanged for WMCC once its scale is
      stored as data *(confirm)*
- [ ] A1b: delete `PointScore.method` — it offers `WMCC`/`LACC`, only WMCC exists
      in code, and LACC was one of the retired scrapers
- [ ] A2: **fix now, not deferred** (third revision) — the inverted
      `MEMBERSHIP_CATEGORY_CHOICES` tuple is a live admin bug: writing `'Race'`
      makes a membership invisible to the seven `category="race"` sites. Correct
      the tuple and normalise any capitalised rows in this phase. Adopting
      AusCycling's *new* vocabulary can follow later as a second migration; the
      inversion should not wait on an unspecified provider date
- [ ] A3: remove or repair `Race.get_absolute_url()` / `Rider.get_absolute_url()`
      (they reverse URL names that no longer exist → admin "View on site" 500s,
      verified through `/admin/r/<content_type>/<id>/`); admin is the one UI we
      keep through Phase 4. `feeds.py` `item_link` has the same fault
- [ ] **A9: the one live production bug** — `api.py:821` compares
      `entry["grade_change"] == "y"` while both clients send a JSON boolean, so
      in-race grade changes have never applied in production. Fix the comparison
      (and the response, which omits `grade_change` entirely so a download
      resets it to `false`), with a regression test through the real HTTP
      boundary

**Membership — two tracks (third revision):**

*Track (a): local verification — **unblocked, do now**.* The React app already
ships a complete manual at-the-track verification flow (`MembershipVerificationDialog`,
`membershipUtils`: `isCurrentMember`, `needsMembershipVerification`,
`isValidMemberDate`, `getEffectiveMemberDate`) that sends `verifiedMemberDate`,
and the server has **zero** support for it (`grep -rn "verifiedMemberDate" races`
→ no matches). With AusCycling polling withdrawn, production currently has **no
membership verification at all**.

- [ ] Store a verified membership date on `Membership` (or `Rider`) and honour it
      on upload alongside `member_category` (A8)
- [ ] Expose membership as a first-class resource, not an upload side effect
- [ ] Fix `Rider.current_membership` (C10) to select by category and validity
      window instead of max date across all categories
- [ ] Port the verification semantics out of the client into the server so they
      are enforced once rather than per client

*Track (b): provider integration — **blocked** on the new API provider's spec.*

- [ ] Capture AusCycling's new membership category set when the spec lands
- [ ] Define the seam now (a `MembershipSource` interface or equivalent) so the
      provider supplements track (a) rather than rewriting it — and so (a) is
      **not** held hostage to (b)
- [ ] Never re-introduce a model field holding a provider client secret (C9 —
      the lesson from the withdrawn polling)

**Database integrity (one additive migration):**
- [ ] `UniqueConstraint` on `Club.slug`, `ClubRole.name`,
      `Membership(rider, club, category, date)`, `ClubGrade(rider, club)`,
      `UserRole(user, club, role)`, `PointscoreTally(pointscore, rider)`
      — `Race.hash` is moot now that ingest is retired (B7)
- [ ] Replace the `ClubGrade.save()` Python uniqueness override with the
      constraint
- [ ] Bib-number uniqueness that actually fires: `UniqueConstraint` with
      `condition=Q(number__isnull=False)`; then delete the "increment to avoid
      clash" workarounds (one survives in `api.py`, the others went with 2.0)
- [ ] `Index` on `Race(date, status)` and the pointscore ordering columns
- [ ] Confirm no duplicate data against a production copy before applying
      (fixtures verified clean)

**Structure (shapes the API):**
- [ ] C1: merge `usermodel.py` into `models.py`, removing the six function-level
      circular imports
- [ ] C2: extract `services/` (results, pointscore, officials, exports) — pure
      functions, `transaction.atomic()` at the operation boundary, typed
      results, no HTTP or filesystem I/O in models
- [ ] C3: **simplified by the briefing** — with one client club, permissions
      answer "is this an official of the club that owns this object?". Keep the
      schema (capability flags, `UserRole`/`ClubRole`) but do not design a
      general RBAC engine. `Club.manage_results` has no reference outside its own
      definition; `manage_races` none outside tests
- [ ] C5/C6: structure `Race.grading` (the per-race grade set the entry screen
      renders — the React app needs it as an array, not a comma string); resolve
      the `place` 0-vs-NULL and `dob` 1970-01-01 sentinels; give
      `Rider.commissaire` a real boolean or drop its `"0"` sentinel
- [ ] C8: make `Rider.updated` delta tracking explicit instead of relying on
      `rider.save()  # to trigger timestamp update`
- [ ] C11/C12: kill the N+1 paths (`get_officials_with_counts`,
      `PointScore.tabulate` serialization, `tally_helpers`) and normalise
      `Club.statistics()` to counts + nested resources

**Success Criteria:** all tests pass (adjusted for A1/A2 semantics) plus new
tests for each fix; `makemigrations --check` clean; constraints verified against
a copy of production data; no model method performs network or filesystem I/O.

### 2.2 Monorepo: Vendor the Race-Day App (Week 6)

The unfinished React client moves into this repo. **Third revision framing:** it
is *not* the deployed system — **Angular is**, and Angular maps the upload
payload correctly — so there is no live data loss and nothing urgent. Vendoring
matters for a different reason: the React app is the forward path, it already
contains the post-AusCycling local-verification design (A8), and its D1/D2
defects are cheap to fix precisely *because* it is now in-repo and can be tested
against the real API.

**Three clients, one forward path — deliberate:**

| App | Status | Role here |
|---|---|---|
| Angular (`cabici-raceday`, Angular 8 / TS 3.5, 5,164 lines, 11 components, last touched 2022) | **Deployed race-day system, retires at cutover alongside the new API** | Reference for legacy wire format in `docs/raceday-contract.md` — not carried forward into the new endpoint |
| React (`cabici-raceday-react`, 3,724 lines, 8 pages/components, last commit 2026-09-05) | **unfinished**, predates the server work | Vendored as `frontend/apps/raceday`; the thing we finish |
| `frontend/apps/web` | to be built | The SPA replacing the Django template screens |

- [ ] **Do not vendor Angular as a buildable app.** Building Angular 8 in this
      repo's CI is cost with no benefit, and a third race-day implementation in
      the tree invites "which one is live?" confusion at the worst time
- [ ] **Extract Angular's wire semantics into this repo as documentation**
      (`docs/raceday-contract.md`): the `_buildUploadPayload()` field list
      (`payload.riders`, with `id, first_name, last_name, email, clubslug,
      licenceno, member_date, dob, gender, phone`) and the
      `getRider(e.riderid)` download mapping. That specification must not depend
      on a sibling checkout surviving
- [ ] **Keep the new results endpoint acceptable to Angular unchanged**, so the
      deployed system works throughout Phases 2–3 and its retirement is a clean
      deletion rather than a migration

**What is being vendored** (verified, not assumed):

| Source | Target |
|---|---|
| `../cabici-raceday-react` — Vite + React 18 + TS + MUI + pnpm, Vitest (23 tests), PWA/offline, Sentry; last commit 2026-09-05 | `frontend/apps/raceday` |
| (to be built) the SPA replacing the Django views | `frontend/apps/web` |
| generated from the OpenAPI schema (2.3) | `frontend/packages/api-client` |

**Mechanics:**

- [ ] Vendor with history preserved — `git subtree add --prefix=frontend/apps/raceday
      <repo> main` (simple, keeps the app buildable immediately) or
      `git filter-repo` + merge if a flattened tree is preferred. Do **not**
      copy files; losing the blame history loses the D1/D2 provenance evidence
- [ ] Root `package.json` workspaces (`frontend/apps/*`, `frontend/packages/*`),
      pnpm (the app already ships `pnpm-lock.yaml`), Node pinned in
      `.nvmrc`/`packageManager`
- [ ] **Mount `apps/raceday` on a subpath** (e.g. `/raceday/`) — required by
      same-origin, and the app is **not** configured for it today: `vite.config.ts`
      sets no `base`, `App.tsx` uses `<BrowserRouter>` with no `basename`, and it
      has a catch-all `<Route path="*" element={<Navigate to="/login"/>}>`.
      Narrow the PWA service-worker scope to the subpath as well
- [ ] Keep the two apps **separate deployables**. Race day is high-stakes and the
      entry app is offline-first; do not merge it into the club SPA. They share
      `packages/api-client` and (later) `packages/ui`
- [ ] Frontend CI: new workflow on `frontend/**` — `pnpm install --frozen-lockfile`,
      `lint`, `tsc --noEmit`, `vitest run`, `build`. Existing Python workflow
      gains path filters so each side only runs on its own changes
- [ ] Bring `PROJECT_CONTEXT.md` from the app repo into `frontend/apps/raceday/`
      (it is the design record for the Angular→React rewrite)
- [ ] Update `.devcontainer` (still Python 3.10 + pylint-era settings) so the
      monorepo has one reproducible dev environment

**Fixes — client-side (React only, so not urgent):**

- [ ] **D1:** the app sends `newriders`, `api.py:654` reads `riders` → **riders
      registered at the track are never saved**, their entries are dropped into an
      `errors` array the app discards, and the response is HTTP 200
      `"race results uploaded"`. Reproduced against the real API at cutover — an artifact of the legacy interface.
      The new API uses `newriders[]` natively.
- [ ] **D2:** the app looks riders up by `String(entry.rider)` but the API returns
      `rider` as a **display string** and the ID as `riderid` → **downloading
      existing entries always returns an empty sheet**. Angular used
      `e.riderid`. **Not live.** Fix accordingly
- [ ] **D4:** surface the server's `errors[]` to the race director instead of
      dropping it in `EntryService.uploadEntries()`
- [ ] Add regression tests that exercise the **real HTTP boundary** for all of the
      above — the absence of exactly this is why D1/D2 survived both test suites

**Fixes — server-side (affects the deployed Angular app):**

- [ ] **A9 (live production bug):** `api.py:821` compares `grade_change == "y"`
      while **both** clients send a JSON boolean, so in-race grade changes have
      never applied in production. Also absent from the GET response, so a
      download resets it to `false`. Fix both ends
- [ ] **D3 (server half):** the upload deletes all results then re-inserts only
      what is sent, with no permission class and no transaction — so *any*
      authenticated user can replace any race's results, and a mid-request failure
      leaves the race half-populated. Reproduced: 3 results → 1, HTTP 200, no
      conflict signal. Add `transaction.atomic()`, a permission class, and an
      explicit overwrite contract (confirmation flag or version/`If-Match`)
      instead of silent replace-all — **while staying acceptable to Angular**
- [ ] **A8:** honour `member_category` and `verifiedMemberDate` instead of
      hardcoding `category="race"` — this is track (a) of the membership work in
      2.1, and it is what makes the React app finishable
- [ ] **Preserve the offline contract:** `RiderService` does a full paginated
      load, caches riders in `localStorage`, and refreshes with
      `?changed=<unix>`, merging by `rider.id`. That is load-bearing at a
      velodrome with poor reception. Any replacement (`?updated_after=`) must
      keep delta sync, pagination and stable IDs, and must not silently drop
      deleted riders
- [ ] **Treat Angular as the reference implementation** for upload/download
      semantics — `../cabici-race-manager-owen/src/app/services/entry.service.ts`
      is the only place the correct wire mapping still exists, which is why its
      extraction into `docs/` is a task above

**Why this is a Phase 2 task, not Phase 3:** the API contract is being designed in
2.3, and both clients' shapes are inputs to it — Angular's because it is the
compatibility target, the React app's because it is what we are finishing.

**Success Criteria:** both apps build and test green in this repo's CI; D1–D4
closed with regression tests; one shared generated client; no hand-written API
types left in either app.

### 2.3 Resource Model & API Contract (Week 7)

Replaces the old "map current views to endpoints" task — the old views are going
away, so resources are derived from the domain instead. **One contract, designed for the React app alone**, and the generated client is the only sanctioned way to talk to it.

- [ ] Enumerate resources from the merged models: clubs, races, racecourses,
      riders, memberships, club roles, user roles, club grades, race staff, race
      results, pointscores, pointscore tallies, users/auth
- [ ] One public identifier per concept, applied consistently (rider = `Rider.id`
      everywhere; the old API used `Rider.id`, `User.id` and a display string
      interchangeably under the same key names)
- [ ] Explicit representation contracts (read shape, write shape) — never
      `fields='__all__'`
- [ ] Filters as `django-filter` `FilterSet`s, replacing `?select=`/`?count=`/
      `?prefix=`/`?changed=` with `?status=`, `?date_after=`, `?club=`,
      `?search=`, `?ordering=`, `?updated_after=`
- [ ] Domain operations as explicit actions: `POST /races/bulk/`,
      `POST /pointscores/{id}/recalculate/`,
      `POST /clubs/{slug}/officials/allocate/`
- [ ] Publish the OpenAPI spec **before** implementing and generate the
      TypeScript client from it (`openapi-typescript` / `orval`) into
      `frontend/packages/api-client`, which **both** apps must consume — this is
      the control that prevents a repeat of D1/D2
- [ ] Re-express delta sync as `?updated_after=<iso8601>` while preserving the
      offline behaviour listed in 2.2
- [ ] Contract test in CI: the served schema, the generated client and the
      raceday app's upload payload are checked against each other end-to-end

**Success Criteria:** written contract covering 100% of the operations both
clients need; OpenAPI spec committed and served; generated TS client compiles in
both apps; the contract test fails if either side drifts.

### 2.4 Authentication & Same-Origin Wiring (Week 8)

Same-origin (decided — see 3.1) removes a whole category of work here and adds a
few specific tasks.

- [ ] `djangorestframework-simplejwt` with access + refresh endpoints
- [ ] Register, password reset (request + confirm), profile read/patch
- [ ] Logout / token blacklist or short-lived access + rotating refresh
- [ ] allauth → JWT for the social/session path; keep session auth for `/admin/`
- [ ] Fix the carried-over defects: unknown email must return 401 (not 500), and
      a user without a `Rider` must not 500 on `user.rider.club` — the raceday
      login depends on `club` and `official` being present
- [ ] **Token storage settled by same-origin:** access token in memory, refresh
      token in an **httpOnly SameSite cookie**. The previous
      "memory vs httpOnly cookie" question is closed, and bearer-in-`localStorage`
      is off the table. Cookie-authenticated writes need CSRF protection (DRF's
      `SessionAuthentication` provides it; a cookie-JWT authentication class must
      too)
- [ ] **Delete CORS entirely** rather than scoping it: `corsheaders` from
      `INSTALLED_APPS`, `CorsMiddleware`, and `CORS_ALLOW_ALL_ORIGINS` /
      `CORS_URLS_REGEX` / `CORS_ALLOW_METHODS` all go. Also drop
      `django-cors-headers` from `requirements/base.txt`
- [ ] **allauth links must resolve into the SPA.** Password-reset and
      email-confirmation URLs are currently rendered as absolute template links;
      with those flows moving to SPA screens they must point at SPA routes —
      needs allauth URL/adapter configuration, not just endpoints. Previously
      untasked anywhere
- [ ] **Flatpages need a decision:** `FlatpageFallbackMiddleware` + the `/` flatpage
      back the current home page content. With `/` owned by the SPA, either
      expose pages as a resource (`GET /api/pages/<path>/`) or reorder the
      middleware
- [ ] **Delete DRF token auth** at cutover alongside Angular — neither the React
      raceday app nor the SPA needs it; both use JWT (refresh in httpOnly cookie)
      from the start.
- [ ] Migrate `frontend/apps/raceday` off `AUTH_HEADER_PREFIX = 'Token'` and its
      `localStorage` token storage

**Success Criteria:** every auth endpoint tested, including the failure paths
that currently 500; no CORS configuration anywhere in the project; password reset
and email confirmation work end-to-end against the SPA routes.

### 2.5 Core CRUD Implementation (Weeks 9-10)

**Code structure:**
```
races/apps/cabici/
  models.py                  # merged domain models (2.1)
  services/                  # domain operations (2.1)
    __init__.py
    results.py               # race-day upload
    pointscore.py            # tally / recalculate
    officials.py             # allocation
    exports.py               # rider XLS, race summary, member CSV
  api/
    __init__.py
    routers.py               # DefaultRouter wiring for /api/v1/
    pagination.py
    permissions.py           # club-official model (C3, simplified)
    filters/
      __init__.py
      race.py
      rider.py
      results.py
    serializers/
      __init__.py
      club.py
      race.py
      rider.py
      membership.py
      results.py
      pointscore.py
    views/
      __init__.py
      club.py
      race.py
      rider.py
      membership.py
      results.py             # the race-day contract (2.2)
      pointscore.py
      auth.py
```

**Tasks:**
- [ ] ViewSets + `DefaultRouter` under `/api/v1/` (no hand-wired URL pairs)
- [ ] Explicit serializer fields for every resource; write shapes separated from
      read shapes
- [ ] `select_related` / `prefetch_related` on every queryset (C11)
- [ ] Pagination on every list endpoint, uniform defaults (200/1000 lifted from
      `StandardResultsSetPagination`)
- [ ] Permission classes from 2.1/C3 applied uniformly — including the result
      uploader, which currently has none
- [ ] `transaction.atomic()` around every multi-row write
- [ ] Schema annotations (`drf-spectacular`) on each viewset/action as it lands

**Success Criteria:**
- All CRUD operations available via API with tests for permissions, filtering,
  pagination and error shapes
- No endpoint reachable by an unauthenticated write; no 500s on expected client
  errors (400/401/403/404/409 instead)
- >80% coverage on `api/` and `services/`
- The race-day contract from 2.2 is served by `api/views/results.py`, not by the
  legacy module

### 2.6 API Documentation (Week 11)

- [ ] `drf-spectacular` generating OpenAPI 3.x from annotations
- [ ] Interactive docs at `/api/docs/`, schema at `/api/schema/`
- [ ] Postman/Insomnia collection generated from the schema
- [ ] Usage guide covering auth flow, filtering, pagination, error envelope,
      result upload and the export endpoints
- [ ] Regenerate the TypeScript client from the final spec

**Success Criteria:** interactive docs; every endpoint documented with examples.

### 2.7 Test Suite Rebuild & Retirement of `api.py` (Week 12)

- [ ] Per-resource endpoint tests (CRUD, filters, pagination, permissions)
- [ ] Service-layer tests for result upload, bulk race creation, official
      allocation, pointscore recalculation, membership validation
- [ ] Contract test: generated TS client types match the served schema
- [ ] Achieve >80% coverage; raise `fail_under` in `pyproject.toml` in step
      (42 → 60 → 80) so the gate ratchets rather than leaping
- [ ] **Delete `races/apps/cabici/api.py`** and its hand-wired URL pairs in one
      commit, once the new package covers the surface. No shim, no dual-running

**Success Criteria:** all tests passing, >80% coverage enforced in CI, `api.py`
gone.

---

## Phase 3: React Frontend Development

**Goal:** Build modern React frontend consuming the API

### 3.1 Frontend Architecture — DECIDED: monorepo (Week 13)

**Decision (2026-10-11): both React apps live in this repository**, under a
`frontend/` workspace root. This supersedes the previous recommendation here
(*"Separate repository approach for maximum flexibility"*) and resolves the
contradiction with `.github/copilot-instructions.md`, which had always described
an in-repo frontend directory.

**Why the earlier recommendation is now wrong.** "Separate repository" was
written when the only frontend was the Django template layer. Since then the
race-day app was rewritten in React in its own repo, and the D1/D2 defects are
the direct product of that split: two repos hand-maintaining one wire format,
with every layer mocking the layer beneath it, so neither test suite could see
the mismatch. A monorepo with a schema-generated client makes that class of bug
uncompilable — which is the whole reason it is worth more than the flexibility it
costs.

**Layout:**

```
frontend/
  package.json            # pnpm workspaces root
  pnpm-lock.yaml
  packages/
    api-client/           # GENERATED from the Django OpenAPI schema (2.3)
    ui/                   # shared components, added when a second consumer needs it
  apps/
    raceday/              # vendored from stevecassidy/cabici-raceday-react (2.2)
    web/                  # new SPA replacing the Django template views (Phase 3)
```

**Pros:** one contract and one generated client for both clients; atomic changes
across backend and frontend; a single CI run can test both ends of the upload
path (the control that would have caught D1); shared tooling, types and
components; one place to look for a new contributor.

**Cons, and mitigations:** heavier root-level tooling (Node pinned, workspaces
scoped entirely under `frontend/`); CI needs path filters so Python and JS runs
stay independent; two apps tempt premature abstraction — keep `packages/ui` empty
until a real second consumer exists.

**Kept deliberately separate:** `apps/raceday` and `apps/web` remain two
deployables. Race day is high-stakes, offline-first and used by volunteers on
tablets; merging it into the club SPA would put that reliability in the same
release train as routine feature work.

**Newly-opened decision — deployment topology. DECIDED (2026-10-11): same-origin
for now.** Django serves both SPA builds via WhiteNoise; the split stays open
later because the apps are already separate build outputs. Rationale and the
consequences it commits us to:

| | **Same-origin (DECIDED)** | Separate hosting (deferred) |
|---|---|---|
| CORS | **none to configure or reason about** | required for both apps |
| Auth | httpOnly cookie + CSRF; access token in memory | in-memory + refresh across origins |
| Deploys | one image, one cutover — matches the plan's approach | frontend ships independently of the API |
| Static assets | WhiteNoise (already in use) | CDN, image optimisation, preview deploys |
| Risk | frontend redeploy restarts the backend container | two places to monitor |

It removes a whole class of Phase 4 integration work (CORS policy, credential
handling, two-host smoke tests) and it is reversible later. What it commits to is
enumerated in 2.2 (subpath mounting), 2.4 (CORS deleted, cookie auth, allauth
links into the SPA, flatpage disposition) and 4.3 (multi-stage Docker, the
static-storage trap, `.dockerignore`).

The trade-offs considered, kept as the record of what was weighed:

| | Same-origin (Django serves the SPA builds) | Separate hosting (Vercel/Cloudflare Pages) |
|---|---|---|
| CORS | none to configure or reason about | required for both apps |
| Auth | httpOnly cookie + CSRF, tokens never in `localStorage` | in-memory + refresh, or bearer in cookie scope |
| Deploys | one image, one cutover — matches the plan's approach | frontend ships independently of the API |
| Static assets | WhiteNoise (already in use) | CDN, image optimisation, preview deploys |
| Risk | frontend redeploy restarts the backend container | two places to monitor |

**~~Recommendation~~ → DECIDED: same-origin for now** (2026-10-11). Django serves
both builds via WhiteNoise; the split remains open later because the apps are
already separate build outputs. See the table above for what this commits to, and
2.2 / 2.4 / 4.3 for the resulting tasks.

**Also decided by the vendoring:** the stack is whatever the raceday app already
uses — **React 18 + TypeScript + Vite + MUI + react-hook-form + axios + Vitest**.
That settles two questions the plan had left open ("Tailwind or MUI", and the
choice of HTTP client and form library): `apps/web` should match `apps/raceday`
so `packages/ui` and the generated client are used identically by both. React
Query is still worth adding for server state (the raceday app hand-rolls
`localStorage` caching and pagination, which is exactly what it replaces) —
introduce it in `apps/web` first, then retro-fit `apps/raceday` only if it helps
the offline path.

### 3.2 Frontend Setup (Week 13-14)

**Technology Stack** — fixed by the app already in production (see 2.2 and 3.1);
`apps/web` matches `apps/raceday` so both use the generated client and any shared
components identically:
- React 18 + TypeScript (already in use)
- Vite (already in use)
- **Material UI** + Emotion (already in use — this settles the "Tailwind or MUI"
  question in favour of MUI)
- React Router 6 (already in use)
- React Hook Form (already in use)
- Axios (already in use) — but replaced by the **generated `packages/api-client`**
  for all API calls
- **TanStack Query** — to add. `apps/raceday` hand-rolls pagination, `localStorage`
  caching and delta merge; that is precisely server-state management. Introduce it
  in `apps/web` first and retro-fit `apps/raceday` only where it helps the offline
  path
- Zustand or Context API for UI state (raceday uses Context today)
- Zod for validation, where schemas are not already derivable from the OpenAPI
  types
- Vitest + React Testing Library (already in use)

**Initial Setup:**
```bash
# 2.2 vendors apps/raceday with `git subtree`; apps/web is scaffolded alongside it
mkdir -p frontend/apps/web frontend/packages/api-client
cd frontend && pnpm create vite@latest apps/web -- --template react-ts
pnpm add -D openapi-typescript   # in packages/api-client, from the served schema
```

**Project Structure:**
```
frontend/
  package.json            # pnpm workspaces root
  packages/
    api-client/           # GENERATED from the Django OpenAPI schema - the only
                          # sanctioned way either app talks to the API
    ui/                   # shared components (only once a 2nd consumer needs it)
  apps/
    raceday/              # vendored React entry app (offline PWA)
      src/
        components/  context/  hooks/  pages/  services/  types/  utils/
    web/                  # new SPA replacing the Django template views
      src/
        components/    # Reusable components
        features/      # clubs/ races/ riders/ auth/
        hooks/  lib/  pages/  routes/  types/
```
    App.tsx
    main.tsx
  public/
  tests/
```

**Tasks:**
- [ ] Initialize React project with TypeScript
- [ ] Set up routing structure
- [ ] Configure API client with authentication
- [ ] Set up state management
- [ ] Configure build pipeline
- [ ] Set up environment variables (.env)

### 3.3 Core Features Implementation (Week 15-24)

**Priority Order:**

#### Phase 3.3.1: Authentication & Layout (Week 15-16)
- [ ] Login/logout functionality
- [ ] User registration
- [ ] Password reset
- [ ] Protected routes
- [ ] Main layout with navigation
- [ ] User profile page

#### Phase 3.3.2: Club Management (Week 17-18)
- [ ] Club list view
- [ ] Club detail view
- [ ] Club dashboard
- [ ] Club member management
- [ ] Club statistics display

#### Phase 3.3.3: Race Management (Week 19-20)
- [ ] Race list with filters
- [ ] Race detail view
- [ ] Race creation form (single + bulk)
- [ ] Race editing
- [ ] Race officials management
- [ ] Race status management (draft/published)

#### Phase 3.3.4: Rider Management (Week 21-22)
- [ ] Rider list with search
- [ ] Rider detail/profile
- [ ] Rider creation/editing
- [ ] Rider grade management
- [ ] Rider autocomplete component

#### Phase 3.3.5: Results & Pointscores (Week 23-24)
- [ ] Result upload interface
- [ ] Result display
- [ ] Pointscore displays
- [ ] Pointscore audit view

### 3.4 Advanced Features (Week 25-26)

**Tasks:**
- [ ] Excel file upload with drag-and-drop
- [ ] Real-time updates (if needed, use WebSockets)
- [ ] Advanced filtering and search
- [ ] Data export functionality
- [ ] Google Maps integration for race locations
- [ ] Calendar views for races
- [ ] Email composition interface

### 3.5 Testing & Quality (Week 27-28)

**Tasks:**
- [ ] Unit tests for components
- [ ] Integration tests for features
- [ ] E2E tests with Playwright or Cypress
- [ ] Accessibility audit (WCAG 2.1 AA)
- [ ] Performance optimization
- [ ] Bundle size optimization
- [ ] Mobile responsiveness testing

---

## Phase 4: Integration & Final Testing

**Goal:** Integrate all components, clean up legacy code, and prepare for production deployment

### 4.1 Backend Cleanup (Week 29)

**Tasks:**
- [ ] Remove all Django template files (archived in git history)
- [ ] Remove jQuery code and static assets
- [ ] Remove frontend-related URL patterns
- [ ] Remove template views from views.py
- [ ] Update Django to API-only mode:
  - Remove template configuration from settings
  - Keep session auth only for admin panel
  - Keep CSRF only for admin panel
  - Remove template middleware
- [ ] Clean up settings.py (remove TEMPLATES, STATICFILES_DIRS, etc.)
- [ ] Update INSTALLED_APPS (remove unnecessary apps)
- [ ] Final code cleanup and formatting

**Success Criteria:**
- Django serves only API and admin
- All template code removed
- Clean codebase ready for deployment

### 4.2 Integration Testing (Week 30-31)

**Tasks:**
- [ ] Full integration testing of React + Django API
- [ ] Test all user workflows end-to-end
- [ ] Cross-browser testing (Chrome, Firefox, Safari, Edge)
- [ ] Mobile device testing (iOS, Android)
- [ ] Performance testing with realistic data volumes
- [ ] Load testing API endpoints
- [ ] Security audit and penetration testing
- [ ] Accessibility testing (WCAG 2.1 AA)
- [ ] Test error scenarios and edge cases
- [ ] Fix all critical and high-priority issues

**Success Criteria:**
- All critical bugs fixed
- Performance meets targets
- Security vulnerabilities addressed
- Accessibility standards met

### 4.3 Production Deployment (Week 32)

**Architecture: Option 3 — Django serves both SPA builds (DECIDED, same-origin).**
The options below are kept as the record of what was considered; Options 1 and 2
are not being taken.

```
Docker container (python:3.14-alpine, multi-stage)
  ├── node stage: pnpm install && pnpm -r build  → frontend/apps/*/dist
  └── python stage: collectstatic + gunicorn
        ├── /            → apps/web   (SPA index.html via a catch-all view)
        ├── /raceday/    → apps/raceday (vendored entry app, SW scoped to subpath)
        ├── /admin/      → Django admin (session auth)
        ├── /accounts/   → allauth (email confirmation / reset links resolve to SPA routes)
        ├── /api/        → DRF (/api/v1/ + legacy shapes for Angular until retirement)
        └── /static/     → WhiteNoise, both builds' hashed assets
```

No CORS, no second host, one image, one cutover — which is why same-origin was
chosen. The split (Option 1) stays available later because the apps are already
separate build outputs.

**Build & packaging work this decides:**

- [ ] **Multi-stage Dockerfile.** Today it is `python:3.14-alpine` with no Node:
      add a `node` stage that runs `pnpm install --frozen-lockfile && pnpm -r
      build`, and copy the `dist` outputs into the Python image
- [ ] **`.dockerignore` must exclude `node_modules`** — verified absent today
      (zero matches); without it the build context carries every sibling app's
      dependencies
- [ ] **Resolve the static-storage/manifest trap ⚠️.** Vite emits
      content-hashed filenames; `CompressedManifestStaticFilesStorage` re-hashes
      them and rewrites references inside collected CSS/JS **but not inside
      `index.html`** (served as a template), so asset URLs break. Manifest hashing
      adds nothing for already-fingerprinted files → use
      `whitenoise.storage.CompressedStaticFilesStorage` (compression, no
      rewriting), keeping manifest hashing only if Django's own static needs it
- [ ] **CI smoke test for exactly that trap:** run `collectstatic` against a real
      frontend build and assert every `src`/`href` in the emitted `index.html`
      resolves to a collected file. Cheap to write, and it is the difference
      between discovering this in CI and discovering it at 11pm before race day
- [ ] **SPA catch-all routing** for both apps, with the admin/api paths ordered
      before it, plus `404.html`/`500.html` handling that does not assume the
      template layer
- [ ] `STATICFILES_DIRS` gains both builds; `ALLOWED_HOSTS` /
      `SECURE_*` / `CSRF_TRUSTED_ORIGINS` reviewed for one-origin operation

**Preparation:**
- [ ] Final database backup before deployment
- [ ] Prepare rollback plan (previous Docker image)
- [ ] Configure production environment variables
- [ ] Set up monitoring (Sentry — already a dependency of `apps/raceday`)
- [ ] Verify SSL certificates
- ~~Set up frontend hosting (Vercel recommended)~~ — not applicable same-origin
- ~~Configure CDN if needed~~ — deferred; WhiteNoise + immutable cache headers
  cover the interim

**Deployment Steps:**
- [ ] Build the image (Node stage compiles both frontends)
- [ ] Deploy Django to production (Docker) — one image, one cutover
- [ ] Run database migrations
- [ ] Confirm both SPAs load through `collectstatic` output
- [ ] Run migrations and smoke test all critical functionality
- [ ] Monitor logs and error rates
- ~~Update DNS/routing as needed~~ · ~~Update CORS settings for production domain~~
  — both eliminated by same-origin

**Angular retirement (cutover, not a separate gate):**
- [ ] Angular retires at cutover alongside the new API, `apps/web`, and
      `apps/raceday`. No phased withdrawal — all three deploy together.
- [ ] Before cutover, confirm parity: `apps/raceday` has equivalent features for all
      11 Angular components, D1/D2/D4 are fixed, A8/A9 honored, offline behavior
      verified on a real race.

**Post-Deployment:**
- [ ] Monitor application for 24-48 hours
- [ ] Address any immediate issues
- [ ] Communicate changes to users
- [ ] Collect user feedback

**Success Criteria:**
- Application fully functional in production
- No critical errors
- Performance meets targets
- Users can access and use the application

### 4.4 Documentation (Week 33)

**Tasks:**
- [ ] Create API documentation
- [ ] Document React component library
- [ ] Write deployment guide
- [ ] Create developer onboarding docs
- [ ] Document environment setup
- [ ] Create troubleshooting guide
- [ ] Video tutorials for key features

---

## Phase 5: Optimization & Modern Django Features

**Goal:** Leverage new Django features and optimize performance

### 5.1 Django 5.x Features (Week 34-35)

**New Features to Implement:**

1. **Field Groups in Forms**
   - Update ModelForms to use field groups
   - Improve form rendering in API responses

2. **Database-Computed Default Values**
   - Add `db_default` to model fields where appropriate

3. **Simplified Templates** (if keeping admin)
   - Use new template features

4. **Async Views** (if beneficial)
   - Convert high-traffic endpoints to async
   - Requires async database driver

5. **Composite Primary Keys** (Django 5.1+)
   - Evaluate models that could benefit

**Tasks:**
- [ ] Audit models for Django 5.x features
- [ ] Update model definitions
- [ ] Add database indexes where needed
- [ ] Implement select_related/prefetch_related optimizations

### 5.2 Performance Optimization (Week 36)

**Backend:**
- [ ] Add Redis caching for frequently accessed data
- [ ] Implement API response caching
- [ ] Optimize database queries (N+1 problems)
- [ ] Add database indexes
- [ ] Implement query result pagination
- [ ] Add API rate limiting

**Frontend:**
- [ ] Implement code splitting
- [ ] Lazy load routes
- [ ] Optimize images
- [ ] Add service worker for offline support
- [ ] Implement optimistic updates
- [ ] Add skeleton loaders

### 5.3 Security Hardening (Week 37)

**Tasks:**
- [ ] Security audit of API endpoints
- [ ] Implement rate limiting (django-ratelimit)
- [ ] Add request throttling
- [ ] Review and update CORS policies
- [ ] Add CSP headers
- [ ] Implement API key authentication for integrations
- [ ] Add audit logging
- [ ] Security headers configuration
- [ ] Dependency security scan (npm audit, safety)

### 5.4 Monitoring & Observability (Week 38)

**Tasks:**
- [ ] Set up Sentry for error tracking
- [ ] Configure Django logging
- [ ] Add application metrics (Prometheus + Grafana)
- [ ] Set up uptime monitoring
- [ ] Create performance dashboards
- [ ] Add user analytics (privacy-respecting)
- [ ] Set up alerts for critical issues

---

## Django + React Integration Deep Dive

### Authentication Strategy

**Recommended Approach: Dual Authentication**

```python
# settings.py
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': [
        'rest_framework_simplejwt.authentication.JWTAuthentication',
        'rest_framework.authentication.SessionAuthentication',  # For admin
    ],
    'DEFAULT_PERMISSION_CLASSES': [
        'rest_framework.permissions.IsAuthenticatedOrReadOnly',
    ],
}
```

**JWT Flow:**
1. User logs in via `/api/auth/login/`
2. Backend returns access + refresh tokens
3. Frontend stores tokens (localStorage or memory)
4. Frontend includes token in Authorization header
5. Backend validates token on each request

**Social Auth (Strava) Integration:**
- Keep django-allauth for OAuth flow
- Return JWT after successful social auth
- Frontend redirects to auth endpoint
- Backend handles OAuth callback, returns JWT

### CORS Configuration

```python
# settings.py
CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",  # Vite dev server
    "https://app.cabici.com",  # Production frontend
]

CORS_ALLOW_CREDENTIALS = True

CORS_ALLOW_METHODS = [
    'DELETE',
    'GET',
    'OPTIONS',
    'PATCH',
    'POST',
    'PUT',
]
```

### Frontend API Client Setup

```typescript
// src/lib/api.ts
import axios from 'axios';

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

// Add auth token to requests
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('accessToken');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// Handle token refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    if (error.response?.status === 401) {
      // Try to refresh token
      // If refresh fails, redirect to login
    }
    return Promise.reject(error);
  }
);

export default api;
```

---

## Migration Strategies & Risk Mitigation

### Risk: Breaking Existing Functionality

**Mitigation:**
- Work on feature branches merged to `modernization` by reviewed PR; production
  remains stable
- Comprehensive test suite before deployment
- Full integration testing before production deployment
- Rollback plan ready (previous Docker image + database backup)
- Database backup immediately before deployment

### Risk: Data Loss During Migration

**Mitigation:**
- Database backups before any migration
- Test migrations on copy of production data
- Verify data integrity after migrations
- Keep audit trail of changes

### Risk: User Adoption of New Frontend

**Mitigation:**
- Similar UI/UX to existing application (minimize learning curve)
- User training materials and video walkthrough
- Advance communication about changes
- Feedback collection mechanism
- Support channel for issues
- Be responsive to early feedback

### Risk: Performance Degradation

**Mitigation:**
- Load testing before launch
- Monitoring and alerting
- Performance budgets
- CDN for static assets
- Database query optimization

---

## Resource Requirements

### Development Team
- 1 Full-stack developer or 1 Backend + 1 Frontend developer
- Part-time DevOps for deployment
- QA/Testing support (can be same developers)

### Timeline
- **Phase 1 (Foundation):** 4 weeks
- **Phase 2 (Backend API):** 8 weeks
- **Phase 3 (Integration & Deployment):** 4 weeks
- **Phase 5 (Optimization):** 5 weeks
- **Buffer:** 3 weeks
- **Total:** ~38 weeks (~9 months)

*Note: Timeline assumes part-time development (15-20 hours/week). Full-time development could complete in 4-5 months.*

**Development Approach:** All work is done on short-lived branches merged into
the `modernization` integration branch by reviewed pull request. Production
remains on `master` branch and stays stable throughout development. Once all
phases are complete and tested, the new version is merged and deployed to
production in a single cutover.
*Note: Timeline assumes part-time development (15-20 hours/week). Full-time development could complete in 5-6 months.*

### Infrastructure Costs

**Development:**
- Free tier services sufficient (Vercel, Railway, etc.)

**Production:**
- Backend: Current Digital Ocean droplet (unchanged)
- Frontend: $0-20/month (Vercel, Netlify)
- Potential CDN costs if high traffic

---

## Success Metrics

### Technical Metrics
- [ ] Test coverage > 80%
- [ ] API response time < 200ms (p95)
- [ ] Frontend bundle size < 500KB
- [ ] Lighthouse score > 90
- [ ] Zero critical security vulnerabilities
- [ ] 99.9% uptime

### User Experience Metrics
- [ ] Page load time < 2 seconds
- [ ] Time to interactive < 3 seconds
- [ ] User error rate < 5%
- [ ] User satisfaction score > 4/5

### Business Metrics
- [ ] No data loss during migration
- [ ] < 1 day downtime total
- [ ] Feature parity with old application
- [ ] Successful user adoption (> 80%)

---

### Quick Wins (Early in Development)

While working through the full plan on the development branch:

### Week 1-2
- Create development branch
- Update to Django 5.2
- Set up CI/CD pipeline
- Configure code formatting (Black, ruff)

### Week 3-6
- Complete API documentation
- Add missing API endpoints
- Implement JWT authentication

### Week 7-16
- Build React authentication flow
- Create component library
- Implement major features
- Continuous integration testing

---

## Appendix

### A. Technology Comparison

#### State Management
| Option | Pros | Cons |
|--------|------|------|
| Context API | Built-in, simple | Performance issues with frequent updates |
| Zustand | Lightweight, simple API | Less ecosystem |
| Redux Toolkit | Mature, DevTools | More boilerplate |
| Jotai/Recoil | Atomic state | Learning curve |

**Recommendation:** Zustand for UI state, React Query for server state

#### Styling

**Decided (2026-10-11): Material UI.** The vendored race-day app is already built
on MUI 5 + Emotion, and `apps/web` matches it so shared components and the
generated client are used identically by both. The options below are kept only as
the record of what was considered.

| Option | Pros | Cons |
|--------|------|------|
| Tailwind CSS | Utility-first, fast | Verbose HTML |
| **Material UI** | Complete component library; **already in production use** | Large bundle |
| Chakra UI | Accessible, themeable | Smaller ecosystem |
| CSS Modules | Scoped CSS | Manual work |

### B. Code Examples

#### Modern API ViewSet

```python
# races/apps/cabici/api/views/race.py
from rest_framework import viewsets, filters, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django_filters.rest_framework import DjangoFilterBackend

class RaceViewSet(viewsets.ModelViewSet):
    queryset = Race.objects.select_related('club', 'location').all()
    serializer_class = RaceSerializer
    filter_backends = [DjangoFilterBackend, filters.SearchFilter, filters.OrderingFilter]
    filterset_fields = ['club', 'status', 'discipline']
    search_fields = ['title', 'location__name']
    ordering_fields = ['date', 'title']
    
    def get_queryset(self):
        queryset = super().get_queryset()
        if self.request.query_params.get('select') == 'future':
            queryset = queryset.filter(date__gte=timezone.now().date())
        return queryset
    
    @action(detail=True, methods=['post'])
    def upload_results(self, request, pk=None):
        race = self.get_object()
        serializer = ResultUploadSerializer(data=request.data)
        if serializer.is_valid():
            # Process results
            return Response({'status': 'success'})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
```

#### React Component Example

```typescript
// src/features/races/components/RaceList.tsx
import { useQuery } from '@tanstack/react-query';
import { getRaces } from '@/api/races';

export function RaceList() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['races', { select: 'future' }],
    queryFn: () => getRaces({ select: 'future' }),
  });

  if (isLoading) return <LoadingSkeleton />;
  if (error) return <ErrorMessage error={error} />;

  return (
    <div className="space-y-4">
      {data?.results.map((race) => (
        <RaceCard key={race.id} race={race} />
      ))}
    </div>
  );
}
```

### C. Useful Resources

**Django:**
- [Django 5.2 Release Notes](https://docs.djangoproject.com/en/5.2/releases/5.2/)
- [Django REST Framework Documentation](https://www.django-rest-framework.org/)
- [DRF Spectacular](https://drf-spectacular.readthedocs.io/)
- [Django CORS Headers](https://github.com/adamchainz/django-cors-headers)
- [Simple JWT](https://django-rest-framework-simplejwt.readthedocs.io/)

**React:**
- [React Documentation](https://react.dev/)
- [Vite Guide](https://vitejs.dev/guide/)
- [TanStack Query](https://tanstack.com/query/latest)
- [React Router](https://reactrouter.com/)
- [Tailwind CSS](https://tailwindcss.com/)

**Testing:**
- [Django Testing](https://docs.djangoproject.com/en/5.2/topics/testing/)
- [React Testing Library](https://testing-library.com/react)
- [Playwright](https://playwright.dev/)

**Deployment:**
- [Vercel](https://vercel.com/)
- [Netlify](https://www.netlify.com/)
- [Railway](https://railway.app/)

---

## NeCreate development branch** from master (`git checkout -b modernization`)
3. **Set up development environment** for Phase 1
4. **Create GitHub project board** for tracking progress
5. **Begin Phase 1** - Django upgrade on development branch
6. **Production remains stable** on master branch until final deployment

**Key Decisions to Make:**
- Timeline target (9 months part-time or 4-5 months full-time)?
- Development capacity (hours per week)?
- Testing strategy (manual vs. automated priority)?
- Target deployment date?
- Communication plan for users about upcoming changes?
- Maintenance window requirements for deployment
- Will you have dedicated development time or part-time?
- Do you want to involve the existing client (React) in the planning?
- What's the budget for infrastructure/hosting?

---

*Last Updated: 2026-08-29*
*Version: 1.0*
