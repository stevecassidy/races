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

> **Read the revisions first.** The evidence in Parts 1 and 2 stands, but the
> *dispositions* changed three times on 2026-10-11 as the owner briefings landed.
> **The third revision is the operative one** — where anything below contradicts
> it, the third revision wins. See
> [Third revision](#-third-revision-angular-is-live-react-is-not)
> immediately below, then the earlier revisions it corrects.

---

## ⚠️ Third revision — Angular is live, React is not

The briefing that settles the client question: **the Angular app is what is
actually deployed on race day** (old, reliable, in production), and **the React
rewrite is unfinished and predates the server-side modernization work**. The
monorepo is confirmed, and **same-origin deployment (Django serves the SPA
builds) is decided for now**, with a split left open later.

### My "urgent data loss" claim was wrong — retracted

The second revision warned that D1–D3 might be losing race data *today* and
recommended an out-of-band hotfix. That was wrong, and the cause is worth
recording because it is a reasoning error rather than a missing fact: I treated
the only client I could find in the tree as the deployed client.

- **D1/D2 do not affect production.** They are in the *unfinished React* app.
  Angular — the deployed system — maps internal `newriders` state to the wire key
  `riders` and reads entries back with `getRider(e.riderid)`. Both correct.
- **No hotfix is needed.** Nothing is losing rider data or wiping meetings at
  race time.
- **D3's server-side half still stands.** Independent of any client, the upload
  endpoint has no permission class and no transaction, so *any* authenticated
  user can replace a race's results and a mid-request failure leaves the race
  half-populated. That is a Phase 2 fix, not an emergency, and it is why the
  endpoint needs an explicit overwrite contract rather than silent replace-all.

### A9 is the one live production bug, and A8 is not

Re-reading both clients against the server separates these cleanly:

| | Who sends it | Status |
|---|---|---|
| **A9** `grade_change` | **Angular (deployed)** — `entry.ts:10` `grade_change: boolean = false`, forwarded verbatim into the payload (`entry.service.ts:240`) | **Live production bug.** `api.py:821` compares `== "y"`, so the comparison never matches and **in-race grade changes have never applied in production**. Low severity (no data loss; riders keep their recorded grade) but real, and it has been silently no-oping since the Angular app shipped. |
| **A8** `member_category` | **React only** — Angular's payload builder sends exactly `id, first_name, last_name, email, clubslug, licenceno, member_date, dob, gender, phone` and **no `member_category`** | **Forward requirement, not a production bug.** It becomes relevant when the React app is finished. |

The `"y"` is template-era residue: `forms.py` had a `ChoiceField` whose values were
`'y'`/`'n'`, and the API inherited the comparison after the form layer was
deleted. So this is a genuine server bug that both clients trip over.

### The finding that outranks all of the above: the post-AusCycling workflow already exists, client-side, unsupported

The React app ships `MembershipVerificationDialog` (105 lines) and
`membershipUtils` (`isCurrentMember`, `needsMembershipVerification`,
`isValidMemberDate`, `getEffectiveMemberDate`) — a complete **manual,
at-the-track membership verification** flow: when a rider isn't current, the
race director enters the expiry date from their card and it is sent upstream as
`verifiedMemberDate`.

The server has **zero support for any of it**:

- `grep -rn "verifiedMemberDate\|verified_member" races --include="*.py"` → **no
  matches**. The field is dropped on upload, exactly like `member_category` (A8).
- Angular has none of this either — it just stamps `member_date` to year-end or
  today (`new-rider-dialog.component.ts:70-78`). No verification concept at all.
- Meanwhile the AusCycling polling that *was* the verification mechanism has been
  **withdrawn** (fact 2), and its replacement provider has no spec yet.

So the app currently has **no membership verification whatsoever** in production,
and the unfinished React client contains the design for the interim one. This
splits the membership work in 2.1 into two tracks with very different blocking
status:

- **(a) Local verification — unblocked, do now.** Store a verified date,
honour `member_category` and `verifiedMemberDate` on upload, expose membership
as a resource. No provider dependency. This is the workflow race directors
actually need today, and it is what makes the React app finishable.
- **(b) Provider integration — blocked** on the new API provider's spec. Design
  the seam (a `MembershipSource` interface or equivalent) so (a) can be
  supplemented rather than rewritten when the spec lands. Do **not** hold (a)
  hostage to (b).

That also revises the earlier "fix A2 when the new categories land" instruction:
the inverted `MEMBERSHIP_CATEGORY_CHOICES` tuple (A2) is a **live bug in the
admin** today — writing `'Race'` makes a membership invisible to the seven
`category="race"` sites — and it should be fixed with track (a), not deferred to
an unspecified provider date. Adopting the new category vocabulary can follow
later as a second migration; the inversion should not wait.

### What same-origin actually commits us to

Decided: Django serves both SPA builds on one origin, split later if warranted.
Concrete consequences, several of which are easy to miss until cutover:

| Consequence | Detail |
|---|---|
| **CORS disappears entirely** | `corsheaders` app, `CorsMiddleware`, `CORS_ALLOW_ALL_ORIGINS`, `CORS_URLS_REGEX`, `CORS_ALLOW_METHODS` all go. Phase 2.4's "scope CORS to the frontend origin" becomes "delete CORS"; Phase 4's "Update DNS/CORS settings" task disappears. Also removes a whole class of credential/CORS preflight bugs from Phase 4. |
| **Refresh token can be an httpOnly cookie** | Resolves the standing "memory vs httpOnly cookie" question: access token in memory, refresh in an httpOnly SameSite cookie. Requires CSRF protection for cookie-authenticated writes (DRF's `SessionAuthentication` does this; a cookie-JWT class must too). Worth revisiting whether JWT is needed at all vs Django sessions now that we are same-origin — recommendation: keep JWT (stateless, works for non-browser clients, cleaner generated client) but stop treating bearer-in-`localStorage` as an option. |
| **Two apps, one origin ⇒ path allocation is mandatory** | `apps/raceday` must mount under a subpath (e.g. `/raceday/`). The React app is **not** configured for this: `vite.config.ts` sets no `base`, `App.tsx` uses `<BrowserRouter>` with no `basename`, and it has a catch-all `<Route path="*" element={<Navigate to="/login"/>}>`. The PWA service worker scope must be narrowed to the subpath too. Real 2.2 work, not a deploy-time detail. |
| **`ManifestStaticFilesStorage` fights Vite's hashing** ⚠️ | Vite already emits content-hashed filenames. Django's manifest storage re-hashes them and rewrites references inside collected CSS/JS **but not inside `index.html`** (served as a template), so the asset URLs break at cutover. Manifest hashing adds nothing for already-fingerprinted files. Resolution: `whitenoise.storage.CompressedStaticFilesStorage` (compression, no rewriting) for the SPA assets, keeping manifest hashing only if Django's own static needs it — plus a CI smoke test that loads the built `index.html` through `collectstatic`. This is the kind of thing that eats a day at 11pm before race day if it is discovered late. |
| **Dockerfile gains a Node stage** | Currently `python:3.14-alpine` with no Node. Needs a multi-stage build (node ⇒ `pnpm build`, copy `dist` into the Python image). And `.dockerignore` does **not** currently exclude `node_modules` (verified: zero matches) — it must, once `frontend/` lands. |
| **URL space is reassigned, not just cleaned up** | `/` is currently `HomePage` (a Django `ListView`); under same-origin it becomes the web SPA. `/admin/` and `/api/` stay. So Phase 4's "remove template views" becomes a **URL allocation** task: `/` → `apps/web`, `/raceday/` → `apps/raceday`, `/admin/`, `/api/`. |
| **allauth's email links must point into the SPA** | Password-reset and email-confirmation URLs are rendered as absolute links from templates. With the flows moving to SPA screens, they must resolve to SPA routes — needs allauth URL/adapter configuration, not just endpoint work. Currently untasked anywhere; added to 2.4. |
| **Flatpages need a home** | `FlatpageFallbackMiddleware` + the `/` flatpage back the current home page content. With `/` owned by the SPA, either expose pages as a resource (`GET /api/pages/<path>/`) or reorder the middleware. Small, but it must be decided. |

### Angular's status: production system and executable specification

Angular 8 / TypeScript 3.5, 5,164 lines, 11 components, last touched 2022 — and
**it is the thing that runs race day**. It is also the only remaining record of
correct upload/download semantics. Recommendation:

- **Keep it deployed and untouched** until `apps/raceday` is finished against the
  new API. It is reliable; there is no urgency to move it off its own stack.
- **Do not vendor it as a buildable app.** Building Angular 8 in this repo's CI
  is cost with no benefit, and a third race-day implementation in the tree invites
  the question "which one is live?" at the worst time.
- **Do extract its wire semantics into the repo as documentation** — the
  `_buildUploadPayload()` field list and the `getRider(e.riderid)` download
  mapping, committed under `docs/` with the source file referenced. That is the
  specification the new contract must satisfy, and it should not depend on a
  sibling checkout surviving.
- **Design the new results endpoint to accept what Angular sends.** This is the
  useful part of the earlier "frozen contract" idea, correctly attributed: the
  frozen contract exists, it is the Angular app, and it happens to be *right*.
  Keeping the API Angular-compatible means the deployed system keeps working
  through the whole of Phase 2 and 3, and retirement becomes a clean deletion
  rather than a migration.

### Net effect on the phase plan

- **2.2** becomes "finish-ready vendoring": bring `apps/raceday` in, mount it on
  a subpath, fix D1/D2/D4 (client-side correctness, no longer urgent), keep D3's
  server-side hardening, and treat Angular's payload as the compatibility target.
- **2.3** the contract must be satisfiable by *both* Angular (unchanged,
  deployed) and the React app (evolving in-repo). The generated client serves the
  React side; Angular is the regression baseline.
- **2.1** membership splits into track (a) unblocked now and track (b) blocked on
  the provider; **A2 is fixed now**, not deferred.
- **2.4** deletes CORS, adds the allauth-link-into-SPA task, and settles token
  storage as httpOnly cookie + in-memory access.
- **Phase 4** gains: multi-stage Docker with a Node build, the
  static-storage/manifest trap and its CI smoke test, `.dockerignore`
  `node_modules`, URL-space allocation, flatpage disposition, and **Angular
  retirement** as an explicit cutover gate.
- **New open question (much smaller than before):** does `apps/web` (the SPA
  replacing the Django template screens) get built on the unfinished React app's
  codebase, or start fresh with the React app mined for parts? Its stack is
  already the chosen one, and it is ~70% of Angular's surface (3,724 vs 5,164
  lines, 8 pages/components vs 11 components), so building on it is probably
  right — but it predates all the server work, so it should be assessed rather
  than assumed.

---

## ⚠️ Second revision — the race-day client is in-house React

The briefing added two facts that overturn the "frozen contract" framing: the
race-day app **was rewritten in React in-house**, and the decision is to
**bring it into this repository** alongside the SPA that will replace the Django
views.

Both repos are on this machine, so this revision is based on reading the actual
client rather than inferring it from the server:

| Artefact | Location |
|---|---|
| Race-day React app (current) | `../cabici-raceday-react` — `stevecassidy/cabici-raceday-react`, Vite + React 18 + TS + MUI + pnpm, Vitest, PWA/offline, Sentry. Last commit 2026-09-05; upload feature landed 2026-08-29 (`c2e029c`) |
| Angular predecessor (reference) | `../cabici-race-manager-owen` — remote `stevecassidy/cabici-raceday`, Angular 8 + Material |
| Its own context doc | `PROJECT_CONTEXT.md`: *"React 18 rewrite of Angular 8 race management application … Backend API remains unchanged (separate repository)"*, *"in regular production use"* |

### This overturns the "frozen contract"

> **Partly corrected by the third revision.** The XLS finding stands. But
> "token auth can be deleted" does not — **Angular is the deployed client and it
> uses token auth**, so it survives until Angular retires. And the contract is not
> wholly co-designed either: it must keep **accepting what Angular sends
> unchanged**, which is a real compatibility binding, just a correctly attributed
> one (in-house, and right — unlike the React app's D1/D2).

The first revision concluded that `POST /api/raceresults/` and
`GET /clubs/<slug>/riders.xlsx` were a **frozen external contract** to be
reproduced byte-compatibly. Wrong on both counts:

- **The client is in-house and updatable**, so the contract is *co-designed*, not
  frozen. Token auth can be deleted rather than preserved, and the API can be
  shaped around what the React app actually needs.
- **The XLS export has no live consumer.** `grep -rn "xlsx|xls\b|octet-stream|blob"
  src index.html public` across the React app returns **nothing** — it fetches
  riders as JSON via `/api/riders/` (paginated) and `?changed=` (delta). The
  `riders.xlsx` route and its *"the java desktop app requires a number"* comment
  belong to the superseded desktop workflow. **`pyexcel`, `pyexcel-xls` and
  `openpyxl` can go in the retirement pass after all** — the first revision's
  "hold pyexcel" instruction is rescinded.

And freezing it would have been actively harmful, because the contract as it
stands carries **two silent data-loss defects** (D1, D2 below). A frozen contract
would have preserved them in the new API by design.

### D1–D4: what reading the real client revealed

| # | Finding | Evidence |
|---|---|---|
| **D1** | **CRITICAL in the React app; NOT live in production** (third revision) — new riders are silently dropped on every upload. The React app sends the key `newriders`; `api.py:654` reads `data.get("riders", [])`. Reproduced against the real API with the app's exact payload shape: `ridermap: {}`, `errors: ["Ignored result record with unknown temporary rider ID (A/8)"]`, HTTP **200**, message `"race results uploaded"`, and `Rider` count for the new rider **0**. | React `src/context/EntryContext.tsx:59` builds `newriders: newRiders`; server reads `"riders"`. **This is a React regression** — the Angular `_buildUploadPayload()` keeps `newriders` as *internal* state name and maps it to `payload.riders` on the wire (`entry.service.ts:261`). The rewrite copied the state name into the wire format and dropped the mapping step. `git log -S newriders` in races-git across **all** branches: no hits — the server never accepted it. |
| **D2** | **CRITICAL in the React app; NOT live in production** (third revision) — downloading existing entries always yields nothing. `GET /api/raceresults/?race=N` returns `rider` as a **display string** (`"Jane Known"`) and the ID as `riderid`; the React app looks riders up by `String(entry.rider)` in a map keyed by `rider.id`. Reproduced: `riderMap.get(String(entry.rider)) -> None`, so every row is skipped. `grade_change` is absent from the response entirely, so it also resets to `false`. | React `EntryContext.tsx:211-224`. **Also a React regression** — Angular used `this.ridersService.getRider(e.riderid)` (`entry.service.ts:199`). |
| **D3** | **D1+D2 compound into result destruction.** *Client half not live; the server half (no permission class, no transaction) is a genuine defect independent of any client.* The upload deletes every result for the race and re-inserts only what the payload contains. A clerk whose app downloaded an empty sheet (D2), adds one rider and uploads, **wipes the whole meeting's results** — and pointscores are recalculated over the wiped set. Reproduced: 3 results → upload 1 → **1 result remains**, HTTP 200, no conflict signal. The server has no `If-Match`/version check and the app's `uploadedSignaturesByRace` guard is per-session client state, which does not survive a reload or a second device. | probe output in [Verification](#verification) |
| **D4** | **The React app discards the server's `errors` array** (React-only, so not live). `EntryService.uploadEntries()` returns only `ridermap`; `errors` is never read, so D1's "Ignored result record" messages are invisible to the race director. | `src/services/EntryService.ts:17-42` |

**A9 is also confirmed, and it is older than React.** Both SPAs send
`grade_change` as a JSON boolean (Angular `entry.ts:10`, React `models.ts:85`);
`api.py:821` compares `== "y"`. So in-race grade promotions have never worked
through the API — the `"y"` is template-era residue. **A8** (`member_category`
dropped) is likewise confirmed and now matters more, since the React
`Rider` type carries both `member_category` and a `verifiedMemberDate` field
commented *"sent to server on upload"* that the server has never handled.

### Why the drift happened — and the one-line lesson for the plan

Two repos hand-maintained the same wire format, and **neither side's tests could
catch the mismatch**:

- races-git: `test_upload_results` posts a fixture JSON built with the server's
  own key (`riders`), so it passes forever.
- cabici-raceday-react: `results-upload.integration.test.tsx` **mocks
  `EntryService.uploadEntries`** and asserts the app's own payload; 23/23 green.

Every layer mocks the layer below it. This is the concrete argument for
contract-first with a **generated client**: if the React app had imported types
and a client generated from the server's OpenAPI schema, `newriders` would not
have compiled. It is also the argument for vendoring: one repo, one CI run, one
contract test that exercises both ends.

### What changes in the plan

1. **Monorepo, decided.** `frontend/` workspace root with `apps/raceday` (the
   vendored React app), `apps/web` (the SPA replacing the Django views) and
   `packages/api-client` (generated from the schema). This finally resolves the
   standing contradiction between the instructions (*"future `cabici-frontend/`
   directory"*) and PLAN §3.1 (*"Recommended: separate repository"*). Phase 3.1
   is updated.
2. **2.2 is no longer "reproduce a frozen contract"** — it is *vendor, audit,
   then co-design*. The Angular repo becomes the reference implementation for
   the upload/download semantics the React rewrite lost.
3. **Token auth is deleted, not retained** (2.4). The only token-auth client is
   now in-house and updated in the same repo, in the same cutover.
4. **The offline requirement is now a first-class API constraint.** The React app
   is a PWA that caches the full rider list in `localStorage` and refreshes with
   `?changed=<unix>`; that is load-bearing at a velodrome with poor reception.
   `?updated_after=` must preserve delta sync **and** pagination **and** survive
   the app's merge-by-id logic. Do not trade it for `ETag`-only caching.
5. ~~**New urgent question:** which client is live on race day?~~ — **Answered by
   the third revision: Angular.** No live data loss and no hotfix; the React app's
   D1/D2 defects become ordinary fix-on-vendoring work.

### ~~Urgent: the hotfix decision~~ — **retracted by the third revision**

This section proposed an out-of-band hotfix for D1/D2 on the assumption that the
React app was the deployed client. **It is not** — Angular is deployed and maps
both correctly — so there is no live data loss and no hotfix. It is retained
because the reasoning error is instructive (see the third revision) and because
two elements survive as ordinary Phase 2 work:

- the upload endpoint needs an explicit overwrite contract instead of silent
  replace-all, plus `transaction.atomic()` and a permission class — a genuine
  server defect independent of any client;
- when `apps/raceday` is finished, D1/D2 are two one-line client fixes.

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
without a fix, and it takes **2,742 measured lines** with it (see
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
deleted features. Line counts are **measured on the current branch** (after the
Phase 1 formatting pass), not estimated:

| Retire | Lines | Evidence |
|---|---|---|
| `races/ingest/` entirely (lacc, penrith, waratahs, csvingest) | 384 | fact 1; only `manage.py ingest` and the disabled tests reach it |
| Commands: `ingest`, `csvingest`, `harvestclubs`, `loadusers`, `wmccimport` | 645 | one-off historical imports / scrapers |
| `auscycling.py` (169) + `validate_memberships.py` (136) + `Club.validate_membership()` (72) | 377 | fact 2 — withdrawn pending a new provider |
| `Club.auscycling_client_id/_secret/_club_id`, `Membership.last_validated`/`validation_error` | 5 fields | same; also removes the plaintext-secret finding C9 |
| `Race.load_excel_results()` | 168 | **only** callers are 4 tests in `testresults.py`; the production caller `RaceUploadExcelView` exists on master and is gone here |
| `RiderManager.update_from_tidyhq_spreadsheet()` (255) + `parse_img_members()`/`IMG_MAP` (49) | 304 | tidyhq app already removed (`f5d37e4`) |
| `save_rider()` (Strava callback) | 27 | never registered as an allauth pipeline |
| `RacePrototype` | 15 | never referenced outside its own migration (closes C4) |
| `ClubManager.closest()` + `RaceCourseManager.find_location()` | 22 | sole users of `ngram`; every caller is retired above, so both managers reduce to `models.Manager` |
| Three unrouted export views in `views.py` (`club_riders_csv_view`, `ClubRidersExcelView`, `RaceSummarySpreadsheet`) | 200 | **already unrouted on this branch**; the live React client uses none of them |
| `tests/testingest.py` (230), `imgsampledict.py` (370) | 600 | tests the code they cover no longer exists (closes A7) |
| 7 VCR cassettes in `fixtures/vcr_cassettes/` | 428 KB | unused once `testingest.py` goes |
| `Club.icalurl`, `Club.icalpatterns` | 2 fields | ingest-only |
| **Dependencies**: `icalendar`, `ngram`, `beautifulsoup4`, `requests`, `vcrpy`, `pytz`, `pyexcel`, `pyexcel-xls`, `openpyxl` | 9 packages | each verified used only by code deleted in this pass |
| **Total Python lines removed** | **2,742** | plus 5+2 model fields, 428 KB of cassettes, 9 dependencies |

**Keep, but move into `services/`** (these encode real domain rules):
`PointScore.score()`/`tally()`/`recalculate()`, `Race.tally_pointscores()`,
`fix_small_races()`, `Club.allocate_officials()`/`promotion()`/`performancereport()`,
`Rider.classification()`.

**Correction (Second revision): `pyexcel` is *not* held.** The three export views
in `views.py` (`club_riders_csv_view`, `ClubRidersExcelView`,
`RaceSummarySpreadsheet`) are **already unrouted on the `modernization` branch**
— unreachable — and the live React client uses none of them (no `xlsx`/`blob`
reference anywhere in its source; it fetches riders as JSON). So the spreadsheet
stack retires with the rest of the pass. If any of the three exports is still
wanted for humans or the desktop workflow, it comes back as an explicit
`services/exports.py` + action endpoint in 2.5, not as inherited dead code.

### Decisions this briefing created

> Superseded where relevant by the **Second and Third revisions**: decision 1 is
> answered (in scope, vendored, and the deployed client is Angular), and the XLS
> export is retired rather than held.

1. ~~Is the race-day front end in scope?~~ **Answered: yes, and it moves into
   this repo.** Consequences — the contract is co-designed not frozen, token auth
   is deleted not retained, and the XLS export disappears (no live consumer).
   ~~**New question in its place: which client is live on race day?**~~ —
   **Answered by the third revision: Angular.** No live data loss, no hotfix.
2. **Membership categories are blocked on the new AusCycling spec.** Don't ship
   two migrations: fix the inverted tuple (A2) *as part of* adopting the new
   category set, in one migration. The upload payload already carries
   `member_category` (A8) and the React app also sends a `verifiedMemberDate`
   the server has never handled — settle all three together. Historical note:
   the Angular app once used a `'trial'` category (`2e838ef Change membership
   types`, 2022), so this vocabulary has churned before; pin it in the schema
   rather than letting clients invent values.
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
| A8 | **The upload endpoint silently drops `member_category`** — and, more importantly, **the entire `verifiedMemberDate` mechanism**. The React app ships a complete manual at-the-track membership verification flow (`MembershipVerificationDialog`, `membershipUtils`) that sends `verifiedMemberDate`; `grep -rn "verifiedMemberDate\|verified_member" races --include=*.py` returns **nothing**. Angular sends neither field. | `api.py:694,757` | **Forward requirement, not a production bug** (third revision). Becomes load-bearing when the React app is finished, and it is the core of *track (a)* of the membership work — which is **unblocked** and should not wait for the new provider. |
| A9 | **⚠️ LIVE PRODUCTION BUG — `grade_change` never applies.** Both clients send a JSON boolean; `api.py:821` compares `== "y"`. Angular (deployed) forwards it verbatim (`entry.service.ts:240`), so **in-race grade changes have never worked in production**. The `"y"` is template-era residue from a `ChoiceField` whose form layer was deleted. | `api.py:821` | **Fix now-ish in Phase 2.1/2.2** — low severity (no data loss; riders keep their recorded grade) but it is the one genuine live bug this review found. |

A1 and A2 change computed results or stored data. **A9 is the one live
production bug** in the review; **A8 is a forward requirement** that gates
finishing the React client and is the substance of the unblocked half of the
membership work (third revision). A8 and A9 were both found only by reading the
actual clients rather than inferring them from the server.

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

> **Superseded in part by the Second revision.** The shape below is accurate as
> far as it goes, but two readings were wrong: the XLS export (**step 2**) has
> **no live consumer** — the React app fetches riders as JSON — so it retires
> rather than freezes; and the contract is **co-designed**, not frozen, because
> the client is in-house. Most importantly, the payload as the current client
> actually sends it is broken in two ways (**D1** `newriders` vs `riders`, **D2**
> `rider` vs `riderid`) that this pass could not see, because it was reading the
> server side only.

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

- **The Angular `_buildUploadPayload()` / download mapping**
  (`../cabici-race-manager-owen/src/app/services/entry.service.ts`) — the
  **reference implementation** of the upload semantics. It maps internal
  `newriders` state to the wire key `riders`, and reads entries back via
  `e.riderid`. The React rewrite lost both. Restore them from here, not from the
  server code.
- **`tests/result-upload.json` + `testapi.py`'s upload tests (790 lines)** as a
  partial specification of the round trip. **Caveat:** this fixture encodes the
  *server's* key (`riders`), not what the live client sends (`newriders`) — which
  is precisely why D1 survived both test suites.
- **The `ridermap` temporary-ID mechanism.** Non-obvious, load-bearing, and the
  first thing to break when the payload key drifts (D1). Reproduce it deliberately.
- ~~The XLS rider export (`ClubRidersExcelView`, 13 columns)~~ — **retired**, not
  held. The React app never calls it; it belonged to the superseded Java desktop
  workflow. `pyexcel`, `pyexcel-xls` and `openpyxl` drop in the retirement pass.
- **The delta-sync feature** (`?changed=<unix>`) — not merely a good idea: it is
  **in live use** by `RiderService.loadChangedRiders()`, on top of a full
  paginated load and a `localStorage` cache, in a PWA built for velodromes with
  poor reception. It is a hard API requirement, not a nice-to-have: preserve
  delta sync + pagination + merge-by-`rider.id` when re-expressing it as
  `?updated_after=`.
- **`ClubOfficialPermission`'s intent** (safe methods open; writes need club
  affiliation) — right logic, wrong implementation (unguarded `.rider` → 500).
- **`StandardResultsSetPagination`** (200/page, max 1000) — sensible defaults.
- ~~The AusCycling validation hook~~ — **withdrawn**; retire it now, and design
  the replacement against the new provider when its spec lands.

### Revised Phase 2

> **Superseded by the Second revision**, which reorders this as: 2.0 Retirement
> pass → 2.1 Model hardening → **2.2 Monorepo scaffold + vendor & audit the
> raceday app** → 2.3 Resource model & contract covering *both* clients → 2.4
> Auth (JWT only; token auth deleted, not retained) → 2.5 CRUD → 2.6 Docs → 2.7
> Tests + delete `api.py`. `MODERNIZATION_PLAN.md` carries the task lists.

Contract-first, and the race-day contract first:

1. **2.0 Retirement pass** *(new, from the briefing)* — delete the ingest
   pipelines, the withdrawn AusCycling polling, the tidyhq/IMG import paths,
   `load_excel_results`, `RacePrototype` and the dead tests/cassettes
   (2,742 measured lines, 9 dependencies). Resolves A4–A7 by removal. Do this before
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

# ---------------------------------------------------------------------------
# Second revision: the race-day client, and D1-D4
#
# React app: /Users/Steve/projects/cabici-raceday-react (stevecassidy/cabici-raceday-react)
#   Vite + React 18 + TS + MUI + pnpm + Vitest + vite-plugin-PWA + @sentry/react
#   last commit 2026-09-05; upload feature c2e029c (2026-08-29); payload key
#   introduced by c338416 "implement upload/download of entries"
# Angular reference: /Users/Steve/projects/cabici-race-manager-owen (cabici-raceday)
#
# No XLS consumer in the live client:
#   $ grep -rn "xlsx\|xls\b\|octet-stream\|blob" src index.html public   -> nothing
#
# D1 - key mismatch, reproduced against the real API with the app's payload shape:
#   POST /api/raceresults/ {race, entries[... "rider":"ID9001" ...], newriders:[...]}
#   -> 200 {'message': 'race results uploaded', 'ridermap': {},
#           'errors': ['Ignored result record with unknown temporary rider ID (A/8)']}
#   Rider.objects.filter(user__last_name='Rider').count()  -> 0   # never created
#   server reads: api.py:654  for record in data.get("riders", [])
#   client writes: EntryContext.tsx:59  newriders: newRiders
#   Angular does it right: entry.service.ts:261  payload.riders.unshift(r)
#
# D2 - download mapping, same probe:
#   GET /api/raceresults/?race=N -> keys ['club','dnf','grade','id','number',
#     'place','race','rider','riderid','usual_grade']
#   row['rider'] == 'Jane Known' (display string), row['riderid'] == 2
#   app: riderMap keyed by String(rider.id), looked up with String(entry.rider)
#      -> None, so every downloaded entry is skipped
#   Angular does it right: entry.service.ts:199  getRider(e.riderid)
#
# D3 - compound wipe, reproduced:
#   1st upload: 3 entries -> results in DB: 3 [('Ann',1),('Ben',2),('Caz',3)]
#   2nd upload: 1 entry   -> results in DB: 1 [('Ben',2)]   # Ann and Caz GONE
#   both HTTP 200, message 'race results uploaded', no conflict signal
#
# D4 - errors discarded: EntryService.uploadEntries() returns ridermap only
#
# Why neither test suite caught it:
#   races-git: test_upload_results posts result-upload.json, which uses the
#              SERVER key ('riders') - so it passes regardless of the client
#   React app: results-upload.integration.test.tsx does
#              vi.spyOn(EntryService, 'uploadEntries').mockResolvedValue(null)
#              and asserts the app's own payload -> 23/23 green, no real HTTP
#   => every layer mocks the layer beneath it
#
# A9 confirmed on both clients:
#   Angular entry.ts:10  grade_change: boolean = false
#   React   models.ts:85 grade_change: boolean
#   server  api.py:821   entry["grade_change"] == "y"      # template-era residue
#
# The three export views are unreachable on the modernization branch:
#   $ grep -n "club_riders_csv_view\|ClubRidersExcelView\|RaceSummarySpreadsheet" \
#       races/apps/cabici/urls.py        -> no matches
#   $ git show origin/master:races/apps/cabici/urls.py | grep -cE "xlsx|members.csv"
#       -> 3
```
