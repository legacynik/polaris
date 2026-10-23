# Changelog

All notable changes to Polaris Team OS. The installed version is pinned in
`polaris/.claude-plugin/plugin.json`.

## Unreleased

### The PR chain, review tiers, and a package that stands alone

**Upgrading:** `npx skills update -g -y` does not delete retired skills. Remove them once:

```bash
npx skills remove -g skill-meta pol-apex-curate pol-adr pr polaris-memory review
```

Added

- **The PR chain.** `pol-ship` 2.1.0 is the single entry point once work is done: it loops locally
  until the Definition of Done holds (tests, `polaris-review`, simplify, `real-testing`), pushes a
  draft PR through `git-power`, signs the head on staging, writes the body with `pol-pr`, runs
  `pol-babysit` to the owner's label, then sends one merge-and-deploy proposal with a rollback plan.
  It merges once (a plain squash, never `gh pr merge --auto`) and deploys only on the owner's yes; a
  verification window then reports advance, hold or a proposed rollback, never an automatic one.
  `pol-pr` 1.2.0 writes the PR body the owner judges without reading code and absorbs the retired
  `pr` (its visuals and evidence rules; English headings). `pol-babysit` 1.1.0 drives an open PR to
  the owner's label on its current head.
- **`codex-review` 1.0.0 ships standalone**: an independent, read-only Codex review whose findings
  are checked against the source. It owns the Codex invocation for `polaris-review` and
  `polaris-sweep`.
- **`issue-contract` 2.3.0 is back** (it had left the package in the previous entry below), with a
  checked AFK label: `tracker.afk_human` / `tracker.afk_agent` from `_polaris/config.yml`, else the
  repository's own labels; work for a person with no label to carry it is not filed (exit 2).
- **`tdd-dev` 2.5.0** ships `references/writing-tests.md`, with its four rules inline in the cycle;
  `bugfix` Phase 4 points to it.
- **`base-workflow` 0.4.0** checks the pinned version's documentation before calling a library API.

Changed

- **`review` is renamed `polaris-review`** (1.1.0) and picks its reviewer tier from the diff: size,
  file count and risk paths (auth, money, schema, security, concurrency, plus the repository's
  `review.risk_paths`). Tier 3 adds `codex-review`.
- **`crasher` 0.4.0 proposes, a person picks.** It lists one deduplicated finding per confirmed
  crash and files, through `issue-contract`, only the ones a person selects.
- **`git-power` 0.6.0** finalizes in the repository's own checkout by returning to the base instead
  of crashing.
- `polaris-sweep` and `polaris-review` no longer name private infrastructure or unshipped skills.
- `start`'s `config.yml` template shows a placeholder login (`your-github-login`), not a real one.
- **`init` 0.4.0 needs no vault.** It ships its own scripts and uses the installed `architecture`
  skill's backbone checker. Without a vault it audits, proposes and applies, writes no
  `polaris.vault`, and skips only the ContextPack check, with one line.
- Skill bodies and references are in English throughout (`polaris-sweep`, `end`, `plan-week`,
  `update` and the bypass-test references). Strings that scripts print or tests match stay
  verbatim. `pol-ship` records a missing contract field as `mode: reduced`.
- Attributions moved out of the skill bodies into `CREDITS.md` for `end`, `plan-week` and
  `database-schema`.
- `start`'s `config.yml` template marks `contributors` as an optional roster that no skill reads.
- `AGENTS.md` is short: the skills CLI is the only install path, and the skill list lives in the
  README and `docs/skills.md`.
- Docs: the README is rebuilt around the skills CLI and a phase table; new
  [docs/skills.md](docs/skills.md) reference, [CONTRIBUTING.md](CONTRIBUTING.md) and a
  [CREDITS.md](CREDITS.md) index; onboarding no longer requires Superpowers.

Removed

- **`polaris-memory`** no longer ships, and no shipped skill runs `polmem`: `end`, `plan-week`,
  `polaris-grill`, `polaris-status`, `report`, `reference-capture` and `start` read the
  repository's decision log and lessons instead.
- `pr` (folded into `pol-pr`) and `review` (renamed `polaris-review`). `skill-meta`, `pol-apex-curate`
  and `pol-adr` left in earlier releases; machines installed before then may still carry them.

Fixed

- **The vault sync no longer deletes package files.** It carries every file a skill folder holds
  (CREDITS.md, LICENSE, `agents/`), reports a file only the package has instead of removing it, and
  rewrites `skills-suite/` only in real paths: `polaris-sweep`'s pipeline regex keeps its last
  alternative instead of matching every path.
- **`init`'s Decision probe works on a skills-CLI install**: it finds the architecture skill's
  checker under `~/.agents/skills` (or `.claude`, `.codex`) when no vault is declared.
- **The ContextPack resolver ships whole.** `polaris/scripts/` gains the modules `contextpack.py`
  and its siblings import (`contextpack_labels`, `contextpack_plans`, the receipt, flight, seal and
  lesson-consolidation modules, `token_count`) with the tests that build their own fixtures; the
  resolver and empty-repo test follow the no-stored-seals contract.

### Earlier unreleased changes

- **Le porte installate da sole bastano a se stesse.** `architecture` 1.4.0 porta con sé il checker
  del backbone (`scripts/check_context_backbone.py`): `arch_doctor.py --which` stampa la copia della
  skill; senza il resolver `contextpack.py` accanto, `--emit-context` esce 2 con
  `CONTEXTPACK_UNAVAILABLE`. `architecture` e `domain` 0.4.0 allineate al vault: regole proprie in
  `references/decision-rules/` per argomento, attribuzioni in `CREDITS.md`. Nuova porta
  `base-workflow` 0.3.0 (draft): il metodo di build, soglie prese dal repository (`CONSTRAINTS.md`
  prima). `issue-contract` esce dal pacchetto: `crasher` 0.3.0 stampa per ogni finding una ricerca
  `gh issue list --search <fingerprint>` e un `gh issue create` col contratto nel corpo; i riferimenti
  in `ambitious-goal`, `bugfix`, `git-power`, `polaris-sweep` seguono. `real-testing` 3.2.2:
  `verdict.py` su un repository troppo giovane per la base esce 2 senza traceback. `tdd-dev` 2.4.2: i
  due test con venv annidato si saltano, con il motivo, sotto `uv run --with pytest`. `polaris-status`
  1.3.3 usa l'indice del portfolio solo se c'è, altrimenti ordina per recenza; `end` e `bugfix` parlano
  di code-graph in generale, non di un fornitore. README: tolta la riga di `/pol-apex-curate`.

- **`/start` mette davanti la coda del founder e dice quando il cockpit va riscritto** (`start` 1.13.1 →
  **1.14.0**). Nuovo `_cockpit_signal.py`: dalla sezione `## Coda founder` del cockpit stampa fino a 5
  righe `QUEUE:` (sicurezza e scadenze entro 7 giorni sempre, anche oltre 5), un `QUEUE_MORE:` contato per
  tipo (ok · decisioni · altro) e al massimo un `QUEUE_ASK: avanti o scarto?` sulla voce più vecchia oltre
  30 giorni; `COCKPIT_REWRITE:` quando ci sono più righe `Updated:`, il file supera 8000 caratteri, manca
  la coda o l'ordine è vecchio (stessa regola di `PRIORITIES_STALE`). Locale e in sola lettura: il file più
  un `git log -1`; un repo senza commit da 60 giorni non stampa nulla. Nel brief, `**Da ricordare**`
  viene prima di Pack e Segnali.
- **`/update` legge e timbra solo gli appunti della propria sessione** (`update` 3.3.1 → **3.3.2**).
  Con più panel sullo stesso repo `checkpoint.sh` prendeva il file scratch più recente del login: il
  checkpoint riportava il testo di un altro panel e spostava il timbro nel suo file (polaris-os#536,
  ricorrenza di #89). Ora il file è quello che porta l'id della sessione (`POLARIS_SID`, che la skill
  passa da `${CLAUDE_SESSION_ID}`); senza id vale l'unico file toccato oggi, e con più candidati non si
  legge e non si timbra nulla. Tolto il tetto di 40 righe: in un file tutto della sessione tagliava le
  righe più recenti, che il timbro dava poi per lette. Una sessione che attraversa la mezzanotte ha due
  file: si leggono e si timbrano tutti, dal più vecchio, e `verify` fallisce finché uno ha righe non lette.
  Il timbro è riconosciuto solo a inizio riga. Conta come scratch solo il nome che scrive l'hook
  (`<data>-<12 caratteri dell'id>`): una nota datata lasciata nella cartella non è un candidato. Senza id
  vale l'unica sessione che ha scritto oggi, con tutti i suoi file. Nessun fork per file: 1,1-1,5 secondi
  per comando misurati su una cartella vera di 186 file.
  Un byte non UTF-8 nel file non azzera più la lettura (`awk` in locale C).
  Limite dichiarato: senza id, se oggi ha scritto una sola sessione, il checkpoint legge quella —
  che può non essere la propria.
  Prova: `polaris/tests/test_update_scratch_session.py`.

- **A citation of another repository never decides a lane here** (`end` 1.23.0 → **1.23.1**,
  package → **0.31.2**). The prune read `<other-repo>#123` as issue 123 of the current repository:
  it got no answer, called it `BLOCKED`, and one `BLOCKED` stops the whole run, so a cockpit that
  mentioned any other tracker was never pruned. A qualified citation is now compared with this
  checkout's own names (directory and `origin`); a foreign one is `OPEN` and keeps its lane. A
  bare number that is neither a PR nor an issue here is `OPEN` too, on the tracker's own
  «could not resolve» answer; no `gh`, an error or a rate limit stay `BLOCKED`. Not covered: a
  bare number of another tracker that also exists here.

- **The contract test stops pinning sentences** (tests and CI only, no skill changed).
  `test_team_os_contract.py` asserted 169 times, mostly that a phrase existed in a SKILL.md: it
  went red when a skill was reworded and stayed green when a mechanism broke. It now asserts only
  what a machine reads (manifest, frontmatter as strict YAML, links, templates, the `start` size
  budget, denylists that walk the tree). Three blocks no test ran are now executed verbatim from
  the skills: the `/report` week resolver (`test_report_week.py`), the `/start` provisioning and
  identity gate (`test_start_identity.py`), the `/end` journal check (`test_end_journal_wiring.py`).
  Every new test was proven by breaking its mechanism. A workflow runs the suite on every pull
  request: until now a red test stopped no merge. Rules that live only in prose are no longer
  "tested" by substring; they belong to review and to the evals under `polaris/evals`.

