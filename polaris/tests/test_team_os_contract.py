"""Release contract for the small, repository-first Polaris Team OS surface."""

import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
TEMPLATES = ROOT / "templates" / "repo-contract"


def test_only_the_team_lifecycle_commands_are_shipped() -> None:
    assert {path.name for path in SKILLS.iterdir() if path.is_dir()} == {
        "start",
        "update",
        "end",
        "plan-week",
        "report",
    }


def test_every_command_is_repo_first_and_not_founder_vault_based() -> None:
    for skill in SKILLS.glob("*/SKILL.md"):
        text = skill.read_text()
        assert "user-invocable: true" in text
        assert "POLARIS_VAULT" not in text
        assert "Desktop/All Vibe Proj" not in text


def test_the_new_commands_have_one_shared_team_contract() -> None:
    start = (SKILLS / "start" / "SKILL.md").read_text()
    update = (SKILLS / "update" / "SKILL.md").read_text()
    end = (SKILLS / "end" / "SKILL.md").read_text()
    plan = (SKILLS / "plan-week" / "SKILL.md").read_text()
    report = (SKILLS / "report" / "SKILL.md").read_text()

    assert "`_polaris/`" in start
    for lifecycle_skill in (start, update, end):
        assert "state/current.md" in lifecycle_skill
    # current.md semantics: RECONCILE — blind overwrite loses other panels' open
    # items (the fear that bred checkpoint stacking); append breeds 83KB diaries.
    for writer in (update, end):
        assert "econcile" in writer
        assert "never blind-overwrite" in writer or "exact\nsemantics" in writer or "exact semantics" in " ".join(writer.split())
    assert "does not create issues, branches, pull requests or assignments" in " ".join(
        plan.split()
    )
    assert "planned versus actual" in report


def test_contract_root_is_single_underscore_polaris() -> None:
    # The Polaris root is `_polaris/`, full stop — the dual-root (`polaris/` or
    # `_polaris/`) resolver was a drift from the convention every product repo
    # already uses, and "root chosen per-repo" is exactly how one repo ended up
    # carrying both.
    start = (SKILLS / "start" / "SKILL.md").read_text()
    update = (SKILLS / "update" / "SKILL.md").read_text()
    readme = (ROOT.parent / "README.md").read_text()
    onboarding = (ROOT.parent / "docs" / "TEAM-ONBOARDING.md").read_text()

    assert "_polaris/config.yml" in start
    # Founder-vault case: a repo whose root IS _polaris resolves to its own root.
    assert "root is itself named `_polaris`" in start
    for text in (start, update, readme, onboarding):
        flat = " ".join(text.split())
        assert "`polaris/` or `_polaris/`" not in flat
        assert "`polaris/` if" not in flat


def test_start_provisions_own_path_from_the_real_github_login() -> None:
    # A contributor's path is created on THEIR machine from THEIR GitHub login
    # (`gh api user`) — never pre-created for someone else and never guessed:
    # placeholder folders (team/jeanpierre) break every gh evidence query.
    start = (SKILLS / "start" / "SKILL.md").read_text()
    onboarding = (ROOT.parent / "docs" / "TEAM-ONBOARDING.md").read_text()

    assert "gh api user --jq .login" in start
    assert "Never create `team/<login>/` folders for other people" in start
    assert "gh api user --jq .login" in onboarding
    assert "Never create a `team/` folder for a teammate" in onboarding


def test_plans_and_reports_are_authored_by_their_owner() -> None:
    # Locked 2026-07-13: the contributor writes THEIR OWN plan (/plan-week runs
    # on their machine, in their own team/<login>/weeks/); the CEO signs it but
    # never writes it for them. Worked examples must not model placeholder
    # logins (team/jeanpierre) — that is the exact pattern that shipped a broken
    # contract into a product repo.
    plan = (SKILLS / "plan-week" / "SKILL.md").read_text()
    report = (SKILLS / "report" / "SKILL.md").read_text()

    assert "Never write another contributor's plan" in " ".join(plan.split())
    for text in (plan, report):
        assert "team/jeanpierre" not in text
        assert "team/giovanni" not in text


