# Credits

The loop, the verdict model (READY/WAITING/ACTION/CLOSED), the blocker rules, the triage of threads, the attribution line and the treatment of comment text as untrusted data come from `babysit` and `scripts/pr-status.ts` of tester-army/e2e (Apache-2.0, commit ef977f48), ported to Python.

Added here: a real-test receipt bound to the head, a label vouched by a marker comment naming the head (no workflow needed to drop it), red checks a repo declares non-gating with their reason, and a check run twice read as its latest run.
