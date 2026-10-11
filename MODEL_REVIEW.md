# Model & API Review

**Date:** 2026-10-11 (Parts 1–2 written, then revised the same day after an
owner briefing — see below)
**Scope:** `races/apps/cabici/models.py` (845 lines), `usermodel.py` (886 lines),
`api.py` (871 lines), plus the ingest, import and AusCycling surfaces and
`origin/master` for the race-day routes
**Purpose:** input to the revised Phase 2. Two questions:

1. Are the models fit to be the foundation of the new API?
2. Should the existing API be adapted, or scrapped and rebuilt?

Every claim below was checked at runtime against the shipped fixtures, not read
off the screen. The probes are reproduced in [Verification](#verification) so
you can re-run them after changes.

> **Read the revision first.** The evidence in Parts 1 and 2 stands, but the
> *dispositions* changed after the owner briefing on 2026-10-11. See
> [Revision](#-revision-2026-10-11-after-owner-briefing) immediately below.

---

## ⚠️ Revision (2026-10-11, after owner briefing)

Four facts about how the application is actually used today, none of which is
visible from the code:

1. **The ingest pipelines are all out of date.** The club web scrapers, the
   iCal feed ingestion and the historical data imports no longer match the
   landscape. Nothing is maintained there.
2. **AusCycling membership polling has been withdrawn.** It was the most recent
   change to the codebase; it is now switched off pending a **new API
   provider**.
3. **The only way riders are added today is the race-day front end, one at a
   time, through the result upload endpoint.**
4. **WMCC is the only client club.** The pointscore is "very much a WMCC
   thing" — no other club runs it that way — which is almost certainly why the
   point values are hardcoded (a quick fix rather than an oversight).

Membership categories also need updating to reflect AusCycling's new membership
system — a forward requirement, not merely the inverted-choices bug in A2.

### What this changes

**Four of the seven Tier A defects are resolved by deletion, not repair.**
A4 (dead relation), A5 (Python-2 `except` form), A6 (broken `ingest_ical()`) and
A7 (disabled ingest tests) all live in code that should be retired. That removes
the largest single scare from this review — a silently broken core feature —
without a fix, and it takes roughly **2,400 lines** with it (see
*Retirement pass* below).

**My Part 2 conclusion was partly wrong, and the correction matters.** I wrote
that the API "has no consumer to stay compatible with" because the only clients
in the repository are `cabici.js` and the templates. There is an **external
client**: the race-day entry application, which is not in this repo. Traced
through `origin/master` (see *The live race-day contract*), its loop is:

| Step | Master route | Purpose |
|---|---|---|
| 1 | `POST /api/token-auth/` | DRF **token** auth |
| 2 | `GET /clubs/<slug>/riders.xlsx` | rider list — `urls.py` comment: *"get rider csv file for race entry front end"*; `ClubRidersExcelView` carries *"the java desktop app requires a number"* |
| 3 | `POST /api/raceresults/` | results JSON, `{race, entries[], riders[]}` |

So "scrap the API" is still right — but **one endpoint and one export are a live
external contract**, not a shape we are free to redefine. Steps 2 and 3 are
currently **unrouted on the `modernization` branch** (removed in `b5bd661
remove view references`), which is harmless while the branch is undeployed but
means the cutover cannot happen without a replacement.

Everything downstream of that contract also moves up in priority, including two
silent defects I had not found when Part 2 was first written — see **A8** and
**A9**.

**Multi-tenancy is speculative.** With one client club, the three-layer
authorization model in C3 does not need to be a general RBAC engine; it needs to
answer "is this person an official of the club that owns this object". Several
Tier B constraints (B1 `Club.slug` uniqueness, B7 `Race.hash`) drop from
"important" to "cheap hygiene". Resist any design that assumes a second club
until one exists.

**A1 is reframed, not downgraded.** The hardcoded pointscale is single-tenant
reality leaking into code rather than carelessness. It is still a landmine —
five configurable fields sit in the database looking live while `score()`
ignores them, and the test suite asserts the defaults so it passes — but the fix
is small and behaviour-preserving for WMCC: read the config, seed WMCC's actual
scale as data. See *Decisions*.

### The retirement pass (new Phase 2.0)

Verified unreferenced by any live code path — the only callers are tests or
deleted features:

| Retire | Lines | Evidence |
|---|---|---|
| `races/ingest/` entirely (lacc, penrith, waratahs, csvingest) | 384 | fact 1; only `manage.py ingest` and the disabled tests reach it |
| Commands: `ingest`, `csvingest`, `harvestclubs`, `loadusers`, `wmccimport` | 645 | one-off historical imports / scrapers |
| `auscycling.py` + `validate_memberships.py` + `Club.validate_membership()` | ~375 | fact 2 — withdrawn pending a new provider |
| `Club.auscycling_client_id/_secret/_club_id`, `Membership.last_validated`/`validation_error` | 5 fields | same; also removes the plaintext-secret finding C9 |
| `Race.load_excel_results()` | ~150 | **only** callers are 4 tests in `testresults.py`; the production caller `RaceUploadExcelView` exists on master and is gone here |
| `RiderManager.update_from_tidyhq_spreadsheet()`, `parse_img_members()`, `IMG_MAP` | ~300 | tidyhq app already removed (`f5d37e4`) |
| `save_rider()` (Strava callback) | ~25 | never registered as an allauth pipeline |
| `Club.icalurl`, `Club.icalpatterns`, `RacePrototype` | 2 fields + 1 model | ingest-only / never referenced outside its own migration |
| `ClubManager.closest()`, `RaceCourseManager.find_location()` | ~30 | sole users of `ngram`; every caller is retired above, so both managers reduce to `models.Manager` |
| `tests/testingest.py`, `imgsampledict.py`, 7 VCR cassettes | ~590 | tests the code they cover no longer exists |
| **Dependencies**: `icalendar`, `ngram`, `beautifulsoup4`, `requests`, `vcrpy`, `pytz` | 6 packages | `icalendar`/`ngram` → ingest only; `bs4` → scrapers + tidyhq; `requests` → **auscycling only**; `vcrpy` → ingest tests; `pytz` → one `timezone()` call, replaceable with `zoneinfo` |

**Keep, but move into `services/`** (these encode real domain rules):
`PointScore.score()`/`tally()`/`recalculate()`, `Race.tally_pointscores()`,
`fix_small_races()`, `Club.allocate_officials()`/`promotion()`/`performancereport()`,
`Rider.classification()`, and the XLS/CSV export builders in `views.py`.

**Hold, do not delete yet:** `pyexcel`/`pyexcel-xls`/`openpyxl` — the XLS rider
export is step 2 of the live contract. Drop them only once the race-day client is
replaced.

### Decisions this briefing created

1. **Is the race-day front end in scope?** This is now the single most
   important open question in the project. If the entry app will be rewritten as
   part of the React frontend, the contract is negotiable, token auth can go,
   the XLS export disappears, and Phase 2 simplifies a lot. If it stays
   external, then `POST /api/raceresults/` and `GET /clubs/<slug>/riders.xlsx`
   must be reproduced **byte-compatible**, token auth must keep working until
   that app is retired, and A8/A9 below are production bugs to fix rather than
   design notes.
2. **Membership categories are blocked on the new AusCycling spec.** Don't ship
   two migrations: fix the inverted tuple (A2) *as part of* adopting the new
   category set, in one migration. Note the upload payload already carries
   `member_category` — see A8.
3. **Pointscale:** wire `score()` to its config fields (WMCC scale becomes
   data, behaviour unchanged, landmine removed) — recommended — or delete the
   fields and state the WMCC-only assumption explicitly. Do not leave them
   decorative.
4. **`PointScore.method`** offers `WMCC`/`LACC` but only WMCC exists in code, and
   LACC is one of the retired scrapers. Delete the field.

---

## Part 1 — Models

**Verdict: the structure is sound, the details are not.** The domain model
(Club → Race → RaceResult → PointScore, Rider/Membership, ClubRole/UserRole) is
coherent and matches how graded track/road racing actually works. Nothing here
needs redesigning. But there are nine live defects, a set of missing integrity
constraints, and a structural problem that directly shapes the API: **almost all
real behaviour lives in model methods that do I/O and bulk mutation.**

Data is clean today — zero duplicate slugs, roles, grades or tallies in the
fixtures — so the integrity gaps below are latent, not active. That is the
good news: they can be fixed with plain additive migrations rather than a data
rescue.

**After the briefing, the picture is better than it first looked.** Four of the
nine defects (A4–A7) sit in code that is being retired, and C2/C3/C4/C9 shrink
or disappear — so the model layer is in less trouble than the raw count
suggests. Two defects become *more* important instead: **A8** and **A9**, both in
the race-day upload contract, which is the app's only live rider-creation path.

The general lesson from A6/A7 still stands and is the argument for doing model
work before endpoints: a core feature raised `TypeError` on every call for years
inside a test suite that collected zero tests, and nobody noticed because a
sibling path worked. Untested surfaces rot silently.

### Tier A — Defects

Nine findings. The **Disposition** column reflects the owner briefing above:
four are retired with the code they live in rather than repaired.

| # | Finding | Where | Disposition |
|---|---|---|---|
| A1 | **`PointScore.score()` ignores its own configuration.** Hardcodes `points = [7,6,5,4,3]`, `smallpoints = [5,4]`, `participation = 2`; never reads `self.points`, `self.smallpoints`, `self.smallthreshold`, `self.participation` or `self.method`. `get_points()`/`get_smallpoints()` are called only from a test. | `usermodel.py:727-780` | **Fix** — wire to config, WMCC scale becomes data. Behaviour unchanged for the only club. *(decision 3)* |
| A2 | **`MEMBERSHIP_CATEGORY_CHOICES` is inverted.** `(("Ride","ride"),("Race","race"),("Non-riding","non-riding"))` — Django reads `(value,label)`, so the stored value is `"Ride"`. All 6288 rows use lowercase (`race` 6076, `ride` 116, `non-riding` 96). `get_category_display()` returns `'race'` for both `'race'` and `'Race'`, so admin-written corruption is invisible in the UI. | `usermodel.py:571` | **Fix, deferred** — fold into the single migration that adopts AusCycling's new categories; do not migrate twice. *(decision 2)* |
| A3 | **`get_absolute_url()` reverses URL names that no longer exist** (`Race`→`'race'`, `Rider`→`'rider'`), so the admin "View on site" link 500s — verified end-to-end through `/admin/r/<content_type>/<id>/`. `feeds.py` `item_link` has the same fault, so the iCal/Atom feeds cannot be re-routed as-is. | `models.py:636`, `usermodel.py:437` | **Fix** — admin is the one UI we keep through Phase 4. |
| A4 | **`RaceResult.pointscores()` references a relation that does not exist** (`resultpoints_set`); no model has an FK to `RaceResult` with that related name. | `usermodel.py:691-693` | **Delete** with the retirement pass. |
| A5 | **`except ValueError, Rider.DoesNotExist:`** — Python 2 syntax that only parses because PEP 758 landed in 3.14; invisible to ruff, breaks on ≤3.13. | `models.py:706` | **Delete** — it lives inside `load_excel_results()`, whose only callers are 4 tests. |
| A6 | **`Club.ingest_ical()` raises `TypeError` on every call** — builds `Race(date=…, time=…)`; `Race` has no `time` field. Reproduced against `tests/cccc.ical`. Invisible because `manage.py ingest` catches per club and only *prints*, and the sibling `ingest_by_module()` path works, so half the subsystem functions. | `models.py:461-470` | **Delete** with the retirement pass (fact 1). Was flagged "check production"; moot once ingest is retired. |
| A7 | **The whole ingest test suite is disabled** — `testingest.py` declares `class IngestTests():` with the `TestCase` base commented out, so **0 tests collect** (verified) and 7 VCR cassettes are dead. The direct cause of A6 surviving for years. | `tests/testingest.py:26` | **Delete** with the retirement pass. Keep the lesson: untested surfaces rot silently. |
| A8 | **⚠️ The upload endpoint silently drops `member_category`.** The external client sends it (`tests/result-upload.json` → `"member_category": "race"`), but `api.py` hardcodes `category="race"` at lines 694 and 757. No test asserts the category — `test_upload_results` checks club, phone, DOB and gender but never this. | `api.py:694,757` | **Fix, and it is now load-bearing** — it collides head-on with the new membership categories: race-day entries would file every rider as `race` whatever the entry app sends. *(decisions 1, 2)* |
| A9 | **⚠️ `grade_change` type mismatch in the live contract.** `api.py:821` tests `entry["grade_change"] == "y"`; the sample payload sends JSON booleans (`true`/`false`). If the real client sends booleans, **in-race grade promotions never apply.** | `api.py:821` | **Needs the real client to resolve** — either the sample is stale or this is a production bug. *(decision 1)* |

A1, A2, A8 and A9 change computed results, stored data, or the behaviour of a
live feature, so each needs an owner decision before it is touched. A8 and A9
were found only because the briefing revealed that the upload endpoint has an
external client — they are the two highest-value findings in this review.

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

**Rows the briefing simplifies** (the table above is the pre-briefing analysis;
these dispositions override it):

- **C2** shrinks dramatically. Of the I/O-in-models offenders, `ingest_ical()`,
  `ingest_by_module()` and `validate_membership()` are **retired**, and
  `load_excel_results()` and `RiderManager.update_from_tidyhq_spreadsheet()`
  (~250 lines, tidyhq already removed) are dead. What genuinely moves to
  `services/` is the results-upload handler, the pointscore
  tally/recalculate, official allocation and the export builders.
- **C3** stops being an RBAC design problem. One client club means the question
  is "official of the owning club?", not "general role-based access across
  tenants". Keep the schema; do not build the general case. Note
  `Club.manage_results` has exactly one reference — its own field definition —
  and `manage_races` none outside tests, while `manage_members` is consumed by
  `cabici.js` and `ClubBriefSerializer` (so the React app will still need it).
- **C4** is resolved: `RacePrototype` is retired.
- **C5** splits. `PointScore.points`/`smallpoints` become honest under A1;
  `Rider.commissaire` stays free text (it holds values like `"2 Road Track MTB"`)
  but should be paired with a boolean "is a commissaire" or the `"0"` sentinel
  dropped, since `Club.statistics()` currently filters it with
  `.exclude(commissaire__exact="")` *and* `.exclude(commissaire__exact=0)` — an
  integer against a `CharField`. `Race.grading` **survives and matters**: it is
  the per-race grade set the race-day entry screen renders, so the React app
  needs it as a structured array, not a comma string.
- **C6** loses one of its two spellings. With `load_excel_results()` and
  `wmccimport` retired, only `api.py` writes `place=0`; `wmccimport`'s `None`
  writes disappear. `fix_small_races()` still filters `place__gt=0` and
  `score()` still tests `if not result.place`, so 0-vs-NULL still needs one
  answer — but it is now a one-writer problem, not a three-writer archaeology
  dig. Same for `Rider.dob`'s `1970-01-01` sentinel.
- **C9** is resolved by retirement: the plaintext secret column goes with the
  withdrawn AusCycling polling. Revisit when the new provider's credentials are
  designed — ideally in the environment or a secret store, not a model field.

### Tier D — Judgement calls

The briefing above resolved some of these and reopened others. The current list
of open decisions is consolidated in
[*Decisions this briefing created*](#decisions-this-briefing-created); what
follows are the model-layer questions that remain.

1. **A1 (pointscale config):** confirmed as a deliberate WMCC-only quick fix.
   Recommended resolution — wire `score()` to its own fields and store WMCC's
   scale as data, so behaviour is unchanged for the only club and the
   decorative-fields landmine is removed. Alternative: delete the fields and
   state the WMCC-only assumption in the model docstring. Either way, do not
   leave five editable fields that do nothing.
2. **A2 (inverted choices):** still needs fixing, but as **one** migration
   together with the new AusCycling category set — not twice.
3. ~~A6/A7 (broken ical ingest)~~ — **resolved by retirement**; the production
   `icalurl` question is moot once the code is gone.
4. **C4:** `RacePrototype` is deleted by the retirement pass. `Race.grading`
   survives — see the note under C5, it is the grade set the race-day entry
   screen renders per race, and the React app will need it in a structured form.
5. **C7:** keep `django.contrib.auth.User` (no `AUTH_USER_MODEL` swap) through
   this modernization; a custom user model is post-cutover work. Recommended.
6. **B8:** should bib numbers be unique per race (not per race+grade), and
   nullable-or-allocated? That decides whether the three "increment to avoid
   clash" hacks can be deleted.
7. **New, from the briefing:** with WMCC the only club, how much of the
   multi-club abstraction (`Club.manage_*` flags, per-club `ClubGrade`,
   `UserRole`/`ClubRole`, global `ClubRole` naming) should stay generic versus
   be simplified? My recommendation: keep the schema as-is — it costs nothing
   and re-shaping it is risk without user-visible gain — but stop *designing*
   for multi-tenancy in the API layer.

---

## Part 2 — Should we scrap the API?

**Yes — with one exception, and the exception is the most important thing in
Phase 2.**

*Correction to the first draft of this section.* It originally argued "scrap it,
there is no consumer to stay compatible with" because the only clients in the
repository are `cabici.js` (588 lines), `riders.js` (81 lines) and the templates,
all deleted in Phase 4. That was **wrong**: the race-day entry application is
external to this repo, and it is the app's only rider-creation path today. The
general conclusion survives — everything except the race-day contract should be
rebuilt, because adapting it would touch ~100% of the file while inheriting every
inconsistency, and there is no client for those parts. But `POST /api/raceresults/`
(and the `riders.xlsx` export that feeds it) must be treated as a **frozen
external contract** unless the entry app itself is brought into scope.

So the question is no longer "adapt or scrap?" — it is
**"what is the boundary between the part we throw away and the one contract we
must reproduce?"** Everything below that boundary is free.

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

Scope is everything **below** the race-day contract; that one endpoint is handled
separately in 2.2 because it is frozen either way.

| | Adapt `api.py` | Rebuild |
|---|---|---|
| URLs | Change anyway (`/api/v1/`, routers) | New |
| Serializers | Rewrite anyway (naming, `__all__`, 5 missing models) | New |
| Filters | Replace `?select=`/`?count=`/`?prefix=` anyway (React needs composable filters) | New |
| Permissions | Redesign anyway (C3 + the unguarded `.rider`) | New |
| Result upload | Move into a service, add atomicity, add permissions, fix A8/A9 | **Same work** — frozen contract, reproduced once |
| Tests | 790 lines tied to the old shapes; rewrite with the endpoints | New (upload tests become the spec) |
| Compatibility burden | Only for the race-day endpoint | Only for the race-day endpoint |

So adaptation buys nothing: the one place it would have helped is the one place
where the shape is fixed by an external client and must be reproduced exactly —
and that reproduction is needed in either case. Every other row is a rewrite.
The 80% coverage of `api.py` measures the old shapes, not reusable ones.

### The live race-day contract

Reconstructed from `origin/master` (the routes are already gone from the
`modernization` branch — removed in `b5bd661 remove view references`), plus
`tests/result-upload.json`, which is the only in-repo artefact of the payload:

| Step | Master route | Notes |
|---|---|---|
| 1 | `POST /api/token-auth/` | DRF **token** auth — so token auth is in production use by an external client |
| 2 | `GET /clubs/<slug>/riders.xlsx` | `urls.py` comment: *"get rider csv file for race entry front end"*; `ClubRidersExcelView` builds the 13-column sheet and comments *"eventno won't be used but the java desktop app requires a number"* |
| 3 | `POST /api/raceresults/` | `{race, entries[], riders[]}` → `{message, errors, ridermap}` |
| 4 | `GET /api/riders/?prefix=` | typeahead autocomplete (`riders.js`) |

Payload shape, verified against the sample file:

```jsonc
{
  "race": 1,
  "entries": [                       // 12 in the sample
    { "rider": 2930,                 // existing Rider.id, or "ID…" temporary key
      "grade": "B", "number": "1", "place": 2,
      "dnf": false, "grade_change": true }   // ← server compares to "y": see A9
  ],
  "riders": [                         // new and updated riders
    { "id": "ID123", "first_name": "Caleb", "last_name": "Ewan",
      "email": "…", "clubslug": "OGE", "licenceno": "123456",
      "member_date": "2019-12-31", "member_category": "race",  // ← dropped: see A8
      "phone": "…", "gender": "M", "dob": "1997-12-03" }
  ]
}
```

Response: `{"message": "race results uploaded", "errors": [...],
"ridermap": {"ID123": 4521, ...}}` — the temporary→real ID map is how the client
resolves a rider it invented moments before submitting.

**Why this matters more than anything else in the review.** This one endpoint is
the app's only remaining rider-creation path, it is invoked live on race day,
it is the piece with no permission class and no transaction, and it is the piece
whose semantics (`member_category`, `grade_change`) the new membership system and
the A8/A9 defects touch directly. It should be the **first** thing designed in
Phase 2, not the last — everything else is ordinary CRUD that can follow.

### What to salvage (do not lose this domain knowledge)

- **`tests/result-upload.json` + `testapi.py`'s upload tests (790 lines total)**
  as the executable specification of the contract above. Mine them before
  rewriting; the sample payload is the only record of the external client's
  shape that exists in this repo.
- **The `ridermap` temporary-ID mechanism.** Non-obvious, load-bearing, and easy
  to lose in a rewrite. Reproduce it deliberately.
- **The XLS rider export** (`ClubRidersExcelView`, 13 columns) — until the entry
  app is replaced. This is why `pyexcel` is *held*, not dropped, in the
  retirement pass.
- **The delta-sync idea** (`?changed=<unix>`) — a genuinely good feature for a
  4k-row rider list. Re-express as `?updated_after=<iso8601>` + `ETag`.
- **`ClubOfficialPermission`'s intent** (safe methods open; writes need club
  affiliation) — right logic, wrong implementation (unguarded `.rider` → 500).
- **`StandardResultsSetPagination`** (200/page, max 1000) — sensible defaults.
- ~~The AusCycling validation hook~~ — **withdrawn**; retire it now, and design
  the replacement against the new provider when its spec lands.

### Revised Phase 2

Contract-first, and the race-day contract first:

1. **2.0 Retirement pass** *(new, from the briefing)* — delete the ingest
   pipelines, the withdrawn AusCycling polling, the tidyhq/IMG import paths,
   `load_excel_results`, `RacePrototype` and the dead tests/cassettes
   (~2,400 lines, 6 dependencies). Resolves A4–A7 by removal. Do this before
   anything else: it shrinks every subsequent estimate.
2. **2.1 Model hardening** — A1 (wire the pointscale config), A3 (fix or drop
   `get_absolute_url`), Tier B constraints, then C1 (merge `usermodel.py` →
   `models.py`) and C2 (extract `services.py`). A2 is deferred to the membership
   migration. Must precede serializers: the API surface follows the domain model.
3. **2.2 Race-day contract design** — decide the entry app's fate, then specify
   `POST /races/{id}/results/` and the rider export as a frozen, documented,
   permission-checked, atomic contract, with A8/A9 resolved.
4. **2.3 Remaining resource model + OpenAPI contract** — derive the rest from the
   domain: one identifier per concept, explicit representations, filters as
   `django-filter` `FilterSet`s. Publish the spec, generate the TypeScript client.
5. **2.4 Auth** — JWT + refresh for the React app; **keep token auth alive**
   until the race-day client is retired (or until 2.2 says otherwise).
6. **2.5 Core CRUD** — routers + ViewSets under `/api/v1/`, query optimisation
   (C11), pagination and permissions everywhere.
7. **2.6 Docs, exports, test rebuild** — drf-spectacular, CSV/XLS exports as
   service-backed actions, coverage ratcheted 42 → 60 → 80.
8. **2.7 Delete `api.py`** once the new package covers the surface.

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

# A8: member_category is sent by the client, dropped by the server
import json
payload = json.load(open("races/apps/cabici/tests/result-upload.json"))
assert "member_category" in payload["riders"][1]        # client sends it
# api.py hardcodes it instead:
#   line 694: Membership(..., category="race")
#   line 757: Membership(..., category="race", ...)
# test_upload_results asserts email/phone/dob/gender/club - never category

# A9: grade_change type mismatch
{str(e.get("grade_change")) for e in payload["entries"]}  # -> {'None','True','False'}
# api.py:821 -> if ... and entry["grade_change"] == "y"

# The live race-day contract (routes exist on master only)
# $ git show origin/master:races/apps/cabici/urls.py | grep -n xlsx
#   62: re_path(r'^clubs/(?P<slug>[^/]*)/riders.xlsx$',
#               views.ClubRidersExcelView.as_view(), name='club_riders_excel')
#   61: # get rider csv file for race entry front end
#   35: re_path(r'^races/(?P<slug>\w+)/(?P<pk>\d+)/results/$',
#               views.RaceUploadExcelView.as_view(), name='race_results_excel')
# in-repo JS never builds the upload payload:
# $ git grep -n "entries:" origin/master -- "*.js" "*.html"   -> no results
# => the client is external (the "java desktop app" referenced in
#    ClubRidersExcelView, whose comment notes it requires a numeric eventno)

# load_excel_results has no production caller

# $ grep -rn "update_from_tidyhq" races                                      -> def only
# $ grep -rn "load_excel_results" races --include=*.py | grep -v tests/
#   races/apps/cabici/models.py:645:    def load_excel_results(...)   (definition only)
# dependency census after the retirement pass:
#   requests -> imported only in auscycling.py
#   pytz     -> models.py:25 import, :420 pytz.timezone() inside ingest_ical()
#   icalendar/ngram -> ingest paths only (ngram also ClubManager.closest,
#                     reached only by load_excel_results)
#   bs4      -> races/ingest/*, parse_img_members(), harvestclubs
#   vcrpy    -> tests/testingest.py only

# Tier A census after the briefing: 9 findings
#   fix: A1, A3   defer: A2 (with the membership migration)
#   retire: A4, A5, A6, A7   decide-then-fix: A8, A9

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
