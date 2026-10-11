# Model & API Review

**Date:** 2026-10-11
**Scope:** `races/apps/cabici/models.py` (845 lines), `usermodel.py` (886 lines), `api.py` (871 lines)
**Purpose:** input to the revised Phase 2. Two questions:

1. Are the models fit to be the foundation of the new API?
2. Should the existing API be adapted, or scrapped and rebuilt?

Every claim below was checked at runtime against the shipped fixtures, not read
off the screen. The probes are reproduced in [Verification](#verification) so
you can re-run them after changes.

---

## Part 1 — Models

**Verdict: the structure is sound, the details are not.** The domain model
(Club → Race → RaceResult → PointScore, Rider/Membership, ClubRole/UserRole) is
coherent and matches how graded track/road racing actually works. Nothing here
needs redesigning. But there are seven live defects — including one that silently
breaks automatic race ingestion — a set of missing integrity constraints, and a
structural problem that will directly shape the API: **almost all real behaviour
lives in model methods that do I/O and bulk mutation.**

Data is clean today — zero duplicate slugs, roles, grades or tallies in the
fixtures — so the integrity gaps below are latent, not active. That is the
good news: they can be fixed with plain additive migrations rather than a data
rescue.

The counterweight to that optimism is **A6/A7**: a core feature has been raising
`TypeError` on every call, for years, inside a test suite that collects zero
tests. That is the argument for doing model hardening *before* endpoints, not
alongside them.

### Tier A — Defects to fix before Phase 2 (the API would inherit them)

| # | Finding | Where | Impact |
|---|---|---|---|
| A1 | **`PointScore.score()` ignores its own configuration.** It hardcodes `points = [7,6,5,4,3]`, `smallpoints = [5,4]`, `participation = 2` and never reads `self.points`, `self.smallpoints`, `self.smallthreshold`, `self.participation` or `self.method`. The accessors `get_points()` / `get_smallpoints()` exist and are called from nowhere except a test. | `usermodel.py:727-780` | Five model fields are decorative. A club that configures a different pointscale gets WMCC numbers silently. The existing test asserts the *defaults*, so it passes and hides the bug. **This is a scoring-correctness bug in the app's core purpose.** |
| A2 | **`MEMBERSHIP_CATEGORY_CHOICES` is inverted.** `(("Ride", "ride"), ("Race", "race"), ("Non-riding", "non-riding"))` — Django reads `(value, label)`, so the stored value is `"Ride"` and the label is `"ride"`. All 6288 existing rows use lowercase (`race` 6076, `ride` 116, `non-riding` 96). | `usermodel.py:571` | Admin and any ModelForm writes `"Race"`, which is invisible to the seven `category="race"` create/filter sites (`models.py:132,181,734`, `api.py:694,757`, `views.py:184`, `wmccimport.py:298`). `get_category_display()` returns `'race'` for *both* `'race'` and `'Race'`, so the corruption is undetectable in the UI. Verified: `Membership(category='Race').get_category_display() == 'race'`. |
| A3 | **`get_absolute_url()` reverses URL names that no longer exist.** `Race` → `reverse('race', …)`, `Rider` → `reverse('rider', …)`; neither name is registered since the template views were removed. | `models.py:636`, `usermodel.py:437` | The admin "View on site" link 500s — verified end-to-end through `/admin/r/<content_type>/<id>/`. Admin is the one piece of UI we are keeping through Phase 4. `feeds.py` `item_link` has the same problem, so the iCal/Atom feeds cannot be re-routed as-is. |
| A4 | **`RaceResult.pointscores()` references a relation that does not exist** (`resultpoints_set`); no model has an FK to `RaceResult` with that related name. | `usermodel.py:691-693` | `AttributeError` on call. Dead code that will be mistaken for a live API surface. |
| A5 | **`except ValueError, Rider.DoesNotExist:`** — Python 2 syntax that only parses because PEP 758 landed in 3.14. | `models.py:706` | Reads as a bug to every reviewer, is invisible to ruff, and breaks the moment anyone builds on ≤3.13. Needs parentheses. |
| A6 | **⚠️ `Club.ingest_ical()` is broken: it raises `TypeError` on the first race it creates.** It constructs `Race(date=…, time=…, …)` but `Race` has no `time` field (it is `starttime`/`signontime`). Verified end-to-end against the repo's own `tests/cccc.ical` fixture: `TypeError: Race() got unexpected keyword arguments: 'time'`. | `models.py:461-470` | Automatic race ingestion silently does nothing for any club that configures `icalurl`. `management/commands/ingest.py` wraps `club.ingest()` in a per-club `try/except` that only *prints* the error, so a full nightly run reports "Club: CCCC error: …" and exits 0 — no alarm, no races. The sibling path `ingest_by_module()` / `ingest_race_list()` is unaffected (it uses `starttime` correctly), which is why this survived: half the ingest subsystem works. No club in the local dev databases or fixtures currently sets `icalurl`, so the fault is dormant here — **check production before assuming the feature works.** |
| A7 | **The entire ingest test suite is disabled.** `tests/testingest.py` declares `class IngestTests():` with the `TestCase` base commented out on the line above, so the runner collects **0 tests** from it (verified). | `tests/testingest.py:26` | Seven VCR cassettes in `fixtures/vcr_cassettes/` are unused, the ical/module/CSV ingest paths have zero coverage, and that is precisely why A6 went unnoticed for years. Any Phase 2 work on ingest starts by re-enabling these tests. |

A1, A2 and A6 need a decision from you before I touch them (see Tier D) because
all change computed results, stored data, or a live feature's behaviour.

### Tier B — Integrity that belongs in the database

Verified absent (all models: `unique_together=()`, `constraints=[]`, `indexes=[]` except where noted):

| # | Gap | Why it matters |
|---|---|---|
| B1 | `Club.slug` is not unique but is the **API lookup key** (`lookup_field='slug'` on clubs and clubroles) | Two clubs with one slug → `MultipleObjectsReturned` → 500, or silent hijack of another club's endpoint. Also `SlugField()` with the default `max_length=50` and no explicit length. |
| B2 | `ClubRole.name` is not unique but `get_or_create(name=…)` is the universal idiom (7 call sites) | Duplicates make `UserRolesView` and `allocate_officials()` silently partial, then `.get()` raises. |
| B3 | `ClubGrade` uniqueness is enforced in a **Python `save()` override** (`usermodel.py:652`), not the DB | The override is bypassed by `bulk_create`, queryset `.update()`, and any concurrent writer. Zero DB protection for a rule the whole grading flow depends on. |
| B4 | `Membership` has no `unique_together (rider, club, category, date)` | The result-upload path creates a new membership whenever a later date arrives; nothing stops duplicates from concurrent uploads. |
| B5 | `PointscoreTally` has no `unique_together (pointscore, rider)` while `tally()` does `get_or_create` and `audit()` does `.get()` | Duplicate tallies → `MultipleObjectsReturned` in the audit view, doubled points in `tabulate()`. |
| B6 | `UserRole` has no `unique_together (user, club, role)` | `allocate_officials()` compensates with a manual `filter().count() == 0` check — a Python-level workaround for a DB constraint. |
| B7 | `Race.hash` is not unique; dedupe is `filter(hash=…).count() == 0` | Two overlapping ingest runs create duplicate races. `hash` is also `max_length=100` for a 40-char SHA-1 hex. |
| B8 | `RaceResult.unique_together = (('race','grade','number'), …)` with `number` **nullable** | On PostgreSQL NULLs are distinct, so the constraint does not fire for blank bibs — which is exactly why three separate "increment the number to avoid a clash" hacks exist (`models.py`, `api.py`, `wmccimport.py`). |
| B9 | No indexes on the hot query columns | `Race.date` + `Race.status` drive the home page, every race list and the feeds; `PointscoreTally` orders by `(-points, eventcount)`. None indexed. |

Recommended shape: `UniqueConstraint` (named, so they are reversible),
`condition` for the nullable-bib case (`number__isnull=False`), plus
`Index` on `Race(date, status)` and `PointscoreTally(pointscore, -points)`.
Because the data is already clean, this is one migration with no backfill.

### Tier C — Structural: these shape the API, fix them during Phase 2

| # | Finding | Consequence for the new API |
|---|---|---|
| C1 | **The domain is split arbitrarily across two modules.** `models.py` holds Club / RaceCourse / RacePrototype / Race; `usermodel.py` holds Rider / Membership / ClubRole / UserRole / RaceStaff / ClubGrade / RaceResult / PointScore / PointscoreTally. `Race` and `RaceResult` — the tightest-coupled pair in the app — live in different files, producing **6 function-level circular imports** (`models.py:98,175,252,296,380,650`). | Serializers and views will need to import from both. Merge into one `models.py` (or a `models/` package) first: it is mechanical, needs no data migration, and removes the function-level imports that hide dependencies from static analysis. |
| C2 | **Model methods do I/O and bulk mutation.** `Club.ingest_ical()` opens a URL; `Club.ingest_by_module()` does `import_module("races.ingest." + self.slug.lower())` — dynamic import keyed on a user-editable CharField; `Club.validate_membership()` calls the AusCycling HTTP API *and saves a Membership*; `Race.load_excel_results()` is ~150 lines that deletes every result, re-creates riders, memberships, grades and results, then recalculates pointscores — with `transaction.atomic()` only around individual row saves; `RiderManager.import_*()` parses CSV and IMG HTML tables. | These cannot be exposed safely as endpoints. They need a `services.py` layer: pure functions, explicit arguments, `transaction.atomic()` at the operation boundary, typed result/error objects. The API then becomes thin projections over services instead of re-implementing the logic in `post()` overrides (which is what `api.py` does today). |
| C3 | **Authorization is three overlapping concepts** — `Rider.official` (boolean), `Club.manage_races` / `manage_members` / `manage_results` (capability flags), and `UserRole` + `ClubRole` (RBAC) — and the code only ever consults `Rider.official`. `ClubRole` is global rather than per-club, so role names collide across clubs. | The new permission classes need one authoritative answer to "can this user edit this race". Decide whether the flags are club-capability gates and `UserRole` is membership-in-role, then express permissions as `role in club ∧ club capability`, dropping `Rider.official` to a cached convenience. |
| C4 | **`RacePrototype` has zero references** anywhere — no admin, no API, no view, no test, no migration beyond creation. Bulk race creation is done with `dateutil.rrule` in `views.py` instead. | Dead table. Drop it, or finally use it for the planned bulk-create feature. |
| C5 | **Free-text pseudo-structures.** `Race.grading` = `"A,A2,B,C,D,E,F"` (never parsed server-side — its only consumer was `cabici.js:255`); `PointScore.points`/`smallpoints` = comma strings; `Rider.commissaire` = `"0 if not a Commissaire, otherwise eg. 1, RT"`, filtered with `.exclude(commissaire__exact="").exclude(commissaire__exact=0)` (an int against a CharField). | Each becomes either a JSONField/array, a proper choice, or a child table — or gets deleted. The React app cannot render a validation-safe editor for a comma string. |
| C6 | **Sentinel ambiguity.** `RaceResult.place` uses both `0` and `NULL` for "unplaced" (`load_excel_results` and `api.py` write `0`, `wmccimport` writes `None`, `fix_small_races` filters `place__gt=0`, `score()` tests `if not result.place`); `Rider.dob` defaults to `1970-01-01` rather than NULL, and feeds `classification`; 48 of 4335 riders have `club = NULL`. | Pick one sentinel per field. Otherwise every API filter (`?placed=true`, `?classification=`) has two correct spellings. |
| C7 | **Two identities per person.** `User` (auth, names, email) ↔ `Rider` (OneToOne profile) ↔ `Rider.id` vs `User.id`, with no `AUTH_USER_MODEL` swap. `PointScoreSerializer` exposes `user.id` as `riderid`, `RaceResultSerializer` exposes `rider.id` as `riderid` and the *display string* as `rider`. | Not worth restructuring now (swapping the user model mid-modernization is a large, risky migration for no user-visible gain), but the API must settle on **one public identifier for a rider** and use it everywhere. Recommend `rider.id` consistently, with `user` fields flattened into the rider resource. |
| C8 | **Change tracking is a hack.** `Rider.updated = auto_now` and the upload path calls `rider.save()  # to trigger timestamp update` on rows it did not otherwise change, because the `?changed=<unix ts>` delta filter depends on it. | If the React app keeps delta sync (it should — rider lists are 4k+ rows), make the timestamp explicit and correct: touch on related writes via signals or `F()` updates, and expose `updated_at` in the payload. |
| C9 | **`Club.auscycling_client_secret` is plaintext in the DB** (acknowledged TODO at `models.py:73`). | Irrelevant to the current hand-written `ClubSerializer`, fatal for a `fields='__all__` rewrite. Never serialize it; write-only via a dedicated endpoint, or move to env/secret store. |
| C10 | **`Rider.current_membership` takes the max date across all categories** (`membership_set.order_by('-date')[0]`), so a further-future `non-riding` membership masks the race membership, and `member_category` / `member_date` report the wrong thing. `classification` computes age as `now.year - dob.year` (ignores month/day), returns `None` implicitly for age ≥ 110, and derives women's categories by string munging (`"M1"→"W1"`, `"U23 Men"→"Elite Women"`). | Both are display-facing. `current_membership` should filter by category and validity window; classification rules should be an explicit mapping, not `.replace()` calls, since the React app will render these labels directly. |
| C11 | **N+1 by construction in the aggregate paths.** `Club.get_officials_with_counts()` runs one `COUNT` per candidate; `Club.allocate_officials()` re-counts per race; `PointScore.tabulate()` → serializer calls `club.grade(rider)` per row; `tally_helpers()` parses the JSON audit trail per staff member. | The pointscore table (a headline screen) is O(riders × races) today. The new API needs `select_related`/`prefetch_related` per queryset and possibly a materialised tally, or the React app will be slower than the jQuery one it replaces. |
| C12 | `Club.statistics()` returns a dict mixing integers with **querysets** (`roles`, `commissaires`). | Fine for a template, wrong for a serializer. Normalise to counts + nested resources. |

### Tier D — Judgement calls I need from you

1. **A1 (pointscore config ignored):** is the hardcoded WMCC scale deliberate —
   i.e. are `points`/`smallpoints`/`method` genuinely unused by design — or a
   bug? Fixing it changes points for any club whose config differs from
   `7,6,5,4,3` / `5,4` / `2`, which means recalculated standings.
2. **A2 (inverted choices):** I'd flip the tuple and add a data migration
   normalising any `'Race'`/`'Ride'`/`'Non-riding'` values to lowercase. Fixtures
   are clean, so this is a no-op on current data. Confirm.
3. **A6/A7 (broken ical ingest):** does production have clubs with `icalurl` set?
   If yes, this feature has been silently failing and deserves an out-of-band fix
   rather than waiting for Phase 2. Either way I'd re-enable the ingest tests
   (A7) immediately and fix `time=` → `starttime=` (A6) as a small standalone
   commit, since it is a one-line correction to a broken feature.
4. **C4:** delete `RacePrototype` and `Race.grading`, or wire them into the
   bulk-create feature? Both are currently dead weight the API would otherwise
   have to expose.
5. **C7:** are you willing to keep `django.contrib.auth.User` (no
   `AUTH_USER_MODEL` swap) through this modernization? I recommend yes, and
   treating a custom user model as post-cutover work.
6. **B8:** should bib numbers be unique per race (not per race+grade), and
   nullable-or-allocated? That decides whether the three "increment to avoid
   clash" hacks can be deleted.

---

## Part 2 — Should we scrap the API?

**Yes. Scrap `api.py` and build the new API from scratch on the models.**
Adapting it is more expensive than replacing it, and — decisively — **it has no
consumer to stay compatible with**: the only clients are `cabici.js` (588 lines),
`riders.js` (81 lines) and the templates, all scheduled for deletion in Phase 4.
The plan's own governing principle is "no backward compatibility during
development". Preserving an idiosyncratic contract for a client that is about to
disappear buys nothing.

### What "ad-hoc" actually costs (all verified)

**It is not a REST API over the domain; it is a set of screen-scrapes.**
13 models, 8 resources with endpoints, 16 named URL patterns, hand-wired as
list/detail pairs — no routers, no ViewSets, no `DefaultRouter` baseline. No
endpoint for `Membership`, `ClubGrade`, `ClubRole` or `PointscoreTally`, all of
which the planned club-management and results screens need.

**The query vocabulary is per-view, not per-resource.** Instead of filters:
`?select=future|recent|raceday|results` (hardcoded date windows in a branch
chain), `?count=N` (silent slice, `except: pass`), `?prefix=%QUERY` (built for
typeahead), `?changed=<unix ts>` (delta sync), `?commissaire`, `?placed`,
`?race=`. And `RaceResultList.get_queryset()` returns `.none()` when no `race`
param is supplied — a collection endpoint that cannot list its collection,
because "we'd never actually want that".

**The same concept is spelled differently per serializer.** For a rider:
`RaceResultSerializer.rider` = display string, `.riderid` = `Rider.id`;
`PointScoreSerializer.riderid` = `User.id`; `RaceStaffSerializer.rider` =
`Rider.id` (via `__all__`); `RiderSerializer` has no `name` field at all. A React
client written against this needs per-endpoint knowledge of what an ID means —
the opposite of a typed generated client.

**Writes are unsafe.** `fields = '__all__'` on `RaceCourse`, `RaceStaff`,
`RaceResult` (with C9 in mind); `RaceResultList.post` — the highest-value
endpoint in the app — has **no permission class** (inherits
`IsAuthenticatedOrReadOnly`), so any authenticated user can wipe and replace any
race's results; it deletes then re-inserts with **no transaction**; it returns a
`ridermap` of temporary→real IDs; and it stashes raw payloads to disk.
`ClubOfficialPermission` reads `request.user.rider` unguarded → 500 (not 403)
for any authenticated user without a Rider. `RaceOfficialField.to_internal_value`
exists only to `print()` and return `[]`.

**Auth is a dead end for the React app.** Token auth with no refresh, no
registration, no password reset; `CustomAuthToken` does
`User.objects.get(email__iexact=…)` → 500 on an unknown email instead of 401,
then dereferences `user.rider.club` → 500 for a user without a Rider. Phase 2.3
has to build all of that anyway.

**Documentation is absent.** No schema, no versioning, no filter docs — so the
"generate the TypeScript client from OpenAPI" step that makes a new frontend
affordable cannot start until this is rebuilt regardless.

### Cost comparison

| | Adapt `api.py` | Rebuild |
|---|---|---|
| URLs | Change anyway (`/api/v1/`, routers) | New |
| Serializers | Rewrite anyway (naming, `__all__`, missing resources) | New |
| Filters | Replace `?select=`/`?count=` anyway (React needs composable filters) | New |
| Permissions | Redesign anyway (C3 + the unguarded `.rider`) | New |
| Upload path | Move into a service (C2) | New |
| Tests | 790 lines tied to the old shapes; rewrite with the endpoints | New |
| Compatibility burden | None — the only client is being deleted | None |

Every row says the same thing: adaptation touches ~100% of the file while
inheriting its inconsistencies. The 80% coverage of `api.py` measures the old
shapes, not reusable ones.

### What to salvage (do not lose this domain knowledge)

- **`testapi.py` (790 lines) as a behavioural spec.** Mine it for requirements —
  especially the result-upload round trip — then rewrite the tests against the
  new endpoints. Don't delete it before that's done.
- **The result-upload payload shape** (`{race, riders[], entries[]}` with
  `"ID…"` temporary rider IDs and the `ridermap` response). That contract is
  shared with the race-sheet/desktop workflow; reproduce it deliberately as
  `POST /races/{id}/results/`, documented, transactional, permission-checked.
- **The delta-sync idea** (`?changed=<unix>`) — a genuinely good feature for a
  4k-row rider list. Re-express as `?updated_after=<iso8601>` + `ETag`/
  `Last-Modified`.
- **`ClubOfficialPermission`'s intent** (safe methods open; writes need club
  affiliation) — that logic is right, its implementation is not. Port it into
  the new permission classes driven by C3.
