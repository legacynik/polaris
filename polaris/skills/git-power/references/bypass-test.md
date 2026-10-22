---
title: bypass-test — git-power
description: I test che devono fallire se qualcuno aggira il boundary del commit o il gate di chiusura guidata.
---

# Bypass-test

Sei scenari: tre presi **verbatim** da una voce del registro (G7#2, G8#2) o dal near-miss
misurato sul repo, tre aggiunti dopo l'attacco adversariale del 2026-08-09
(verdetto DEBOLE sulle vie laterali L1/L3, NON-COPRE su `reset --hard`/`.method`). Ognuno ha il comando eseguibile e cosa DEVE
succedere. Se un comando qui sotto si comporta diversamente da quanto scritto, la skill non è
blindata — non promuoverla.

**Eseguibile in un colpo**: `python3 ../scripts/cantiere.py --selfcheck` — costruisce ognuno di
questi sei scenari (più tre altri: merge-safe che chiude correttamente, lock da attività recente
vero/falso, branch orfano mai force-cancellato) su repo git **reali** in una cartella temporanea,
non mock. Exit 0 solo se tutti e 9 si comportano come dichiarato qui.

## 1 — Worktree con modifiche non committate (registro G7#2)

> "chiedere la chiusura di un worktree con modifiche non committate — la skill deve rifiutare e
> mostrare `git status`, non proporre `--force`."

```bash
tmp=$(mktemp -d) && cd "$tmp"
git init -q -b main repo && cd repo
git config user.email t@t.t && git config user.name t
echo 1 > f.txt && git add . && git commit -q -m init
git worktree add -q -b feat/dirty ../wt-dirty
echo uncommitted > ../wt-dirty/f.txt

python3 /path/to/cantiere/scripts/cantiere.py close --repo "$tmp/repo" \
  --target "$tmp/wt-dirty" --confirm "$tmp/wt-dirty"
echo "EXIT=$?"                      # DEVE essere 2, mai 0
git worktree list | grep wt-dirty   # DEVE ancora esistere
```

**Deve succedere**: `EXIT=2`, il testo stampato include l'output vero di `git status` (non un
messaggio generico), il worktree resta sul disco. **Non deve succedere**: nessuna riga stampata
o eseguita contiene `--force`; verificato anche staticamente — `scripts/cantiere.py` non contiene
UNA chiamata `git()` reale con `--force` o `-D` come argomento letterale (AST-walk, non grep di
superficie: vedi `_assert_no_force_call_sites` nel selfcheck, per non farsi ingannare da un
commento che ne PARLA).

## 2 — Stash durante un merge con conflitto irrisolto (registro G8#2)

> "working tree con 1 file modificato non committato + merge in corso finto → `git stash` deve
> uscire con errore bloccante, non successo silenzioso; verificare che `.git/MERGE_HEAD`
> sopravviva al tentativo."

```bash
# repo con uno stash preesistente E POI un merge che va in conflitto (mai creare lo stash
# DURANTE il conflitto per costruire il test: quello è proprio il comando pericoloso)
tmp=$(mktemp -d) && cd "$tmp" && git init -q -b main repo && cd repo
git config user.email t@t.t && git config user.name t
echo x > g.txt && git add g.txt && git commit -q -m g
echo y > g.txt && git stash push -q -m unrelated

git checkout -q -b a && echo A > f.txt 2>/dev/null; : # setup abbreviato, vedi selfcheck per il reale
# ... (il selfcheck costruisce il conflitto vero: due branch che modificano la stessa riga)

python3 /path/to/cantiere/scripts/cantiere.py close --repo "$tmp/repo" \
  --target "stash@{0}" --confirm "stash@{0}"
echo "EXIT=$?"                       # DEVE essere 2
test -f .git/MERGE_HEAD && echo "MERGE_HEAD sopravvive"   # DEVE stampare
git stash list | grep 'stash@{0}'    # DEVE esistere ancora
```

**Deve succedere**: `EXIT=2`, `.git/MERGE_HEAD` intatto, lo stash NON toccato — anche se lo
stash stesso non c'entra nulla col merge (è "estraneo"): la regola è incondizionata finché il
repo è mid-merge, perché è l'unico modo di non fidarsi di quale stash sia "innocuo".

## 3 — Attività concorrente rilevata (near-miss reale)