def test_start_grounds_the_live_repo_state() -> None:
    # /start is the situational view, not a file reader: it must pull the repo
    # pulse (what landed, which branches are in motion, open PRs) and lean on
    # polmem — hot cache first, then a targeted recall — before briefing.
    start = (SKILLS / "start" / "SKILL.md").read_text()
    assert "git log origin/main" in start          # what landed recently
    assert "git branch -vv" in start               # active branches, ahead/behind
    assert "gh pr list" in start                   # open PRs in motion
    assert "hot.md" in start                       # polmem hot cache recap
    assert "Landed:" in start                      # the brief carries the pulse
    assert "In motion" in start
    # Context budget caps — a live measure found decisions.md at 111KB and
    # hot.md at 20KB: /start reads slices, recall retrieves the rest on demand.
    assert "10 most recent" in start
    assert "first screen" in start
    assert "never read the whole file" in " ".join(start.split())
    # UX contract: the answer is the brief, not a reading diary; a stale
    # checkout is the FIRST line, with the action.
    assert "Answer with the brief ONLY" in start
    assert "behind `origin/main`" in start
    # MARVIN-style sections + the answering plugin version in the header.
    for header in ("**THIS WEEK**", "**PULSE**", "**LAST SESSION**", "**MY CALL**"):
        assert header in start, header
    # Cynical co-pilot contract: opinionated close (ranked call with scores),
    # a dry verdict on the last session, motivational language banned.
    assert "(n/10)" in start
    assert "Overrule me" in start
    # The brief renders as markdown (bold headers), never inside a code fence.
    assert "NEVER inside a code fence" in start
    # The brief speaks the contributor's profile language.
    assert "`language:`" in start
    tpl = (TEMPLATES / "profile.yml").read_text()
    assert "language: en" in tpl
    # Voice is per-contributor TONE only; structure (icons, rated call,
    # motivational ban) is invariant product behavior.
    assert "voice: cynical" in tpl
    assert "`voice:`" in start
    assert "not\nthe personality" in start or "not the personality" in " ".join(start.split())
    assert "No\n  motivational language" in start or "no motivational language" in " ".join(start.split()).lower()


def test_codex_review_findings_stay_fixed() -> None:
    # 2026-07-13 external Codex review of v0.5.0..v0.6.1 — pin every fix:
    start = (SKILLS / "start" / "SKILL.md").read_text()
    end = (SKILLS / "end" / "SKILL.md").read_text()
    report = (SKILLS / "report" / "SKILL.md").read_text()
    onboarding = (ROOT.parent / "docs" / "TEAM-ONBOARDING.md").read_text()
    agents = (ROOT.parent / "AGENTS.md").read_text()

    # H1: a copied-but-unedited profile keeps github: octocat → wrong gh target.
    assert 'grep -q "^github: $LOGIN$"' in start
    # H2: non-Claude CLIs need the checkout shim, the installed launcher is Claude-only.
    assert "polaris/bin/polmem" in agents
    # H3: remember WRITES committed history — privacy rule is explicit.
    assert "no secrets, credentials, customer data or personal information" in end
    assert "**writes**" in onboarding
    # M: gh list default is 30 — explicit limits; open PRs are "now", not "as of".
    assert report.count("--limit 200") >= 3
    assert "open at report time" in report
    # M (SUPERSEDED 2026-07-15): "an unsigned plan is not a commitment baseline"
    # assumed the signature model. With no signature, the contributor's own plan
    # IS the baseline — that is what makes planned-vs-actual honest. What
    # survives of the finding: a baseline overtaken by a real reprioritisation
    # must not be reported as a miss. See test_no_signature_gate_anywhere_*.
    assert "the contributor's own stated intent" in " ".join(report.split())
    assert "not a miss" in report
    # M: decisions/lessons carry the owner marker for deterministic attribution.
    assert "(@<login>)" in end