- **The team contract test follows the skills again** (tests and `AGENTS.md` only, no skill changed).
  `test_team_os_contract.py` had been red on `main` since `update` 3.0.0 (#32) and the Sunday-dated
  report of 2026-07-28: its assertions pinned sentences those rewrites replaced. Each one now names
  the sentence, or the script, that carries the same rule today; one rule was reversed on purpose
  (the lane is the work, not the branch) and one moved (`/end` names stale lanes, `/update` no longer
  flags them). A machine path is removed from `tests/tdd/END-DEAD-LANES.jsonl`. The `start` size caps
  are re-based from 7,000 bytes / 940 words to the measured 12,000 / 1,800, because the skill had
  grown to 11,677 bytes with the guard red; shrinking it back is polaris-os#546. `AGENTS.md`
  describes the skills-CLI install and what it does not carry.

- **Six skill paths resolve without the Claude Code plugin** (`plan-week` 1.4.0 → **1.4.1**,
  `pol-apex-curate` 1.1.0 → **1.1.1**, `polaris-status` 1.3.0 → **1.3.1**, `report` 1.3.0 → **1.3.1**,
  `start` 1.13.0 → **1.13.1**, package → **0.31.1**). They named a bare `$CLAUDE_PLUGIN_ROOT/skills/...`,
  which is empty when the skills are installed with `npx skills` into `~/.agents/skills`, so the
  template copies, the apex gate and the wiki quality check pointed at `/skills/...`. They now use
  `${CLAUDE_PLUGIN_ROOT:-$HOME/.agents}`, the chain every other call site already had.

- **`pr` and `retro` join the Polaris skill catalog** (each 1.0.0, package **0.31.0**).
  Upstream: `mattpocock/skills@49dd158d` (MIT); `pr` writes a GH-visible Summary,
  before/after Evidence and Merge Danger; `retro` is explicitly invoked and proposes
  improvements to the agent environment. The same skill directories are linked into
  Claude Code, Codex and Hermes on this workstation. `pr` credits Humanlayer's
  `show-me` visual patterns.

- **`/end` chiude anche il lavoro abbandonato** (`end` 1.22.1 → **1.23.0**, `update` 3.3.0 → **3.3.1**,
  pacchetto → **0.30.0**). Misurato su un repo prodotto: 38 fili sotto `## Open`, 15 morti, zero chiusi.
  Nuovo verdetto `DEAD` (PR chiusa senza merge, issue chiusa come not planned): la lane esce e il log
  scrive `DEAD`, mai completato; un `DEAD` accanto a un `OPEN` la tiene. Le lane senza citazioni più
  vecchie di 14 giorni escono come `STALE=` e vanno risolte nella stessa `/end`. `state_close --key #N`
  chiude l'unica lane che cita #N; un `--todos` inesistente viene saltato. Supera la regola «not planned
  resta aperto» di #202. Prova: `polaris/tests/test_end_dead_lanes.py`.

- **`exact()` accetta di nuovo il qualificatore** (`update` 3.2.1 → **3.2.2**, pacchetto → **0.29.2**).
  #43 aveva ristretto l'intestazione alla riga intera `## Active Priorities`; il cockpit del vault la scrive
  `## Active Priorities — l'ordine del lavoro`, lo script non l'ha riconosciuta e al primo uso reale ha
  aggiunto una seconda sezione. Livello esatto (un `###` altrove resta escluso), qualificatore ammesso
  come nel resto del registro. Prova: `polaris/tests/test_state_priorities_qualified.py`.

- **Breaker su `state_priorities` e `/end` Step 4b** (`end` 1.22.0 → **1.22.1**, `update` 3.2.0 → **3.2.1**,
  pacchetto → **0.29.1**). Cinque difetti con input riproducibile, corretti:
  - lo snippet dello Step 4b usava virgolette doppie: una lane con backtick veniva eseguita dalla shell e
    l'ordine scritto corrotto con exit 0. Ora heredoc quotato (`<<'ORDER'`) e fallback su `$HOME/.agents`;
  - l'intestazione era cercata a qualunque livello: un `### Active Priorities` dentro un'altra sezione veniva
    riscritto e cancellato. Nuovo `state_sections.exact()` nel registro unico: solo l'h2, riga intera;
  - un input di soli marcatori (`1.`, `*`) passava come elementi e cancellava l'ordine: ora STOP;
  - un timbro malformato zittiva `/start`: ora `PRIORITIES_STALE=malformed`;
  - lo Step 4b poteva togliere una lane viva: ora esce solo ciò che lo Step 4 ha chiuso `PROVEN`, su
    `BLOCKED` non si riscrive l'ordine, e oltre 7 righe la coda si piega in una riga, mai si scarta.
  Prova: `polaris/tests/test_state_priorities_breaker.py`, tre ricevute in `tests/tdd/PRIORITIES-B42-*`.

- **`## Active Priorities` ha un proprietario: `/end`** (`end` 1.21.0 → **1.22.0**, `update` 3.1.0 →
  **3.2.0**, `start` 1.12.0 → **1.13.0**, pacchetto 0.28.0 → **0.29.0**). Nessuna porta scriveva la
  sezione: `/update` scrive `## Open`, `/end` `## Recent Context`, e in una repo prodotto le priorità
  sono rimaste al 13/09 per dieci giorni. Quel giorno una modifica a mano aveva trovato l'intestazione
  con `s.index` non ancorato, agganciando una menzione fra backtick nella prosa e fondendo la nuova
  intestazione in una frase. Ora `/end` (Step 4b) ricostruisce l'ordine da `goals.md`, `todos.md`, i
  thread `## Open` e la sessione, e lo scrive con `update/scripts/state_priorities.py set`: intestazione
  trovata dal registro fence-aware, scrittura atomica sotto lock, timbro di data. `/start` legge solo
  il cockpit e nomina un ordine più vecchio di 7 giorni (`PRIORITIES_STALE=<n>d`) invece di
  presentarlo come attuale. Prova: `polaris/tests/test_state_priorities.py` (4) e
  `test_start_priorities_signal.py` (1), RED→GREEN in `tests/tdd/PRIORITIES-*.jsonl`.

- **`/start` non stampa più il pack** (`start` 1.11.0 → **1.12.0**, pacchetto 0.27.0 → **0.28.0**).
  Misurato il 2026-09-23 su tre repository, sei agenti a contesto fresco, `/start` con e senza
  pack: brief identici, +15% token, **0 righe `layer:` su 131** hanno cambiato un brief, e un
  repository fermava il brief per chiedere «quale area?» per un pack che nessuno leggeva. Decisione
  founder: il pack si carica all'ingresso in una lane, mai a `/start`. Il resolver gira ancora
  (un'emissione bloccata resta rumorosa); le righe sono contate in una sola riga
  `PACK: <n> rows held for lane entry`, la domanda sull'area non viene più posta.
  Prova: `polaris/tests/test_start_no_pack_rows.py`, RED→GREEN in `tests/tdd/START-NO-PACK.jsonl`;
  cinque test del contratto precedente (#405, «stampa le righe») aggiornati al conteggio.

- **La sessione si APRE da `/start`, e le altre due porte raggiungono quella** (`start` 1.10.0 →
  **1.11.0**, `update` 3.0.0 → **3.1.0**, `end` 1.20.0 → **1.21.0**, pacchetto 0.26.0 → **0.27.0**).
  Il motore della continuità (`scripts/session_continuity.py`) stava nel vault da settimane e
  **nessuna skill chiamava il suo `start`**: la ricevuta del pack (`area-<slug>.json`) e il
  reinserimento dopo una compaction rispondevano `RECEIPT: none` e `NO_OPEN_SESSION`, cioè tutto il
  lavoro del resolver moriva con la finestra di contesto in cui era stato stampato
  (polaris-os#155).
  Ora `/start` ha un passo 5b — **prima** dei segnali, perché la ricevuta appartiene a una sessione
  già aperta — che apre con un **sid derivato**: `s-<login>-<YYYYMMDD>-<hash6 del checkout>`.
  Derivato, non passato: `/update` e `/end` lo ricalcolano e arrivano alla stessa sessione senza
  che nulla viaggi fra i processi. Una seconda `/start` nello stesso giorno è un **resume**, non un
  errore; un pack rifiutato è **una riga** (`SESSION: blocked — <CODE>`) e il brief continua; un
  repo senza motore non stampa niente e non scrive niente — la feature-detection di #155 resta
  intatta.
  `/update` aggiunge un evento append-only al checkpoint, `/end` chiude la stessa sessione: il
  `sid` non si scrive più a mano (il corpo spediva letteralmente `--sid "<sid>"`) e il gate non si
  cerca più solo nel repo (`$ROOT/scripts/…`, che in una repo di prodotto non esiste) ma **host poi
  vault dichiarato**, la stessa ricerca del compilatore del brief.
  **Una chiave sola per il vault.** `/end` leggeva `polaris.vault-root` mentre `/start`, `/init` e
  il doctor leggono `polaris.vault`: due chiavi per lo stesso fatto sono una repo che risponde a una
  porta e non all'altra. Ora la chiave è `polaris.vault`; la vecchia è ancora **letta per un giro**,
  con una nota di deprecazione su stderr che nomina quella che la sostituisce.
  Prova reale su una repo di prodotto (worktree usa e getta, `origin/main`, nessun backbone
  tipizzato): `SESSION: opened s-…`, la ricevuta `state/session/<sid>/area-all.json` con lo stesso
  `pack_seal` della `start.json`, un evento con `prev` = ricevuta di start, `end.json` che li lega,
  e il reinserimento che passa da `NO_OPEN_SESSION` a `REINSERT: HEAD unchanged … 0 tracker calls`
  con `CHAIN: prev=<ricevuta di start>`.
  **Giro 1 della review.** Il seat resta sotto il **checkout**, che è la sola radice contro cui
  il pack è compilato (`emit_pack` passa `git rev-parse --show-toplevel`) e quindi la sola dove la
  dashboard cerca la sessione; a essere sbagliati erano i **lettori**: lo Step 3b e l'hook di
  compaction chiedevano `$ROOT` (`<repo>/_polaris`) e in ogni repo di prodotto rispondevano
  `NO_OPEN_SESSION` — l'hook, per giunta, cercava `contextpack_reinsert.py` solo nel repo, quindi
  non ha mai fatto nulla lì. Ora passano dalla porta (`session_gate.py reinsert`, host poi vault,
  radice del checkout) e `install_settings` **sostituisce** il blocco vecchio invece di
  affiancarne uno nuovo che continuerebbe a girare.
  `/update` e `/end` non ricalcolano più il sid: agiscono sulla **sessione aperta**. A mezzanotte
  la derivazione cambia mentre la sessione è ancora aperta, un pannello può non aver mai fatto
  `/start`, e un secondo `/end` non ha più niente da chiudere: tutti e tre uscivano `SESSION_UNKNOWN`
  rc 2, cioè `/end` moriva prima di committare l'handoff. Ora sono `SESSION: none open — nothing to
  close` con exit 0, e una ricevuta già scritta non viene mai riscritta; dopo una chiusura `/start`
  apre un **seat nuovo** (`…-2`) invece di «riprendere» una sessione chiusa. Il seat ignora sé
  stesso (`state/session/.gitignore`), così non sporca `git status` nei repo ospite, e la causa di
  un rifiuto è il **codice** del motore o la sua ultima riga, mai `Traceback (most recent call
  last):`.
  **Giro 2.** Senza sessione aperta il motore non gira, e con lui nessuno dei sette rifiuti di
  #407: un `/end` con il log di sessione non ancora su disco usciva 0. Ora i due rifiuti che il log
  si guadagna da solo — `HANDOFF_MISSING`, `HANDOFF_UNREADABLE` — li controlla la porta **prima** di
  qualunque domanda sulla sessione, exit 1. E `chain`, che era rimasto l'ultimo lettore a chiedere
  `$ROOT`, passa dalla porta come `reinsert`: stessa radice, ma l'exit code arriva al chiamante,
  perché una verifica che inghiotte `CHAIN_BROKEN` non verifica niente.
  Tre cose che una riga sola rompeva: l'ignore del seat su un `state/` non scrivibile faceva
  morire il brief con un traceback (è igiene, ora non alza), il selfcheck di `install_settings`
  eseguiva l'hook contro la copia **installata** invece del pacchetto in cui vive (rosso 12/13 su
  una macchina senza install, e `check_skills.sh` con lui), e `--login` divergente da
  `polaris.login` lasciava una sessione aperta per sempre in silenzio — ora `/end` dice di chi è
  il seat aperto invece di tacere.

- **Una repo che esiste gia' entra dalla porta `init`, e la porta non trasporta l'harness**
  (`init` **0.1.0** nuova, pacchetto 0.25.2 → **0.26.0**). Il pacchetto spediva le skill ma nessun
  modo di *entrare*: in una repo di prodotto senza triade tipizzata il context pack non emette
  niente, e il doctor dice «harness not installed». La porta esegue i quattro passi nell'ordine che
  il founder ha fissato — **audit** (JSON: ogni documento vivo `absent`/`prose`/`typed`, ogni
  bloccante col rimedio, e UNA domanda per ogni scelta non provabile), **propose** (piano in
  Markdown con la tabella delle aree **da firmare**), la firma, **apply --mode minimal** — e solo
  alla fine mostra il pack. I primi due verbi scrivono **zero file**: e' il contratto della spec
  `repo-adoption` («il primo giro non esegue lavoro»), non una cortesia.
  La porta **chiama** `polaris_init.py` del vault risolto da `git config polaris.vault` e, se non
  c'e', dice una riga ed esce 0: il pacchetto non vendorizza gli script, e il test lo verifica
  (`test_it_ships_no_copy_of_the_harness`). Le aree restano **proposte e firmate, mai derivate**
  (#331 KILL): un dossier senza manifest firmato blocca il sigillo invece di far inventare un
  manifest all'agente.

- **Il puntatore al vault si rilegge a ogni giro, e il cockpit si chiede** (`init` 0.1.0 →
  **0.2.0**). `polaris.vault` vive nel `.git/config` condiviso: un'altra sessione lo riscrive
  sotto di te, e un puntatore morto non da' errore — il pack semplicemente smette di emettere.
  `audit` ora porta un campo `vault` con cio' che e' dichiarato e se risolve ancora. E un cockpit
  senza intestazione `## Active Priorities` (misurato: le priorita' ci sono, l'intestazione era
  finita dentro una riga di prosa) diventa una **domanda** in `propose`, mai una scrittura: quali
  siano le priorita' e in che ordine lo dice il founder, non questo strumento.

- **La prova non e' piu' un falso verde** (`init` 0.2.0 → **0.3.0**). Il passo 4 risolveva il pack
  PRIMA del commit: il pack sigilla contro l'albero committato, quindi a `HEAD` senza backbone
  stampava `CTX-UNKNOWN` con `documents: 0` ed usciva **0** — sembrava riuscito e non lo era. Ora
  il commit (pathspec: triade + `decisions/`) sta prima del resolve, e la sezione «Proof it
  worked» legge i **valori**: `workspace` diverso da `UNKNOWN` e `documents: 3`, non l'exit code.
  Due test lo fissano. Dichiarato anche che `VAULT_UNDECLARED` non e' raggiungibile da qui: il
  passo 1 si ferma prima, e la skill stampa la riga di rimedio invece di fingere di gestirlo.

- **Il brief STAMPA le righe del pacchetto, non le riassume** (`start` 1.9.0 → **1.10.0**).
  Misurato end to end su un repo ospite con una sessione fresca: `brief_signals.py` emette 42 righe
  `layer:` e 3 righe `UNKNOWN:`, e il brief reso ne portava **zero** — una frase al posto di tutto
  («DOMAIN.md e' assente, quindi il pacchetto non e' filtrato per area»). Il resolver funzionava, il
  tubo era collegato, e il contesto moriva nell'ultimo metro. Il passo 6 diceva solo che le righe
  `layer:` «sono il pacchetto dell'area scelta»: descrivere non e' consegnare. Il passo 4 ora
  prescrive una sezione `**Pack**` con le righe copiate **verbatim** — prima `UNKNOWN:`/`AREA:`/
  `QUESTION:`/`RECEIPT:`, poi una riga `layer:` per riga, nell'ordine emesso — con un tetto
  dichiarato: oltre **40** righe si stampano le prime 40 e una riga `… and <K> more rows`, mai un
  taglio silenzioso. Una riga `layer:` e' un INDIRIZZO: una frase sulle righe non e' il contesto, e'
  la sua perdita. Il test e' dichiarato per quello che e': una **guardia**, non una prova — nel
  pacchetto non esiste un renderer, il brief lo rende il modello, quindi si tiene che l'istruzione
  dica «verbatim» e dichiari il tetto in entrambi i posti dove un lettore guarda.

- **Il brief trova il resolver anche quando l'harness non e' nel repo ospite** (`start` 1.8.0 →
  **1.9.0**). Misurato su due repo prodotto: il compiler del vault rispondeva gia' con un pacchetto
  intero (29 e 34 righe `layer: declared` — `CONTEXT.md` in prosa piu' gli ADR), e `/start` non ne
  mostrava **una**. Il tubo non era collegato: il pacchetto cercava
  `scripts/contextpack_dashboard.py` DENTRO il repo ospite e pretendeva un `decisions/manifest.json`
  che nessun repo prodotto ha. Ora il resolver si cerca prima nell'host — chi spedisce il suo
  compiler lo possiede — e poi nel **vault che il repo dichiara** (`$POLARIS_VAULT`, altrimenti
  `git config polaris.vault`, dichiarazione LOCALE che non viaggia in un commit): lo stesso
  contratto che `arch_doctor_sources.vault` tiene nel vault, non un secondo modo di dire la stessa
  cosa. Nessuno dei due presente resta **silenzio** (#155), e un vault dichiarato che non ha piu'
  lo script e' quello stesso caso, mai un errore; un resolver che rifiuta resta rumoroso
  (`PACK: blocked — <CODE>`, DB-FR-05). Il requisito del manifest **cade**: un pacchetto in prosa,
  strato `declared` con `freshness: UNKNOWN` dichiarata riga per riga, e' valido per contratto
  (polaris-os#403) — a rifiutare ci pensa il resolver, non un pre-check del pacchetto. Il reperto
  meno ovvio del giro: il pacchetto va compilato sul **checkout** (`git rev-parse --show-toplevel`),
  non su `$ROOT`, che e' la cartella del contratto `_polaris/`; i documenti tipati stanno ACCANTO ad
  essa, e compilando dentro di essa gli stessi due repo rispondevano **0** righe `declared` invece di
  29 e 34. Dal primo giro di review, quattro cose che mordono: il test del checkout passava anche
  sbagliando, perche' `assertIn` su tutto lo stdout e' contento di `<repo>/_polaris` (ora confronta la
  riga intera); la precedenza host→vault non aveva prova, e ora un host che RIFIUTA vince su un vault
  sano, perche' chi spedisce il suo compiler possiede la risposta; un `polaris.vault` relativo veniva
  risolto contro la cwd del processo e un `~` non veniva espanso — entrambi finivano in SILENZIO, la
  sola risposta indistinguibile da un repo che non ha dichiarato niente; e l'output non-UTF-8 di un
  resolver uccideva **tutta** la brief con un `UnicodeDecodeError`, non solo il pacchetto. In piu' la
  riga di rifiuto ora nomina il resolver che ha rifiutato. `reference/two-stage-brief.md` spiega i due posti e il pacchetto in prosa una volta sola.

- **Dopo una compaction il pacchetto torna dalla ricevuta, non da un secondo calcolo**
  (`start` 1.7.0 → **1.8.0**). Una compaction svuota la finestra di contesto e non tocca niente su
  disco: il pacchetto era gia' risolto, e rifarlo significa ricamminare il tracker in rete per una
  risposta che non e' cambiata. Il passo 3b chiede invece al repo ospite di **rimetterlo davanti**
  (`contextpack_reinsert.py reinsert`): a `HEAD` fermo ristampa le righe della ricevuta con **zero**
  chiamate al tracker; solo un `HEAD` avanzato paga una riemissione, e la seconda ricevuta si mette
  ACCANTO alla prima nominandola in `CHAIN: prev=` — cosi' cio' che l'agente aveva PRIMA della
  compaction resta auditabile. Ricevuta assente o ricevuta di un'altra area sono costi dichiarati
  (`RECEIPT_MISSING`, `AREA_MISMATCH`), non errori: si riemette e si esce 0. Il passo porta anche
  l'hook dell'host (`SessionStart` con matcher `compact`), perche' un meccanismo che dipende dal
  fatto che qualcuno se lo ricordi non e' un meccanismo. Dal giro di review: l'hook era **JSON in
  prosa**, e il JSON in prosa non installa niente — ora sta in `templates/settings.team.json`, che
  pero' non aveva **nessun** installer (il suo, `pol-bootstrap`, e' stato rimosso e il template era
  orfano insieme al preset dei permessi). Il passo 2 chiama `scripts/install_settings.py`, che fonde
  senza mai sovrascrivere e al secondo giro non cambia nulla; il suo `--selfcheck`, agganciato a
  `check_skills.sh`, **esegue** il comando dell'hook due volte — senza resolver (muto, exit 0) e con
  un resolver (lo lancia) — perche' un hook e' una stringa finche' qualcuno non lo esegue. Il `sid`
  non e' un flag da riempire: il comando risolve da solo la sessione aperta oggi. Detto onestamente:
  **oggi vedrai `NO_OPEN_SESSION`**, perche' una ricevuta del pack appartiene a una sessione e il
  `/start` spedito non ne apre ancora una (polaris-os#155); l'hook resta cablato e silenzioso finche'
  quello non atterra. Il pacchetto non trasporta l'harness: senza resolver dell'host non stampa nulla
  (contratto #155). `reference/two-stage-brief.md` spiega le righe una volta sola, comprese le sei
  che dicono che la ricevuta non era affidabile e cosa vale davvero la catena.
  Dal secondo giro di review, il reperto peggiore di tutto il task: l'installer **distruggeva** il
  file che prometteva di non toccare. Un `.claude/settings.json` con una parentesi di troppo non
  parsava, il merge partiva da `{}` e ci scriveva sopra il template — via la `deny` list, il
  `model`, i permessi e gli hook di ogni altro plugin, senza backup e con una scrittura non
  atomica. Ora un file che esiste, non parsa e non e' vuoto ferma l'installazione
  (`SETTINGS_UNREADABLE`, exit 1, niente scritto), la scrittura e' atomica, e il `--selfcheck`
  tiene giu' entrambe le meta': che un file malformato non venga toccato, e che su un file sano
  sopravvivano `deny`, `model` e gli hook altrui. (polaris-os#406)

- **`/start` a due tempi: l'indice delle aree prima, il pacchetto dell'area dopo — e mai piu' una
  riga opaca** (`start` 1.6.0 → **1.7.0**). Il brief portava `PACK=CTX-<id>`, e polaris-os#326 ha
  misurato quanto vale un id opaco: l'agente lo ignorava, quindi il resolver era invisibile proprio
  alla sessione per cui esiste, e l'indice del repo restava a voce. Ora `emit_pack` esegue il brief a
  due tempi dell'host e stampa cio' che risponde: **tempo 0** una riga per area con tre conteggi —
  issue aperte, PR aperte, ultima Decision (`AREA: <slug>  issues: N  prs: N  last_decision: …`), piu'
  la priorita' 1 del cockpit; **tempo 1** il pacchetto dell'area scelta **per righe**
  (`layer: … source_id: … path: … freshness: …`), su cui si agisce. La scelta dell'area segue tre
  segnali (branch, issue aperte del contributor, priorita' 1) e quando nessuno risponde il brief porta
  `QUESTION: which area? candidates: …`: **una** domanda con l'indice davanti, mai un'ipotesi. Un
  conteggio che nessuno ha potuto leggere e' `UNKNOWN`, mai uno zero inventato. Il pacchetto non
  trasporta l'harness: senza il resolver dell'host la riga non esiste (contratto #155 invariato), e un
  resolver che rifiuta resta rumoroso (`PACK: blocked — <causa>`). Niente comincia piu' per `PACK=`.
  Il passo 6 instrada le tre forme di riga e `reference/two-stage-brief.md` le spiega una volta.
  Dal giro di review: **un repo senza mappa d'area non perde il pacchetto** — non c'e' nulla da
  chiedere e nulla su cui filtrare, quindi il brief dice `UNKNOWN: no area map — unfiltered pack` e
  consegna il pacchetto intero, che e' il caso di ogni repo appena adottato; `ISSUES_UNLABELLED`
  accanto a `PRS_UNLABELLED`, perche' una label come `P1` non e' un'area e quattro aree leggevano
  `issues: 0` senza dirlo; l'indice resta consegnato anche quando il pacchetto rifiuta; e
  `RECEIPT: none — no open session` dice quando le righe sono vere e nessuno ha registrato di
  averle consegnate. (polaris-os#405)
- **`/end` non chiude su una decisione che non ha casa, e i sei campi del log sono i cinque elementi
  del confine ripartibile** (`end` 1.19.0). Le sei righe erano un formato gradito; sono ciò che rende
  la sessione ripartibile, e la sessione dopo apre da lì. Ora la skill nomina la corrispondenza
  (scope e decisioni → `Key context`; stato e prossimo → `In progress` + `Next session`; file e
  albero → `Files`; verifiche ed esito → `Done`; domande aperte → `Blocker`), dichiara che un campo
  vuoto si scrive `none` e che un campo **assente** è il confine rotto, e aggiunge il rifiuto: una
  clausola taggata `#decisione` o `#superata` deve nominare la Decision, la voce di `decisions.md` o
  l'issue che la porta — una ritrattazione compresa, che va accanto al numero. Dove il repo porta il
  gate del backbone la regola è eseguibile e i suoi sei rifiuti sono elencati; dove non c'è, un solo
  rigo di degrado e le sei righe restano la checklist. **Il guard era invertito:** la catena
  `[ -f ] && … || echo` trasformava ogni rifiuto del gate in «nessun gate» con exit `0`, e la skill
  proseguiva al commit proprio nei casi che il gate esiste per fermare; ora è un `if`/`else` e un
  rifiuto ferma `/end`. La forma dell'issue è scritta per esteso (`issue:<repo>#<numero>`, mai il
  numero nudo) perché era l'unica accettata dal gate mentre la skill diceva solo «nomina l'issue»:
  chi seguiva la skill veniva rifiutato. Gate e test vivono nel repo dell'harness, non qui.

- **`/update` riscritta nella forma Osmani, e il cockpit lo aggiorna il modello, non uno script**
  (`update` 3.0.0). Prova misurata su una repo cliente: **14** sezioni `## Open` impilate, **13**
  righe `Updated:`, **6** righe per `main` — con la regola «una riga per lane» scritta in prosa da
  settimane e `state_upsert.py` obbligatorio nel passo. Lo script guardava solo la PRIMA `## Open`
  (3 righe su 228), sostituiva lì e dichiarava successo; la chiave era la stringa tra backtick, non
  la lane, quindi un nome diverso appendeva in silenzio e un `main` di un altro repo sovrascriveva.
  Founder: «/update deve vedere che lane ci sono e aggiornare quella sua; se non c'è nulla della sua
  lane ne crea un'altra». Ora il passo 4 dice esattamente questo: leggi `## Open`, se una riga è il
  tuo lavoro (anche con altro branch, anche di un altro pannello) la riscrivi, altrimenti ne aggiungi
  una; una sola `Updated:`; tutto il resto byte-identico. La skill passa da 245 a 153 righe con la
  forma `Overview → When to Use → Process → Rationalizations → Red Flags → Verification`.
  `state_upsert.py` resta nel bundle per `state_close.py`, `prune_threads.py` e i selfcheck, ma
  nessun passo di `/update` lo invoca più. Nasce `eval/checks.json` (prima skill del pacchetto ad
  averlo: il `change_gate` chiedeva T3 e nessuna skill poteva rispondere).

- **Il resolver del ContextPack viaggia nel pacchetto** (`polaris-os#344`). Fino a ieri una repo
  che installava il pacchetto riceveva le porte e nessun modo di emettere un pack: `contextpack.py`
  e il validatore del backbone che importa vivevano solo nel vault. Ora `polaris/scripts/` porta
  `contextpack.py`, `check_context_backbone.py`, `check_decision_execution.py`,
  `decision_probe_shadow.py`, `area_map.py`, `skill_outputs_check.py` e i loro test, copiati dallo
  stesso `sync_package` che porta le porte — una sola direzione, la stessa guardia di perimetro
  sui byte spediti, e `--check` rosso appena le due copie smettono di essere identiche.
  Il layout e' **specchiato**, non tradotto: un test sta in `scripts/test/` nel vault e in
  `polaris/scripts/test/` qui, quindi `parents[2] / "scripts"` trova la CLI da entrambe le parti e
  nessuna riga viene riscritta per strada.
- **Otto porte invece di sette** — `architecture` e `real-testing` entrano nel pacchetto.
  `architecture` era esclusa da un `lifecycle:` scalare che conteneva `": "`: per YAML e' una
  mappa annidata, e l'installer scartava la skill intera in silenzio.
- **`marketplace.json` lo scrive il sync**, da cio' che ha appena spedito. Era una lista a mano, e
  otto porte in un colpo l'hanno resa falsa insieme al test di release che la controlla.
- **Il contratto minimo per emettere un pack e' eseguibile**: `polaris/scripts/test/
  test_contextpack_empty_repo.py` costruisce una repo da zero, scrive le tre autorita' vive piu'
  una Decision `accepted`, sigilla con `--reseal` e `--init` e ottiene un `CTX-…`.
  `_polaris/config.yml` non serve al resolver, e il test lo prova non scrivendolo.

- `end` 1.15.0 → **1.16.0** · `update` 2.15.0 → **2.16.0** — `/end` elenca le PR aperte
  dell'autore e dice quali portano gia' la loro ragione nel cockpit
  (`checkpoint.sh open-prs`). Chi apre una PR la porta al merge: una PR lasciata aperta a
  fine sessione va in conflitto con la lane dopo. **Non rifiuta mai** (decisione founder,
  2026-09-06): esce `0` in ogni ramo — PR senza ragione, nessuna PR, `gh` assente, tracker
  che rifiuta. Un gate che blocca la chiusura e' un gate che si aggira, e una sessione
  chiusa male perde l'handoff, non solo la lista delle PR.
- `end` 1.16.0 → **1.17.0** — l'audit ADR di Step 3 cercava ogni record in `docs/adr/NNNN-<slug>.md`.
  **Quella casa non esiste** nel vault che spedisce questa skill, e in una repo ospite qualunque è
  un'ipotesi: l'audit girava contro una directory vuota e non trovava mai una decisione mancante —
  un backstop che non può fallire. Ora legge la riga `decision:` della mappa `outputs:` del contratto
  ospite (`write-contract`, `polaris-os#284`), e senza mappa guarda dove quella repo tiene già le sue
  scelte durevoli **dicendo dove ha guardato**. Trovato dal cancello nuovo
  `check_named_houses.py` (polaris-os), non a occhio.

## 0.25.2 — 2026-09-05

- `update` 2.14.0 → **2.15.0** — `checkpoint.sh commit` porta anche **l'handoff di oggi**, se esiste.
  Prima prendeva solo il session log, quindi l'handoff restava untracked e dipendeva da `/end`:
  esattamente ciò che DB-FR-07 vieta — *«no durable information may depend on `/end`, because the
  founder does not reliably end sessions»*. Misurato su una sessione reale il 2026-09-05: l'handoff
  prioritario è rimasto fuori dal commit, e senza un intervento a mano sarebbe morto lì.
  Un handoff **assente** non è un errore, e uno di **ieri** non viene trascinato dentro: appartiene
  alla sessione che lo ha scritto.

## 0.25.1 — 2026-09-05

Igiene, nessun cambiamento di comportamento. `#20` e `#21` hanno cambiato sette skill senza alzare
nessuna versione: il pacchetto dichiarava `start 1.5.0` mentre spediva uno `start` diverso. **Una
versione che mente è peggio di una assente**, perché chi confronta due installazioni conclude che
sono uguali.

- `start` 1.5.0 → **1.6.0** — `emit_pack` esegue il resolver; i template vivono dentro la skill.
- `update` 2.13.0 → **2.14.0** — `_selfcheck_parts` risolve i template sulla radice delle skill.
- `end` 1.14.0 → **1.15.0** — `prune_threads` segue i template spostati.
- `plan-week` 1.3.0 → **1.4.0** · `report` 1.2.0 → **1.3.0** — riferimenti ai template aggiornati.
- `polaris-status` 1.2.0 → **1.3.0** — `wiki_quality_check.py` vive dentro la skill.
- `pol-apex-curate` 1.0.0 → **1.1.0** — `mcp/` vive dentro la skill.

**Regola (founder, 2026-09-05):** ogni cambiamento a una skill alza la sua versione e lascia una
riga qui, **nella stessa PR che lo introduce** — mai nel rilascio successivo.

E la regola ha un cancello, perché una regola che nessuno verifica torna a rompersi:
`polaris/scripts/check_skill_versions.py <base-ref>` rifiuta una skill toccata e ferma. Provato
contro la storia vera: su `59ecfef` avrebbe elencato **tutte e sette**.

## 0.25.0 — 2026-09-05

- `fix(start)`: il segnale del pack **esegue** il resolver invece di leggere una chiave che nessuno
  scrive. `emit_pack` apriva `decisions/manifest.json` cercando `pack_id`, chiave che il manifest
  vivo non ha: la riga era morta in ogni repo reale, e il test si scriveva da solo il file che poi
  leggeva. Ora esegue `contextpack.py resolve` e riporta il `context_pack_id` vero; una emissione
  bloccata e' rumorosa (`PACK=BLOCKED:<causa>`). (#20)
- `fix(package)`: **cio' che una skill nomina viaggia dentro la skill.** `npx skills` installa solo
  `skills/`, quindi `templates/`, `mcp/` e `wiki_quality_check.py` non arrivavano mai: il
  provisioning del primo `/start` falliva con exit 1, `plan-week` e `report` restavano senza
  template, e quattro selfcheck spediti crashavano. Ogni file vive ora dentro la skill che lo usa, e
  un test gira su un albero a forma di **installazione** invece che di repository. (#21)

## 0.24.0 — 2026-09-04

### Changed
- `update` 2.13.0 / `end` 1.14.0 / `start` 1.5.0: **il log di sessione si committa sul branch
  corrente, sempre** (decisione founder, 2026-09-04). Un `/end` che rinvia invece di committare è un
  `/end` che non ha lavorato. `session_commit.sh` non guarda più quale worktree sta su quale branch:
  committa nel checkout in cui gira, sul branch che quel checkout ha, con il pathspec esatto dei soli
  file di sessione passati e `git commit -- <paths>` invece del commit dell'indice, così ciò che un
  altro pannello aveva staged resta staged e fuori dal commit. Restano **due eccezioni dichiarate**,
  exit 2 e una riga che dice quale, con i file lasciati dove la sessione li ha scritti e nessuna copia
  altrove: HEAD staccato, e `polaris.commit-policy no-direct-default` mentre si è sul default branch
  (la stessa policy su un branch qualsiasi non si applica). Un repo senza alcun commit **non** è
  un'eccezione: `git commit -- <path>` accetta un branch unborn, quindi il primo checkpoint di un
  repo nuovo atterra. Un hook che rifiuta resta exit 1 con la sua riga, indice ripulito dei soli path
  Polaris e mai `--no-verify`.

- `update` 2.13.0 / `end` 1.14.0 / `start` 1.5.0: **il log vive e si committa dove gira il pannello;
  il cockpit vive nel worktree principale** (gate polaris#17, G1). `checkpoint.sh` ed
  `resume_paths.sh` risolvevano `ROOT` sul worktree PRINCIPALE e `/end` apriva con `cd "$MAIN_WT"`:
  da un worktree secondario il session log finiva sul branch del checkout principale — l'incidente
  che questa PR chiude, con un'altra forma. Ora `ROOT` è il contratto di QUESTO worktree, quindi
  log, handoff e tick del piano nascono e atterrano sul branch su cui la sessione è avvenuta, e solo
  `CURRENT` (il cockpit, gitignored) resta a casa unica nel principale, insieme a scratch, `due.md`
  e radar. Riprodotto: sessione su `feat/mine`, principale parcheggiato su `feat/main-panel`, HEAD
  del principale invariato dopo il commit.
- `update` 2.13.0: **un path che git rifiuta è dichiarato e non uccide l'handoff** (gate polaris#17,
  G2). Un log gitignorato o un journal dentro un `.wiki/` che è un repo annidato dava exit 0 «no
  session-state change, skip» oppure exit 1 sull'intero set. Ora esce 2 con
  `session_commit: git refuses <path> (ignored|nested repo) — not committed` e **gli altri path del
  set atterrano comunque**. `git add` da solo non era il test: dentro un repo annidato ritorna 0 e
  non stage niente, e il pathspec faceva poi saltare tutto il commit — decide l'indice.

### Removed
- **Lo spool di rinvio** (`session_spool.sh`, `.git/polaris-deferred`, il drain, `_wt_on_default`,
  `_wt_count`, `_main_wt_branch`, `_defer_no_default`, `_drop_landed`, la consegna a un worktree
  fratello sul default). Tre settimane di macchinario di rinvio il cui output affidabile era un
  working tree lasciato sporco e un messaggio rassicurante. `session_commit.sh` scende da 199 a 141
  righe e la deriva «due checkout e nessuno sul default» sparisce con il codice che la produceva.
- I test che asserivano il rinvio (`test_worktree_defer.py`, `test_worktree_count.py`): il loro
  soggetto non esiste più. Le stesse forme di repo — un checkout, tre worktree, un fratello sul
  default — sono coperte da `test_commit_here.py` con l'aspettativa nuova.

### Fixed
- `start` 1.5.0: il segnale `DEFERRED=` diventa **`SPOOL_LEGACY=`** e cambia significato — non più
  «entry in attesa di drenaggio», ma «entry lasciate da una versione precedente, portale a mano con
  `git add`». `checkpoint.sh prepare` stampa la stessa riga e non tocca la cartella.

## 0.23.0 — 2026-09-04

### Fixed
- `start` 1.4.0: **`resume_paths.sh` quotes what it prints** (`polaris#14`). Step 1b `eval`s that
  output, and the values went out bare, so a checkout under a directory with a space in its name
  split into words and `/start` died with «command not found» on the founder's own vault. `printf
  '%s=%q\n'` round-trips a space, an apostrophe and a `$` byte-identically; the Step 1b line in the
  SKILL body is unchanged. Fixtures: a repo under `Dir With Spaces` and one under `it's $HOME repo`.
- `update` 2.12.0: **two checkouts and neither on the default branch is not «one checkout»**
  (`polaris#12`). `_wt_on_default` comes back empty when no SIBLING can take the commit, and
  `session_commit.sh` read that as "there is only me": from a linked worktree it committed the
  session onto whatever branch another panel had parked the MAIN checkout on, and drained the spool
  onto it as well — measured live on 2026-09-04, a commit on a foreign branch carrying a session log
  from another day. With a second checkout present it now defers: 0 commits, the entry in the spool
  `/start` counts, and the reason names the branch the main checkout is on. A repo with ONE checkout
  still commits on its current branch, with exactly the file the run wrote.
- `update` 2.12.0 / `start` 1.4.0: **one registry of section names** (`polaris#11`). `state_lines`
  now declares the names the package expects and the rule for matching them, and `state_upsert`,
  `brief_signals`/`_brief_parts` and `recent_context` read that instead of compiling a heading each.
  A heading QUALIFIES a declared name after a dash, a colon or a parenthesis, so the vault's
  `## Open — thread vivi` is `## Open`; `## Active Priorities` is still not `## Active`, and a
  translated heading is still reported `SECTIONS_MISSING`. A new row now lands among the rows, not
  at the end of the span: the live cockpit closes its threads with an `Owner:` line and the new lane
  was written under it. With no recognised section the writer refuses with exit 2, names the heading
  it expected, and leaves the file byte-identical. The registry is a new module,
  `skills/update/scripts/state_sections.py`, so `state_lines.py` stays byte-identical with the
  vault copy the wiring gate compares; `state_upsert.py`'s fixtures moved next door into
  `state_upsert_selfcheck.py`, the same split `session_commit_selfcheck.sh` already uses, which
  keeps every touched file inside the 200-line limit. Gate round 2 finished the job: `state_close`,
  `todos_roll` and `prune_threads` read the registry too, so a `todos.md` headed
  `## Active — settimana 36` is no longer written by `/update`, counted by `/start`, ignored by
  `plan-week` and refused by `/end` all at once — and a cockpit headed `## Open threads` is refused
  by every one of them instead of being written by none and pruned by one. `grep 're.compile(r"^#'`
  over the shipped scripts now finds exactly one file. A qualifier must start with whitespace, so
  `## Open-source backlog` is its own section, and a section whose only content is a multi-line HTML
  comment takes the new row after the closing `-->` instead of inside the comment.
- `update` 2.12.0: **a worktree whose directory was deleted is not a checkout.** `git worktree list`
  keeps reporting it until someone prunes it; counting it made a repo with ONE real checkout defer
  every single run, so the session log never landed and the deferral became the data loss it exists
  to prevent. `prunable` and `bare` entries are skipped.
- `end` 1.13.0: the census vocabulary line names `MAIN` as a bare word again, so the vault's
  `test_end_speaks_the_census_contract_that_actually_runs` can see it.

## 0.22.0 — 2026-09-04

### Fixed
- `update` 2.11.0 / `end` 1.12.0: **the shipped `/end` blocks are executed by the suite, not
  grepped.** `polaris/tests/test_end_runs.py` reads Step 4, Step 5, `Recent Context` and the lane
  phase out of the SKILL body with `skill_block` and runs them on a host repo built from the
  templates, the way `test_update_gates` has always done for `/update`. It found two contract
  breaks on the first run. Step 4 passed `--todos "$ROOT/state/todos.md"` unconditionally, and the
  contract does not require that file: on a repo without one — the shape the templates build — every
  close came back `UNWRITABLE` and the prune removed nothing, while the same SKILL promised a
  `"todo": "skipped"` path that only fired when the flag was empty. And Step 5's `git add` refuses
  the WHOLE pathspec when one named file is absent (exit 128, nothing staged), so a weekly plan
  never opened silently landed the entire handoff nowhere.
- `update` 2.11.0: **a refused commit no longer leaves the handoff staged.** With branch protection
  the repo has not declared — a `pre-commit` hook that exits 1 on the default branch — the error was
  honest but the files this script had just `git add`ed stayed in the index, so the next commit
  without a pathspec swallowed the handoff: the AC4 regression, moved one step later. The index is
  restored and the files go to the spool.
- `update` 2.11.0: **a worktree can no longer hand work to itself.** On a detached or unborn HEAD
  `git rev-parse --abbrev-ref HEAD` says `HEAD` while `git worktree list` still reports
  `branch refs/heads/main`, so the dispatch delegated to the tree it was already in and recursed
  until killed (pre-existing on `origin/main`: 205 identical lines in 15s). A detached HEAD now
  defers with its reason, because a commit reachable only through the reflog is not a landed handoff.
- `end` 1.12.0: **a thread citing two PRs closed on the first one.** `cite()` used `search`, so
  «chiude #77, poi #79» closed the moment #77 merged. Every citation is resolved now, and the worst
  answer wins: one open citation keeps the whole lane.
- `end` 1.12.0: **a failed close no longer silences the rows after it.** `bad = bad or (...)`
  short-circuited the loop, so a lane could be left unclosed and unmentioned. Every PROVEN row is
  attempted and reported; the run still exits 2 if any failed.
- `update` 2.11.0: **closing takes the whole lane.** A closed thread left its indented children and
  its fenced resume command orphaned under `## Open` — residue the next session had to reconcile.
- `update` 2.11.0: **`drop_placeholder` respected the fence.** It deleted a placeholder-shaped line
  sitting inside a code block, against `state_lines`' own invariant that nothing inside a fence is
  structure. It asks `kinds()` now, like every other writer.
- `update` 2.11.0 / `end` 1.12.0: **`/end` leaves the working tree clean** (`polaris-os#202` AC4).
  `session_commit.sh` used to defer on any branch that was not the default, on the assumption that
  another session on the default branch would land it. On a repo with ONE checkout parked on a
  feature branch that session never comes: measured on 2026-09-03 with the shipped skills, after
  `/end` the log sat staged and the handoff untracked, `git status --short` returned two lines
  while both skills reported success, and the next session swallowed the log into its own unrelated
  commit. Three cases now, decided in code: a sibling worktree already on the default branch takes
  the commit and this tree keeps no untracked copy of what it handed over; **one checkout commits on
  its own branch**, pathspec-only; a repo that declares `git config polaris.commit-policy
  no-direct-default` gets `deferred` with 0 commits and the entry in the spool `/start` counts —
  never a forced commit (`polaris-os#141`). What was already staged by another panel comes back
  exactly as it was, in every case.
- `update` 2.11.0: **an absolute pathspec survived the hand-off to a sibling worktree.** `/end`
  names its files absolutely; the delegated worktree was then asked to `git add` a path outside
  itself, git refused, and the run reported `no session-state change on main, skip` while the
  handoff sat uncommitted. Paths are normalised to repo-relative at the one door in. Caught by
  `tests/real_session_commit.sh` R2, not by a unit test — the harness passes what the skill passes.
- `end` 1.12.0: **`git config polaris.vault_root` never existed.** git refuses a config key
  containing an underscore, so the declared cross-repo `## Recent Context` copy was a branch that
  could not run on any machine. The key is `polaris.vault-root`.
- `end` 1.12.0: **`post-push` on a repo with no remote.** `git-power phase post-push` answered
  «push presente ma nessuna PR verificabile» where nothing had been pushed because there is nowhere
  to push — a refusal that reads like a broken branch. `end/scripts/lane_phase.sh` now holds both
  guards (no remote, no `git-power`) for the two sites that ask the question.
- `update` 2.11.0: **the contract's example thread is no longer a permanent lane.** The template
  ships `- \`<branch>\` (<repo>) — <state in one line> · since YYYY-MM-DD` so `## Open` is never an
  empty heading; it survived every session, and `/end` could never close it (there is no branch to
  prove merged). The first real `state_upsert thread` removes exactly that line, and only it.

### Added
- `end` 1.12.0: **automatic removal of a thread whose PR provably merged**, replacing the declared
  manual step. The defect that parked it was real — a truth built on `bool(merged)` reports success
  and removes nothing, because the local branch ref is gone after a merge with `--delete-branch` —
  so `end/scripts/merge_truth.py` requires TWO sources to agree: the tracker (`gh pr view N` says
  `MERGED`, or `gh issue view N` says `CLOSED` for `COMPLETED`) and this checkout (that PR's head,
  or its merge commit, is an ancestor of the default branch HERE). Four verdicts, never two:
  `PROVEN` leaves `## Open` and lands in `## Completed` with its verdict appended to the session
  log; `AMBIGUOUS` is a merge this checkout cannot see, or a branch carrying commits past its merged
  head — a reused lane is alive, not closed; `OPEN` is a PR that is not merged; `BLOCKED` is a
  tracker that cannot be read at all, and **one `BLOCKED` stops the whole run** with exit 2 naming
  the line, because a prune that removes four lanes and quietly skips the fifth is the same silent
  no-op inverted. `end/scripts/prune_threads.py` applies it; `state_close.py candidates` stays the
  read-only list and no longer claims removal is parked.

## 0.21.0 — 2026-09-04

### Added
- `start` 1.3.0: **the three signals the system already computed and never showed**
  (`polaris-os#243`), plus the two surfaces the donor's four-file form landed with no reader
  (`#240`). One shipped script, `start/scripts/brief_signals.py`, prints a line ONLY when it has
  something to say: `TODOS_ACTIVE`/`TODO`/`FOLLOWUP_DUE` from `state/todos.md`, `RECENT` from the
  `## Recent Context` ring, `DEFERRED` (the `polaris-deferred` spool, counted under the git COMMON
  dir so a worktree sees the same number), `DRIFT` (the branch the MAIN worktree is parked on plus
  the count of modified files that are not this contributor's) and `SECTIONS_MISSING`. A repo
  without `state/todos.md` gets one line and exit 0, never an error.
  **Feature-detect for the typed backbone** (`#155`): `PACK=<id>` appears only where the host repo
  carries both `decisions/manifest.json` and `scripts/contextpack.py`; everywhere else the brief is
  exactly what it was. The `/start` word budget moved 900 → 940 ONCE for this step, declared in the
  test; the byte cap did not move.
- `end` 1.11.0: **`## Recent Context` is a real ring again** — `update/scripts/recent_context.py`,
  cap 5, newest first, idempotent, and every byte outside the section comes back identical. It
  replaces the per-repo `state/current-state.md` append: that surface was measured at 188 KB /
  93 blocks, last written nine days before anyone noticed it had died. `current-state.md` survives
  ONLY as the declared cross-repo vault copy (`git config polaris.vault_root`), explicitly not a
  cockpit and never authority.
- `end` 1.11.0: **closing means removing** — `update/scripts/state_close.py close` takes the thread
  out of `## Open`, moves its `state/todos.md` row from `## Active` to `## Completed` with today's
  date, and collapses `Updated:` to date and owner. An unknown key exits 2 and touches nothing.
  Automatic removal stays PARKED on `polaris-os#268` (`merge_truth` answers `None` once the branch
  ref is gone, the normal case after `--delete-branch`): `state_close.py candidates` lists the
  threads citing an issue or a PR, read-only, and the human closes them one line at a time.
- `update` 2.10.0: **the todo of the week follows the thread** — a checkpoint that advances a row in
  `state/todos.md` updates THAT row through `state_upsert.py week`, carrying its original `· Added:`
  stamp. The stamp is the age signal; re-stamping makes three-week-old work read as news.
- `plan-week` 1.3.0: Step 6b now reconciles `state/todos.md` (the live view) instead of writing
  `## Active` into the weekly plan, which has no such section — the merge could never have run.
  `## Completed` is rolled to the current week only (`state_close.py week-roll`); `## Active` is
  never zeroed and `## Follow-ups`, the only section that crosses weeks, is never touched.
- Templates for the host repo's state contract: `templates/repo-contract/state/{current,todos,goals}.md`.
  `todos.md` is the donor's TABLE form, the same shape `polaris-os#240` seeded, footer included.
  The one fence-aware line parser learned a `table_row()` branch (`state_lines.py`) rather than the
  package growing a second notion of "line" — that second notion is the root cause that once made
  seven state writers disagree, and a bullets-only reader had already proved it here: against the
  real `state/todos.md` it reported `TODOS_ACTIVE=0`, lost an overdue follow-up, and `state_upsert`
  appended a duplicate row stamped with this week beside the real one carrying `W32`.
- `todos.md` names its three writers, in the template and in the skills that obey it: `plan-week`
  reconciles `Active` and rolls `Completed`, `/update` refreshes the TEXT of a row the current
  thread cites and may not create one (`state_upsert --no-add`), `/end` moves a landed row into
  `Completed`. None of the three re-stamps `Added`; none empties `Active`.
- `plan-week` 1.3.0 / `update` 2.10.0: `update/scripts/todos_roll.py` — the `Completed` roll, split
  out of `state_close.py` because rolling the week is `plan-week`'s move, not `/end`'s.
- `polaris-status` 1.2.0: the state-health line counts `## Recent Context` entries against the cap
  instead of the blocks of a dense file that no longer exists.

### Fixed
- The shipped line model reads the donor's tables the way the donor writes them, and a section ends
  where the donor ends it. `state_lines.section()` now stops at a horizontal `---` rule, not only at
  a heading or the contract sentinel: the shipped `current.md`/`todos.md` separate sections with
  rules, so a finder that only knew the sentinel ran to EOF — `/end` wrote the `Completed` row
  BELOW the rule, outside the table, and `/update` appended a thread under the contract line. One
  rule, one place, four consumers. An escaped pipe (`a\|b`) is content, not a cell boundary: the
  old split shredded the task name and shifted every later cell left, silently eating the `Added`
  stamp.
- `## Recent Context` dedup compares first line with first line. It compared a SAVED entry's first
  line against a WHOLE incoming block, so it only ever fired on one-line entries: a second `/end`
  in the same session duplicated its own entry and evicted a real session out of the ring.
- `/start`'s `DEFERRED=` signal fires at all. `session_commit.sh` spools NESTED (the repo path under
  the branch it deferred from) and the reader used a flat `iterdir()`, so the count was zero forever
  and the signal never appeared once since it landed.
- `/end` validates the todos file before touching the cockpit, and all THREE `cantiere.py` call
  sites resolve through the same chain with `[ -f ]` and a declared degrade line — two of them
  hardcoded `$HOME/.agents` with no guard and broke a half-finished `/end` with a raw Python error
  on a machine without `git-power`.
- `verify` matches the login EXACTLY: `@adalberto` no longer passes the gate for `ada`.
- `plan-week` keeps the promise `state/todos.md` makes: a `Follow-up` whose Review Date has arrived
  returns to `## Active`, stamped with the week it CAME DUE. The template claimed it, `plan-week`
  denied it, and no code did it.
- `update` 2.10.0: **`verify` binds the cockpit to the run** (`polaris-os#84`). Three bypasses, three
  fixtures: an empty `touch` (mtime moves, nothing else), a cockpit re-dated by hand with nobody's
  name on it, and a cockpit with no `Updated:` line at all while the session logged today. The line
  must carry TODAY and this contributor, and `verify "<title>"` additionally requires that title to
  be the NEWEST entry in the append-only session log — which is what catches a `sed -i` re-date with
  no checkpoint behind it. Per `#240` the `Updated:` line is date and owner ONLY, so the title is
  asserted in the log, not in the line: one fact in each place. Selfcheck 7 → 11 cases.
- `update` 2.10.0: **the first harvest of the day is capped** (`polaris-os#89`).
  `checkpoint.sh harvest-slice <sid>` emits every line carrying this session's id wherever it sits,
  plus the head of the delta up to `HARVEST_CAP` (40). The cap is on the FOREIGN prefix, never on
  position: a positional cap drops exactly the own-id line that arrived last. Measured on the
  issue's fixture: 150-line scratch, 80% foreign → 38 lines read, 30/30 own lines kept.
- Release hygiene (`polaris#5`): the package no longer ships a founder machine path
  (`evals/scripts/replay_tasks.py` now reads `POLARIS_VENDOR_DIR`) or a real GitHub login in a
  fixture (`session_commit.sh` and `tests/real_session_commit.sh` use `acme-dev`). The perimeter
  test walks the tree instead of holding a list, and skips only lines marked `perimeter-guard`.

### Unchanged, and declared
- **The plan tick: RESTORE holds** (`polaris-os#85`) — the state declared in 0.20.0 stands, and it now
  has a gate that proves it: an existing weekly plan left unticked fails `checkpoint.sh verify`.
  `#85` decides the state by counting the hyphenated spelling in this file, which in RESTORE must be
  0: it is written "the plan tick" everywhere, and this note is the reason why.
  The other state is provably absent: nowhere does this changelog declare the tick superseded, and
  the apex `/update` row keeps the words "tick del plan".

## 0.20.0 — 2026-08-18

### Fixed
- The shipped line model reads the donor's tables the way the donor writes them, and a section ends
  where the donor ends it. `state_lines.section()` now stops at a horizontal `---` rule, not only at
  a heading or the contract sentinel: the shipped `current.md`/`todos.md` separate sections with
  rules, so a finder that only knew the sentinel ran to EOF — `/end` wrote the `Completed` row
  BELOW the rule, outside the table, and `/update` appended a thread under the contract line. One
  rule, one place, four consumers. An escaped pipe (`a\|b`) is content, not a cell boundary: the
  old split shredded the task name and shifted every later cell left, silently eating the `Added`
  stamp.
- `## Recent Context` dedup compares first line with first line. It compared a SAVED entry's first
  line against a WHOLE incoming block, so it only ever fired on one-line entries: a second `/end`
  in the same session duplicated its own entry and evicted a real session out of the ring.
- `/start`'s `DEFERRED=` signal fires at all. `session_commit.sh` spools NESTED (the repo path under
  the branch it deferred from) and the reader used a flat `iterdir()`, so the count was zero forever
  and the signal never appeared once since it landed.
- `/end` validates the todos file before touching the cockpit, and all THREE `cantiere.py` call
  sites resolve through the same chain with `[ -f ]` and a declared degrade line — two of them
  hardcoded `$HOME/.agents` with no guard and broke a half-finished `/end` with a raw Python error
  on a machine without `git-power`.
- `verify` matches the login EXACTLY: `@adalberto` no longer passes the gate for `ada`.
- `plan-week` keeps the promise `state/todos.md` makes: a `Follow-up` whose Review Date has arrived
  returns to `## Active`, stamped with the week it CAME DUE. The template claimed it, `plan-week`
  denied it, and no code did it.
- `update` 2.3.0: **the plan tick is back — the SECOND undeclared drop of the v2.0.0
  rewrite (498ed70), restored by founder verdict (polaris-os#85: plans are the roadmap).**
  Owed ONLY when `team/<login>/weeks/<current-week>.md` exists: absent file, zero noise
  (no gate that fails on nothing); present and untouched by the checkpoint, `verify`
  FAILs naming the file. `prepare` now prints `WEEKLY=` and `commit` takes N paths so
  the ticked plan lands with the session log in one pathspec-only commit. Fixture-proven:
  no-weekly pass · untouched-weekly exit 1 · ticked pass · multi-path commit.

## 0.19.0 — 2026-08-18

### Fixed
- The shipped line model reads the donor's tables the way the donor writes them, and a section ends
  where the donor ends it. `state_lines.section()` now stops at a horizontal `---` rule, not only at
  a heading or the contract sentinel: the shipped `current.md`/`todos.md` separate sections with
  rules, so a finder that only knew the sentinel ran to EOF — `/end` wrote the `Completed` row
  BELOW the rule, outside the table, and `/update` appended a thread under the contract line. One
  rule, one place, four consumers. An escaped pipe (`a\|b`) is content, not a cell boundary: the
  old split shredded the task name and shifted every later cell left, silently eating the `Added`
  stamp.
- `## Recent Context` dedup compares first line with first line. It compared a SAVED entry's first
  line against a WHOLE incoming block, so it only ever fired on one-line entries: a second `/end`
  in the same session duplicated its own entry and evicted a real session out of the ring.
- `/start`'s `DEFERRED=` signal fires at all. `session_commit.sh` spools NESTED (the repo path under
  the branch it deferred from) and the reader used a flat `iterdir()`, so the count was zero forever
  and the signal never appeared once since it landed.
- `/end` validates the todos file before touching the cockpit, and all THREE `cantiere.py` call
  sites resolve through the same chain with `[ -f ]` and a declared degrade line — two of them
  hardcoded `$HOME/.agents` with no guard and broke a half-finished `/end` with a raw Python error
  on a machine without `git-power`.
- `verify` matches the login EXACTLY: `@adalberto` no longer passes the gate for `ada`.
- `plan-week` keeps the promise `state/todos.md` makes: a `Follow-up` whose Review Date has arrived
  returns to `## Active`, stamped with the week it CAME DUE. The template claimed it, `plan-week`
  denied it, and no code did it.
- `update` 2.2.0: **the `state/current.md` reconcile step is back.** The v2.0.0 rewrite
  (498ed70, released in 0.17.0) silently dropped "Step 3 — Reconcile state/current.md"
  without a changelog line — the removal is hereby declared, late. Consequence observed
  2026-08-17: a session that checkpoints with `/update` but never runs `/end` leaves the
  open-items ledger stale, and whether it got refreshed depended on panel habit. Restored
  as a short prose step (Updated: line overwrite + Open add-and-flag, never close another
  owner's line) enforced by `checkpoint.sh verify`, which now FAILs when `current.md`
  predates today's session log.

### Added
- `end` 1.3.0: **worktree sweep** in the State-hygiene pass (`scripts/wt_sweep.sh`).
  The founder works worktree-first and `/end` is the only janitor he runs: a worktree
  that is clean AND merged into the default branch is removed (branch deleted with
  `-d`); a dirty worktree is NEVER touched (reported); clean-but-unmerged is a pause,
  reported with age; `git worktree prune` always. `--selfcheck` proves all four
  behaviors on a fixture repo; report-mode real-test on a 29-worktree repo found
  11 removable / 11 dirty (untouched) / 7 paused.
- `update` 2.1.0: after landing, one hygiene line via `wt_sweep.sh --report` —
  count only, `/update` never removes.

## 0.18.0

### Removed
- `real-testing`: the skill moved to its single source in the Polaris suite
  (`skills-suite/real-testing` v2.0.0, installed by symlink via `_standard/install.sh`).
  The plugin no longer ships a copy — a second distribution channel is exactly the
  divergence the 2026-08-16 single-source refactor removed (see the suite CHANGELOG
  and `docs/skill-refactor/2026-08-16-real-testing/`).

## 0.17.0

### Changed
- **`/update` 2.0.0 — the entry carries what is not progress.** The 31-Jan design had
  Completed / In Progress / Key Context / Files Modified; three of those fields eroded away over
  seven months of rewrites, leaving Done/Next/Blocker with nowhere to record a decision, a
  discovery, or a mistake — so that content either went missing or got improvised into an
  unstructured `Nota:` line. Restored as **In progress**, **Key context** (tagged
  `#decisione #architettura #scoperta #errore #superata #incidente`) and **Files**, plus a titled
  header and `wt:`/`branch:` provenance for multi-panel work. `Files` is written
  `path · symbol · why`: Serena navigates by symbol, so that is where the log and the code graph
  meet months later. Body down from 192 to 111 lines — the deterministic half moved to a script.
- **`/end` 1.2.0 — same entry format as `/update`.** It emitted Shipped / Still open / Next session
  while `/update` emitted a different set: same file, same reader, two grammars. It now writes the
  same entry, changing only the word after the timestamp and closing on `Next session`.
- **Both skills follow one memory rule.** Archive (`lessons.md`, `decisions.md`): write always,
  append-only — a lesson waiting for approval dies with the session. Apex (`CLAUDE.md`, `rules/`):
  never from a session skill; it is reached only through `/pol-apex-curate`, which proposes.
  Architectural choices are proposed as ADRs, where they stay linked to the code.

### Added
- **`skills/update/scripts/checkpoint.sh`** — the deterministic half of the checkpoint: `prepare`
  (root, login, branch, worktree, paths, harvest offset, hygiene), `harvest-done`, `commit`,
  `verify`, `due-done`. It costs no context and cannot be skipped by a model in a hurry.
- **`verify` fails loudly when a step was skipped.** It exists because a step that lives only in
  prose eventually gets skipped — including by whoever wrote it: on 2026-08-08 the author of the
  harvest step skipped it the same day he added it.
- **Recurring work rides the ritual that actually runs.** `state/due.md` lists jobs as
  `YYYY-MM-DD · name · every Nd`; `prepare` prints whatever is due and `due-done` moves the date
  forward by itself. Hung off `/update`, which runs daily, rather than `/end`, which often does not.
- **Six behavioural eval cases for `/update`**, cut down from fourteen by an adversarial review that
  removed the tautological ones (checks any model passes forever) and merged two pairs — notably
  keep-the-facts and invent-nothing, which as separate cases are both satisfied by a degenerate
  "dump everything, then say nothing" strategy that never exercises selection.

### Fixed
- The shipped line model reads the donor's tables the way the donor writes them, and a section ends
  where the donor ends it. `state_lines.section()` now stops at a horizontal `---` rule, not only at
  a heading or the contract sentinel: the shipped `current.md`/`todos.md` separate sections with
  rules, so a finder that only knew the sentinel ran to EOF — `/end` wrote the `Completed` row
  BELOW the rule, outside the table, and `/update` appended a thread under the contract line. One
  rule, one place, four consumers. An escaped pipe (`a\|b`) is content, not a cell boundary: the
  old split shredded the task name and shifted every later cell left, silently eating the `Added`
  stamp.
- `## Recent Context` dedup compares first line with first line. It compared a SAVED entry's first
  line against a WHOLE incoming block, so it only ever fired on one-line entries: a second `/end`
  in the same session duplicated its own entry and evicted a real session out of the ring.
- `/start`'s `DEFERRED=` signal fires at all. `session_commit.sh` spools NESTED (the repo path under
  the branch it deferred from) and the reader used a flat `iterdir()`, so the count was zero forever
  and the signal never appeared once since it landed.
- `/end` validates the todos file before touching the cockpit, and all THREE `cantiere.py` call
  sites resolve through the same chain with `[ -f ]` and a declared degrade line — two of them
  hardcoded `$HOME/.agents` with no guard and broke a half-finished `/end` with a raw Python error
  on a machine without `git-power`.
- `verify` matches the login EXACTLY: `@adalberto` no longer passes the gate for `ada`.
- `plan-week` keeps the promise `state/todos.md` makes: a `Follow-up` whose Review Date has arrived
  returns to `## Active`, stamped with the week it CAME DUE. The template claimed it, `plan-week`
  denied it, and no code did it.
- **Two eval assertions were wrong, not the skill.** `current.md resta fuori dal commit` was written
  inverted and said so in a `_negated_by_design` field nobody ever closed, so it reported red on
  correct behaviour; new `head_files_omit` lets a negative claim be stated directly. `dichiara il
  differimento` looked for the English word `defer` while the skills write Italian logs — the model
  had correctly written "rinviato"; `output_mentions` now accepts `a|b` alternatives.
- **The harness keeps the model output** (`_eval_output.txt`). A red assertion with no transcript
  costs a full re-run to diagnose, and reading it is what showed the skill was right both times.

## 0.16.0

### Added
- **`/polaris-status` measures state health before sweeping it.** New Step 5b.0: counts open threads
  and cockpit blocks first (two commands, no thread reading), reports the numbers, and only over
  threshold (>10 threads / >8 KB, or >20 blocks / >50 KB) asks ONE question before investigating.
  Under threshold it says "state healthy" and skips the expensive pass entirely — the sweep used to
  run unconditionally, paying full price on a file with five live threads.
- **Per-repo investigation of what already landed.** `state_reconcile.py` keys on the branch alone,
  so threads sitting on `main` and identified by issue/PR numbers in their text came back
  `unverified` forever and the file only grew. Everything it cannot resolve now goes to ONE Sonnet
  subagent **per product repo** (never one per thread), which resolves each `#N` via `gh`, each
  branch against `origin/main`, each SHA for reachability, and returns LANDED / OPEN / UNCLEAR with
  its evidence. UNCLEAR is a valid answer and is never rounded to LANDED; another contributor's
  thread is reported, never proposed for removal.
- **A behavioural eval harness for the session skills** (`polaris/evals/`). Fixtures build a
  throwaway repo in a declared state (N threads, N blocks, chosen branch, full `_polaris/` contract);
  assertions read the filesystem and git, so a case has one answer instead of a graded opinion. Every
  case declares `fails_before` — the skill version it must be RED on, because a case green on both
  sides tests nothing. `--selfcheck` verifies the harness with no model in the loop, and it already
  caught a bug in its own test data.

### Changed
- **`/update` pinned to `model: sonnet`.** Measured at 13% of a week's usage: it reads ~88k tokens of
  state to produce ~60 tokens of checkpoint. Sonnet rather than a cheaper tier because Step 3
  reconciles `current.md` across parallel panels — that step needs judgment, and losing another
  panel's thread costs more than the tokens saved.

### Proof
First real benchmark (`polaris/evals/polaris-status-workspace/iteration-1/benchmark.md`), new skill
vs the pre-change version on identical fixtures: **8/8 vs 4/8** — and the 4 the baseline passes are
the four non-discriminating safety guards. On 5 threads the baseline ran the full sweep
(`DID_INVESTIGATE: yes`) where the new one stops; on 14 threads the baseline investigated **without
asking**, the new one reported both counts and waited. Cost delta −5.3k tokens / −40s and
−6.0k / −76s. Stated honestly in the benchmark: the fixture has no remote and no issues, so it
understates the saving on a real vault, and half the assertions do not discriminate.

## 0.15.0

### Fixed
- The shipped line model reads the donor's tables the way the donor writes them, and a section ends
  where the donor ends it. `state_lines.section()` now stops at a horizontal `---` rule, not only at
  a heading or the contract sentinel: the shipped `current.md`/`todos.md` separate sections with
  rules, so a finder that only knew the sentinel ran to EOF — `/end` wrote the `Completed` row
  BELOW the rule, outside the table, and `/update` appended a thread under the contract line. One
  rule, one place, four consumers. An escaped pipe (`a\|b`) is content, not a cell boundary: the
  old split shredded the task name and shifted every later cell left, silently eating the `Added`
  stamp.
- `## Recent Context` dedup compares first line with first line. It compared a SAVED entry's first
  line against a WHOLE incoming block, so it only ever fired on one-line entries: a second `/end`
  in the same session duplicated its own entry and evicted a real session out of the ring.
- `/start`'s `DEFERRED=` signal fires at all. `session_commit.sh` spools NESTED (the repo path under
  the branch it deferred from) and the reader used a flat `iterdir()`, so the count was zero forever
  and the signal never appeared once since it landed.
- `/end` validates the todos file before touching the cockpit, and all THREE `cantiere.py` call
  sites resolve through the same chain with `[ -f ]` and a declared degrade line — two of them
  hardcoded `$HOME/.agents` with no guard and broke a half-finished `/end` with a raw Python error
  on a machine without `git-power`.
- `verify` matches the login EXACTLY: `@adalberto` no longer passes the gate for `ada`.
- `plan-week` keeps the promise `state/todos.md` makes: a `Follow-up` whose Review Date has arrived
  returns to `## Active`, stamped with the week it CAME DUE. The template claimed it, `plan-week`
  denied it, and no code did it.
- **Session state can no longer strand on a feature branch.** `session_commit.sh` now commits only
  from the repository's default branch (resolved from `origin/HEAD`, falling back to a local
  `main`/`master`) and **defers** everywhere else: the file stays on disk as the single copy and the
  next default-branch session lands it. Supersedes the 2026-07-19 "Option A" (commit-on-current-branch),
  which stranded daily session logs on branches that were paused or never merged — invisible to
  `/start` until merge — and produced N diverging branch copies of one append-only file.
- **`/end` no longer hand-commits in prose.** Step 5 now calls the same script with the new `--end`
  mode, so the handoff, session log, weekly plan, `decisions.md`, `lessons.md` and the `polmem`
  journal line inherit the identical guard: pathspec-only, default-branch-only, no `git add -A`,
  no foreign-file drag, honest failure reporting. `--end` may commit the two ledgers (its vetted
  promotion) but still refuses `state/current.md` and `.env*`.
- **The guard is reachable from the skills-CLI install.** The script moved to
  `skills/update/scripts/session_commit.sh` so `npx skills` ships it with the skill (previously it
  lived outside any skill directory, so on a skills-CLI machine `$CLAUDE_PLUGIN_ROOT/scripts/…`
  resolved to nothing and the whole "enforced in code" step silently did nothing). Both skills
  resolve plugin-root first, then `~/.agents/skills/…`, with an explicit same-rule manual fallback.

### Added
- Six adversarial self-checks covering every new branch: off-default defer (nothing committed, file
  intact on disk), deferred content landing on the next default-branch run, `--end` promoting the
  ledgers, `--end` still refusing state/secrets, `--end` deferring off-default, `origin/HEAD`-driven
  default resolution, and a `master`-default repository. Each guard was mutation-tested: breaking it
  fails a named check.

## 0.10.0

### Added
- **`/polaris-grill`.** A read-only, repo-grounded product and technical interview that combines
  live code, backend and schema contracts, `_polaris/` state, decisions, lessons, targeted
  `polmem recall`, and version-aware Context7 documentation. It auto-answers from evidence, asks one
  decision-bearing question at a time, and emits a bounded execution handoff without implementing,
  mutating trackers, or inventing a second spec system.
- **Portable `/polaris-status`.** The existing full-status workflow now ships from the versioned
  package as a provider-neutral Agent Skill. It owns the expensive Git/GitHub pulse, team scan,
  freshness, memory and health paths removed from `/start`, and is discoverable by Agent Skills
  installers as well as the Claude plugin.

### Changed
- **`/start` is resume-only.** It reads the current outcome, local branch, latest owned
  handoff/checkpoint, active blocker and concrete next action. Repo pulse, remote fetch, open PRs,
  other contributors, decision/lesson slices, memory recall and health moved behind the explicit
  operator status workflow instead of being paid on every session start.
- **Recurring identity resolution is local.** The exact GitHub login is resolved and cached in
  repo-local git config on first use; subsequent starts do not call GitHub just to locate the
  contributor profile.
- The release contract now caps `/start` at 7 KB / 900 words and fails if status operations creep
  back into it.

## 0.9.0

### Removed
- **The CEO signature gate is gone — `ceo_signature`, `execution_authorized` and `auto_authorized`
  no longer exist** (founder call, 2026-07-15: "leva proprio la mia firma"). The model was
  backwards, and 0.8.0's `auto_authorized: secondary` was a patch on a broken default rather than a
  fix. The live engineering charter this plugin is supposed to serve says the opposite in writing:
  green work is **self-merged by its owner** after the applicable gates, amber **proceeds** on a
  recorded `Decision / Why / Risk / Next step` ("silence is not a block"), the lead "**is not the
  default technical gate**", and their review of the weekly focus is "**priority alignment, not a
  technical approval gate**". A plugin shipping the inverse trains contributors to ask permission
  for reversible work and makes the founder the whole team's bottleneck.

### Changed
- **The weekly plan states truth, not permission**: `status: active|carried|superseded` +
  `lead_review: pending|read|reordered`. The plan is committed and travels into the PR — visible
  and correctable at any time, blocking at none. `/start` briefs it as **active work**; `/report`
  measures against it as the contributor's own stated intent, and a plan overtaken by a real
  reprioritisation is reported as a priority change, not a miss.
- **The gate survives exactly where being wrong is irreversible — the red stop-lines**, and it
  names an approver instead of defaulting to the lead: access/RLS/auth expansion, personal-data
  use/retention/deletion, new processor/vendor, irreversible migration, legal/customer commitment,
  audited production promotion, material outcome/architecture change. **The repository's own
  charter (`profile.yml` → `workflow:`) outranks this list** — an audited repo may name approvers
  the plugin cannot know about (e.g. a signed segregation-of-duties matrix).
- **`weekly_capacity` is a planning guide, not a quota.** The live contract had already corrected
  this by hand (`weekly_capacity: 3 # planning guide, not a quota`) before the plugin caught up; a
  hard cap turns an honesty device into a lid on output.
- **`/end` closes a thread only against verified merge.** `git worktree list` (a worktree still
  holding the branch = live), `git branch --merged origin/main`, `gh pr list --head`. An open PR is
  not a closed thread, a green real-test is not a merge, and a branch with no recent commits is
  **parked, not dead** — with several panels on several worktrees, parked-while-you-work-elsewhere
  is the normal shape of the work, and dropping it is the exact loss this file exists to prevent.
- **There is no CEO in this contract.** The role is gone, not just the signature field — `/plan-week`
  Step 1 still read "the CEO reviews and signs it", which the first sweep missed because it banned
  the phrase `CEO signs`. What exists: a repo **owner**, and (where a repo has one) a **lead** who
  sets outcomes, priorities and red stop-lines. `## PM action` in `/report` is no longer "decisions
  the CEO must take" but "blockers only someone else can clear, with a named owner" — and "none" is
  the healthy default. The contract test now bans the bare word, because authority-by-rank is how
  the gate grows back under a new name.
- **`current.md` converges on the MAIN worktree** — `/update` and `/end` resolve it via
  `git worktree list --porcelain | head -1`, never from the checkout they happen to sit in. The real
  workflow is many panels in many worktrees whose handoff must land where the next session opens:
  main. Since the file is gitignored it never travels with a branch, so v0.8.1's per-checkout
  isolation was the **bug, not the safety** — measured on one live repo, three worktrees each held
  an orphaned copy (80KB last touched 12 July, 66KB last touched 8 July, one absent), every one a
  handoff its own author never saw again. Consequences: **the branch is a thread's identity** (one
  panel, one worktree, one branch — the panel discriminator that makes the merge check possible
  without any panel knowing which others are alive), threads and `Next` lines are branch-keyed so
  panels stop overwriting each other, and a `current.md` found in a non-main worktree is surfaced as
  a pre-rule orphan, never silently deleted — it may be the only copy of a handoff.

## 0.8.2

### Changed
- **`/update` loses closing authority over `current.md` — only `/end` may close an item**
  (founder correction, issue #24 follow-up). 0.8.1 gave `/update` and `/end` the identical
  reconcile contract, including the same power to remove/close a ledger item. `/update` runs
  often, sometimes from several panels within the same hour — that shared delete path is exactly
  the surface that lets one panel's cleanup collide with another panel's still-open thread.
  `/update` may now only add a new item, update its own item's context, or flag one `stale?`;
  it never closes one, even its own. `/end` is unchanged: the sole, deliberate, evidence-cited
  (or promotion-with-pointer) point where an item leaves the ledger. Non-destructive by design if
  `/end` is skipped for a while — closed-but-unpruned items are noise, not corruption, and the
  existing `stale?` flag already surfaces them.
## 0.8.1

### Changed
- **`current.md` becomes an open-items LEDGER with reconcile semantics** (founder design session).
  Blind overwrite loses other panels' open items — the very fear that bred checkpoint stacking;
  append breeds 83KB diaries (a live 62-checkpoint file was purged today). `/update` and `/end` now
  READ the file first and reconcile: an item leaves ONLY by evidence-named closure or by promotion
  to an issue/plan (which leaves a `→ #123` pointer, never a silent delete); other owners' items
  are untouchable; idle >14d → flagged `stale?`, never auto-dropped. **Size is an output of the
  only-open-truth discipline, never an eviction criterion** — 10 open items = 10 items, each with
  its 1–3 lines of context; shipped-work narrative goes to the session log, decisions to
  decisions.md. `/start` reads it as the ledger and never drops open items itself.

## 0.8.0

### Added
- **Scoped pre-authorization (founder-granted).** `config.yml` may grant a contributor
  `auto_authorized: secondary`: the plan's secondary items start before the CEO signature
  (`status: auto-authorized`, surfaced by `/start` as startable). The grant lives in
  founder-owned `config.yml` ONLY — a self-provisioned profile can never grant it. The primary
  outcome and anything touching production or client-facing surfaces always waits for the
  signature. Closes G4 gap #3 (founder-bottleneck) without an SLA: the gate stays where it
  protects, disappears where it strangles.

## 0.7.12

### Added
- **`## Bottleneck` — mandatory section in `/report`.** The single biggest thing that slowed the
  week (from the evidence, not vibes) + ONE concrete removal proposal. Never "none" — a week with
  no named bottleneck means the author didn't look. Turns continuous bottleneck-hunting into a
  per-person async ritual (G4 gap #2, ai-native-engineering-team reference); the removal proposals
  feed PM action.

## 0.7.11

### Changed
- Version dropped from the brief header (founder: noise once the cache-staleness hunt is over) —
  header is now `{Greeting}. {Weekday} {date} — <repo> on <branch>`.

## 0.7.10

### Fixed
- The shipped line model reads the donor's tables the way the donor writes them, and a section ends
  where the donor ends it. `state_lines.section()` now stops at a horizontal `---` rule, not only at
  a heading or the contract sentinel: the shipped `current.md`/`todos.md` separate sections with
  rules, so a finder that only knew the sentinel ran to EOF — `/end` wrote the `Completed` row
  BELOW the rule, outside the table, and `/update` appended a thread under the contract line. One
  rule, one place, four consumers. An escaped pipe (`a\|b`) is content, not a cell boundary: the
  old split shredded the task name and shifted every later cell left, silently eating the `Added`
  stamp.
- `## Recent Context` dedup compares first line with first line. It compared a SAVED entry's first
  line against a WHOLE incoming block, so it only ever fired on one-line entries: a second `/end`
  in the same session duplicated its own entry and evicted a real session out of the ring.
- `/start`'s `DEFERRED=` signal fires at all. `session_commit.sh` spools NESTED (the repo path under
  the branch it deferred from) and the reader used a flat `iterdir()`, so the count was zero forever
  and the signal never appeared once since it landed.
- `/end` validates the todos file before touching the cockpit, and all THREE `cantiere.py` call
  sites resolve through the same chain with `[ -f ]` and a declared degrade line — two of them
  hardcoded `$HOME/.agents` with no guard and broke a half-finished `/end` with a raw Python error
  on a machine without `git-power`.
- `verify` matches the login EXACTLY: `@adalberto` no longer passes the gate for `ada`.
- `plan-week` keeps the promise `state/todos.md` makes: a `Follow-up` whose Review Date has arrived
  returns to `## Active`, stamped with the week it CAME DUE. The template claimed it, `plan-week`
  denied it, and no code did it.
- The brief renders as plain markdown, **never inside a code fence** — a fenced brief shows
  literal asterisks instead of bold section headers in the terminal (founder caught it live).

## 0.7.9

### Changed
- **Brief goes MARVIN-style.** Founder UX iteration: bold section headers with bullets
  (**THIS WEEK / PULSE / MEMORY / LAST SESSION / MY CALL**) instead of one-emoji-per-line; empty
  sections are omitted, never padded. Greeting + date + version header; ⛔ stale-checkout line
  still leads when the tree is behind. Headers translate to the profile `language:`; structure
  stays invariant across voices.

## 0.7.8

### Changed
- Brief template breathes: blank lines between the four blocks (header / this week / pulse /
  evidence+close) — ten content lines, never a squashed wall (founder UX feedback).

## 0.7.7

### Added
- **`voice:` in the contributor profile.** Per-contributor TONE for the brief: `cynical` (default
  dry co-pilot), `plain` (neutral, facts only), or a free-text tone line. Structure is invariant
  whatever the voice — fixed icons, rated `▶ My call`, evidence-grounded 💬 verdict, motivational
  ban: that's the product, not the personality.

## 0.7.6

### Added
- **`language:` in the contributor profile.** `/start` writes the brief in the contributor's own
  language (`language: it` → Italian lines under the same fixed icons); committed artifacts keep
  the repo convention. Default `en` when absent.

## 0.7.5

### Changed
- **Cynical co-pilot voice.** Motivational language is banned outright; "merged" is a fact,
  "great progress" is not. Two new closing lines: `💬 Last session:` — one dry verdict on what it
  actually moved (from the log, not from charity; unproven "done" claims get called out) — and
  `▶ My call:` — a ranked recommendation with blunt scores (n/10, leverage vs cost) and a
  one-clause why. The user overrules, but never gets a menu without a recommendation. Closes the
  iter-3 "ranked-recommendation nel briefing" item.

## 0.7.4

### Changed
- **The brief gets a face.** Fixed icon scheme (🧭 header · 🎯 outcome · 🔨 active · 📦 landed ·
  🌊 in motion · 🧪 proof · ⚠️/✅ blocker · 🧠 recall · ▶ first move) — the icons are the scanning
  UI. Voice: calm co-pilot on the radio — verb-first, punchy, dry wit at most one line, never
  instead of a fact.
- **Version in the header.** The brief opens with `· Team OS v<version>` read from plugin.json at
  runtime — no more guessing which cached release answered.

## 0.7.3

### Changed
- **The answer is the brief, not a reading diary.** `/start` outputs the ten-line brief only — no
  "everything read, nothing relevant" narration, no tool-log recap (live-run UX feedback). One
  exception leads: a checkout behind `origin/main` opens the answer with the action line
  ("pull before working"), because everything else was read from a stale tree.

## 0.7.2

### Changed
- **Context budget caps in `/start`.** A live measure on a mature repo found the real context cost
  is not the skill (+~1k tokens across 0.4.2→0.7.1) but uncapped inputs: `decisions.md` at 111KB
  (~28k tokens) and `hot.md` at 20KB. `/start` now reads the 10 most recent decisions/lessons
  entries, the first screen of `hot.md`, and treats a >30-line `state/current.md` as a decayed
  diary (read newest block, flag for trim). Older context is recall's job, on demand.

## 0.7.1

### Changed
- `/start` closes with an explicit build-method bridge: when the chosen first move is code, enter
  through the Superpowers flow (brainstorm → plan → TDD) or the workflow skill the repo's CLAUDE.md
  names — never straight into edits from the brief. No skill is force-loaded at session start:
  Superpowers already self-injects via its own SessionStart hook, and orientation sessions stay
  cheap.

## 0.7.0

### Added
- **`/start` repo pulse.** The brief is now a situational view, not a file read-back: after the
  contract files, `/start` grounds the LIVE state — `git log origin/main -5` (what landed),
  `git branch -vv --sort=-committerdate` (branches in motion, ahead/behind), `gh pr list` (open
  PRs by owner) — and treats plan-vs-pulse mismatches as brief-worthy collisions. Where the plan
  and the pulse disagree, the pulse wins.
- **polmem two-pass at start.** Warm recap first (`.wiki/hot.md` — what the repo's memory has been
  touching lately, zero queries), then the targeted recall; with no signed plan the query derives
  from the last session log + last landed commits.
- Brief grows to ten lines with `Recently landed:` and `In motion:`.

## 0.6.5

### Changed
- `/start` description slimmed to what the user sees in the command palette: "start a session —
  branch check, current state and recent decisions, polmem recall, 7-line brief; provisions your
  team path only on first use". Behavior unchanged.

## 0.6.4

### Changed
- **Founder-vault resolver case.** A repository whose root IS `_polaris` (the founder vault) now
  resolves to its own root when it carries `./config.yml` — one flow everywhere, no parallel
  founder-only session skills. Part of the single-method consolidation: the personal MARVIN-era
  `/start` `/end` `/update` command files are retired on the founder machine; the CEO layer is an
  external pull-based skill, never a second write path.

## 0.6.3

### Fixed
- The shipped line model reads the donor's tables the way the donor writes them, and a section ends
  where the donor ends it. `state_lines.section()` now stops at a horizontal `---` rule, not only at
  a heading or the contract sentinel: the shipped `current.md`/`todos.md` separate sections with
  rules, so a finder that only knew the sentinel ran to EOF — `/end` wrote the `Completed` row
  BELOW the rule, outside the table, and `/update` appended a thread under the contract line. One
  rule, one place, four consumers. An escaped pipe (`a\|b`) is content, not a cell boundary: the
  old split shredded the task name and shifted every later cell left, silently eating the `Added`
  stamp.
- `## Recent Context` dedup compares first line with first line. It compared a SAVED entry's first
  line against a WHOLE incoming block, so it only ever fired on one-line entries: a second `/end`
  in the same session duplicated its own entry and evicted a real session out of the ring.
- `/start`'s `DEFERRED=` signal fires at all. `session_commit.sh` spools NESTED (the repo path under
  the branch it deferred from) and the reader used a flat `iterdir()`, so the count was zero forever
  and the signal never appeared once since it landed.
- `/end` validates the todos file before touching the cockpit, and all THREE `cantiere.py` call
  sites resolve through the same chain with `[ -f ]` and a declared degrade line — two of them
  hardcoded `$HOME/.agents` with no guard and broke a half-finished `/end` with a raw Python error
  on a machine without `git-power`.
- `verify` matches the login EXACTLY: `@adalberto` no longer passes the gate for `ada`.
- `plan-week` keeps the promise `state/todos.md` makes: a `Follow-up` whose Review Date has arrived
  returns to `## Active`, stamped with the week it CAME DUE. The template claimed it, `plan-week`
  denied it, and no code did it. (second external review, gpt-5.6 — 3 High, 3 Medium)
- **Identity gate now gates** (High): the v0.6.2 `grep || echo` continued on failure and skipped
  pre-existing profiles entirely. The gate hard-stops (`|| { …; exit 1; }`) and runs in BOTH
  branches — fresh or pre-existing profile.
- **Non-Claude users no longer stranded by the failure branch** (High): `command not found: polmem`
  now routes Codex/Cursor users to the checkout shim (`python3 <checkout>/polaris/bin/polmem`)
  instead of a Claude-only installer that exits 127 without a plugin cache.
- **The `/end` journal line reaches the team** (High): `polmem remember` writes `.wiki/journal/…`,
  but the offered pathspec commit staged only sessions/weeks — the journal file is now part of the
  handoff commit.
- `/start` never briefs an unsigned weekly file as active work (`execution_authorized` checked);
  commit evidence paginates (`gh api --paginate`); onboarding preflights the GitHub CLI
  (`gh --version`, `gh auth status`, `gh auth login`).
- All pinned in `test_terra_review_findings_stay_fixed`.

## 0.6.2

### Fixed
- The shipped line model reads the donor's tables the way the donor writes them, and a section ends
  where the donor ends it. `state_lines.section()` now stops at a horizontal `---` rule, not only at
  a heading or the contract sentinel: the shipped `current.md`/`todos.md` separate sections with
  rules, so a finder that only knew the sentinel ran to EOF — `/end` wrote the `Completed` row
  BELOW the rule, outside the table, and `/update` appended a thread under the contract line. One
  rule, one place, four consumers. An escaped pipe (`a\|b`) is content, not a cell boundary: the
  old split shredded the task name and shifted every later cell left, silently eating the `Added`
  stamp.
- `## Recent Context` dedup compares first line with first line. It compared a SAVED entry's first
  line against a WHOLE incoming block, so it only ever fired on one-line entries: a second `/end`
  in the same session duplicated its own entry and evicted a real session out of the ring.
- `/start`'s `DEFERRED=` signal fires at all. `session_commit.sh` spools NESTED (the repo path under
  the branch it deferred from) and the reader used a flat `iterdir()`, so the count was zero forever
  and the signal never appeared once since it landed.
- `/end` validates the todos file before touching the cockpit, and all THREE `cantiere.py` call
  sites resolve through the same chain with `[ -f ]` and a declared degrade line — two of them
  hardcoded `$HOME/.agents` with no guard and broke a half-finished `/end` with a raw Python error
  on a machine without `git-power`.
- `verify` matches the login EXACTLY: `@adalberto` no longer passes the gate for `ada`.
- `plan-week` keeps the promise `state/todos.md` makes: a `Follow-up` whose Review Date has arrived
  returns to `## Active`, stamped with the week it CAME DUE. The template claimed it, `plan-week`
  denied it, and no code did it. (external Codex review of v0.5.0..v0.6.1 — 3 High, 5 Medium, 2 Low)
- **Self-provisioned profile kept `github: octocat`** (High): `/start` now rewrites the login
  (`perl -pi`) and gates on `grep -q "^github: $LOGIN$"` — a template login silently targets the
  wrong GitHub user in every evidence query.
- **AGENTS.md promised polmem to non-Claude CLIs the installer couldn't deliver** (High): the
  installed launcher resolves the Claude plugin cache only; non-Claude agents now get the checkout
  path (`python3 polaris/bin/polmem`, alias documented).
- **`remember` writes committed history but docs said polmem "only reads"** (High): read/write
  split stated everywhere; explicit privacy rule (no secrets/credentials/customer data/PII) on the
  `/end` journal line; shim header corrected.
- `gh pr/issue list` now pass `--limit 200` (default 30 truncated busy weeks); open PRs labeled
  "open at report time" (not reconstructable as of a past week); an unsigned plan is reported as an
  **unapproved proposal**, never a commitment baseline; decisions/lessons proposals carry the
  `(@<login>)` owner marker so report attribution is deterministic; `/end` commit snippet uses
  `$LOGIN` instead of literal placeholders; worked-example weekdays corrected.
- All fixes pinned in `test_codex_review_findings_stay_fixed`.

## 0.6.1

### Changed
- **`/end` feeds the repository memory.** After the handoff block, one machine-readable line goes
  into the repo journal (`polmem remember "session … — next: …"`); the offline distill decides what
  is durable. This closes the daily memory cycle mechanically — `/start` consumes (recall), `/end`
  feeds — for every contributor, since `remember` ships in the thin repo bundle. Same failure
  branches as `/start` (never `polmem init`).

## 0.6.0

### Changed
- **`/report` is a real report now, not a diff table.** Modeled on the production weekly reports
  (a product repo, W20–W27): `TL;DR` → `Planned versus actual` → `Day by day` (from the contributor's session
  logs, each linked) → `Merged PRs` (ground truth from `gh`, LOC + merge SHA; where logs and `gh`
  disagree, `gh` wins) → `Decisions in range` → `Blockers and incidents` → `Metrics` (derived at
  report time, never copied) → `PM action` (what the CEO must decide) → `Next week`. Scales
  honestly: a quiet week is a short report — never pad.
- **Evidence wiring fixed by a live REAL test.** Commits are resolved login→commits **server-side**
  (`gh api repos/$REPO/commits?author=$LOGIN&since=…&until=…`): the previous author-email approach
  returned zero on a real repo because squash commits carry the user's configured (personal) email,
  not the noreply form. `git fetch --prune` precedes evidence gathering; open PRs at end of range
  are part of the picture. This closes audit finding #5 (thin evidence commands) — commit/PR
  evidence now links into the repo graph mechanically, not "a intuito".
- Weekly-report template rewritten to the new structure.

## 0.5.2

### Added
- **`_polaris/README.md` template** (`polaris/templates/repo-contract/README.md`) — the contract's
  front door in every product repo: structure table (who writes what), the locked rules (single
  root, own-path provisioning, CEO signature gate, tracker stays the execution truth) and the
  privacy boundaries (no personal capacity data, no mentor/investor terms, neutral commit
  messages). Evolved from a product repo's pre-Team-OS README.
- **`AGENTS.md` bridge** — the five skills are consumable by non-Claude agent CLIs (Codex, etc.)
  from a plain repo checkout: skill index with relative paths, `$CLAUDE_PLUGIN_ROOT` substitution
  note, contract root and boundary rules. Contract-tested.
- `team/<login>/handoff/` documented as the optional home for rich multi-session handoff docs.

### Decided (layout frozen)
- `weeks/` + `reports/` stay separate siblings — the identical ISO-week filename pairs them by
  construction; a `weekly/` merge would buy one click and cost a 3-surface migration.
- `team/<login>/` stays (vs bare `_polaris/<login>/`) — it separates people-space from contract
  files and keeps skill globs (`team/*/weeks/`) unambiguous.
- `state/current.md` stays at the root — ephemeral and per-checkout; moving it under a login adds
  no isolation.

## 0.5.1

### Changed
- **Plans are authored by their owner.** `/plan-week` now states it explicitly: the plan file lives
  in **your own** `team/$LOGIN/weeks/` (login from `gh api user`, same resolver as `/start`) and you
  never write another contributor's plan — the CEO reviews and signs (`ceo_signature`), they don't
  write it for you. Locked with the founder 2026-07-13 after a pre-created plan shipped into a
  product repo.
- **Worked examples de-placeholdered.** `/plan-week` and `/report` examples used `team/jeanpierre/`
  — the exact placeholder-login pattern that broke a real contract. Now `team/octocat/`, and the
  release contract test forbids placeholder logins in the skills.

## 0.5.0

### Changed
- **Single Polaris root: `_polaris/`.** The dual-root resolver (`polaris/` or `_polaris/`) is gone —
  it drifted from the convention every product repository already uses, and per-repo root choice is
  exactly how one repository ended up carrying both roots at once. `/start` and `/update` now
  resolve `_polaris/config.yml` only; README, onboarding and the release contract tests pin it.
- **Self-provisioning contributor paths.** A contributor's `team/<login>/` path is created by
  **their own first `/start`**, from the exact login `gh api user --jq .login` returns on their
  machine: profile.yml (from the plugin template), `weeks/`, `reports/`, `sessions/`. Nobody
  pre-creates paths for other people, and no login is ever guessed — placeholder folders
  (e.g. `team/jeanpierre`) silently break every `gh` evidence query.
- **`lessons.md` joins the contract.** Product repos carry `<root>/lessons.md` next to
  `decisions.md`; `/end` proposes durable lessons through the same confirm-before-write gate, and
  `/start` reads it alongside decisions.

### Migration
- Repositories that carried a `polaris/` root (no underscore): the repo owner renames it
  (`git mv polaris _polaris`) and deletes pre-created placeholder `team/` folders — real paths are
  recreated by each contributor's `/start`. See the migration note in `docs/TEAM-ONBOARDING.md`.

## 0.4.4

### Changed
- **Per-contributor sessions path.** Session logs move from the shared `<root>/sessions/` to the
  per-contributor `<root>/team/<login>/sessions/` — the same isolation `weeks/` and `reports/`
  already use, so contributors never write to a shared, collision-prone directory. `/update` and
  `/end` now append to `team/<login>/sessions/YYYY-MM-DD-@<login>.md`; `/start` reads its own recent
  session logs from the same path and globs `team/*/sessions/` for cross-contributor
  collision-awareness, alongside the existing `team/*/weeks/` check.
- README's repo-contract tree and `docs/TEAM-ONBOARDING.md`'s contract checklist updated to show
  `sessions/` nested under `team/<login>/`.

### Migration
- Repositories on ≤0.4.3: move existing `<root>/sessions/*-@<login>.md` files into
  `<root>/team/<login>/sessions/`. See the migration note in `docs/TEAM-ONBOARDING.md`.

## 0.4.3

Iteration from a live 6-run benchmark (with-skill vs baseline) — objective defects only.

### Fixed
- The shipped line model reads the donor's tables the way the donor writes them, and a section ends
  where the donor ends it. `state_lines.section()` now stops at a horizontal `---` rule, not only at
  a heading or the contract sentinel: the shipped `current.md`/`todos.md` separate sections with
  rules, so a finder that only knew the sentinel ran to EOF — `/end` wrote the `Completed` row
  BELOW the rule, outside the table, and `/update` appended a thread under the contract line. One
  rule, one place, four consumers. An escaped pipe (`a\|b`) is content, not a cell boundary: the
  old split shredded the task name and shifted every later cell left, silently eating the `Added`
  stamp.
- `## Recent Context` dedup compares first line with first line. It compared a SAVED entry's first
  line against a WHOLE incoming block, so it only ever fired on one-line entries: a second `/end`
  in the same session duplicated its own entry and evicted a real session out of the ring.
- `/start`'s `DEFERRED=` signal fires at all. `session_commit.sh` spools NESTED (the repo path under
  the branch it deferred from) and the reader used a flat `iterdir()`, so the count was zero forever
  and the signal never appeared once since it landed.
- `/end` validates the todos file before touching the cockpit, and all THREE `cantiere.py` call
  sites resolve through the same chain with `[ -f ]` and a declared degrade line — two of them
  hardcoded `$HOME/.agents` with no guard and broke a half-finished `/end` with a raw Python error
  on a machine without `git-power`.
- `verify` matches the login EXACTLY: `@adalberto` no longer passes the gate for `ada`.
- `plan-week` keeps the promise `state/todos.md` makes: a `Follow-up` whose Review Date has arrived
  returns to `## Active`, stamped with the week it CAME DUE. The template claimed it, `plan-week`
  denied it, and no code did it.
- **`/report` ISO-week off-by-one.** The report week is now the ISO week of the *period being
  reported* (`date +%G-W%V`; explicit `WEEK` for a past week), and the evidence window is derived
  from that week via `datetime.fromisocalendar`, so filename and evidence can no longer diverge. A
  run had filed a W28 report as W29.
- **`/report` used the local machine's git identity.** Evidence now queries the tracker by the
  contributor's GitHub login (`author:$LOGIN`) instead of
  `git log --author="$(git config user.email)"`, which resolves to whoever runs the command. Added a
  branch-sync guard: verify commit authorship before crediting a PR.
- **`/plan-week` ranking buried critical issues.** Severity now strictly outranks age: a
  `[CRITICAL]`/priority-labelled issue always ranks above an older non-critical one; staleness is the
  final tiebreak only.

### Added
- **`/plan-week` scope grounding.** When `preferred_areas` is empty, the skill looks for scope
  evidence in the repo (onboarding docs, `CODEOWNERS`, the contributor's recent PRs) and proposes
  updating `profile.yml` before ranking.
- **polmem not-memory-wired branch.** `/start` (and, by reference, `/plan-week` and `/report`)
  documents the real failure: tell the repo owner, do **not** run `polmem init` yourself. Reaffirms
  `recall` is assumed context, not current state.
- Tests for the week computation, login-based evidence, severity ranking, scope grounding, the
  not-wired branch, and template existence/English/worked-example parity.

### Changed
- Repo-contract templates (`config.yml`, `profile.yml`, `weekly-plan.md`, `weekly-report.md`)
  reconciled to English and aligned exactly to the skills' worked examples. The `github` field is
  now documented as the exact, case-sensitive GitHub login. Skills reference the plugin template path
  (`$CLAUDE_PLUGIN_ROOT/...`) so it always resolves.
- Genericised founder-specific strings in the `polmem` CLI (repo owner / CI).
- Professional README pass and English onboarding.

## 0.4.2 and earlier

Reduced the surface to the five repository-first commands plus the `polmem` CLI; removed the
founder-vault coupling, the bootstrap command, and duplicate report commands. Established the
committed repo-contract model and the plugin release gates (`check_skills.sh`, contract tests).
