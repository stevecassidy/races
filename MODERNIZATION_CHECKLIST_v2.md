# Modernization Checklist — Revised (post-2026-10-23)

This checklist reflects the re-planned architecture described in
[`REPLANNED_ARCHITECTURE.md`](REPLANNED_ARCHITECTURE.md). Items completed under
the previous plan remain marked. The phase sequence has been revised:
- Phase 2 is expanded and re-sequenced (API-first, content endpoints, revised auth)
- Phase 3 is monorepo setup (was frontend setup)
- Phase 4 is the React management frontend (was Phase 3)
- Phase 5 is the Astro presentation frontend (new)
- Phase 6 is integration & deployment (was Phase 4)

**Development Approach:** Work happens on short-lived branches cut from
`modernization`, each landing as a reviewed pull request. `modernization` is the
integration branch and is never committed to directly.

---

## ✅ Phase 1: Foundation — COMPLETE

See original checklist for detailed verification. Summary:
- Django 5.2, Python 3.14, all deps pinned
- Black / ruff / mypy / pre-commit / CI in place
- 49 tests passing, coverage 44%

---

## ✅ Phase 2: Backend API Rebuild

Goals:
1. Complete the API for **all** domain resources
2. Add content management endpoints for the Astro presentation site
3. Support both same-origin (management apps) and cross-origin (Astro) auth
4. Retire `api.py` once the new API covers its surface

### 2.0 Retirement Pass — ✅ COMPLETE

3,463 Python lines removed. See original checklist.

### 2.1 Model Hardening — MOSTLY COMPLETE

- [x] A1: PointScore reads configurable fields (defaults match legacy)
- [x] A1b: deleted `PointScore.method` — migration `0018`
- [x] A2: membership categories `Ride`/`Club`/`Race` — migration `0019`
- [x] A9: grade_change boolean fix (live production bug)
- [x] Integrity constraints — migrations `0020`, `0021`
- [x] C1: merged `usermodel.py` into `models.py`
- [x] C2: services extracted (`results.py`, `pointscore.py`, `officials.py`, `exports.py`)
- [ ] **C3:** permissions model — simplified to "official of owning club"
- [ ] **C5/C6:** `Race.grading` structure; `place` 0-vs-NULL; `dob` 1970-01-01 sentinel; `Rider.commissaire` boolean
- [ ] **C8:** explicit `Rider.updated` delta tracking
- [ ] **C11/C12:** N+1 elimination; `Club.statistics()` normalisation
- [ ] **Before deploy:** run `checkconstraints` against production copy, resolve duplicates
- [ ] A3: `Race`/`Rider.get_absolute_url()` (fixed in some branches, verify landed)

### 2.2 API Contract & OpenAPI Design

- [ ] Enumerate all resources from the domain:
  - clubs, racecourses, races, riders, memberships
  - club roles, user roles, club grades, race staff, race results
  - pointscores, pointscore tallies
  - users, auth, sessions
  - **content pages, posts** (new for Astro site)
  - ✅ current v1 contract now includes clubs, races, racecourses, riders,
    race results, pointscores, club roles and user roles
- [ ] Design race-day upload/download contract:
  - Extract Angular semantics into `docs/raceday-contract.md`
  - Design clean contract for React app (no legacy shapes)
  - Preserve offline contract: full paginated load + delta merge by `rider.id`
- [ ] Design public read endpoints (no auth required), club-scoped by default:
  - `GET /clubs/`, `GET /clubs/<slug>/`
  - `GET /races/`, `GET /races/<id>/`, `GET /races/<id>/results/`
  - `GET /riders/` (limited fields), `GET /riders/<id>/` (public profile)
  - `GET /pointscores/`, `GET /pointscores/<id>/`
  - `GET /pages/`, `GET /pages/<club>/<slug>/`
  - `GET /posts/`, `GET /posts/<slug>/`
- [ ] Design member portal endpoints (auth required):
  - `GET /me/` — current user profile
  - `GET /me/results/` — own results
  - `PATCH /me/` — update profile
- [ ] One consistent public identifier per concept (`Rider.id` everywhere)
- [x] Explicit read/write serializer shapes for all resources currently exposed
  in v1; no `fields='__all__'` in the new contract serializers
- [x] `django-filter` FilterSets for the initial v1 contract: `?status=`,
  `?date_after=`, `?club=`, `?search=`, `?ordering=` and the associated list
  filters are implemented for the v1 resources shipped in
  `races/apps/cabici/api/`
- [x] Domain operations as explicit actions in the initial v1 contract:
  - `POST /api/v1/pointscores/{id}/recalculate/`
  - the action pattern is in place for later bulk/allocation endpoints
