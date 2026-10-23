# Re-planned Architecture: Management + Presentation Split

**Date:** 2026-10-23
**Status:** Proposal — replaces the single-SPA frontend design in `MODERNIZATION_PLAN.md` §3 onwards

## Executive Summary

The previous plan built one React SPA (`apps/web`) to replace the entire Django template layer, with a separate React PWA (`apps/raceday`) for race-day operations. This document revises that to a **two-frontend architecture**:

1. **Management Frontend** (`apps/manage` + `apps/raceday`): React-based transactional system for club officials. Handles race CRUD, results, pointscores, official allocation, race-day entry, and content editing for the public site.

2. **Presentation Frontend** (`apps/web`): Astro-based public site for race data presentation, club content, and a lightweight member portal. Replaces both the Django template views and the club's WordPress site.

The API is built out completely before any frontend work begins. The monorepo structure is retained.

## Why This Change

| Concern | Old Plan | New Plan |
|---|---|---|
| Separation of concerns | One SPA does everything (admin + public) | React for transactional work, Astro for content presentation |
| SEO & performance | React SPA is poor for public content | Astro ships minimal JS, excellent for public pages |
| WordPress replacement | None — still need WordPress plugin | Astro site subsumes the club website entirely |
| Content editing | Not addressed | Built into the management app, served via API |
| Member experience | No member portal | Lightweight portal in Astro (own results, profile) |
| Reliability | Race-day merged into general SPA eventually | Race-day stays isolated as offline-first PWA |

## Key Decisions

### 1. Two Conceptual Frontends, Three Build Targets

The management workload splits into two build outputs for reliability:

| App | Stack | Role | Deploy |
|---|---|---|---|
| `apps/manage` | React 18 + Vite + MUI + TanStack Query | Full transactional management for officials | Same-origin with Django |
| `apps/raceday` | React 18 + Vite + MUI (vendored) | Offline-first race-day entry & results | Same-origin with Django, mounted on `/raceday/` |
| `apps/web` | Astro + React islands + TanStack Query | Public site, SEO content, member portal | **Separate per club** (Vercel/Netlify/Cloudflare Pages) |