def test_terra_review_findings_stay_fixed() -> None:
    # 2026-07-13 second external review (gpt-5.6) — pin every fix:
    start = (SKILLS / "start" / "SKILL.md").read_text()
    end = (SKILLS / "end" / "SKILL.md").read_text()
    report = (SKILLS / "report" / "SKILL.md").read_text()
    onboarding = (ROOT.parent / "docs" / "TEAM-ONBOARDING.md").read_text()

    # H1: the identity gate HARD-STOPS (|| echo continued happily) and covers
    # pre-existing profiles, not only freshly created ones.
    assert 'exit 1' in start
    assert "runs in BOTH branches" in start
    # H2: non-Claude users get a working polmem path in the failure branch itself.
    assert "polaris/bin/polmem" in start
    # H3: the handoff commit stages the journal line remember just wrote.
    assert ".wiki/journal" in end
    # M (REVERSED 2026-07-15): "an unsigned weekly file is never briefed as active
    # work" was itself the defect — it is how /start told a contributor their own
    # focus was not authorised work. The plan is theirs and is briefed as active;
    # only a RED item waiting on a NAMED approver is briefed as blocked.
    assert "brief it as active work" in start
    assert "waiting on its **named** approver" in start
    # M: commit evidence paginates past 100.
    assert "--paginate" in report
    # M: onboarding preflights gh install + auth.
    assert "gh auth status" in onboarding and "gh auth login" in onboarding


def test_current_md_converges_on_the_main_worktree_nothing_open_lost() -> None:
    # The founder's actual workflow (2026-07-15): "lavoro con mille panel wt
    # diversi ma devo fare poi handoff su main di current". current.md is
    # gitignored, so it never travels with a branch — a panel that writes it in
    # its own worktree writes a handoff nobody reads, because the next session
    # opens the MAIN checkout. Measured on one live repo: three worktrees, three
    # orphaned copies (80KB @ 12 Jul, 66KB @ 8 Jul, one absent) — each one a
    # handoff its author never saw again. So resolve to the main worktree and let
    # the panels converge there. v0.8.1's per-checkout isolation was the bug, not
    # the safety; and size stays an OUTPUT of only-open-truth, never an eviction
    # criterion.
    update = (SKILLS / "update" / "SKILL.md").read_text()
    end = (SKILLS / "end" / "SKILL.md").read_text()
    flat = " ".join(update.split())

    for writer in (update, end):
        # Mechanical resolution — main worktree is the first entry of the list.
        assert "git worktree list --porcelain | head -1" in writer
        assert "MAIN_WT" in writer
    assert "Resolve it from the MAIN worktree, always" in update
    assert "nobody will ever read" in flat

    # The branch is the panel's identity: one panel, one worktree, one branch —
    # which is also what makes /end's merge check possible without any panel
    # having to know which others are alive.
    assert "the branch is a thread's identity" in flat
    assert "`feat/123-short-name`: <one concrete first step>" in update
    assert "never overwrite it with yours" in flat

    assert "Nothing open is ever lost" in flat
    assert "never a silent delete" in " ".join(end.split())
    assert "Never trim a live thread to make the file smaller" in flat
    assert "stale?" in update
    assert "not yours to remove" in flat
    assert "## Open" in update
    # Orphans from before this rule are surfaced, never silently deleted.
    assert "may be the only copy of a handoff" in flat


def test_end_closes_a_thread_only_against_verified_merge() -> None:
    # THE founder requirement (2026-07-15), and the one an inference-based rule
    # gets wrong: with several panels on several worktrees, a branch parked for
    # days while its owner works elsewhere is LIVE work. "No recent activity" and
    # "no active branch" are not death certificates — merge status is, and it is
    # mechanically checkable. An open PR is not a closed thread.
    end = (SKILLS / "end" / "SKILL.md").read_text()
    flat = " ".join(end.split())
    assert "only when its work actually landed" in flat
    assert "git worktree list" in end          # a worktree holding the branch = live
    assert "git branch --merged origin/main" in end
    assert "gh pr list --head" in end
    assert "an open PR is not a closed thread" in flat
    assert "parked, not dead" in flat
    # /update stays powerless here regardless.
    update = (SKILLS / "update" / "SKILL.md").read_text()
    assert "`/update` has no closing authority" in " ".join(update.split())