- [x] **OpenAPI schema is live for the v1 contract** — served under
  `/api/v1/schema/` and `/api/v1/docs/` in the project repo
- [ ] Generate TypeScript client into `frontend/packages/api-client`
- [x] Initial contract test coverage is in place for the v1 schema and
  endpoints/actions, including racecourses, race results and user roles
  (`races/apps/cabici/tests/test_api_contract.py`); full generated-client parity
  remains a frontend monorepo follow-up

### 2.3 Authentication & Authorization

- [x] Install `djangorestframework-simplejwt`; access + refresh endpoints
  (`/api/v1/auth/token/`, `/api/v1/auth/token/refresh/`) and initial
  authenticated profile endpoint (`/api/v1/auth/me/`)
- [ ] Register / password reset (request + confirm) / profile endpoints
- [ ] allauth → JWT for social auth; session auth for `/admin/` only
- [ ] **CORS configuration:** keep `django-cors-headers`, allow all club Astro origins
  - `CORS_ALLOWED_ORIGINS` managed as an allow-list of club domains
  - Public read endpoints may be open; member portal endpoints require origin matching
- [ ] **Management apps (same-origin):**
  - Access token in memory
  - Refresh token in `httpOnly` `SameSite=Strict` cookie
  - CSRF protection on cookie-authenticated writes
- [ ] **Astro site (cross-origin):**
  - Public endpoints: no auth
  - Member endpoints: JWT `Authorization: Bearer <access>`
  - Refresh flow via Astro API routes (Astro sets `httpOnly` cookie for refresh)
- [ ] Permission classes applied uniformly:
  - Reads: open for public resources, or authenticated for member resources
  - Writes: club official of owning object
- [ ] Fix carried-over defects:
  - Unknown email → 401 (not 500)
  - User without a Rider must not 500 on `user.rider.club` (partially done:
    `/api/v1/auth/me/` now returns nullable rider fields instead of 500)
- [ ] allauth links resolve into `apps/manage` SPA routes (password reset, email confirmation)

### 2.4 Core CRUD Implementation

Code structure:
```
races/apps/cabici/
  models.py
  services/
    __init__.py
    results.py, pointscore.py, officials.py, exports.py
  api/
    __init__.py
    routers.py
    pagination.py
    permissions.py
    filters/           # club.py, race.py, rider.py, results.py, content.py
    serializers/       # one per resource, explicit fields, read/write split
    views/             # club.py, race.py, rider.py, membership.py, results.py,
                       # pointscore.py, auth.py, content.py
```

- [ ] ViewSets + DefaultRouter under `/api/v1/`
- [ ] Explicit serializer fields; write shapes separated from read shapes
- [ ] `select_related` / `prefetch_related` on every queryset
- [ ] Club scoping: public list endpoints default to the requesting club (via `?club=` or domain-based routing)
- [ ] Pagination on every list endpoint (200 default, 1000 max)
- [ ] `transaction.atomic()` around every multi-row write
- [ ] Schema annotations (`drf-spectacular`) on each viewset/action

### 2.5 Content Management API (New)

- [ ] `ContentPage` model:
  - `club` (FK, nullable for global pages)
  - `slug`, `title`, `content` (Markdown)
  - `status` (`draft` / `published`)
  - `created_at`, `updated_at`, `published_at`
  - `unique_together = [("club", "slug")]`
- [ ] `Post` model:
  - Same fields as ContentPage plus `excerpt`, `featured_image`, `author`
- [ ] Endpoints:
  - `GET /api/v1/pages/` — list published (public)
  - `GET /api/v1/pages/<club>/<slug>/` — get page (public)
  - `GET /api/v1/posts/` — list published with pagination (public)
  - `GET /api/v1/posts/<slug>/` — get post (public)
  - Write endpoints: club officials only
- [ ] Management app gets a Markdown editor for pages/posts
- [ ] Astro renders Markdown (server-side or at build time)

### 2.6 Race-Day Contract Implementation

- [ ] Upload endpoint: `POST /api/v1/races/<id>/results/upload/`
  - Atomic, row-locked, permissioned (club official)
  - Accepts both Angular legacy shape and new clean shape
  - Returns `ridermap`, `errors[]`, `deleted`, `created`
- [ ] Download endpoint: `GET /api/v1/races/<id>/entries/`
  - Returns entries with `riderid` (not display string)
  - Includes `grade_change` as `grade != usual_grade`
- [ ] Delta sync endpoint: `GET /api/v1/riders/?updated_after=<iso8601>`
  - Preserves pagination, stable IDs, does not silently drop deleted riders
- [ ] Preserve Angular compatibility until cutover
- [ ] Explicit overwrite contract (confirmation flag or `If-Match`)

### 2.7 API Documentation

