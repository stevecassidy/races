# Django Application Modernization Plan

## Executive Summary

This document outlines a comprehensive plan to modernize the Cabici racing application from its current state (Django 4.2 with jQuery-based templates) to a modern architecture with Django 5.x backend API and React frontend. **The work will be done on a development branch with a single production deployment when complete.**

**Development Approach:**
The current production application remains stable while modernization work happens in parallel on a development branch. Once all phases are complete and tested, the new version will be deployed to production. This allows for more aggressive refactoring without concern for intermediate states or maintaining backward compatibility during development.

**Current State:**
- Django 4.2.23
- Python 3.11
- Template-based frontend with Bootstrap 3
- jQuery 3.3.1 with various plugins
- Partial REST API implementation
- Mixed class-based and function-based views
- SQLite dev / PostgreSQL production
- Docker deployment

**Target State:**
- Django 5.1 LTS (latest stable)
- Python 3.11+
- API-only backend with comprehensive REST endpoints
- React SPA frontend
- Modern authentication (JWT + session)
- Comprehensive API documentation
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
- [ ] Update Django 4.2.23 → Django 5.1 LTS
- [ ] Update Python dependencies in requirements.txt
- [ ] Address deprecation warnings
- [ ] Update URL patterns from `re_path` to `path` with converters
- [ ] Test all existing functionality
- [ ] Update Django REST Framework to latest version

**Breaking Changes to Address:**
- `django.utils.translation` → use `gettext_lazy` consistently
- Update middleware configuration if needed
- Check for removed features in Django 5.x
- Update settings for new defaults

**Success Criteria:**
- All tests pass with Django 5.1
- No deprecation warnings
- Database migrations successful
- Development environment functional

### 1.2 Modernize Dependencies (Week 2-3)

**Tasks:**
- [ ] Remove obsolete packages (frontend being replaced):
  - Bootstrap, jQuery libraries (no longer needed)
  - `django-bootstrap-form` (not needed for API)
  - `django-pagination` (use Django's built-in)
  - `webtest/webob` (if not essential for testing)
  - Review need for `pinax-webanalytics`
- [ ] Update third-party packages:
  - django-allauth (latest)
  - django-cors-headers (latest)
  - djangorestframework (latest)
  - gunicorn (latest)
  - whitenoise (latest)
- [ ] Pin all package versions for reproducibility

**Success Criteria:**
- All dependencies up to date
- Security vulnerabilities resolved
- requirements.txt properly versioned
- Unnecessary frontend dependencies removed

### 1.3 Code Quality & Standards (Week 3-4)

**Tasks:**
- [ ] Set up pre-commit hooks
- [ ] Configure Black for code formatting
- [ ] Configure ruff or flake8 for linting
- [ ] Add mypy for type checking
- [ ] Run formatters on existing codebase
- [ ] Add GitHub Actions / CI pipeline for testing

**Success Criteria:**
- Consistent code formatting
- CI/CD pipeline running tests
- Linting integrated into workflow

---

## Phase 2: Backend API Completion

**Goal:** Complete the REST API to support all frontend operations

### 2.1 API Audit & Planning (Week 5)

**Current API Endpoints:**
- `/api/clubs/` - List/detail
- `/api/races/` - List/detail  
- `/api/riders/` - List/detail
- `/api/raceresults/` - List/detail
- `/api/pointscores/` - List/detail
- `/api/racecourses/` - List/detail
- `/api/racestaff/` - List/detail
- `/api/clubroles/` - User roles

**Tasks:**
- [ ] Document all current template views
- [ ] Map views to required API endpoints
- [ ] Identify missing API functionality
- [ ] Design API endpoint structure
- [ ] Plan authentication/authorization strategy

**Missing API Endpoints (to be created):**
```
POST   /api/races/:id/upload-results/
POST   /api/races/:id/publish/
GET    /api/clubs/:slug/statistics/
GET    /api/clubs/:slug/members/
POST   /api/clubs/:slug/email/
GET    /api/riders/:id/results/
GET    /api/pointscores/:id/audit/:rider_id/
POST   /api/races/bulk-create/
PATCH  /api/races/:id/officials/
GET    /api/clubs/:slug/duty-roster/
```

### 2.2 API Development (Week 6-10)

**Tasks:**
- [ ] Create comprehensive serializers for all models
- [ ] Implement ViewSets for remaining models
- [ ] Add filtering, searching, ordering to all endpoints
- [ ] Implement proper pagination
- [ ] Add comprehensive permission classes
- [ ] Create custom actions for complex operations (e.g., result upload)
- [ ] Add API versioning (e.g., `/api/v1/`)

**Code Structure:**
```
races/apps/cabici/
  api/
    __init__.py
    serializers/
      __init__.py
      club.py
      race.py
      rider.py
      results.py
    views/
      __init__.py
      club.py
      race.py
      rider.py
      results.py
    filters.py
    permissions.py
    pagination.py
```

**Success Criteria:**
- All CRUD operations available via API
- Proper permissions enforced
- Comprehensive test coverage (>80%)
- API documentation generated

### 2.3 Authentication Modernization (Week 11)

**Tasks:**
- [ ] Implement JWT authentication alongside session auth
- [ ] Add refresh token endpoint
- [ ] Update CustomAuthToken to return JWT
- [ ] Implement user registration endpoint
- [ ] Add password reset via API
- [ ] Maintain allauth integration for social auth
- [ ] Add CORS configuration for frontend

**Recommended Packages:**
- `djangorestframework-simplejwt`
- `dj-rest-auth` (for common auth endpoints)

**Endpoints:**
```
POST   /api/auth/login/
POST   /api/auth/logout/
POST   /api/auth/register/
POST   /api/auth/token/refresh/
POST   /api/auth/password/reset/
POST   /api/auth/password/reset/confirm/
GET    /api/auth/user/
PATCH  /api/auth/user/
```

### 2.4 API Documentation (Week 12)

**Tasks:**
- [ ] Set up drf-spectacular or drf-yasg for OpenAPI/Swagger
- [ ] Add docstrings to all API views
- [ ] Document request/response examples
- [ ] Generate interactive API documentation
- [ ] Create Postman/Insomnia collection

**Success Criteria:**
- Interactive API docs at `/api/docs/`
- OpenAPI 3.0 schema generated
- All endpoints documented with examples

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
- Update to Django 5.1
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
- [Django 5.1 Release Notes](https://docs.djangoproject.com/en/5.1/releases/5.1/)
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
- [Django Testing](https://docs.djangoproject.com/en/5.1/topics/testing/)
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