def test_update_has_no_closing_authority_only_end_closes() -> None:
    # Founder correction (2026-07-14, issue #24 follow-up): /update runs often,
    # sometimes from several panels within the same hour — giving it authority
    # to remove/close a ledger item is exactly the surface that let one panel's
    # cleanup collide with another panel's live thread. Only the deliberate,
    # one-shot /end may close an item; /update may only add, update its own
    # entries, or flag one stale.
    update = (SKILLS / "update" / "SKILL.md").read_text()
    end = (SKILLS / "end" / "SKILL.md").read_text()
    flat_update = " ".join(update.split())
    flat_end = " ".join(end.split())

    assert "`/update` has no closing authority" in flat_update
    assert "never closes anything" in flat_update
    assert "only `/end` may remove a thread" in flat_update
    assert "only Team OS command with closing authority" in flat_end


def test_end_checks_repo_wiring_before_remember_not_the_binary() -> None:
    # Found by a live eval, then reproduced by hand (2026-07-15): `polmem` is
    # often installed GLOBALLY and wired to another repo. Run `remember` in a
    # repo with no `.wiki/journal/` and it does not fail — it silently writes the
    # handoff into that other vault, carrying this session's content out of this
    # repository and breaking /end's own "never writes outside the current
    # repository" guarantee. The old failure branches only covered "binary
    # missing" and "announces not memory-wired"; neither catches the dangerous
    # middle state, and `command -v polmem` passes right through it. So the
    # wiring test must be the repo's directory, never the binary resolving.
    end = (SKILLS / "end" / "SKILL.md").read_text()
    flat = " ".join(end.split())
    assert "test -d .wiki/journal" in end
    assert "the binary resolving is not the test" in flat
    assert "silently lands in **someone else's** journal" in flat
    # The remember call must come AFTER the wiring check, or the check is theatre.
    assert end.index("test -d .wiki/journal") < end.index("polmem remember")


def test_end_feeds_the_repo_journal() -> None:
    # The daily loop closes the memory cycle mechanically: /start consumes
    # (recall), /end FEEDS — one machine-readable line into the repo journal
    # via polmem remember; the offline distill decides what is durable. Without
    # this, the graph only grows when someone remembers to propose a decision.
    end = (SKILLS / "end" / "SKILL.md").read_text()
    assert "polmem remember" in end
    assert "not memory-wired" in end  # same failure branch as /start


def test_no_signature_gate_anywhere_work_is_owner_led() -> None:
    # Founder correction (2026-07-15): the signature model is REVERSED, not
    # tuned. v0.8.0's `auto_authorized: secondary` was a patch on a broken
    # default — "blocked until the CEO signs" — and the default was the bug.
    # The repo's own charter says it plainly: green work is self-merged by its
    # owner after the applicable gates, amber proceeds on a recorded decision
    # ("silence is not a block"), and the lead "is not the default technical
    # gate" — their review of the weekly focus is PRIORITY ALIGNMENT, "not a
    # technical approval gate". A plugin that ships the opposite trains
    # contributors to ask permission for reversible work and makes the founder
    # the bottleneck for the whole team at once.
    texts = {
        "plan-week": (SKILLS / "plan-week" / "SKILL.md").read_text(),
        "start": (SKILLS / "start" / "SKILL.md").read_text(),
        "report": (SKILLS / "report" / "SKILL.md").read_text(),
        "end": (SKILLS / "end" / "SKILL.md").read_text(),
        "config.yml": (TEMPLATES / "config.yml").read_text(),
        "profile.yml": (TEMPLATES / "profile.yml").read_text(),
        "weekly-plan.md": (TEMPLATES / "weekly-plan.md").read_text(),
        "README.md": (TEMPLATES / "README.md").read_text(),
    }
    for name, text in texts.items():
        for banned in ("ceo_signature", "execution_authorized", "auto_authorized",
                       "auto-authorized", "unapproved proposal"):
            assert banned not in text, f"{banned} still gates work in {name}"

    plan = texts["plan-week"]
    flat_plan = " ".join(plan.split())
    # The plan states truth, not a permission state.
    assert "lead_review: pending" in plan
    assert "priority alignment, never a gate" in plan
    assert "silence is not a block" in flat_plan
    # The gate survives exactly where being wrong is irreversible — and it names
    # an approver rather than defaulting to the lead.
    assert "red stop-lines" in flat_plan
    assert "waits for its named approver" in flat_plan
    for red in ("RLS", "personal-data", "processor/vendor", "irreversible data migration"):
        assert red in plan, red
    # The repo's own charter outranks the plugin: an audited repo may name
    # approvers this list cannot know about (e.g. a signed SoD matrix).
    assert "charter wins over this section" in flat_plan
    assert "segregation-of-duties" in plan
    # /start briefs the contributor's plan as their work, not as a pending request.
    assert "brief it as active work, never as something\n   awaiting permission" in texts["start"]
    assert "never blocks urgent or clearly-owned work" in " ".join(texts["start"].split())


