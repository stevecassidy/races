# GitHub Copilot Instructions for Cabici Project

## Project Context

This is the Cabici cycling race management application, currently undergoing a comprehensive modernization.

## 🚧 Active Modernization Project

**Critical:** This project is in active modernization from Django 4.2 + jQuery to Django 5.1 + React.

### Key Documents
- **[MODERNIZATION_README.md](../MODERNIZATION_README.md)** - Project overview
- **[MODERNIZATION_PLAN.md](../MODERNIZATION_PLAN.md)** - Detailed implementation plan
- **[MODERNIZATION_CHECKLIST.md](../MODERNIZATION_CHECKLIST.md)** - Task tracking
- **[TECHNICAL_ASSESSMENT.md](../TECHNICAL_ASSESSMENT.md)** - Current state analysis

### Development Strategy
- **All modernization work happens on `modernization` branch**
- **`master` branch stays stable for production**
- **Single deployment when complete** (not incremental)
- **No backward compatibility needed during development**

## Technology Stack

### Current (Legacy - Being Replaced)
- Django 4.2.23
- jQuery 3.3.1 + Bootstrap 3
- Django templates
- Token authentication

### Target (Under Development)
- Django 5.1 LTS
- React 18 + TypeScript
- Vite build tool
- JWT authentication
- Complete REST API

## Development Guidelines

### When Working on Backend (`races/` directory)
1. **Check current phase** in MODERNIZATION_CHECKLIST.md
2. **Follow Django 5.1 patterns** - Use modern conventions
3. **API-first approach** - Build REST endpoints, not template views
4. **Remove template code** - Templates are being eliminated
5. **Use JWT for API auth** - Not session auth (except admin)

### When Working on Frontend (Future `cabici-frontend/` directory)
1. **Use TypeScript** - All React code should be typed
2. **React Query for API state** - Use TanStack Query
3. **Tailwind or MUI for styling** - Not Bootstrap
4. **Component-based architecture** - Reusable components
5. **API client in `/src/api/`** - Centralized API calls

### Code Quality Standards
```bash
# Before committing, always run:
black .                      # Format Python code
ruff check --fix .          # Lint and fix Python
python bin/develop.py test   # Run tests
```

### Testing Requirements
- **Write tests for all new code**
- **Maintain >80% coverage**
- **API endpoints must have tests**
- **React components need component tests**

## Current Phase

Check [MODERNIZATION_CHECKLIST.md](../MODERNIZATION_CHECKLIST.md) for current phase and progress.

**Phases:**
1. Foundation & Django Upgrade (Weeks 1-4)
2. Backend API Completion (Weeks 5-12)
3. React Frontend Development (Weeks 13-26)
4. Integration & Deployment (Weeks 27-32)
5. Optimization (Weeks 33-38)

## Important Notes

### DO:
✅ Work on `modernization` branch
✅ Follow the modernization plan
✅ Write modern Django 5.1 code
✅ Build API endpoints, not template views
✅ Use type hints in Python
✅ Write comprehensive tests
✅ Check the plan before making architectural decisions

### DON'T:
❌ Add new template views (we're removing them)
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
    cabici/           # Main application
      models.py       # Database models
      api/            # REST API (new structure)
        serializers/  # DRF serializers
        views/        # API ViewSets
        permissions.py
        filters.py
      tests/          # Test files
```

### Frontend Structure (To Be Created)
```
cabici-frontend/
  src/
    api/              # API client
    components/       # Reusable components
    features/         # Feature modules
      clubs/
      races/
      riders/
    hooks/            # Custom hooks
    pages/            # Page components
```

## API Patterns

### Use This Pattern for API Endpoints
```python
from rest_framework import viewsets, filters
from rest_framework.decorators import action

class RaceViewSet(viewsets.ModelViewSet):
    queryset = Race.objects.select_related('club').all()
    serializer_class = RaceSerializer
    filter_backends = [filters.SearchFilter, filters.OrderingFilter]
    search_fields = ['title', 'location__name']
    
    @action(detail=True, methods=['post'])
    def upload_results(self, request, pk=None):
        # Custom action
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
python bin/develop.py test
python bin/develop.py makemigrations

# Code quality
black .
ruff check --fix .

# React (when available)
npm run dev
npm test
npm run build
```

---

**Remember:** We're building a modern, maintainable application. Quality over speed!