`apps/manage` and `apps/raceday` are single deployments serving all clubs (each user sees their own club's data via auth). `apps/web` is deployed **once per club** on the club's own domain, configured with a `PUBLIC_CLUB_SLUG` (or fetched from the API by domain). Each instance is an identical Astro build talking to the same Django API. The API serves club-scoped content and race data based on the requesting club.

**Why keep `apps/raceday` separate from `apps/manage`:** Race day is high-stakes, offline-first, and used by volunteers on tablets with poor connectivity. Merging it into the management SPA would couple its reliability to routine feature work. It stays a separate deployable with its own service worker and caching strategy.

### 2. Astro for Presentation

**Chosen:** Astro with React islands.

**Why Astro over Next.js/Remix:**
- **Zero-JS by default** — public race result pages ship mostly HTML, not a React runtime
- **Content-first** — built-in Markdown/MDX support, collections API, perfect for club news and static pages
- **Islands architecture** — interactive parts (member login, result filters, calendar) hydrate as React islands; the rest stays static
- **SSG + SSR hybrid** — build-time generation for stable content, server rendering for dynamic race data
- **Fits the team** — one less heavy framework to learn; the interactive parts are still React
- **Multi-deploy friendly** — Astro builds to static HTML + edge functions; one build can be deployed N times with different config

**Why not Next.js:** Next.js is excellent but ships significantly more JavaScript for pages that are mostly static race listings and results. Astro's output is leaner and faster for the public presentation use case.

### Multi-Club Deployment

Each club runs its **own Astro instance** on a custom domain (e.g., `wmcc.cabici.net`). All instances share the same codebase and are built from the same monorepo, differentiated only by environment configuration:

| Instance | Domain | Config |
|---|---|---|
| WMCC | `wmcc.cabici.net` | `PUBLIC_CLUB_SLUG=wmcc` |
| Penrith CC | `penrith.cabici.net` | `PUBLIC_CLUB_SLUG=penrith` |
| LACC | `lacc.cabici.net` | `PUBLIC_CLUB_SLUG=lacc` |

- `apps/web` is built once and deployed multiple times with different env vars
- The API serves club-scoped content: pages, posts, races, results, riders, pointscores
- Public endpoints implicitly filter by the requesting club (or accept an explicit `?club=` override for federation/comparison pages)
- CORS allows all club origins (a known, managed allow-list) or is open for the public read endpoints

This model replaces the WordPress plugin entirely — clubs get a full website with race data, not just an embedded widget.

### 3. API-First Sequence

**The API is completed before any frontend development.** This was always the intent in the old plan, but vendoring the race-day app had become the next concrete step. The revised next step is:

1. **Design the complete API contract** (all resources, including new content/page endpoints)
2. **Generate the TypeScript client** from the OpenAPI spec
3. **Build the API** (CRUD, auth, permissions, content management)
4. **Then** vendoring and frontend work

This prevents the D1/D2 class of bugs (client and server mocking each other with mismatched assumptions) because the client is generated from the served schema.

### 4. Monorepo Confirmed

All three apps live in this repository under `frontend/`. There is no benefit to separate repos — the generated `packages/api-client` must stay in sync with the API, and that is only verifiable in a single repo.

```
frontend/
  package.json                  # pnpm workspaces
  pnpm-workspace.yaml
  packages/
    api-client/                 # GENERATED from Django OpenAPI spec
                                # The only sanctioned way any app talks to the API
    ui/                         # Shared MUI theme + components
                                # Populated when a second consumer needs it
  apps/
    manage/                     # React SPA: club official management
    raceday/                    # React PWA: race-day operations (vendored when ready)
    web/                        # Astro: public presentation + member portal
```

### 5. Auth Strategy (Revised for Cross-Origin)

The old plan deleted CORS entirely because everything was same-origin. Astro deployed separately requires a hybrid approach:

#### Management Apps (`apps/manage`, `apps/raceday`) — Same-Origin
- JWT access token in memory
- Refresh token in `httpOnly` `SameSite=Strict` cookie
- No CORS needed
- Session auth for `/admin/` only

#### Astro Site (`apps/web`) — Cross-Origin, Multi-Instance
- Django API allows CORS from all club Astro origins (managed allow-list in `CORS_ALLOWED_ORIGINS`)
- **Public endpoints** (races, results, clubs, pages, posts): no authentication required, implicitly scoped to the club
- **Member portal endpoints** (own results, profile): JWT required
- **Refresh flow via Astro API routes:**
  - Browser → Astro `/api/auth/login` → Django `/api/v1/auth/login/` → JWT tokens
  - Astro sets refresh token in `httpOnly` cookie on Astro domain
  - Access token returned to client (in-memory, short-lived, e.g. 15 min)
  - Client calls Django API directly with `Authorization: Bearer <access>`
  - On expiry: Browser → Astro `/api/auth/refresh` (cookie sent automatically) → Django `/api/v1/auth/refresh/` → new access token

This keeps the refresh token in an `httpOnly` cookie (XSS-protected) while allowing the Astro client to call Django directly for API data. The access token is short-lived and in memory, which is an acceptable trade-off for a low-risk member portal.

**Why not pure cookie auth cross-origin:** Cross-origin `httpOnly` cookies require `SameSite=None; Secure` and complex CSRF handling. Proxying refresh through Astro API routes is simpler and avoids exposing Django session cookies to a third-party host.

### 6. Content Management via API (New)

The Astro site's pages and posts are stored in Django and served via the API. Club officials create and edit them through the React management app.

**New models:**
```python
class ContentPage(models.Model):
    club = models.ForeignKey(Club, null=True, blank=True, on_delete=models.CASCADE)
    slug = models.SlugField()
    title = models.CharField(max_length=200)
    content = models.TextField(help_text="Markdown")
    status = models.CharField(choices=[("draft", "Draft"), ("published", "Published")])
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    published_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = [("club", "slug")]

class Post(models.Model):
    # Similar to ContentPage plus:
    excerpt = models.TextField(blank=True)
    featured_image = models.URLField(blank=True)
    author = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
```

**API endpoints:**
- `GET /api/v1/pages/` — list published pages (public, no auth)
- `GET /api/v1/pages/<club>/<slug>/` — get page (public)
- `GET /api/v1/posts/` — list posts with pagination/filtering (public)
- `GET /api/v1/posts/<slug>/` — get post (public)
- `POST/PATCH/DELETE /api/v1/pages/...` — club officials only
- `POST/PATCH/DELETE /api/v1/posts/...` — club officials only

Astro renders Markdown at build time or server-render time. The management app provides a Markdown editor (e.g. MDEditor or similar).

### 7. Public API Design

Race data that was previously behind Django template auth is now openly readable via the API:

- `GET /api/v1/clubs/` — list clubs
- `GET /api/v1/clubs/<slug>/` — club detail, statistics
- `GET /api/v1/races/` — list races (filter by date, club, status)
- `GET /api/v1/races/<id>/` — race detail
- `GET /api/v1/races/<id>/results/` — race results
- `GET /api/v1/riders/` — list riders (limited public fields)
- `GET /api/v1/riders/<id>/` — rider public profile
- `GET /api/v1/pointscores/` — list pointscores
- `GET /api/v1/pointscores/<id>/` — pointscore detail & tallies

For multi-club read endpoints (e.g. a rider who races at multiple clubs), the API returns the requesting club's data by default, with optional `?club=` or federation views for cross-club queries.

Write operations require club official status. The permission model simplifies to: **"Is this user an official of the club that owns this object?"**

## Revised Phase Sequence

### Phase 2: Complete Backend API (Weeks 5–14, revised)

Finish what was started, expanded to include content endpoints and revised auth:

1. **2.1 Finish Model Hardening** — complete remaining items (C3 permissions, C5/C6 sentinels, C8 delta tracking, C11/C12 N+1 fixes, constraint verification against production copy)
2. **2.2 API Contract & OpenAPI** — design all resources including content pages/posts, public read semantics, member portal endpoints, race-day contract (from Angular docs + React specs). Publish OpenAPI spec. Generate TypeScript client.
3. **2.3 Auth & Authorization** — SimpleJWT endpoints, allauth integration, permission classes, CORS configuration for Astro origin, login/logout/refresh/profile flows tested
4. **2.4 Core CRUD Implementation** — ViewSets, routers, explicit serializers, filters, pagination, select_related/prefetch_related on every queryset
5. **2.5 Content Management API** — Page/Post models, CRUD endpoints, public read endpoints
6. **2.6 Race-Day Contract** — Upload/download endpoints designed and implemented (Angular compatibility preserved until cutover)
7. **2.7 API Documentation** — drf-spectacular, interactive docs, usage guide
8. **2.8 Test Suite & api.py Retirement** — >80% coverage, contract tests, delete `api.py`

### Phase 3: Frontend Monorepo Setup (Week 15)

- pnpm workspaces, shared configs, CI with path filters
- Generate `packages/api-client` from final OpenAPI spec
- Scaffold `apps/manage` and `apps/web`

### Phase 4: Management Frontend (Weeks 16–26)

- `apps/manage`: Auth, club management, races, riders, results, pointscores, content editor
- `apps/raceday`: Vendor from `cabici-raceday-react`, fix D1/D2/D4, integrate generated client, subpath mount on `/raceday/`
- Both apps consume `packages/api-client` exclusively

### Phase 5: Presentation Frontend (Weeks 27–34)

- `apps/web` (Astro): Public pages, race listings, results, club info
- Content pages and posts sourced from API
- Member portal: login, personal results, profile
- SEO, accessibility, performance optimization

### Phase 6: Integration & Deployment (Weeks 35–38)

- Multi-stage Dockerfile for Django + management builds
- Astro separate deploy pipeline
- CORS configuration for Astro origin
- SPA catch-all routing for management apps
- Production cutover (single deploy for backend + management; Astro already live)

## What This Obsoletes from the Old Plan

- **Single React SPA (`apps/web`) for everything** — split into `apps/manage` (React) and `apps/web` (Astro)
- **CORS deletion** — CORS is kept, scoped to the Astro production origin only
- **Phase 3 as "React Frontend"** — renamed and split into Phase 4 (React management) and Phase 5 (Astro presentation)
- **Vendoring as immediate next step** — deferred to Phase 4; API contract design happens first from documented specs
- **Flatpage disposition question** — answered: replaced by the ContentPage/Post API

## Open Questions

1. **Astro member portal scope:** Should riders be able to enter races online via Astro, or is that still manage-app-only? (Recommendation: keep race entry in the management/race-day apps for simplicity; portal is view-only for results and profile.)

2. **Race-day integration:** Should `apps/raceday` eventually be absorbed into `apps/manage` as a "Race Day" module, or kept forever separate? (Recommendation: keep separate for reliability, but share all packages. Revisit after two race seasons.)

3. **Content editor:** Simple Markdown editor in the management app, or integrate a rich text editor (e.g. TipTap, Plate)? (Recommendation: start with Markdown — club officials are technical enough, and it's portable.)

4. **Astro deployment target:** Vercel, Netlify, Cloudflare Pages, or self-hosted? (Recommendation: Cloudflare Pages or Netlify — generous free tiers, excellent Astro support, custom domain easy.)
