# Modernization Plan Summary

**Last Updated:** 2026-08-29

## Overview

This is a comprehensive plan to modernize the Cabici cycling application from Django 4.2 + jQuery/Bootstrap 3 to Django 5.2 + React TypeScript frontend.

## Key Approach: Development Branch Strategy

**🔑 Core Principle:** Complete modernization on development branch, then deploy all at once.

```
Production (master branch)     Development (modernization branch)
     Stable                           Active Work
        ↓                                  ↓
   [Users continue                  [Complete all 5
    using current                    phases here]
    application]                         ↓
        ↓                           [Full testing]
        ↓                                ↓
        ←───────────[Merge & Deploy]─────┘
```

### Why This Approach?

✅ **Production stays stable** - No risk during development
✅ **More aggressive refactoring** - No backward compatibility concerns  
✅ **Comprehensive testing** - Test everything together before deploy
✅ **Cleaner codebase** - Can remove old code completely
✅ **Single deployment** - One cutover, clear rollback plan

### What's Different from Incremental Approach?

❌ **No parallel operation** - Don't run old and new frontend together
❌ **No feature flags** - Not switching between versions
❌ **No beta testing during development** - All testing before deployment
❌ **No maintaining templates** - Can remove Django templates early
✅ **Work freely** - Make breaking changes without concern

## Timeline

**Total Duration:** ~38 weeks (9 months part-time) or 4-5 months full-time

| Phase | Duration | Focus |
|-------|----------|-------|
| **Phase 1: Foundation** | 4 weeks | Django 5.2, dependencies, tooling |
| **Phase 2: Backend API** | 8 weeks | Complete REST API, JWT auth, docs |
| **Phase 3: React Frontend** | 14 weeks | Full React SPA with TypeScript |
| **Phase 4: Integration & Deploy** | 4 weeks | Testing, cleanup, production deploy |
| **Phase 5: Optimization** | 5 weeks | Performance, security, monitoring |
| **Buffer** | 3 weeks | Contingency |

## Five Phases Explained

### Phase 1: Foundation (Weeks 1-4)
**What:** Upgrade Django and modernize tooling
- Update Django 4.2 → 5.2
- Remove obsolete dependencies (Bootstrap, jQuery)
- Set up Black, ruff, mypy
- Configure CI/CD

**Output:** Modern Django 5.2 foundation

### Phase 2: Backend API Rebuild (Weeks 5-12)
**What:** Retire the dead subsystems, then replace the ad-hoc API with a
contract-first `/api/v1/`
- Retirement pass: ingest pipelines, withdrawn AusCycling polling, dead import
  paths (~2,400 lines, 6 dependencies)
- Harden the models (defects, DB constraints, `services/` extraction)
- Design the **frozen race-day contract** first (external entry app is the only
  rider-creation path today)
- Define remaining resources + OpenAPI contract before implementing
- Build all endpoints as ViewSets with explicit serializers and filters
- Implement JWT authentication (keeping DRF token auth until the entry app goes)
- Generate TypeScript client from the schema
- Write comprehensive tests, then delete the legacy `api.py`

**Output:** Feature-complete REST API

### Phase 3: React Frontend (Weeks 13-26)
**What:** Build modern React frontend
- Set up React + TypeScript + Vite
- Implement authentication
- Build all features:
  - Club management
  - Race management
  - Rider management
  - Results and pointscores
- Component library
- E2E tests

**Output:** Feature-complete React SPA

### Phase 4: Integration & Deployment (Weeks 27-32)
**What:** Integrate, test, and deploy
- Remove Django templates completely
- Clean up old frontend code
- Full integration testing
- Cross-browser and mobile testing
- Performance and security testing
- Deploy to production

**Output:** Modernized app running in production

### Phase 5: Optimization (Weeks 33-38)
**What:** Polish and improve
- Implement Django 5.x features
- Performance optimization
- Caching (Redis)
- Security hardening
- Monitoring and observability

**Output:** Optimized, production-ready application

## Technology Stack

### Current → Future

| Component | Current | Future |
|-----------|---------|--------|
| **Backend Framework** | Django 4.2 | Django 5.2 |
| **Frontend Framework** | jQuery + Bootstrap 3 | React 18 + TypeScript |
| **Build Tool** | None | Vite |
| **API** | Partial DRF | Complete REST API |
| **Authentication** | Token + Session | JWT + Session (admin) |
| **Styling** | Bootstrap 3 | Tailwind CSS or MUI |
| **State Management** | jQuery DOM | React Query + Zustand |
| **Testing** | Django tests | Django + Vitest + Playwright |
| **Documentation** | None | OpenAPI/Swagger |

## Key Deliverables

