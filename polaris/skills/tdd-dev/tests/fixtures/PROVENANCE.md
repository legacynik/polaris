# fixtures — where these outputs come from

One file per case. The name IS the expectation, parsed by the tests:
`<runner>__<case>__exit<N>__<verdict>.txt`, verdict in `rosso` (record it as RED),
`verde` (record it as GREEN), `blocco` (refuse: exit 2, no line written).

Machine paths were rewritten to `/lab`; nothing else was edited. The trailing
`exit=` line of the capture was dropped — the exit code lives in the name.

## Captured from a real runner on 2026-09-17 (macOS, python 3.14.6)

| Fixture | Command |
|---|---|
| `pytest__*` | `python3 -m pytest t_fail.py` (and `-q`, `t_pass.py`, an empty module, a module with a bad import, `--badflag`) — pytest 9.1.1 |
| `unittest__*` | `python3 -m unittest ut_fail` / `ut_pass` |
| `vitest__*` | `vitest run --root . sum.test.js` — vitest 4.1.11 |
| `jest__*` | `jest --rootDir . sum.test.js` — jest from an existing install |
| `go__*` | `go test ./...` on a 3-file module: failing test, passing test, file that does not compile |
| `shell__*` | `bash -c '<command>'`: unterminated subshell, `cd` into a directory whose NAME contains `failed passed`, `cd` into one whose name contains `test`, a compiler-style `1 error generated.` |

## Simulated, declared (no toolchain on the capture machine)

`cargo__*` — cargo/rustc are not installed here, so these five were written by
hand in the shape libtest prints: the `test result: FAILED.` / `ok.` summary
line, `running 0 tests`, a harness killed by SIGSEGV before any summary, and a
compile error. Replace them with a real capture the day cargo is available.

`pytest__ucciso_da_segnale` — a byte-for-byte copy of the real `pytest -q`
failure above, with exit 137 instead of 1: the runner spoke and the process was
then killed (OOM killer, SIGKILL on timeout), so the output can be truncated
mid-run and proves nothing. Same shape as the `verde_ma_exit_non_zero` pair.

`shell__npm_ci_dentro_docker`, `shell__make_target`, `shell__git_push` — the
three shapes the critic used on `d6c1694` to break a bare `^FAILED `. Written by
hand from the tools' real line shapes (buildkit's `FAILED [1/3] RUN npm ci`,
make's failing target, a CI wrapper around a rejected push): they are hostile
inputs, and the point is that none of them is a test runner.