- **`StandardResultsSetPagination`** (200/page, max 1000) — sensible defaults,
  lift the numbers.
- **The AusCycling validation hook** — keep the call site, move the logic to a
  service (C2).

### Revised Phase 2

Contract-first, models-first:

1. **2.0 Model hardening** *(new)* — Tier A defects, Tier B constraints, then
   C1 (merge `usermodel.py` → `models.py`) and C2 (extract `services.py`).
   This must precede serializers: the API surface is determined by the domain
   model, and fixing A1/A2 afterwards changes API responses.
2. **2.1 Resource model + OpenAPI contract** — replace "map old views to
   endpoints" with "derive resources from the domain": one identifier per
   concept, consistent representations, filters as `django-filter` `FilterSet`s,
   writes as explicit actions. Publish the spec, generate the TypeScript client
   from it (`openapi-typescript` or `orval`), so Django and React cannot drift.
3. **2.2 Auth** — JWT (simplejwt) + refresh, register/password-reset, allauth →
   JWT for the admin/session path, CORS for the SPA origin.
4. **2.3 Core CRUD** — routers + ViewSets under `/api/v1/`, `select_related`/
   `prefetch_related` per queryset (C11), pagination everywhere, permissions
   from C3, schema annotations per endpoint.
5. **2.4 Domain operations** — result upload, bulk race creation, official
   allocation, pointscore recalculation, membership validation, CSV/XLS exports,
   iCal feeds — as service-backed actions, not `post()` overrides.