def test_no_permission_language_survives_anywhere_in_the_shipped_surface() -> None:
    # The targeted assertions above check the places we KNEW about; this sweeps
    # every shipped file, because a live grep found two the targeted tests
    # missed — including /plan-week's `description:` frontmatter ("the CEO signs
    # it"), which is the single string the model reads when deciding whether and
    # how to run the skill. A gate deleted from the body but left in the
    # description still ships the gate.
    root = ROOT.parent
    surface = [
        *SKILLS.glob("*/SKILL.md"),
        *TEMPLATES.glob("*"),
        root / "README.md",
        root / "AGENTS.md",
        root / "docs" / "TEAM-ONBOARDING.md",
    ]
    # "CEO" is banned as a bare word, not as a phrase: the first pass banned
    # "CEO signs" and plan-week Step 1 sailed through saying "the CEO reviews
    # and signs it". There is no CEO role in this contract — there is a repo
    # owner, and (where the repo has one) a lead who sets priorities and red
    # stop-lines. A title that grants authority by rank is how the gate grows
    # back.
    banned = ("ceo_signature", "execution_authorized", "auto_authorized",
              "auto-authorized", "unapproved proposal", "CEO", "ceo",
              "signature gates", "until signed", "proposal until")
    offenders = [
        f"{path.relative_to(root)}: {term}"
        for path in surface if path.is_file()
        for term in banned
        if re.search(rf"(?<![A-Za-z]){re.escape(term)}(?![A-Za-z])", path.read_text())
    ]
    assert not offenders, f"permission-gate language still ships: {offenders}"


def test_capacity_is_a_planning_guide_not_a_quota() -> None:
    # The live contract corrected this by hand before the plugin did — a real
    # contributor profile carries `weekly_capacity: 3 # planning guide, not a
    # quota`. A hard cap turns an honesty device into a lid on output.
    plan = (SKILLS / "plan-week" / "SKILL.md").read_text()
    flat = " ".join(plan.split())
    assert "a planning guide, not a quota" in flat
    assert "Capacity rule (hard)" not in plan
    assert "not to cap output" in flat


def test_lessons_are_part_of_the_contract() -> None:
    # Product repos carry lessons.md next to decisions.md; /end proposes durable
    # lessons the same gated way it proposes decisions.
    end = (SKILLS / "end" / "SKILL.md").read_text()
    readme = (ROOT.parent / "README.md").read_text()
    assert "lessons.md" in end
    assert "lessons.md" in readme


def test_evidence_skills_pin_the_iso_week_filename_convention() -> None:
    plan = (SKILLS / "plan-week" / "SKILL.md").read_text()
    report = (SKILLS / "report" / "SKILL.md").read_text()
    # plan-week writes weeks/YYYY-Www.md, report writes reports/YYYY-Www.md — lock both.
    assert "weeks/YYYY-Www.md" in plan
    assert "reports/YYYY-Www.md" in report


