# 🚀 Cabici Modernization Project

Welcome to the Cabici application modernization project! This directory contains all documentation for transforming the application from Django 4.2 + jQuery/Bootstrap 3 to Django 5.2 + React TypeScript.

## 📁 Documentation Overview

| Document | Purpose | Read When |
|----------|---------|-----------|
| **[QUICK_START.md](QUICK_START.md)** | Getting started guide | Starting the project |
| **[MODERNIZATION_SUMMARY.md](MODERNIZATION_SUMMARY.md)** | High-level overview | Understanding the approach |
| **[MODERNIZATION_CHECKLIST.md](MODERNIZATION_CHECKLIST.md)** | Task tracking | Daily development |
| **[MODERNIZATION_PLAN.md](MODERNIZATION_PLAN.md)** | Detailed implementation guide | Implementing each phase |
| **[MODEL_REVIEW.md](MODEL_REVIEW.md)** | Model & API review (Phase 2 input) | Before touching models or the API |
| **[TECHNICAL_ASSESSMENT.md](TECHNICAL_ASSESSMENT.md)** | Current state analysis | Understanding the codebase |

## 🎯 Project Goals

Transform the Cabici cycling application into a modern, maintainable system:

- ✅ Update Django 4.2 → 5.2
- ✅ Replace jQuery/Bootstrap 3 → React + TypeScript
- ✅ Complete REST API implementation
- ✅ Modern authentication (JWT)
- ✅ Comprehensive testing
- ✅ Improved performance and security

## 🏗️ Architecture Transformation

### Before (Current)
```
┌─────────────────────────────────────┐
│         Django 4.2                  │
│                                     │
│  ┌──────────────┐  ┌─────────────┐ │
│  │  Templates   │  │ Partial API │ │
│  │  (jQuery)    │  │    (DRF)    │ │
│  └──────────────┘  └─────────────┘ │
│                                     │
│  Bootstrap 3 + jQuery 3.3.1        │
└─────────────────────────────────────┘
```

### After (Target)
```
            one repo, two apps, one generated client
┌──────────────────────────────┐   ┌───────────────────────┐
│ frontend/apps/raceday        │   │ Django 5.2            │
│  (vendored, offline PWA)     │──►│  /api/v1/  (DRF)      │
├──────────────────────────────┤   │                       │
│ frontend/apps/web            │   │  OpenAPI schema ──────┼──► frontend/
│  (replaces the Django views) │──►│                       │    packages/api-client
├──────────────────────────────┤   │  JWT auth             │    (generated types)
│ React 18 + TS + Vite + MUI   │   │                       │
└──────────────────────────────┘   └───────────────────────┘
```

The stack is fixed by the app already in production: **React 18 + TypeScript +
Vite + MUI + react-hook-form + axios + Vitest** — which settles the plan's earlier
open questions (“Tailwind or MUI”, HTTP client, form library). The deployment
topology (serve both builds from Django via WhiteNoise on one origin, dropping
CORS entirely, versus separate static hosting) is an open decision recorded in
MODERNIZATION_PLAN §3.1.

## ⏱️ Timeline

**Total Duration:** 38 weeks (~9 months part-time)

- **Phase 1:** Foundation (4 weeks) ✅ complete
- **Phase 2:** Backend API rebuild (8 weeks)
- **Phase 3:** React Frontend (14 weeks)
- **Phase 4:** Integration & Deployment (4 weeks)
- **Phase 5:** Optimization (5 weeks)
- **Buffer:** 3 weeks

### Key Decision: the existing API is rebuilt, not adapted

Phase 2 does **not** extend `races/apps/cabici/api.py`. That API grew ad-hoc
around specific jQuery screens (per-view query params, inconsistent rider
identifiers, `fields='__all__'` writes, no schema or versioning) and its in-repo
clients are deleted in Phase 4. It is replaced by a contract-first `/api/v1/`
generated from an OpenAPI spec, with the model layer hardened first. Rationale
and evidence: [MODEL_REVIEW.md](MODEL_REVIEW.md).

**The race-day client is in-house, and the React version moves in.** The race-day
entry app is the only way to add riders today. The system doing that is the
**Angular 8 app** — deployed, old, reliable. It was rewritten in React 18 in its
own repo (`stevecassidy/cabici-raceday-react`), which is **unfinished and predates
the server-side modernization**; that React app is what gets **vendored into this
repository** (see “Key Decision: one repo, two apps”). So the contract is
co-designed rather than frozen externally — but **Angular remains the
compatibility target**, its wire format is the reference, and **DRF token auth
survives until Angular is deliberately retired after cutover**. The XLS rider
export retires unused: the React app fetches riders as JSON.

Reading both clients is what made this a Phase 2 task rather than a Phase 3 one:

- **D1/D2 are React-only, so not live and not urgent** — the app sends
  `newriders` where the server reads `riders` (rider creations vanish), and maps
  downloads by `entry.rider` where the API returns a display string (loading a
  race always yields an empty sheet). Angular gets both right.
