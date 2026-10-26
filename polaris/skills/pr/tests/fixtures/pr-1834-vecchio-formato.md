## What

Closes #1718 and #1430. Row 0c of `docs/areas/sal/plans/open/sal-v1.md`; ADR 2026-08-31 §8.1 (accepted).

- **The committente field suggests from the anagrafica** in the four points: the name panel during the wait, «Per chi e per dove» on the questions screen, the line under the quote title, and the recipient dialog before the PDF. Suggestions start at two characters and come from the server search. Homonyms are listed side by side with type, comune and P.IVA/CF, never merged. The list scrolls past four rows.
- **A choice links the Preventivo.** `PUT /api/quotes/{id}` takes `committente_id`. The snapshot is the server's reading of the record, never the browser's text. A key of another Impresa (or no record at all) is a 404 before anything is written; a non-UUID is a 422. An explicit `null` unlinks: it clears the name, or keeps the one written in the same request.
- **A new name enters the anagrafica on save**, with one creation key per written name, so a double save still makes one record. When the anagrafica cannot take it (a backend without it, offline), the name saves as text and the failure is reported.
- **«Cambia» (#1430)** edits or removes the committente after generation. Removing it recomposes a composed title without the name, or gives back the generated title. A title written by hand stays.
- **`committenti_enabled` defaults to true** and its row leaves `_polaris/features.md`. `COMMITTENTI_ENABLED=false` stays the kill switch. The Committenti section leaves the `?sal=1` preview and shows in the nav once the anagrafica has a committente (ADR-0024).
- The cache empties at a sign-out or a change of person, so one Impresa's data never shows to the next one on the same tab.
- **Domain:** the Preventivo carries the *indirizzo del cantiere*; the Cantiere is the job it opens (ADR §9.4). The UI labels and `CONTEXT.md` say so; the column stays `quotes.cantiere`.

## Why one PR (git-power pre-PR: 43 files, ~1,200 lines)

The field and the flag flip ship together (MERGE = SHIP). Without the field the flag would light an API nobody uses; without the flag the field talks to a 404. About half of the lines are tests and the red→green receipts.

## Not in this PR

- 0d (#1719): the «Spettabile» heading on the PDF, built on this branch next.
- IVA by type (#1653). The `pg_trgm` similarity search (deferred: the word search covers the field).
- **B1 (pre-existing)**: the date in a composed title is the UTC day of `created_at`, not the Italian day. A quote created between 00:00 and 02:00 carries the previous day.
- **U2 (pre-existing)**: a free-text committente accepts bidi control characters and 10k characters. From this PR that text also enters the recomposed title.

## Real test

Receipt: `docs/areas/sal/validation/2026-10-14-committente-suggerisce-real-test.md`, evidence in `.real-test/evidence/1718-committente/`.

**Does what it was meant to**
- [x] Suggestions in 4 of the 4 points from two characters: browser-pilot, 16 cases, `attestazione-ui-0d54abd4.json`
- [x] A pick stores key + server snapshot, and the client text is ignored: `attestazione-api-0d54abd4.json`
- [x] A new name creates one record, also with 8 concurrent requests on the same key: breaker C12/C13
- [x] Homonyms stay two rows: API + browser case 3
- [x] Change and remove after generation (#1430): `20-removed.png`, `r1-d3-composed.png`
- [x] A PDF already produced stays byte-identical after the record changes: API + breaker P3-P5
- [x] `GET /api/committenti` without a token is a 401: local branch backend

**Breaks nothing it touches**
- [x] Tenant isolation: a foreign committente is a 404 on read, edit and link, and nothing is written (`attestazione-tenant-2d921a6e.json`), plus a structural test
- [x] Text alone keeps its meaning and never touches the key
- [x] A composed title follows the change and a hand title stays (breaker T1-T22)
- [x] Breaker, Opus with fresh context and without the diff: 207 attempts in 6 attack classes, no contract rule broken (`breaker-attempts.md`)
- [x] UI walk on the branch, step by step with screenshots: see below
- [ ] **Staging + preview of the final commit, then the founder's visual pass.** Staging is held by the analisi-prezzi lane (#1885); this runs when it is handed back.

**The principles**
- [x] Every test was seen red first: `state/tdd/1718-committente-scelto.jsonl`
- [x] Codex (gpt-5.6-sol): 6 findings, each reproduced red and fixed
- [x] Domain boundaries, import cycles and the flag ledger are green
- [x] The backend suite passes in the pre-push. Locally, `test_step1_righe_impresa_db::test_a_locked_listino_…` was red once in the same way on `main` `ee545c08b`; it does not belong to this lane.
- [x] Frontend 2004/2004 in CI mode

## UI walk on the branch, 2026-10-17 (`73d320f00` + fix `bb754e431`)

Local branch backend on staging data (`/health` commit `73d320f00`), Vite on the worktree, a dedicated headless Chrome (first `list_tabs()`: `about:blank` only), account `qa@example.com`, nothing validated. Second walk after the fix: 7 steps plus 3 extra probes (20 Enter presses across the search answer, extra spaces and case, two identical records), all pass; one PUT per pick, zero POST on picks.

| Step | What it proves | Screenshot |
|---|---|---|
| 1 | «Cambia» puts the focus in the field | <img src="https://github.com/acme/acme-api/blob/4b430068eb38b9572f749782e0cd586d1f5a4c7b/.real-test/evidence/1718-committente-73d320f00/pr/01-cambia-focus.jpg?raw=true" width="420" alt="01-cambia-focus"> |
| 2 | A new name: «Cerco nell'anagrafica…», then the last row «Crea il committente «X»» | <img src="https://github.com/acme/acme-api/blob/4b430068eb38b9572f749782e0cd586d1f5a4c7b/.real-test/evidence/1718-committente-73d320f00/pr/02b-list-create-row.jpg?raw=true" width="420" alt="02b-list-create-row"> |
| 3 | The centred «Nuovo committente» window, type guessed from the name (Srl → Azienda), only that type's fields; Escape and a click outside keep it | <img src="https://github.com/acme/acme-api/blob/4b430068eb38b9572f749782e0cd586d1f5a4c7b/.real-test/evidence/1718-committente-73d320f00/pr/03a-dialog-azienda.jpg?raw=true" width="420" alt="03a-dialog-azienda"> |
| 3 | «Crea il committente» creates, links and saves in one click; persists after reload | <img src="https://github.com/acme/acme-api/blob/4b430068eb38b9572f749782e0cd586d1f5a4c7b/.real-test/evidence/1718-committente-73d320f00/pr/03c-created-linked.jpg?raw=true" width="420" alt="03c-created-linked"> |
| 4 | Empty name: the error per type («Scrivi la ragione sociale.») | <img src="https://github.com/acme/acme-api/blob/4b430068eb38b9572f749782e0cd586d1f5a4c7b/.real-test/evidence/1718-committente-73d320f00/pr/04a-empty-submit-errors.jpg?raw=true" width="420" alt="04a-empty-submit-errors"> |
| 4 | P.IVA and CAP checked on leaving the field | <img src="https://github.com/acme/acme-api/blob/4b430068eb38b9572f749782e0cd586d1f5a4c7b/.real-test/evidence/1718-committente-73d320f00/pr/04b-piva-cap-errors.jpg?raw=true" width="420" alt="04b-piva-cap-errors"> |
| 5 | Enter on a new name opens the window; «Condominio» guessed | <img src="https://github.com/acme/acme-api/blob/4b430068eb38b9572f749782e0cd586d1f5a4c7b/.real-test/evidence/1718-committente-73d320f00/pr/05a-enter-condominio.jpg?raw=true" width="420" alt="05a-enter-condominio"> |
| 6 | Privato: nome and cognome side by side, prefilled from the name | <img src="https://github.com/acme/acme-api/blob/4b430068eb38b9572f749782e0cd586d1f5a4c7b/.real-test/evidence/1718-committente-73d320f00/pr/06a-privato-nome-cognome.jpg?raw=true" width="420" alt="06a-privato-nome-cognome"> |
| 7 | A similar name listed: «Ci sono nomi simili: scegline uno o creane uno nuovo.» | <img src="https://github.com/acme/acme-api/blob/4b430068eb38b9572f749782e0cd586d1f5a4c7b/.real-test/evidence/1718-committente-73d320f00/pr/07a-similar-names.jpg?raw=true" width="420" alt="07a-similar-names"> |
| 8 | PDF without committente: «Dati del committente», cantiere first | <img src="https://github.com/acme/acme-api/blob/4b430068eb38b9572f749782e0cd586d1f5a4c7b/.real-test/evidence/1718-committente-73d320f00/pr/08b-dati-committente-dialog.jpg?raw=true" width="420" alt="08b-dati-committente-dialog"> |
| 8 | «Salva e scarica» empty: each missing field says so under itself | <img src="https://github.com/acme/acme-api/blob/4b430068eb38b9572f749782e0cd586d1f5a4c7b/.real-test/evidence/1718-committente-73d320f00/pr/08c-empty-errors.jpg?raw=true" width="420" alt="08c-empty-errors"> |
| 8 | A new committente is a step of the same dialog, never a second window | <img src="https://github.com/acme/acme-api/blob/4b430068eb38b9572f749782e0cd586d1f5a4c7b/.real-test/evidence/1718-committente-73d320f00/pr/08d-same-dialog-nuovo-step.jpg?raw=true" width="420" alt="08d-same-dialog-nuovo-step"> |
| 8 | Back on the first step: «Committente creato: X.», the cantiere still to write | <img src="https://github.com/acme/acme-api/blob/4b430068eb38b9572f749782e0cd586d1f5a4c7b/.real-test/evidence/1718-committente-73d320f00/pr/08e-back-committente-creato.jpg?raw=true" width="420" alt="08e-back-committente-creato"> |
| 9 | Phone 390×844: full screen, buttons at the bottom, no horizontal scroll | <img src="https://github.com/acme/acme-api/blob/4b430068eb38b9572f749782e0cd586d1f5a4c7b/.real-test/evidence/1718-committente-73d320f00/pr/09a-phone-dialog.jpg?raw=true" width="420" alt="09a-phone-dialog"> |
| 10 | **Found:** Enter on the exact name of an existing committente created a duplicate | <img src="https://github.com/acme/acme-api/blob/4b430068eb38b9572f749782e0cd586d1f5a4c7b/.real-test/evidence/1718-committente-73d320f00/pr/10d-duplicate-in-anagrafica.jpg?raw=true" width="420" alt="10d-duplicate-in-anagrafica"> |
| 11 | **Fixed (bb754e431):** the exact name is highlighted once the search answers… | <img src="https://github.com/acme/acme-api/blob/4b430068eb38b9572f749782e0cd586d1f5a4c7b/.real-test/evidence/1718-committente-73d320f00/pr/11a-lowercase-exact-highlighted.jpg?raw=true" width="420" alt="11a-lowercase-exact-highlighted"> |
| 11 | …and Enter picks it: no window, no POST, one PUT | <img src="https://github.com/acme/acme-api/blob/4b430068eb38b9572f749782e0cd586d1f5a4c7b/.real-test/evidence/1718-committente-73d320f00/pr/11b-after-enter-linked.jpg?raw=true" width="420" alt="11b-after-enter-linked"> |
| 13 | Under «Cambia» a pick saves at once, no «Salva» | <img src="https://github.com/acme/acme-api/blob/4b430068eb38b9572f749782e0cd586d1f5a4c7b/.real-test/evidence/1718-committente-73d320f00/pr/13b-click-picked-saved.jpg?raw=true" width="420" alt="13b-click-picked-saved"> |
| 14 | A true homonym is still the create row, one click | <img src="https://github.com/acme/acme-api/blob/4b430068eb38b9572f749782e0cd586d1f5a4c7b/.real-test/evidence/1718-committente-73d320f00/pr/14a-homonym-create-dialog.jpg?raw=true" width="420" alt="14a-homonym-create-dialog"> |

**What changed after the walk**
- Enter on a name already in the anagrafica (case and spaces ignored) picks it once the search answers; Enter while the search runs does nothing. A true homonym is the create row, one click away.
- Under «Cambia» a pick from the list links and saves at once, as a creation does. The PDF dialog still saves on «Salva e scarica».
- Frontend 2231/2231, `tsc` 0, `check:design` clean, local pre-push CI green in 365 s.

**Seen, not in this lane**
- The local PDF render fails on this Mac (`libgobject-2.0-0` missing), and «Download non riuscito» shows the raw backend message. The full download is to be proven on staging.
- `POST /api/log/client-error` answers 422 for that error (no `code`, `message` over 500 characters): the failure is not logged.
- With two identical records (the duplicate left by step 10), Enter picks the first without saying which.
- `job-economics/…/analyses` 404 on every quote open.

### «Finestra con modulo», a design-system component
The window where the Impresa writes data is `components/form/FinestraModulo.tsx` (`FinestraModulo`, `Modulo`), in `DESIGN.md` → Components and in `_polaris/decisions.md` (2026-10-17). «Nuovo committente» and the PDF dialog are built on it; the next window with a form reuses it. `impeccable` critique 25/32 at round 6, harsh visual audit without blockers.

## Test data left on staging

The test account holds committenti named «RT1718…» (2026-10-17 walk: Edilnord Srl ×2, Condominio Le Rose, Giulia Verdi, Pdf Impianti Srl) and «RT1718B»; there is no delete in the API. Quotes generated: `31bc2b6b`, `7b25d415`, `b36a5bf7`. Draft quotes edited, none validated: `4262fec7`, `f832b127`, `6d9c1166`, `4e2b5ccc`, `f3684a34`.

🤖 Generated with [Claude Code](https://claude.com/claude-code)


