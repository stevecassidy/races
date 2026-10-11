# Quick Start Guide - Modernization Project

## 🚀 Start Here

### 1. Create Development Branch (5 minutes)

```bash
# Ensure you're on master and up to date
git checkout master
git pull origin master

# Create modernization branch
git checkout -b modernization

# Push to remote
git push -u origin modernization
```

### 2. Set Up Development Environment (30 minutes)

```bash
# Create virtual environment
python -m venv venv

# Activate it
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate     # Windows

# Install dependencies
pip install -r requirements.txt

# Run tests to verify
python bin/develop.py test
```

### 3. Update Django (2-3 hours)

```bash
# Edit requirements.txt
# Change: Django==4.2.23
# To:     Django==5.2.0

# Install
pip install -r requirements.txt

# Check for issues
python bin/develop.py check

# Run migrations
python bin/develop.py migrate

# Run tests
python bin/develop.py test

# Fix any deprecation warnings
```

---

## 📊 Development Workflow

```
┌─────────────────────────────────────────────────────────┐
│                    PRODUCTION (master)                  │
│                                                         │
│  ✅ Stays stable and running throughout development    │
│  ✅ Users continue using current application           │
│  ✅ No changes until final deployment                  │
└─────────────────────────────────────────────────────────┘

                            │
                            │ Create branch
                            ↓

┌─────────────────────────────────────────────────────────┐
│              DEVELOPMENT (modernization)                │
│                                                         │
│  Week 1-4:   Django 5.2 + Dependencies                 │
│  Week 5-12:  Complete REST API                         │
│  Week 13-26: Build React Frontend                      │
│  Week 27-32: Integration & Testing                     │
│  Week 33-38: Optimization                              │
└─────────────────────────────────────────────────────────┘

                            │
                            │ After full testing
                            ↓

┌─────────────────────────────────────────────────────────┐
│                    DEPLOYMENT DAY                       │
│                                                         │
│  1. Database backup                                     │
│  2. Deploy new Django API                              │
│  3. Deploy React frontend                              │
│  4. Monitor & support                                  │
└─────────────────────────────────────────────────────────┘
```

---

## 📋 Week-by-Week Roadmap

### Month 1 (Weeks 1-4): Foundation
- **Week 1:** Django 5.2 upgrade, run tests
- **Week 2:** Update/remove dependencies
- **Week 3:** Set up Black, ruff, CI/CD
- **Week 4:** Code quality improvements

**Milestone:** Modern Django 5.2 with clean dependencies ✅

### Month 2-3 (Weeks 5-12): Backend API Rebuild
- **Week 5:** Retirement pass (ingest, withdrawn AusCycling polling, dead import
  paths, unreachable exports) + model hardening
- **Week 6:** Vendor the race-day React app into `frontend/` and audit its upload
  path (D1–D4); publish the resource model + OpenAPI contract for both clients
- **Week 7:** Generate the TypeScript client; wire `apps/raceday` onto it
- **Week 8:** JWT authentication (token auth deleted at cutover)
- **Week 9-10:** Core CRUD as ViewSets under `/api/v1/`
- **Week 11:** API documentation
- **Week 12:** API test suite; delete legacy `api.py`

**Milestone:** Complete REST API with documentation ✅

### Month 3-6 (Weeks 13-26): React Frontend
- **Week 13-14:** React project setup
- **Week 15-16:** Authentication & layout
- **Week 17-18:** Club management
- **Week 19-20:** Race management
- **Week 21-22:** Rider management
- **Week 23-24:** Results & pointscores
- **Week 25-26:** Advanced features

**Milestone:** Feature-complete React application ✅

### Month 7-8 (Weeks 27-32): Integration & Deploy
- **Week 27:** Remove Django templates
- **Week 28-29:** Integration testing
- **Week 30:** Cross-browser/mobile testing
- **Week 31:** Performance & security testing
- **Week 32:** **PRODUCTION DEPLOYMENT** 🚀

**Milestone:** Modernized app in production ✅

### Month 9 (Weeks 33-38): Optimization
- **Week 33:** Documentation
- **Week 34-35:** Django 5.x features
- **Week 36:** Performance optimization
- **Week 37:** Security hardening
- **Week 38:** Monitoring & observability

**Milestone:** Optimized production system ✅

---

## 🎯 Daily Workflow

### As You Work

