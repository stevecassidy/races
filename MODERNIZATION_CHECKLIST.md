# Django Modernization - Quick Reference Checklist

This is a condensed checklist version of the full modernization plan. Use this for quick tracking of progress.

**Development Approach:** All work is done on a development branch. Production remains stable until final deployment when complete.

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
- `usermodel.save_rider()` is a dead Strava social-auth callback.
- Lint debt is quarantined by `per-file-ignores` in `pyproject.toml` for
  `races/ingest/*` (bare excepts that are load-bearing for scraper fallbacks) and
  `races/apps/cabici/tests/*` (star imports, unused locals). Clear them as those
  modules are rewritten.
- `TIME_ZONE = 'Europe/Helsinki'` in base settings for a NSW racing app -
  unresolved, needs an owner decision (changing it shifts displayed times).

**Phase 2 planning outcome (2026-10-11):** a full review of the model and API
layers was carried out as part of closing Phase 1. It found five live model
defects, nine integrity gaps and twelve structural issues, and concluded that the
existing API should be rebuilt rather than adapted. See
[MODEL_REVIEW.md](MODEL_REVIEW.md); the task lists below reflect it.

## ✅ Phase 2: Backend API Rebuild (Weeks 5-12)

> **Decision (2026-10-11): `api.py` is scrapped, not adapted.** Evidence, the cost
> comparison, and the list of what to salvage are in
> [MODEL_REVIEW.md](MODEL_REVIEW.md). Model hardening (2.0) runs first because the
> API surface follows the domain model, and two model defects (A1 pointscore
> config, A2 inverted membership choices) change API responses if deferred.

### 2.0 Model Hardening (Week 5)

**Tier A — defects:**
- [ ] A1: `PointScore.score()` ignores its own points/participation/method config
      (hardcoded WMCC values) — wire up the config, test a non-default scale
      *(owner decision pending)*
- [ ] A2: `MEMBERSHIP_CATEGORY_CHOICES` is inverted (value/label swapped) + data
      migration to normalise capitalised values
- [ ] A3: `Race.get_absolute_url()` / `Rider.get_absolute_url()` reverse removed URL
      names → admin "View on site" 500s
- [ ] A4: delete `RaceResult.pointscores()` (references non-existent relation)
- [ ] A5: parenthesise the PEP-758 `except ValueError, Rider.DoesNotExist:` form

**Tier B — database integrity (one additive migration):**
- [ ] Unique constraints: `Club.slug`, `ClubRole.name`, `Membership(rider, club,
      category, date)`, `ClubGrade(rider, club)`, `UserRole(user, club, role)`,
      `PointscoreTally(pointscore, rider)`, `Race.hash`
- [ ] Replace the `ClubGrade.save()` Python uniqueness override with a constraint
- [ ] Conditional uniqueness for bib numbers, then delete the three
      "increment to avoid clash" workarounds
- [ ] Indexes on `Race(date, status)` and pointscore ordering columns
- [ ] Verify no duplicate data against a production copy before applying

**Tier C — structure:**
- [ ] C1: merge `usermodel.py` into `models.py` (removes 6 circular imports)
- [ ] C2: extract `services/` (ingest, results, pointscore, officials, membership
      validation, exports) with `transaction.atomic()` at operation boundaries
- [ ] C3: one authorization model (capability flags + roles) expressed as reusable
      permission classes
- [ ] C5/C6: resolve free-text pseudo-structures (`Race.grading`, comma-string
      points, `Rider.commissaire`) and the `place` 0-vs-NULL / `dob` 1970 sentinels
- [ ] C7/C8: fix `Rider.current_membership` category filtering; make delta
      timestamps explicit
- [ ] C9: guarantee `Club.auscycling_client_secret` is never serialized
- [ ] C4: decide `RacePrototype` / `Race.grading` — delete or use
- [ ] C11/C12: eliminate N+1 paths and normalise `Club.statistics()`