### By End of Phase 2
- ✅ Django 5.2 running
- ✅ Complete REST API
- ✅ API documentation
- ✅ JWT authentication
- ✅ >80% test coverage

### By End of Phase 3
- ✅ Working React frontend
- ✅ Feature parity with old app
- ✅ Component tests
- ✅ E2E tests

### By End of Phase 4
- ✅ Production deployment
- ✅ No Django templates
- ✅ Clean API-only backend
- ✅ Monitoring in place

## Risk Management

### Low Risk Because:
1. **Production untouched** - Current app stays stable
2. **Comprehensive testing** - Test everything before deploy
3. **Clear rollback** - Previous Docker image + DB backup
4. **Existing API** - Already have foundation
5. **Good test coverage** - Confidence in changes

### Mitigation Strategies:
- Database backup before deployment
- Keep previous Docker image for rollback
- Full integration testing before production
- Monitoring and alerts (Sentry)
- Support plan for post-deployment issues

## Success Criteria

### Technical
- [ ] All tests pass (>80% coverage)
- [ ] API response time <200ms (p95)
- [ ] Frontend loads in <2 seconds
- [ ] Lighthouse score >90
- [ ] Zero critical security vulnerabilities
- [ ] 99.9% uptime

### Functional
- [ ] Feature parity with current application
- [ ] All user workflows working
- [ ] Mobile responsive
- [ ] Cross-browser compatible
- [ ] Accessible (WCAG 2.1 AA)

### Business
- [ ] Users can access and use the app
- [ ] No data loss
- [ ] Minimal downtime (<1 hour)
- [ ] Positive user feedback

## Getting Started

### Step 1: Preparation
```bash
# Create development branch
git checkout -b modernization

# Set up development environment
python -m venv venv
source venv/bin/activate  # or venv\Scripts\activate on Windows
pip install -r requirements.txt
```

### Step 2: Phase 1 Kickoff
```bash
# Update Django
# Edit requirements.txt: Django==5.2.x
pip install -r requirements.txt

# Run tests
python manage.py test

# Fix any issues
```

### Step 3: Track Progress
- Use MODERNIZATION_CHECKLIST.md for day-to-day tracking
- Refer to MODERNIZATION_PLAN.md for detailed guidance
- Check TECHNICAL_ASSESSMENT.md for current state analysis

## Documentation Structure

📄 **MODERNIZATION_PLAN.md** (Main Document)
   - Comprehensive plan with all details
   - Phase-by-phase breakdown
   - Code examples and guidance
   - ~200 pages of detail

📄 **MODERNIZATION_CHECKLIST.md** (Tracking)
   - Checkbox-based progress tracker
   - Quick reference commands
   - Weekly milestones
   - Daily use during development

📄 **TECHNICAL_ASSESSMENT.md** (Context)
   - Current state analysis
   - Codebase review
   - Dependency audit
   - Risk assessment

📄 **MODERNIZATION_SUMMARY.md** (This Document)
   - High-level overview
   - Quick reference
   - Getting started guide

## FAQs

**Q: Why not deploy incrementally?**
A: Current app is stable. Completing everything first allows for more aggressive refactoring and comprehensive testing without backward compatibility concerns.

**Q: What if it takes longer than expected?**
A: Production remains stable. Development can take as long as needed. Buffer time built into schedule.

**Q: Can we add new features during modernization?**
A: Critical fixes can go to production. New features should wait or go on modernization branch.

**Q: What happens to the old code?**
A: Remains in git history. Will be archived/removed from the modernization branch as it's replaced.

**Q: How do we test without affecting users?**
A: All testing happens on development environment. Users continue using production until deployment.

**Q: What if the deployment fails?**
A: Rollback to previous Docker image and database backup. Fix issues, redeploy.

## Communication Plan

### Stakeholders
- Regular progress updates (weekly/bi-weekly)
- Demo sessions for major milestones
- Review sessions at end of each phase

### Users
- Advance notice of upcoming changes (2-4 weeks before deployment)
- Training materials and walkthroughs
- Support channel for questions
- Feedback mechanism post-deployment

### Team
- Use GitHub project board for task tracking
- Regular sync meetings
- Code reviews for all changes
- Documentation updates

## Next Actions

1. ✅ Review this plan and other documents
2. ⬜ Decide on timeline commitment (part-time vs full-time)
3. ⬜ Create `modernization` branch
4. ⬜ Set up GitHub project board
5. ⬜ Begin Phase 1: Django upgrade
6. ⬜ Track progress using checklist

---

**Questions?** Review the detailed MODERNIZATION_PLAN.md or TECHNICAL_ASSESSMENT.md for more information.

**Ready to start?** Create the development branch and begin Phase 1!