6. **2.5 Delete `api.py`** in one commit once the new package covers the
   surface. No shim, no dual-running, per the plan's stated approach.

---

## Verification

Reproducible probes used above (run with `races.settings.testing`):

```python
# A1: score() ignores configuration
import inspect
from races.apps.cabici.usermodel import PointScore
src = inspect.getsource(PointScore.score)
assert not any(p in src for p in ("self.points", "self.smallpoints",
                                  "self.participation", "self.method",
                                  "self.smallthreshold"))
# -> locals: ['points = [7, 6, 5, 4, 3]', 'smallpoints = [5, 4]', 'participation = 2']

# A2: inverted choices
from races.apps.cabici.usermodel import Membership
Membership._meta.get_field("category").choices
# -> [('Ride', 'ride'), ('Race', 'race'), ('Non-riding', 'non-riding')]
Membership(category="Race").get_category_display()   # -> 'race'
Membership(category="race").get_category_display()   # -> 'race'

# A3: dead reverse targets / admin 500
from django.urls import reverse, NoReverseMatch
reverse("race", kwargs={"pk": 1, "slug": "X"})       # -> NoReverseMatch
# GET /admin/r/<content_type_id>/<race_id>/  -> NoReverseMatch (500)

# A6: ical ingest raises, verified with the repo's own fixture
from unittest import mock
from races.apps.cabici.models import Club
club = Club.objects.create(name="CCCC", slug="CCCC",
                           icalurl="http://example.org/x.ical")
with mock.patch("races.apps.cabici.models.urlopen") as m:
    m.return_value.read.return_value = open(
        "races/apps/cabici/tests/cccc.ical", "rb").read()
    club.ingest_ical()
# -> TypeError: Race() got unexpected keyword arguments: 'time'
# Race._meta.local_fields has starttime/signontime, never 'time'
# ingest_by_module()/ingest_race_list() are unaffected (they use starttime)

# A7: ingest tests collect nothing
import unittest
unittest.TestLoader().loadTestsFromName(
    "races.apps.cabici.tests.testingest").countTestCases()   # -> 0

# B: integrity census
for model in (Club, Race, RaceCourse, RacePrototype, Membership, PointScore,
              RaceResult, PointscoreTally, ClubRole, UserRole, ClubGrade, Rider):
    print(model.__name__, model._meta.unique_together,
          model._meta.constraints, model._meta.indexes)
# only RaceStaff (rider,race,role) and RaceResult (race,grade,number)/(race,rider)

# data census (fixtures)
# membership categories: {'race': 6076, 'ride': 116, 'non-riding': 96}
# duplicate club slugs: {}   duplicate ClubRole names: {}
# duplicate tallies: {}      duplicate club grades: {}
# riders without a club: 48 of 4335
# races with duplicate hash: 0

# C1: circular imports
# models.py function-level imports of usermodel at lines 98,175,252,296,380,650

# Part 2: surface census
# 13 models; 16 named API URL patterns; no routers/ViewSets
# ad-hoc query params: api.py lines 370-372 (club/select/count),
#   477-480 (club/commissaire/prefix/changed), 531 (club), 607-608 (race/placed)
# legacy JS clients: cabici.js 588 lines, riders.js 81 lines
```