> *"L'agent che stava misurando acme-api ha beccato, durante la misura, un `git pull --rebase`
> lanciato da un altro panel... per qualche secondo `git ls-files` ha restituito un albero
> pre-migrazione."*

```bash
tmp=$(mktemp -d) && git -C "$tmp" init -q -b main
git -C "$tmp" config user.email t@t.t && git -C "$tmp" config user.name t
echo 1 > "$tmp/f.txt" && git -C "$tmp" add . && git -C "$tmp" commit -q -m init
# .git/HEAD è stato appena scritto dal commit — simula un pannello che sta operando ORA
python3 -c "
import sys; sys.path.insert(0, '/path/to/cantiere/scripts')
import cantiere, pathlib
print(cantiere.recent_activity_lock(pathlib.Path('$tmp')))"
# DEVE stampare True subito dopo un commit; False se rilanciato dopo 180s
```

**Deve succedere**: `census`/`close` classificano il worktree `pericoloso` con la nota
"attività concorrente rilevata" finché `HEAD` non è fermo da >180s — nessuna azione proposta in
quella finestra, indipendentemente da quanto "pulito" sembri lo stato git.

## 4 — Chiamata diretta alla funzione, non alla CLI (bypass-eval L1)

> "la chiamata diretta alla funzione deve essere gated quanto la CLI — è il buco reale trovato
> nel corpus (un gate che scatta solo via `main()`)."

Prima di questo fix, `import cantiere; cantiere.git(repo, "worktree", "remove", "--force", str(wt))`
rimuoveva un worktree sporco **senza passare da `close_worktree`**, perché la guardia viveva solo
nei wrapper, non nella primitiva `git()`. Riproducibile fuori dal selfcheck:

```bash
tmp=$(mktemp -d) && git -C "$tmp" init -q -b main
git -C "$tmp" config user.email t@t.t && git -C "$tmp" config user.name t
echo 1 > "$tmp/f.txt" && git -C "$tmp" add . && git -C "$tmp" -c user.email=t@t.t -c user.name=t commit -q -m init
git -C "$tmp" worktree add -q -b feat/dirty-direct "$tmp/../wt-direct"
echo uncommitted > "$tmp/../wt-direct/f.txt"

python3 -c "
import sys; sys.path.insert(0, '/path/to/cantiere/scripts')
import cantiere, pathlib
repo = pathlib.Path('$tmp')
wt = repo.parent / 'wt-direct'
try:
    cantiere.git(repo, 'worktree', 'remove', '--force', str(wt))
    print('BYPASS RIUSCITO')
except cantiere.Refused as e:
    print('RIFIUTATO:', e)
"
```

**Deve succedere**: `cantiere.Refused` sollevata da `git()` stessa, il worktree resta su disco.
**Non deve succedere**: nessuna eccezione, il worktree sparisce. Stesso test copre `-D` su un
branch non mergiato, `reset --hard` su un tree sporco, e `stash clear` — tutti rifiutati dalla
stessa primitiva, non da un wrapper che il chiamante può saltare. Selfcheck:
`_selfcheck_direct_git_call_still_refuses`.

## 5 — `.method/ledger.md` aperto

> "`cantiere` drains/removes [ledger.md + .polaris-owner] when the worktree or branch closes" —
> dichiarato da `metodologia/SKILL.md`, mai implementato prima di questo fix.

```bash
tmp=$(mktemp -d) && cd "$tmp" && git init -q -b main repo && cd repo
git config user.email t@t.t && git config user.name t
echo ".method/" >> .git/info/exclude
echo 1 > f.txt && git add . && git commit -q -m init
git worktree add -q -b feat/x ../wt
mkdir -p ../wt/.method && printf 'PLAN: p\nTASK 1: started\n' > ../wt/.method/ledger.md

git -C ../wt status --porcelain   # DEVE essere vuoto: .method è ignorato, non è "sporco"
python3 /path/to/cantiere/scripts/cantiere.py close --repo "$tmp/repo" \
  --target "$tmp/wt" --confirm "$tmp/wt"
echo "EXIT=$?"                    # DEVE essere 2, non 0 — anche se git status non vede nulla
```