- [ ] `drf-spectacular` generating OpenAPI 3.x
- [ ] Interactive docs at `/api/docs/`, schema at `/api/schema/`
- [ ] Regenerate TypeScript client from final spec
- [ ] Usage guide: auth flow, filtering, pagination, error envelope, upload, exports

### 2.8 Test Suite Rebuild & Retirement of `api.py`

- [ ] Per-resource endpoint tests (CRUD, filters, pagination, permissions, errors)
- [ ] Service-layer tests (upload, bulk create, allocation, recalculation)
- [ ] Contract test: generated TS types match served schema
- [ ] Content API tests (public read, official write, drafts hidden)
- [ ] Auth tests (login, refresh, logout, failure paths, CORS preflight)
- [ ] Achieve >80% coverage; ratchet `fail_under` (42 → 60 → 80)
- [ ] **Delete `api.py`** and its hand-wired URL pairs in one commit

---

## ✅ Phase 3: Frontend Monorepo Setup

### 3.1 Workspace & Tooling

- [ ] Root `package.json` with pnpm workspaces (`frontend/apps/*`, `frontend/packages/*`)
- [ ] Node pinned (`.nvmrc` / `packageManager` field)
- [ ] Shared TypeScript, ESLint, Prettier configs at `frontend/` level
- [ ] Frontend CI workflow:
  - `pnpm install --frozen-lockfile`
  - `lint`, `tsc --noEmit`, `vitest run`, `build`
  - Path filters so Python CI skips on `frontend/**` changes and vice versa
- [ ] Update `.devcontainer` for monorepo (Node + Python)

### 3.2 Package: `api-client`

- [ ] Generate from Django OpenAPI schema (using `openapi-typescript` or `orval`)
- [ ] Versioned alongside API — CI contract test ensures sync
- [ ] Consumed by all three apps

### 3.3 Package: `ui` (deferred)

- [ ] Create when a second consumer needs shared components
- [ ] MUI theme + common components (buttons, forms, tables, layouts)

### 3.4 App Scaffolds

- [ ] `frontend/apps/manage/` — Vite + React 18 + TS + MUI scaffold
- [ ] `frontend/apps/web/` — Astro + React + TS scaffold
- [ ] `frontend/apps/raceday/` — deferred to Phase 4 (vendoring)

---

## ✅ Phase 4: Management Frontend (React)

**Stack:** React 18 + Vite + TypeScript + MUI + TanStack Query + React Hook Form + React Router 6 + Vitest. Matches the race-day app so `packages/ui` and `packages/api-client` are used identically.

### 4.1 `apps/manage` — Setup & Auth

- [ ] Configure API client with same-origin auth (memory access + cookie refresh)
- [ ] Login / logout / register forms
- [ ] Password reset flow (links into SPA routes)
- [ ] Protected routes
- [ ] User profile page
- [ ] Main layout (nav, footer, responsive)

### 4.2 Club Management

- [ ] Club list & detail views
- [ ] Club dashboard
- [ ] Club member management
- [ ] Club statistics

### 4.3 Race Management

- [ ] Race list with filters (date, club, status)
- [ ] Race detail view
- [ ] Race creation / edit forms
- [ ] Bulk race creation
- [ ] Race officials management
- [ ] Race status management

### 4.4 Rider Management

- [ ] Rider list with search
- [ ] Rider detail / profile
- [ ] Rider creation / editing
- [ ] Rider grade management
- [ ] Rider autocomplete (for race-day prep)

### 4.5 Results & Pointscores

- [ ] Result display
- [ ] Pointscore list & detail
- [ ] Pointscore audit view
- [ ] Pointscore recalculate action
- [ ] Export functionality (CSV)

### 4.6 Content Editor (New)

- [ ] List pages/posts
- [ ] Create/edit page form (Markdown editor)
- [ ] Draft / publish workflow
- [ ] Preview rendered Markdown

### 4.7 `apps/raceday` — Vendor & Integrate

- [ ] `git subtree add --prefix=frontend/apps/raceday stevecassidy/cabici-raceday-react main`
- [ ] Integrate `packages/api-client` (replace hand-written types/axios calls)
- [ ] Fix **D1**: app sends `newriders`, server reads `riders`
- [ ] Fix **D2**: download mapping uses `riderid` not display string
- [ ] Fix **D4**: surface server `errors[]` to the race director
- [ ] Subpath mounting: `/raceday/` (vite `base`, router `basename`, PWA scope)
- [ ] Regression tests through real HTTP boundary
- [ ] Offline contract preserved: full load + `localStorage` cache + delta merge

### 4.8 Testing & Quality