def test_evidence_skills_ship_concrete_tracker_commands() -> None:
    plan = (SKILLS / "plan-week" / "SKILL.md").read_text()
    report = (SKILLS / "report" / "SKILL.md").read_text()
    # plan-week must pull live issues; report must gather tracker evidence.
    assert "gh issue list" in plan
    assert "weekly_capacity" in plan
    assert "gh pr list" in report
    assert "gh issue list" in report
    # The report is ground-truth-first: remote synced, commits resolved
    # login->commits SERVER-SIDE (the REAL test proved an author-email pattern
    # returns 0 on a real repo: squash commits carry the user's configured
    # email, e.g. gmail, not the noreply form), session logs as the day-by-day
    # backbone, decisions.md scanned in-range.
    assert "git fetch --prune" in report
    assert "commits?author=$LOGIN" in report
    assert "@users.noreply.github.com" not in report
    assert "team/<login>/sessions/" in report
    assert "decisions.md" in report


def test_report_is_a_real_report_not_just_a_diff_table() -> None:
    # Locked 2026-07-13: "il report non deve essere solo planned/actual" — the
    # real weekly reports (noemi W20–W27) carry a TL;DR, day-by-day evidence,
    # merged-PR ground truth, metrics, and an explicit PM-action section. The
    # skill and template pin that structure, and scale down honestly.
    report = (SKILLS / "report" / "SKILL.md").read_text()
    report_tpl = (TEMPLATES / "weekly-report.md").read_text()
    for header in ("## TL;DR", "## Planned versus actual", "## Metrics",
                   "## Bottleneck", "## PM action", "## Next week"):
        assert header in report, f"missing {header} in skill"
        assert header in report_tpl, f"missing {header} in template"
    assert "never pad" in " ".join(report.split())
    # The bottleneck hunt is a ritual, not a vibe: mandatory, with a removal proposal.
    flat = " ".join(report.split())
    assert "mandatory, never" in flat and "removal proposal" in flat


def test_report_uses_login_evidence_not_local_git_identity() -> None:
    # The off-by-one + wrong-identity defects from the live benchmark: the report
    # must query the tracker by the contributor's GitHub login and must NOT fall
    # back to git-author-by-local-email (resolves to the running machine, useless
    # for a teammate report).
    report = (SKILLS / "report" / "SKILL.md").read_text()
    assert 'git config user.email' not in report or 'Never use' in report
    assert 'author:$LOGIN' in report


def test_report_pins_the_iso_week_computation() -> None:
    # Week = ISO week of the reported period; the evidence window is derived from
    # WEEK so filename and evidence cannot disagree (the W29-vs-W28 misfile).
    report = (SKILLS / "report" / "SKILL.md").read_text()
    assert "date +%G-W%V" in report
    assert "fromisocalendar" in report


def test_plan_week_ranks_severity_over_staleness_and_grounds_scope() -> None:
    plan = (SKILLS / "plan-week" / "SKILL.md").read_text()
    flat = " ".join(plan.split())
    assert "[CRITICAL]" in plan  # severity signal in the title is a first-tier rank
    assert "severity outranks age" in flat
    # staleness must be introduced after the severity rule (final tiebreak only).
    assert flat.index("severity outranks age") < flat.index("final tiebreak")
    # scope grounding when preferred_areas is empty.
    assert "preferred_areas` is empty" in plan
    assert "CODEOWNERS" in plan


def test_start_handles_not_memory_wired_without_running_init() -> None:
    start = (SKILLS / "start" / "SKILL.md").read_text()
    flat = " ".join(start.split())
    assert "not memory-wired" in start
    assert "Do not run `polmem init` yourself" in start
    # recall is assumed context, not current state.
    assert "not current state" in flat


