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

```
master (production)
  └── modernization (all development work)
       ├── feature/django-upgrade
       ├── feature/api-endpoints
       ├── feature/react-frontend
       └── ... (other feature branches as needed)
```

**Key Points:**
- All modernization work happens on the `modernization` branch or feature branches off it
- `master` branch remains untouched and production-ready throughout development
- No need to maintain backward compatibility during development
- Can make breaking changes freely on development branch
- Single merge to master when complete and tested

### Development Environment

Developers work on the `modernization` branch with:
- Local Django development server
- Local React development server (Vite)
- SQLite or local PostgreSQL for development
- Can freely experiment and refactor

### Testing Strategy

**During Development:**
- Unit tests run on each commit (CI)
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
1. Complete all phases on development branch
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
API built on the existing models.

**Decision (2026-10-11): the existing `api.py` is scrapped, not adapted.**
It was assembled ad-hoc to support specific jQuery front-end capabilities and is
idiosyncratic in ways that a typed React client cannot absorb: per-view query
vocabularies instead of filters (`?select=future`, `?count=N`, `?prefix=`), three
different meanings for `rider`/`riderid` across serializers, `fields='__all__'`
writes, an unpermissioned and non-transactional result uploader, no schema, no
versioning, no refresh auth, and 5 of 13 models unexposed. Because its only
consumers — `cabici.js` (588 lines) and `riders.js` (81 lines) — are deleted in
Phase 4, adaptation would touch ~100% of the file while inheriting every
inconsistency, and there is no client to preserve compatibility for. Full
evidence and the cost comparison live in
[`MODEL_REVIEW.md`](MODEL_REVIEW.md); the domain knowledge worth keeping is
listed there under "What to salvage".

**Sequencing rationale:** model work comes first because the API surface is
determined by the domain model, and two of the model defects (pointscore
configuration, membership category values) change API responses if fixed later.

### 2.0 Model Hardening (Week 5)