```bash
# Start your work session
git checkout modernization
git pull origin modernization

# Create feature branch (optional, for major features)
git checkout -b feature/api-clubs

# Make changes
# ... edit files ...

# Run tests
python bin/develop.py test

# Format code
black .
ruff check --fix .

# Commit
git add .
git commit -m "Add club API endpoints"

# Push
git push origin modernization
```

### Track Progress

Open `MODERNIZATION_CHECKLIST.md` and check off completed items:
```markdown
- [x] Update Django to 5.2
- [x] Update dependencies
- [ ] Set up Black
- [ ] Configure CI/CD
```

---

## 📚 Documentation Reference

Use these docs as you work:

| Document | When to Use |
|----------|-------------|
| **MODERNIZATION_SUMMARY.md** | Overview and quick reference |
| **MODERNIZATION_CHECKLIST.md** | Daily task tracking |
| **MODERNIZATION_PLAN.md** | Detailed implementation guidance |
| **TECHNICAL_ASSESSMENT.md** | Understanding current codebase |

---

## 🔧 Essential Commands

### Django Development
```bash
# Run development server
python bin/develop.py runserver

# Run tests
python bin/develop.py test

# Run specific test
python bin/develop.py test races.apps.cabici.tests.testapi

# Create migrations
python bin/develop.py makemigrations

# Apply migrations
python bin/develop.py migrate

# Django shell
python bin/develop.py shell
```

### Code Quality
```bash
# Format code
black .

# Lint code
ruff check .

# Fix linting issues
ruff check --fix .

# Type check (after setup)
mypy races/
```

### React (Starting Week 13)
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
```

---

## 🚨 Common Issues & Solutions

### Issue: Django upgrade breaks tests
**Solution:** Check deprecation warnings, update code patterns
```bash
python bin/develop.py test --warnings
```

### Issue: Package conflicts
**Solution:** Use exact versions, update one at a time
```bash
pip install Django==5.2.0
pip install djangorestframework==3.14.0
```

### Issue: Migration errors
**Solution:** Reset migrations in development
```bash
# Development only, never in production!
rm db.sqlite3
python bin/develop.py migrate
```

---

## ✅ Phase 1 Checklist (First 4 Weeks)

Use this to get started:

```markdown
## Week 1: Django Upgrade
- [ ] Create modernization branch
- [ ] Update Django in requirements.txt
- [ ] Install new version
- [ ] Run tests
- [ ] Fix deprecation warnings
- [ ] Update URL patterns

## Week 2: Dependencies
- [ ] Remove Bootstrap, jQuery from requirements
- [ ] Update django-allauth
- [ ] Update djangorestframework
- [ ] Update other packages
- [ ] Pin all versions
- [ ] Test everything works

## Week 3: Code Quality Tools
- [ ] Install Black, ruff
- [ ] Create pyproject.toml
- [ ] Run formatters
- [ ] Set up pre-commit hooks
- [ ] Fix linting issues

## Week 4: CI/CD
- [ ] Create GitHub Actions workflow
- [ ] Configure test running
- [ ] Add linting to CI
- [ ] Test CI pipeline
```

---

## 🎓 Learning Resources

### Django 5.2
- [Django 5.2 Release Notes](https://docs.djangoproject.com/en/5.2/releases/5.2/)
- [Django REST Framework](https://www.django-rest-framework.org/)

### React + TypeScript
- [React Docs](https://react.dev/)
- [TypeScript Handbook](https://www.typescriptlang.org/docs/)
- [Vite Guide](https://vitejs.dev/guide/)

### Tools
- [Black Documentation](https://black.readthedocs.io/)
- [Ruff Documentation](https://docs.astral.sh/ruff/)

---

## 💡 Tips for Success

1. **Commit often** - Small, focused commits are easier to review and debug
2. **Test continuously** - Run tests after every significant change
3. **Document decisions** - Add comments explaining non-obvious choices
4. **Ask for help** - Use GitHub issues for questions and discussions
5. **Take breaks** - This is a marathon, not a sprint
6. **Celebrate milestones** - Acknowledge progress at end of each phase

---

## 🆘 Need Help?

1. **Check the docs** - MODERNIZATION_PLAN.md has detailed guidance
2. **Review existing code** - Look at similar patterns in the codebase
3. **Search issues** - Someone may have solved similar problems
4. **Create an issue** - Document your question for future reference

---

## 🎉 Ready to Begin?

```bash
# Create your branch and get started!
git checkout -b modernization
echo "Let's build something great! 🚀"
```

Good luck! You've got this! 💪
