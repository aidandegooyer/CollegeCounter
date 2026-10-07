# Known Bugs & Issues Tracker

Found during automated code review on 2026-07-09. Re-verified against `main`
(`c9c3433`) on 2026-10-07; line numbers updated. Check items off as they're fixed.

> **Note (2026-10-07):** three items below were previously written as "Fixed…"
> (`proxy_image` SSRF, Sanity webhook secret, double Elo in the platform update
> functions). **None of those fixes are in the codebase** — no IP blocking in
> `proxy_image`, no `SANITY_WEBHOOK_SECRET` check, no `old_status` tracking in
> `update_*_match`. They were likely lost from an uncommitted branch/stash. The
> wording below now describes the bug and the intended fix.

## Critical — verified in source

- [x] **`cc-backend/v1/cc/public_views.py:567`** — *(fixed 2026-10-07: renamed to `status_filter`; regression test added)* local variable `status` shadows the DRF `status` module in `public_matches`; every validation-error path after it (lines 602–698) raises `AttributeError` and returns a 500 instead of a 400. Rename the local.
- [x] **`cc-backend/v1/cc/views.py:398`, `:2863`** — *(fixed 2026-10-07: treat missing/null winner as no winner; unmapped status defaults to `scheduled`; tests in `tests/test_regentsleague.py`)* `match_data.get("winner").get("id")` (import) and `winner_team.get("id")` (refresh) crash with `AttributeError` when the Regents League API omits `winner`, aborting the rest of the batch.
- [x] **`cc-frontend/v1/src/services/api.ts:28`** — *(fixed 2026-10-07: replaced with `await auth.authStateReady()`)* hardcoded 300 ms sleep in the auth interceptor on every production API request. It also didn't do its job: `currentUser` was read *before* the sleep, so first-load requests could still go out unauthenticated.
- [ ] ~~**`cc-frontend/v1/src/services/api.ts:511`** — Faceit API key hardcoded in the frontend bundle; also `views.py:2240` (Faceit) and `views.py:3841` (NWES fallback).~~ — WON'T FIX (2026-10-07): these keys are intentionally public; no rotation needed.
- [ ] ~~**`cc-frontend/v1/src/pages/Rankings/Rankings.tsx:392`** — player rankings render `rank={i}`~~ — FALSE POSITIVE: `PlayerRankingComponent.tsx:13` displays `rank + 1`.

## Elo integrity

Elo is applied by mutating `Team.elo` in place (`update_match_elos`,
`views.py:80`) with no record on the `Match` of whether/how much was applied.
That makes every code path below either double-apply, fail to revert, or depend
on a full recalculation to repair. See **Planned: Elo tracking on Match** below
for the fix that addresses most of these at once.

- [ ] **Double Elo on platform refresh** — `update_faceit_match` (`views.py:3051`), `update_leaguespot_match` (`:3213`), `update_regentsleague_match` (`:2877`) call `update_match_elos` whenever *anything* changed and the match is completed — including score/date tweaks on an already-completed match. Default refresh only targets scheduled/in-progress matches (`update_matches`, `:2676`), but refreshing by `match_ids` or `status_filter: "completed"` re-applies Elo. Likely root cause of manual Elo fixups.
- [ ] **`recalculate_all_elos(reset_to_default=False)`** (`views.py:125`) — replays every completed match on top of current Elo, i.e. applies every match a second time. Only safe with reset=true (the default).
- [ ] **Winner change / un-complete doesn't revert** — admin match updates (`views.py:1819`, `:2031`) only log a warning when a completed match's winner or status changes; old Elo stays applied, and the new winner never gets Elo (the transition guard `old_status != "completed"` blocks it).
- [ ] **`delete_match`** (`views.py:2143`) — deleting a completed match leaves its Elo applied to both teams. Same for `delete_competition` / season deletes.
- [ ] **Regents League team flip after Elo** — `update_regentsleague_match` (`:2833`) swaps `team1`/`team2` if the platform flipped them; if Elo was already applied to the old orientation, nothing corrects it.
- [ ] **`update_match_elos` isn't atomic** — saves team1 then team2 separately (`views.py:113–114`) with no `transaction.atomic()` / `select_for_update`; a crash or concurrent refresh between saves leaves one team updated. Also reads `team.elo` from possibly stale cached FKs.

### Planned: Elo tracking on Match

Goal: make Elo application idempotent and reversible, and show per-match Elo
swings in the UI.

**Schema (all nullable/defaulted → backwards compatible, no data loss):**