Prerequisite for everything below. Referenced items (A#, B#, C#) are the
findings in [`MODEL_REVIEW.md`](MODEL_REVIEW.md).

**Tier A — defects (fix first):**
- [ ] A1: make `PointScore.score()` read its own `points` / `smallpoints` /
      `smallthreshold` / `participation` / `method` fields instead of hardcoded
      WMCC constants; wire up `get_points()` / `get_smallpoints()`; add a test
      with a non-default configuration *(owner decision pending)*
- [ ] A2: correct the inverted `MEMBERSHIP_CATEGORY_CHOICES` tuple and add a
      data migration normalising any capitalised values
- [ ] A3: remove or repair `Race.get_absolute_url()` / `Rider.get_absolute_url()`
      (they reverse URL names that no longer exist → admin "View on site" 500);
      route the new URLs or delete the methods
- [ ] A4: delete `RaceResult.pointscores()` (references a non-existent
      `resultpoints_set`)
- [ ] A5: parenthesise `except ValueError, Rider.DoesNotExist:` in
      `load_excel_results`

**Tier B — database integrity (one additive migration):**
- [ ] `UniqueConstraint` on `Club.slug`, `ClubRole.name`,
      `Membership(rider, club, category, date)`, `ClubGrade(rider, club)`,
      `UserRole(user, club, role)`, `PointscoreTally(pointscore, rider)`,
      `Race.hash`
- [ ] Replace the `ClubGrade.save()` Python-level uniqueness override with the
      constraint
- [ ] Bib-number uniqueness that actually fires: `UniqueConstraint` with
      `condition=Q(number__isnull=False)`; then delete the three
      "increment to avoid clash" workarounds
- [ ] `Index` on `Race(date, status)` and `PointScore`/`PointscoreTally` ordering
      columns
- [ ] Confirm no duplicate data before applying (fixtures verified clean)

**Tier C — structure (shapes the API):**
- [ ] C1: merge `usermodel.py` into `models.py` (or a `models/` package),
      removing the six function-level circular imports
- [ ] C2: extract `services.py` — `ingest`, `results` (Excel/JSON upload),
      `pointscore`, `officials`, `membership_validation`, `exports` — as pure
      functions with `transaction.atomic()` at the operation boundary and typed
      result/error objects. No HTTP, no filesystem, no model-save side effects
      hidden inside model methods
- [ ] C3: settle one authorization model — club capability flags +
      `UserRole`/`ClubRole` — and express it in reusable permission classes;
      demote `Rider.official` to a cached convenience
- [ ] C5/C6: resolve the free-text pseudo-structures (`Race.grading`,
      comma-string points, `Rider.commissaire`) and the `place` 0-vs-NULL and
      `dob` 1970-01-01 sentinels
- [ ] C7: fix `Rider.current_membership` to filter by category and validity
      window; make `Rider.classification` an explicit mapping
- [ ] C8: make `Rider.updated` delta tracking explicit (touch on related writes)
- [ ] C9: ensure `Club.auscycling_client_secret` is never serializable
- [ ] C4: decide `RacePrototype` / `Race.grading` — delete or use
- [ ] C11/C12: kill the N+1 paths (`get_officials_with_counts`,
      `PointScore.tabulate` serialization, `tally_helpers`) and normalise
      `Club.statistics()` to counts + nested resources

**Success Criteria:**
- All 49 existing tests pass (adjusted for A1/A2 semantics) plus new tests for
  each Tier A fix
- `makemigrations --check` clean; constraints verified against a copy of
  production data
- No model method performs network or filesystem I/O

### 2.1 Resource Model & API Contract (Week 6)

Replaces the old "map current views to endpoints" task — the old views are
going away, so the resources are derived from the domain instead.

- [ ] Enumerate resources from the (merged) models: clubs, races, racecourses,
      riders, memberships, club roles, user roles, club grades, race staff,
      race results, pointscores, pointscore tallies, users/auth
- [ ] One public identifier per concept, applied consistently (rider = `Rider.id`
      everywhere; no `riderid` meaning `User.id` in one endpoint and a display
      string in another)
- [ ] Define representation contracts (read shape, write shape, sparse field
      set where needed) — never `fields='__all__'`
- [ ] Define the filter surface as `django-filter` `FilterSet`s (replacing
      `?select=`/`?count=`/`?prefix=`/`?changed=` with composable, documented
      query params: `?status=`, `?date_after=`, `?club=`, `?search=`,
      `?ordering=`, `?updated_after=`)
- [ ] Define domain operations as explicit actions, not serializer hacks:
      `POST /races/{id}/results/`, `POST /races/bulk/`,
      `POST /pointscores/{id}/recalculate/`, `POST /clubs/{slug}/officials/allocate/`,
      `POST /memberships/validate/`, `GET /races/{id}/results.woff`-style exports
- [ ] Publish the OpenAPI spec **before** implementing, and generate the
      TypeScript client from it (`openapi-typescript` / `orval`) so Django and
      React cannot drift
- [ ] Salvage the existing result-upload payload contract
      (`{race, riders[], entries[]}` with temporary `"ID…"` rider keys and a
      `ridermap` response) — it is shared with the race-sheet/desktop workflow
- [ ] Mine `tests/testapi.py` (790 lines) for behavioural requirements before it
      is replaced

**Success Criteria:**
- Written contract covering 100% of the operations the React screens in Phase 3
  need
- OpenAPI spec committed and served; generated TS client compiles against it

### 2.2 Authentication (Week 7)

- [ ] `djangorestframework-simplejwt` with access + refresh endpoints
- [ ] Register, password reset (request + confirm), profile read/patch
- [ ] Logout / token blacklist or short-lived access + rotating refresh
- [ ] allauth → JWT for the social/session path; keep session auth for `/admin/`
      only
- [ ] Fix the token-auth defects carried over: unknown email must return 401 (not
      500), and a user without a `Rider` must not 500 on `user.rider.club`
- [ ] CORS scoped to the frontend origin (replace `CORS_ALLOW_ALL_ORIGINS` +
      GET-only `CORS_URLS_REGEX` with credential-aware config)

**Recommended packages:** `djangorestframework-simplejwt`, optionally
`dj-rest-auth`.

**Success Criteria:** every auth endpoint tested, including the failure paths
that currently 500.

### 2.3 Core CRUD Implementation (Weeks 8-10)

**Code structure:**
```
races/apps/cabici/
  models.py                  # merged domain models (2.0)
  services/                  # domain operations (2.0)
    __init__.py
    ingest.py
    results.py
    pointscore.py
    officials.py
    membership.py
  api/
    __init__.py
    routers.py               # DefaultRouter wiring for /api/v1/
    pagination.py
    permissions.py           # capability + role driven (C3)
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
      results.py
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
- [ ] Permission classes from 2.0/C3 applied uniformly — including the result
      uploader, which currently has none
- [ ] `transaction.atomic()` around every multi-row write
- [ ] Schema annotations (`drf-spectacular`) on each viewset/action as it lands
- [ ] Delete `api.py` once coverage is complete (single commit, no shim)

**Success Criteria:**
- All CRUD operations available via API with tests for permissions, filtering,
  pagination and error shapes
- No endpoint reachable by an unauthenticated write; no 500s on expected client
  errors (400/401/403/404/409 instead)
- >80% coverage on `api/` and `services/`

### 2.4 API Documentation (Week 11)

- [ ] `drf-spectacular` generating OpenAPI 3.x from annotations
- [ ] Interactive docs at `/api/docs/`, schema at `/api/schema/`
- [ ] Postman/Insomnia collection generated from the schema
- [ ] Usage guide covering auth flow, filtering, pagination, error envelope,
      result upload and the export endpoints
- [ ] Regenerate the TypeScript client from the final spec

**Success Criteria:** interactive docs; every endpoint documented with examples.

### 2.5 Test Suite Rebuild (Week 12)

- [ ] Per-resource endpoint tests (CRUD, filters, pagination, permissions)
- [ ] Service-layer tests for result upload, bulk race creation, official
      allocation, pointscore recalculation, membership validation
- [ ] Contract test: generated TS client types match the served schema
- [ ] Achieve >80% coverage; raise `fail_under` in `pyproject.toml` in step
      (42 → 60 → 80) so the gate ratchets rather than leaping

**Success Criteria:** all tests passing, >80% coverage enforced in CI.

---

## Phase 3: React Frontend Development

**Goal:** Build modern React frontend consuming the API

### 3.1 Frontend Architecture Decision (Week 13)

**Recommended Approach: Separate Frontend Repository**

**Pros:**
- Clean separation of concerns
- Independent deployment
- Different tech stacks can evolve independently
- Easier to have separate frontend developers
- Can use create-react-app or Vite

**Cons:**
- Two repositories to manage
- CORS configuration required
- Separate deployment pipeline

**Alternative Approach: Django + React Integration**

Options:
1. **django-webpack-loader**: Bundle React with Django
2. **Serve React build as Django static files**: Build React separately, serve via Django
3. **Django as API backend only**: Separate React app, Nginx routes

**Recommended:** Separate repository approach for maximum flexibility

### 3.2 Frontend Setup (Week 13-14)

**Technology Stack:**
- React 18+
- TypeScript (strongly recommended)
- Vite (build tool)
- React Router 6 (routing)
- TanStack Query (React Query) - API state management
- Zustand or Context API - UI state management
- Axios - HTTP client
- React Hook Form - form handling
- Zod - validation
- Tailwind CSS or Material UI - styling
- Vitest + Testing Library - testing

**Initial Setup:**
```bash
npm create vite@latest cabici-frontend -- --template react-ts
cd cabici-frontend
npm install @tanstack/react-query axios react-router-dom
npm install -D tailwindcss postcss autoprefixer
```

**Project Structure:**
```
cabici-frontend/
  src/
    api/           # API client and endpoints
    components/    # Reusable components
    features/      # Feature-based modules
      clubs/
      races/
      riders/
      auth/
    hooks/         # Custom hooks
    lib/           # Utilities
    pages/         # Page components
    routes/        # Route configuration
    types/         # TypeScript types
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

**Deployment Architecture Options:**

**Option 1: Separate Frontend Hosting**
```
Frontend: Vercel/Netlify/Cloudflare Pages
Backend: Current Django setup (Docker/Digital Ocean)
```

**Option 2: Unified Nginx Routing**
```
Nginx
  ├── /api/* → Django backend
  ├── /admin/* → Django admin
  └── /* → React SPA (served as static files)
```

**Option 3: Django Serves React Build**
```
Django collectstatic includes React build
Whitenoise serves React SPA
API at /api/*
```

**Recommended:** Option 1 for best performance and deployment flexibility

**Preparation:**
- [ ] Final database backup before deployment
- [ ] Prepare rollback plan (previous Docker image)
- [ ] Set up frontend hosting (Vercel recommended)
- [ ] Configure production environment variables
- [ ] Set up monitoring (Sentry)
- [ ] Configure CDN if needed
- [ ] Verify SSL certificates

**Deployment Steps:**
- [ ] Deploy Django API to production (Docker)
- [ ] Run database migrations
- [ ] Deploy React frontend to hosting
- [ ] Update DNS/routing as needed
- [ ] Update CORS settings for production domain
- [ ] Smoke test all critical functionality
- [ ] Monitor logs and error rates

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
- Work on development branch; production remains stable
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

**Development Approach:** All work is done on a `modernization` or `development` branch. Production remains on `master` branch and stays stable throughout development. Once all phases are complete and tested, the new version is merged and deployed to production in a single cutover.
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
| Option | Pros | Cons |
|--------|------|------|
| Tailwind CSS | Utility-first, fast | Verbose HTML |
| Material UI | Complete component library | Large bundle |
| Chakra UI | Accessible, themeable | Smaller ecosystem |
| CSS Modules | Scoped CSS | Manual work |

**Recommendation:** Tailwind CSS for flexibility or Material UI for speed

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
