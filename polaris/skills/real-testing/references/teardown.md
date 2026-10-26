# Teardown — close what you opened

Every real-test run ends here, in every mode, before the report. A run that leaves tenants,
worktrees or processes behind is not finished, whatever its verdict says.

1. **Lent data goes back.** Test data the repository lends (a pool tenant, a seeded account) is
   returned through the repository's own release command; its residue report (what was left in
   which table or bucket) goes in the receipt. Where the repository has a pool, take from it:
   create no throwaway tenants or accounts. Where it has none, everything you created is
   listed in the receipt with its id, so the repository's purge can find it.
2. **The receipt is committed, the PR stays draft.** The validation document (at the host's
   `outputs:` path) is committed pathspec-only on the PR branch, after
   `git rev-parse --abbrev-ref HEAD` names that branch. The PR is never marked ready and never
   merged by the run: the merge is the owner's. With no PR yet, the receipt stays local and the
   report says so.
3. **Your own machinery is removed.** Worktrees you added (`git worktree remove`), servers you
   started, browser instances you opened. Never `kill` a pid before `pgrep -P <pid>`: children
   that are other sessions mean it is not yours.
4. **The report ends with one teardown line:** released (residue: none, or what), committed
   (sha), removed (what), left (what and where, and why it could not go).

Example, a product repo with a pool: `backend/scripts/ops/tenant_pool.py` (`checkout`, `release`), described
in `docs/operations/AMBIENTI-E-DEPLOY.md` §4.