| Field | Type | Purpose |
|---|---|---|
| `elo_applied` | `BooleanField(default=False)` | Has this match's result been applied to team Elo? |
| `team1_elo_before` | `IntegerField(null=True)` | team1's Elo at application time |
| `team2_elo_before` | `IntegerField(null=True)` | team2's Elo at application time |
| `team1_elo_change` | `IntegerField(null=True)` | Signed delta applied to team1 (e.g. `+18`) |
| `team2_elo_change` | `IntegerField(null=True)` | Signed delta applied to team2 (e.g. `-18`) |

(Optional: `elo_applied_at = DateTimeField(null=True)` for auditing.)

**Code changes:**

- [ ] `update_match_elos(match)` — no-op if `match.elo_applied`; otherwise, inside `transaction.atomic()` with `select_for_update()` on both teams, compute deltas, update teams, write the five fields, save. This alone fixes the double-apply on platform refresh.
- [ ] New `revert_match_elos(match)` — if applied, subtract stored deltas from both teams, clear the fields, `elo_applied=False`. Call it from:
  - admin match update when status leaves `completed` or the winner changes (then re-apply if still completed with a winner);
  - `delete_match`, and competition/season deletes (or just recommend a recalc after bulk deletes);
  - Regents League flip handling (revert before swapping, re-apply after).
- [ ] `recalculate_all_elos` — when resetting, clear all five fields on every match first, then replay; the replay naturally repopulates them. When not resetting, skip `elo_applied` matches (makes the non-reset mode safe).
- [ ] `apply_match_elo` endpoint (`views.py:2090`) — return 400 "already applied" if `elo_applied`, or add a `force` option that reverts first.
- [ ] `merge_teams` — when moving matches from secondary to primary, the stored deltas stay valid as history; no Elo arithmetic needed (the `keep_secondary_elo` checkbox already handles the team value).
- [ ] Serializers — expose `elo_applied` and the deltas in admin and public match payloads; show `+18 / −18` on match cards / match page / team history.
- [ ] Admin UI — show an "Elo applied" badge on EditMatch with a manual Apply / Revert button.

**Caveats to document:**

- Elo is path-dependent: reverting an *old* match by its stored delta doesn't re-derive every later match. Revert is exact for the most recent match per team and a good approximation otherwise; full recalc remains the source of truth.
- Teams whose Elo is set by hand (`update_player_elo`-style tools, merges with `keep_secondary_elo`) will drift from the sum of stored deltas — expected.

**Backfill decision (needs a call before writing the migration):**

Existing completed matches have `elo_applied=False` after the schema migration,
so the next refresh of any of them would apply Elo again. Options:

1. Data migration that sets `elo_applied=True` (deltas NULL) for every `completed` match with a winner — assumes they were applied once. Cheap, no Elo change, but no historical deltas.
2. After deploying, run **Recalculate Elos (reset)** once — repopulates every match's before/delta values exactly, but recomputes current team Elo, which will differ from today's hand-fixed values.

Recommendation: ship (1) in the migration so nothing double-applies, then run (2) later if/when you're happy for the recalc values to replace the current ones.

## Security