- **A9 is the one live production bug:** the server compares `grade_change` to
  `"y"` while **both** clients send a boolean, so in-race grade changes have never
  applied in production.
- **D3's server half is real regardless of client:** no permission class, no
  transaction — any authenticated user can replace a race's results.
- **A8 is unblocked work everyone assumed was blocked:** the React app already
  ships a complete manual membership-verification flow sending
  `verifiedMemberDate`, and the server ignores it. With AusCycling polling
  withdrawn, production has no verification at all.

### Key Decision: one repo, two apps (monorepo), served same-origin

Both React apps live under a `frontend/` workspace root — `apps/raceday` (the
vendored entry app), `apps/web` (the SPA replacing the Django views) and
`packages/api-client` (generated from the server's OpenAPI schema). This supersedes
the earlier “separate frontend repository” recommendation, and the reason is D1/D2
themselves: two repos hand-maintaining one wire format, with every layer mocking
the layer beneath it, is exactly how a silent data-loss bug survived. A generated
shared client makes that class of bug uncompilable.

**Deployment is same-origin:** Django serves both builds via WhiteNoise, so
**CORS is deleted outright**, the refresh token can be an httpOnly cookie, and
there is one image and one cutover. `apps/raceday` must therefore mount on a
subpath (`/raceday/`) — it is not configured for that today. The split remains
available later because the apps are already separate build outputs.

### Key Decision: Angular is live, and it is the compatibility target

The deployed race-day system is the **Angular 8 app** — old, reliable, and
working. The React rewrite is **unfinished and predates the server-side
modernization**. So Angular keeps running untouched through Phases 2 and 3, the new
results endpoint must accept what Angular sends unchanged, and **DRF token auth
survives until Angular is deliberately retired in a separate step after
cutover**. Angular is also the only correct record of the upload/download wire
format — the React app got two details wrong (D1/D2), and because it is not
deployed those are fix-on-vendoring work rather than production incidents. Its
semantics are extracted into this repo's `docs/` so the specification does not
depend on a sibling checkout surviving.

### Key Decision: retire before rebuilding

The owner briefing established that the **ingest pipelines are out of date** and
that **AusCycling membership polling has been withdrawn**, pending a new API
provider. Phase 2 therefore opens with a retirement pass — **2,742 measured lines** and
nine dependencies — which resolves four of the nine model defects by removal
rather than repair. **WMCC is the only client club**, so the API must not be
designed for multi-tenancy, and the hardcoded pointscale becomes data instead of
a bug. Membership categories are to be redesigned around the new AusCycling
system once its spec lands.

## 🔑 Key Principles

### Development Branch Strategy
- One branch per change, merged to `modernization` by reviewed pull request
- `modernization` never receives direct commits — it is the integration branch
- Production stays stable on `master` (hotfix branches + PR only)
- Single deployment when complete
- No backward compatibility concerns during development

### Quality First
- Comprehensive testing before deployment
- Code quality tools (Black, ruff, mypy)
- CI/CD pipeline
- Security audits

### Modern Best Practices
- TypeScript for type safety
- React Query for state management
- API-first architecture
- Comprehensive documentation

## 🚦 Getting Started

### Quick Start (15 minutes)

```bash
# 1. Switch to the development branch (already created)
git checkout modernization

# 2. Set up environment
python -m venv .venv
source .venv/bin/activate  # or .venv\Scripts\activate on Windows
pip install -r requirements/dev.txt
pre-commit install

# 3. Run the quality gates and tests
ruff check . && black --check . && python bin/runtests.py

# 4. Start Phase 2 work!
# See MODERNIZATION_CHECKLIST.md for the current task list
```

### What to Read First

1. **[QUICK_START.md](QUICK_START.md)** - Start here for setup instructions
2. **[MODERNIZATION_SUMMARY.md](MODERNIZATION_SUMMARY.md)** - Understand the overall approach
3. **[MODERNIZATION_CHECKLIST.md](MODERNIZATION_CHECKLIST.md)** - Your daily task list
4. **[MODERNIZATION_PLAN.md](MODERNIZATION_PLAN.md)** - Detailed phase-by-phase guidance

## 📊 Progress Tracking

### Current Status

```
Phase 1: Foundation               [██████████] 100% ✅
Phase 2: Backend API Rebuild      [░░░░░░░░░░] 0%  ← replanned 2026-10-11
Phase 3: React Frontend           [░░░░░░░░░░] 0%
Phase 4: Integration & Deployment [░░░░░░░░░░] 0%
Phase 5: Optimization             [░░░░░░░░░░] 0%
───────────────────────────────────────────────
Overall Progress:                 [█░░░░░░░░░] 10%
```

Verified state of the `modernization` branch (2026-10-11): Django 5.2 / Python
3.14, clean-install boot, 49 tests passing, coverage 44%, lint/format/type
checks gated in CI. See "Phase 1 Exit Notes" in
[`MODERNIZATION_CHECKLIST.md`](MODERNIZATION_CHECKLIST.md).

### Milestones

- [x] Week 4: Django 5.2 upgraded
- [ ] Week 12: Complete REST API
- [ ] Week 26: React frontend complete
- [ ] Week 32: 🎉 Production deployment
- [ ] Week 38: Optimization complete

## 🛠️ Technology Stack

### Backend
- Django 5.2
- Django REST Framework
- PostgreSQL
- Redis (caching)
- Gunicorn + WhiteNoise
- Docker

### Frontend
- React 18
- TypeScript
- Vite (build tool)
- React Router 6
- TanStack Query (React Query)
- React 18 + TypeScript + Vite + **Material UI** (fixed by the vendored race-day
  app), pnpm workspaces under `frontend/`
- Axios

### Development Tools
- Black (code formatting)
- Ruff (linting)
- Mypy (type checking)
- Vitest (testing)
- Playwright (E2E tests)
- GitHub Actions (CI/CD)

### Infrastructure
- Docker + Docker Compose (multi-stage: Node builds both SPAs)
- **Same-origin:** Django + WhiteNoise serve the SPA builds — no separate frontend
  hosting, no CORS ~~Vercel or Netlify~~ (deferred; the split stays available)
- Digital Ocean (backend)
- Sentry (monitoring — already a dependency of `apps/raceday`)

## 📈 Success Metrics

### Technical
- [ ] Test coverage >80%
- [ ] API response time <200ms (p95)
- [ ] Frontend loads in <2 seconds
- [ ] Lighthouse score >90
- [ ] Zero critical vulnerabilities

### Business
- [ ] Feature parity with current app
- [ ] No data loss
- [ ] <1 hour downtime
- [ ] Positive user feedback

## 🤝 Contributing

### Workflow

1. Branch off `modernization` (`feature/…`, `fix/…`, `chore/…`, `refactor/…`, `docs/…`)
2. Make small, focused commits — one logical change each
3. Write tests for new code
4. Run the quality gates: `ruff check .`, `black --check .`, `mypy races`,
   `python bin/runtests.py`
5. Push the branch and open a PR targeting `modernization`
6. Wait for CI, then for review — **the owner merges**

```bash
git checkout modernization && git pull
git checkout -b chore/phase2.1-model-constraints
# ... work ...
git push -u origin HEAD
```

### Code Quality

```bash
# Before committing
black .                    # Format code
ruff check --fix .        # Lint and fix
python bin/develop.py test  # Run tests
```

### Commit Messages

Use clear, descriptive commit messages:
```
✅ Good:
- "Add JWT authentication to API"
- "Update Django to 5.2"
- "Implement race list component"

❌ Avoid:
- "Fix stuff"
- "WIP"
- "Updates"
```

## 📖 Additional Resources

### Django
- [Django 5.2 Documentation](https://docs.djangoproject.com/en/5.2/)
- [Django REST Framework](https://www.django-rest-framework.org/)

### React
- [React Documentation](https://react.dev/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Vite Guide](https://vitejs.dev/guide/)

### Tools & Libraries
- [TanStack Query](https://tanstack.com/query/latest)
- [React Router](https://reactrouter.com/)
- [Tailwind CSS](https://tailwindcss.com/)

## 🆘 Getting Help

### Documentation
1. Check the relevant .md file for your phase
2. Search existing issues
3. Review similar code in the codebase

### Questions
- Create a GitHub issue for technical questions
- Use clear, specific titles
- Include context and what you've tried

## 🎯 Next Steps

Phase 1 (Foundation) is complete. From here:

1. ✅ **Read this README** - You're here!
2. ⬜ **Scan [MODERNIZATION_SUMMARY.md](MODERNIZATION_SUMMARY.md)** - Understand the plan
3. ⬜ **Read the Phase 1 Exit Notes** in [MODERNIZATION_CHECKLIST.md](MODERNIZATION_CHECKLIST.md) - what works, what's owed
4. ⬜ **Read [MODEL_REVIEW.md](MODEL_REVIEW.md)** — why the API is being rebuilt,
   what the models need, and the D1–D4 race-day upload defects
5. ⬜ **Start Phase 2.0** — the retirement pass, then model hardening
6. ⬜ **Track progress** — Use the checklist daily

```bash
# set up a development environment
git checkout modernization
python -m venv .venv && source .venv/bin/activate
pip install -r requirements/dev.txt
pre-commit install
python bin/runtests.py
```

## 📝 Project Status

**Status:** ✅ Phase 1 complete - Moving to Phase 2 (Backend API)  
**Created:** 2026-08-29  
**Last Updated:** 2026-10-11  
**Target Completion:** Q2 2027 (9 months from start)  
**Current Phase:** Phase 2 - Backend API Rebuild (starts with model hardening)

---

## 💪 Let's Build Something Great!

This modernization will transform the Cabici application into a maintainable, performant, and user-friendly system. The foundation is solid, the plan is clear, and the path forward is well-defined.

---

*Last Updated: 2026-10-11*