### 2.1 Resource Model & API Contract (Week 6)
- [ ] Derive resources from the domain (not from the old views)
- [ ] One consistent public identifier per concept (rider = `Rider.id` everywhere)
- [ ] Explicit read/write serializer shapes; never `fields='__all__'`
- [ ] `django-filter` FilterSets replacing `?select=` / `?count=` / `?prefix=` /
      `?changed=`
- [ ] Domain operations as explicit actions (`POST /races/{id}/results/`,
      `POST /races/bulk/`, `POST /pointscores/{id}/recalculate/`, …)
- [ ] Publish OpenAPI before implementing; generate the TypeScript client from it
- [ ] Salvage the existing result-upload payload contract (shared with the
      race-sheet/desktop workflow)
- [ ] Mine `tests/testapi.py` for behavioural requirements before replacing it

### 2.2 Authentication (Week 7)
- [ ] Install djangorestframework-simplejwt
- [ ] JWT access + refresh endpoints
- [ ] Register / password reset / profile endpoints
- [ ] allauth → JWT; session auth for `/admin/` only
- [ ] Fix carried-over defects: unknown email → 401 not 500; user without a Rider
      must not 500
- [ ] Scope CORS to the frontend origin (replace allow-all + GET-only)
- [ ] Test authentication flow including failure paths

### 2.3 Core CRUD Implementation (Weeks 8-10)
- [ ] ViewSets + routers under `/api/v1/` (no hand-wired URL pairs)
- [ ] Serializers with explicit fields; write shapes separated from read shapes
- [ ] `select_related` / `prefetch_related` on every queryset
- [ ] Pagination on every list endpoint
- [ ] Permission classes applied uniformly — including the result uploader, which
      currently has none
- [ ] `transaction.atomic()` around every multi-row write
- [ ] Custom actions for domain operations, backed by services
- [ ] Delete `api.py` once the new package covers the surface (single commit)

### 2.4 API Documentation (Week 11)
- [ ] Install drf-spectacular
- [ ] Add schema annotations to every view/action
- [ ] Generate OpenAPI schema + interactive docs at `/api/docs/`
- [ ] Create Postman collection from the schema
- [ ] Regenerate the TypeScript client from the final spec
- [ ] Write API usage guide

### 2.5 Test Suite Rebuild (Week 12)
- [ ] Per-resource endpoint tests (CRUD, filters, pagination, permissions, errors)
- [ ] Service-layer tests for upload / bulk create / allocation / recalculation
- [ ] Contract test: generated TS types match the served schema
- [ ] Achieve >80% coverage; ratchet `fail_under` in stages (42 → 60 → 80)

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
- [ ] Final database backup
- [ ] Set up frontend hosting (Vercel)
- [ ] Configure production environment variables
- [ ] Set up monitoring (Sentry)
- [ ] Deploy Django API to production
- [ ] Run migrations
- [ ] Deploy React frontend
- [ ] Update DNS/CORS settings
- [ ] Smoke test functionality
- [ ] Monitor for 24-48 hours

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
# Run tests
python bin/production.py test

# Run migrations
python bin/production.py migrate

# Create migrations
python bin/production.py makemigrations

# Run development server
python bin/develop.py runserver

# Format code
black .
ruff check --fix .

# Type check
mypy races/
```

### Frontend
```bash
# Install dependencies
npm install

# Development server
npm run dev

# Build for production
npm run build

# Run tests
npm test

# Type check
npm run type-check

# Lint
npm run lint
```

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
1. Continue on old branch
2. Review migration issues
3. Fix and retry on development branch

### If API development has issues:
1. Fix issues before frontend integration
2. No impact on production

### If React deployment fails:
1. Rollback to previous Docker image
2. Restore database backup if needed
3. Fix issues and redeploy

---

*Use this checklist alongside the full MODERNIZATION_PLAN.md document*