- [ ] **`cc-backend/v1/cc/admin_views.py:155`** — `proxy_image` SSRF: fetches any user-supplied URL server-side. Intended fix: allow only http/https and block private/loopback/link-local resolved IPs (header auth isn't possible: used as an `<img src>` in Graphic.tsx). **Not yet applied** (see note at top).
- [ ] **`cc-backend/v1/cc/views.py:3236–3371, 3776`** — LeagueSpot and NWES proxy endpoints are unauthenticated. (Deprioritized 2026-07-09: keys are intentionally public/host-restricted per Aidan; only quota abuse remains as a concern.)
- [ ] **`cc-backend/v1/cc/webhooks.py`** — Sanity webhook has no signature verification. Intended fix: optional shared secret via `SANITY_WEBHOOK_SECRET` env var, checked against `?secret=` or `X-Webhook-Secret` header; unset = old behavior. **Not yet applied** (see note at top).
- [ ] **`cc-backend/v1/cc/middleware.py:31`** — `Bearer dev` grants owner access whenever `DEBUG=True`; a misconfigured env var in prod disables all auth.
- [ ] **`cc-backend/v1/cc/image_views.py:38, 91`** — no file-type/magic-byte validation or size cap on uploads; content-type derived from client filename.
- [ ] **`cc-backend/v1/Dockerfile`** — container runs as root (no `USER` directive).
- [ ] **`docker-compose.yml:13, 27, 31`** — Docker socket mounted into containers. It's `:ro`, but read-only on a socket file doesn't restrict the Docker API — still effective root on the host. Consider a socket proxy (e.g. tecnativa/docker-socket-proxy) limited to read endpoints.

## Backend correctness

- [ ] **`views.py:3386` `merge_teams`** — multi-object write with no `transaction.atomic()` (none anywhere in `views.py`); exception mid-merge leaves half-merged state.
- [ ] **`views.py:3653` `delete_competition`** — deletes events and event-matches by *season* (`:3693`, `:3703`) instead of by competition; can delete other competitions' events in the same season.
- [x] **`views.py:2795–2830` `update_regentsleague_match`** — *(fixed 2026-10-07)* `team1_participant`/`team2_participant` were unbound if both lookups failed → `UnboundLocalError`. Also the team2 warning message said "team1".
- [ ] **`views.py:230`** — `Competition.objects.create` runs before Season/Event validation; failed validation leaves an orphaned Competition row.
- [ ] **`views.py:50–58` `safe_parse_datetime`** — unix timestamps parsed with `datetime.fromtimestamp()` → naive datetime under `USE_TZ=True`.
- [ ] ~~`views.py:467–473` — explicit `visible=false` ANDed with `visible=True` default~~ — FALSE POSITIVE: the default only applies when the param is absent; logic verified correct.
- [ ] **N+1 queries** — `list_teams`, `list_players`, `list_matches` (per-match `EventMatch` query defeats prefetch), `public_views.py:304` `public_teams` (~4 queries per team per page).
- [ ] **`settings.py:156`** — `TIME_ZONE = "EST"` is not a valid IANA key; use `America/New_York`. Related: naive `datetime.now()` in `public_views.py:315, 839, 862, 1084`.
- [ ] **`settings.py:46`** — unset `DJANGO_ALLOWED_HOSTS` yields `[""]`, rejecting all requests.
- [ ] **`models.py` `RankingItem`** — no unique constraint on (ranking, team); duplicates possible. (No `UniqueConstraint`/`unique_together` anywhere in `models.py`.)
- [ ] **`models.py` `Participant`** — external IDs (faceit/playfly/regentsleague) not unique per competition; imports can silently create duplicates.
- [ ] **`create_ranking_snapshot`** (changed in `c9c3433`) — now filters to teams active in the season, but still ranks by *current* `Team.elo`, so snapshotting a past season captures today's Elo, not end-of-season Elo. Fine if snapshots are always taken live; worth knowing if anyone back-fills old seasons. (Per-match `teamN_elo_before/change` from the plan above would make historical snapshots reconstructable.)

## Frontend correctness

- [ ] **`pages/Event/Event.tsx:68, 74`** — passes `{ disabled: ... }` to hooks that expect TanStack Query's `enabled`; option silently ignored, queries fire with `event_id: undefined`.
- [ ] **`pages/Admin/EditMatch.tsx:1176, 1544, 1957, 2526`** — "No Winner" option stores literal `"__no_winner__"` in `winner_id` and sends it; backend rejects it with 400 "Winner must be one of the two teams". Also, `winner_id || undefined` omits the key on empty string, so a winner can never be cleared from the UI. Map `"__no_winner__"` → `null` and send `winner_id: null` explicitly.
- [ ] **`keepPreviousData: true`** in `Matches.tsx:787`, `Rankings.tsx:211, 222, 346` — removed in TanStack Query v5, silently ignored → loading flicker on page/filter change. Use `placeholderData: keepPreviousData`.
- [ ] **`pages/Search/Search.tsx:35`** — no abort/cleanup on Sanity fetch → stale results race when typing fast; `:168` — players without a team link to `/teams/undefined`.
- [ ] **`services/api.ts:1157` `fetchAllEvents`** — caps at 100 events, no pagination; admin dropdowns silently omit the rest.
- [ ] **`pages/Admin/EditMatch.tsx` `EventMatchEditForm`** — calls hooks after a conditional early return (Rules of Hooks violation).
- [ ] **`pages/Admin/EditMatch.tsx`** — `new Date("YYYY-MM-DD")` start-date filter parses as UTC midnight; excludes same-day matches in US timezones (endDate side is handled, startDate isn't).
- [ ] **`pages/Admin/EditEvent.tsx`** — empty dates produce `Invalid Date`; `>=` comparison of two Invalid Dates is `false`, bypassing validation.
- [ ] **`pages/Event/Event.tsx` `Stream()`** — returns `undefined` for non-Twitch stream links → blank Stream tab.
- [ ] **`pages/Matches/Matches.tsx:792`** — filter change when already on page 1 doesn't re-trigger the past-matches effect; stale results can persist.

## Low priority

- [ ] Index-as-key in `Home/UpcomingMatchesWidget.tsx:73` and `Home/ResultsWidget.tsx:53`.
- [ ] `console.log` in render paths: `EditEvent.tsx`, `Matches.tsx:214`; debug `print()` in `webhooks.py:50` and `views.py:3101` (LeagueSpot status).
- [ ] `Matches.tsx:211` — fresh `Date` objects as `useMemo` deps defeat memoization.
- [ ] `Rankings.tsx:43` — `window.location.hash` assignment in render body.
- [ ] `views.py:2264` — `players.count()` inside per-player loop → O(N) COUNT queries.
- [ ] `views.py:2288` `reset_player_elo` — per-row saves instead of a single `UPDATE`.
- [ ] `delete_match` / `delete_competition` — hardcoded "security keys" (`confirm-delete-match-456`, `confirm-delete-competition-789`) are confirmation strings, not security; fine as UX guards, but don't rely on them.

## Match import process (investigated 2026-07-09)

The import "works" only when platform team names exactly equal existing DB team
names. Everything else falls through to duplicate-team creation or crashes.

### Why the participant matcher does nothing (confirmed)

The mapping the admin builds in the Participant Matcher UI is broken at three
independent points — any one of them alone would neutralize it:

- [ ] **1. Every import creates a brand-new Competition** (`views.py:230`,
  deliberately: "do not merge with existing ones"). All participant lookups in
  `get_or_create_team` (`views.py:727–768`) are scoped to
  `competition=<the new competition>`, which by definition has no participants
  yet. Participants from previous imports — including any fixed via the
  `match_participants` endpoint — are invisible to the import.
- [ ] **2. Placeholder participants store the team NAME in the platform-ID
  field.** Frontend builds `platform:faceit:team:{TEAM NAME}`
  (`ImportMatches.tsx:966` — it only ever collects names, `:884–896`), and the
  backend stores that name into `faceit_id`/`playfly_id` (`views.py:272–277`).
  But `get_or_create_team` looks participants up by `faction_id`/`teamId`
  (platform UUIDs, `views.py:706, 718`). Name ≠ UUID, so the lookup never hits.
- [ ] **3. The non-placeholder branch updates participants of OLD competitions**
  (`views.py:282–285`) — which the import, scoped to the new competition (point
  1), never reads. Dead code in practice; the UI only sends placeholders anyway.

Net effect: after the matcher lookups all miss, matching falls through to
`Team.objects.get(name=team_name)` (`views.py:777`) — exact-name matching. The
matcher UI exists precisely for the cases where names differ, and in exactly
those cases a **duplicate team is silently created** (`views.py:780`).

**Fix sketch:** key placeholders by platform ID (faction_id/teamId) instead of
name on both ends, create the placeholder participants against the same
competition object the import will use (already true) but store the real
platform ID in it — and/or stop creating a new Competition per import (reuse by
name+season) so prior matches carry over.

### Other confirmed import bugs (the "strange bugs")

- [ ] **Wildcard NULL match assigns the WRONG team** — `views.py:728–735`: the
  Faceit lookup is `filter(Q(faceit_id=<faction_id>) | Q(faceit_id=<playfly_id>))`,
  and for Faceit imports `playfly_id` is `None`, so it becomes
  `... OR faceit_id IS NULL`. Any participant created earlier in the same import
  without a faction_id (TBD/bye teams) matches, and `.first()` returns an
  arbitrary one — a real team's matches get attached to the TBD/bye team.
  Order-dependent and intermittent. The `Q(faceit_id=team_playfly_id)` clause
  (`:732`) looks like a typo; should be removed or guarded.
- [ ] **`Team.objects.get(name=...)` crashes on duplicate names** —
  `views.py:777`: `Team.name` has no unique constraint, and the import itself
  creates duplicates (above). Once two teams share a name, every subsequent
  import touching that name raises `MultipleObjectsReturned`, caught only by the
  top-level handler → whole import 500s. Compounding failure mode.
- [ ] **Import is not atomic** — no `transaction.atomic()` around
  `import_matches` (`views.py:205`); a crash mid-way (e.g. the two above, or the
  Regents League winner crash) leaves a partial import plus an orphaned
  Competition row (created at `views.py:230` before any validation). Any Elo
  applied for completed matches before the crash also stays applied.
- [x] **Regents League: `match_data.get("winner").get("id")` crash** *(fixed 2026-10-07)*
  (`views.py:398`) — kills the rest of the batch when the API omits `winner`.
  (Also listed under Critical.)
- [ ] **`safe_parse_datetime` returns naive datetimes for unix timestamps**
  (`views.py:50–58`) — `datetime.fromtimestamp(ts)` uses server-local time, no
  tzinfo, under `USE_TZ=True`; match dates shift by the server's UTC offset.
- [ ] **`process_player` lookups** (`views.py:~876`) — `Player.objects.get(steam_id=...)`
  can also raise `MultipleObjectsReturned` (constraint removed in migration
  0005); same crash-the-import failure mode. Also does a live Faceit API call
  per roster player per import with no timeout, making imports slow and
  rate-limit-prone.
- [ ] **Competition proliferation** — every import (including re-imports of the
  same league) leaves another `Competition` row named identically; anything
  grouping or filtering by competition sees duplicates. Likely related to the
  recent "competitions hotfix".