def test_repo_contract_templates_exist_are_english_and_match_worked_examples() -> None:
    for name in ("config.yml", "profile.yml", "weekly-plan.md", "weekly-report.md",
                 "state.gitignore", "README.md"):
        assert (TEMPLATES / name).is_file(), f"missing template {name}"

    # The root README is the contract's front door: it must pin the single root,
    # own-path provisioning, the OWNERSHIP boundary (2026-07-15: the signature
    # gate it used to pin is gone — red stop-lines replace it) and privacy.
    root_readme = (TEMPLATES / "README.md").read_text()
    for required in (
        "One root: `_polaris/`",
        "Never create another contributor's path",
        "Your plan does not wait for a signature",
        "silence is not a block",
        "named** approver",
        "Privacy boundaries",
    ):
        assert required in root_readme

    plan_tpl = (TEMPLATES / "weekly-plan.md").read_text()
    report_tpl = (TEMPLATES / "weekly-report.md").read_text()

    # English, reconciled to the skills' worked examples — no residual Italian headers.
    for stale in ("Previsto vs consegnato", "Lavoro proposto", "Non iniziare", "Cosa abbiamo"):
        assert stale not in plan_tpl and stale not in report_tpl

    # Headers must match the skills' worked examples exactly.
    plan_skill = (SKILLS / "plan-week" / "SKILL.md").read_text()
    report_skill = (SKILLS / "report" / "SKILL.md").read_text()
    for header in ("## Outcome", "## Not starting", "## Evidence"):
        assert header in plan_tpl and header in plan_skill
    for header in ("## TL;DR", "## Planned versus actual", "## PM action"):
        assert header in report_tpl and header in report_skill

    # Contributor schema is explicit about the exact GitHub login.
    config_tpl = (TEMPLATES / "config.yml").read_text()
    profile_tpl = (TEMPLATES / "profile.yml").read_text()
    assert "exact GitHub login" in config_tpl
    assert "exact GitHub login" in profile_tpl


def test_sessions_are_per_contributor_not_shared() -> None:
    # v0.4.4: session logs moved from the shared <root>/sessions/ to the per-contributor
    # <root>/team/<login>/sessions/ — same isolation as weeks/ and reports/, so contributors
    # never collide writing to the same directory.
    start = (SKILLS / "start" / "SKILL.md").read_text()
    update = (SKILLS / "update" / "SKILL.md").read_text()
    end = (SKILLS / "end" / "SKILL.md").read_text()
    for skill in (start, update, end):
        assert "team/<login>/sessions/" in skill

    # /start's collision check must glob across contributors' session logs too.
    assert "team/*/sessions/" in start

    readme = (ROOT.parent / "README.md").read_text()
    onboarding = (ROOT.parent / "docs" / "TEAM-ONBOARDING.md").read_text()
    assert "sessions/            # per-day handoffs" in readme
    assert "_polaris/team/<your-github-login>/sessions/" in onboarding
    assert "Migrating from" in onboarding


def test_agents_md_bridges_the_skills_to_non_claude_clis() -> None:
    # Codex/other agent CLIs consume the skills from a repo checkout via
    # AGENTS.md — it must link every shipped skill and explain the
    # $CLAUDE_PLUGIN_ROOT substitution.
    agents = (ROOT.parent / "AGENTS.md").read_text()
    for name in ("start", "update", "end", "plan-week", "report"):
        assert f"polaris/skills/{name}/SKILL.md" in agents
    assert "$CLAUDE_PLUGIN_ROOT" in agents
    assert "_polaris/" in agents


def test_lifecycle_skills_verify_the_branch() -> None:
    for name in ("start", "end"):
        text = (SKILLS / name / "SKILL.md").read_text()
        assert "git rev-parse --abbrev-ref HEAD" in text


def test_onboarding_contains_a_real_tooling_preflight() -> None:
    onboarding = (ROOT.parent / "docs" / "TEAM-ONBOARDING.md").read_text()

    for required in (
        "superpowers@claude-plugins-official",
        "context7@claude-plugins-official",
        "claude plugin list",
        "claude mcp list",
        "codebase-memory-mcp",
    ):
        assert required in onboarding