- [ ] Component tests (Vitest + React Testing Library)
- [ ] Integration tests for key user flows
- [ ] Accessibility audit (WCAG 2.1 AA)
- [ ] Mobile responsiveness

---

## ✅ Phase 5: Presentation Frontend (Astro)

**Stack:** Astro + React islands + TanStack Query + Tailwind CSS (or matching MUI)

### 5.1 Setup

- [ ] Astro project with React integration
- [ ] Tailwind CSS (or shared design tokens with MUI)
- [ ] TanStack Query for client-side data fetching
- [ ] API client configured for cross-origin calls
- [ ] Auth: login form → Astro API route → Django JWT → httpOnly refresh cookie

### 5.2 Public Site

- [ ] Home page (club news, upcoming races)
- [ ] Race calendar / list (filter by date, club)
- [ ] Race detail page (info, course, results)
- [ ] Results display (by race, by rider, by club)
- [ ] Club pages (info, statistics, officials)
- [ ] Pointscore standings
- [ ] Content pages (`/pages/<slug>/`)
- [ ] News/posts (`/news/`)

### 5.3 Member Portal

- [ ] Login page
- [ ] Personal results history
- [ ] Profile view/update
- [ ] Upcoming races (registered / available)

### 5.4 SEO & Performance

- [ ] SSG for stable pages (content pages, club info)
- [ ] SSR for dynamic data (race results, pointscores)
- [ ] Sitemap generation
- [ ] Structured data (Schema.org for events)
- [ ] Meta tags, Open Graph, Twitter cards

### 5.5 Testing

- [ ] Build verification (no broken links)
- [ ] Lighthouse CI (performance, accessibility, SEO)
- [ ] Cross-browser testing
- [ ] Mobile testing

---

## ✅ Phase 6: Integration & Deployment

### 6.1 Backend + Management Apps

- [ ] Multi-stage Dockerfile:
  - Node stage: `pnpm install --frozen-lockfile && pnpm -r build`
  - Copy both `dist` trees into Python image
- [ ] `.dockerignore` excludes `node_modules`
- [ ] Whitenoise serving both SPA builds:
  - `/` → `apps/manage`
  - `/raceday/` → `apps/raceday`
  - `/admin/` → Django admin
  - `/api/` → API
- [ ] `CompressedStaticFilesStorage` (not `CompressedManifestStaticFilesStorage` — avoids the Vite hash double-hash trap)
- [ ] SPA catch-all routes ordered after `/admin/` and `/api/`
- [ ] `STATICFILES_DIRS` includes both build outputs
- [ ] Review `ALLOWED_HOSTS`, `SECURE_*`, `CSRF_TRUSTED_ORIGINS`
- [ ] CI smoke test: `collectstatic` against real build, verify all `src`/`href` resolve

### 6.2 Astro Site (Separate Deploy)

- [ ] Deploy pipeline: one build, deployed N times with different `PUBLIC_CLUB_SLUG`
- [ ] Environment variables per instance: `PUBLIC_API_URL`, `PUBLIC_CLUB_SLUG`
- [ ] Custom domain per club (e.g. `wmcc.cabici.net`)
- [ ] Build-time API calls for SSG content (club-scoped)

### 6.3 Production Cutover

- [ ] Final database backup
- [ ] Run `checkconstraints` against production copy, resolve duplicates
- [ ] Run migrations
- [ ] Deploy Django + management apps (one image)
- [ ] Astro site already live (deployed independently)
- [ ] Smoke test all critical paths:
  - Public race listings
  - Race-day upload/download
  - Management app CRUD
  - Member portal login
- [ ] Monitor (Sentry)
- [ ] **Angular retirement:** run one race on React race-day app, then delete legacy API + DRF token auth

### 6.4 Django Template Cleanup (post-cutover)

- [ ] Remove all Django templates
- [ ] Remove `TEMPLATES` config (except bare minimum for admin/allauth)
- [ ] Remove jQuery/Bootstrap static assets
- [ ] Remove template URL patterns
- [ ] Remove `HomePage`, `flatpages` middleware (replaced by ContentPage API or Astro)
- [ ] Update `INSTALLED_APPS`

### 6.5 Documentation

- [ ] API documentation (interactive + guide)
- [ ] Component documentation (Storybook or similar, optional)
- [ ] Deployment guide
- [ ] Developer onboarding
- [ ] User guide
- [ ] Content editor guide (for club officials)

---

## ✅ Phase 7: Optimization (Ongoing)

- [ ] Database query optimization (N+1 elimination, indexes)
- [ ] Redis caching for API responses
- [ ] Astro build optimization (image optimization, prefetching)
- [ ] Bundle analysis for React apps
- [ ] Performance monitoring (Sentry, Lighthouse CI)
- [ ] Security audit
- [ ] Accessibility remediation