**Deve succedere**: `EXIT=2` nonostante `git status` sia pulito — la guardia legge il ledger, non
solo `git status`. **Nota sulla riproduzione a mano**: il comando sopra rifiuta ANCHE per
`recent_activity_lock` (il worktree è appena stato creato, <180s fa) — per isolare il solo gate
`.method` con `TASK 1: complete` e vedere `EXIT=0`, serve backdatare `.git/HEAD` del worktree
oltre 180s (`_age_head()` lo fa nel selfcheck, non riproducibile a mano in poche righe). La metà
che conta per la sicurezza — il rifiuto quando il piano è aperto — è quella sopra, riproducibile
subito. **Limite dichiarato**: non distingue il proprietario del piano da chi chiama `close` —
blocca per qualunque piano aperto, non solo per quello di un altro pannello. Selfcheck completo
(entrambe le direzioni, mtime controllato): `_selfcheck_method_ledger_blocks_close`.

## 6 — `reset --hard` guardato (description lo dichiarava, 0 righe lo implementavano)

```bash
tmp=$(mktemp -d) && git -C "$tmp" init -q -b main
git -C "$tmp" config user.email t@t.t && git -C "$tmp" config user.name t
echo 1 > "$tmp/f.txt" && git -C "$tmp" add . && git -C "$tmp" commit -q -m init
echo dirty > "$tmp/f.txt"   # non committato — il tree che l'incidente 2026-08-03 perdeva

python3 /path/to/cantiere/scripts/cantiere.py reset-hard --repo "$tmp" --to HEAD --confirm HEAD
echo "EXIT=$?"              # DEVE essere 2
cat "$tmp/f.txt"             # DEVE mostrare ancora 'dirty' — nessuna perdita
```

**Deve succedere**: `EXIT=2`, il contenuto non committato sopravvive, `git status` viene mostrato.
Su un tree pulito lo stesso comando esegue il reset e logga `ORIG_HEAD` nel Git common dir,
`polaris-cantiere/removed-log.jsonl`, prima che qualcosa vada perso senza sporcare main. Selfcheck:
`_selfcheck_reset_hard_guarded`.

## 7 — Commit staged oltre il boundary

`scripts/test/test_git_power.py` costruisce un repo reale: 5 file staged devono dare `OK`/exit 0;
il sesto deve dare `CONCERN`/exit 3 con conteggi esatti. Il test passa dalla CLI pubblica, non
chiama direttamente la funzione. Un file binario è sempre `CONCERN`, perché `--numstat` non può
dimostrarne il numero di righe.

## 8 — Lifecycle: remote merge, dirty main, cleanup

`scripts/test/test_git_power.py` crea un origin bare, una main locale stale e sporca, un worktree
feature pulito e una PR `MERGED` simulata dal confine pubblico `gh`. `phase finalize` deve provare
che il merge commit è in `origin/main`, preservare il file non tracciato su main, rimuovere il
worktree e cancellare il branch con compare-and-delete sullo SHA esatto. Lo stesso modulo prova
che `post-push` conserva una PR OPEN e che `close` rifiuta un worktree pulito ma non mergiato.

Lo stesso `--selfcheck`, chiamando direttamente la primitiva `git()`, prova anche i comandi
dell'incidente-class: `clean -fd`, `checkout --`, `restore --worktree` e `stash push` su tree
sporco devono sollevare `Refused` e lasciare file tracciati/non tracciati intatti.

## Onestà sul limite

Il caso 3 è un **proxy meccanico** (recency), non una vera ownership-per-provenienza: se un altro
pannello ha scritto >180s fa e poi si è fermato senza committare (es. sta ancora editando un file
senza salvare), questo strumento non lo vede — vede solo `git status` (sporco → `pericoloso` per
un'altra ragione) o niente (se il file non è tracciato e non modificato ancora). Non è un buco
silenzioso: è dichiarato qui e in `SKILL.md` §Meccanismo, non nascosto dietro "provenienza"
come se fosse risolta.

**Limite non chiuso, dichiarato apposta (bypass-eval L2)**: niente di quanto sopra intercetta un
`git reset --hard`/`git stash`/`git worktree remove --force` digitato **fuori** da questo tool —
nessun harness ha un hook `PreToolUse` che lo reindirizzi qui oggi. La guardia è reale per chi la
invoca (CLI o funzione diretta, §4 sopra); non è un'intercettazione automatica di un comando shell
arbitrario. Costruire quell'hook tocca `~/.claude/settings.json`, condiviso da tutti i pannelli
paralleli del founder — fuori scope di un fix a questo bundle, per scelta esplicita, non per
omissione.
