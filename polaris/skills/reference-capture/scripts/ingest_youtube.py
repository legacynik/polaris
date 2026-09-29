#!/usr/bin/env python3
"""Fetch a YouTube video's transcript, metadata and cover into the dossier source layout.

Only YouTube is handled here. Articles and repositories are already reachable with the tools an
agent has natively (fetch a page, clone a repo), and wrapping those would add a dependency that
buys nothing. A video is different: without subtitles there is no way to read the source at all,
which is why ten transcript-less videos sat unusable in the archive.

yt-dlp does the fetching. It already provides subtitles, chapters, metadata and the thumbnail, and
it is the fallback every other YouTube transcript tool falls back to when the direct API is
blocked — so calling it first skips the flaky path rather than discovering it later.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

TIMESTAMP_RE = re.compile(r"^(\d{2}:\d{2}:\d{2})\.\d{3} --> ")
TAG_RE = re.compile(r"<[^>]+>")


def _require_ytdlp() -> str:
    binary = shutil.which("yt-dlp")
    if not binary:
        sys.exit("yt-dlp not found. Install it (brew install yt-dlp) and retry.")
    return binary


def _fetch(url: str, workdir: Path, lang: str) -> None:
    """Pull subtitles, metadata and thumbnail without downloading the video itself."""
    cmd = [
        _require_ytdlp(), "--skip-download",
        "--write-subs", "--write-auto-subs", "--sub-langs", lang, "--sub-format", "vtt",
        "--write-info-json", "--write-thumbnail", "--convert-thumbnails", "jpg",
        "-o", str(workdir / "source"), url,
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        sys.exit(f"yt-dlp failed:\n{result.stderr[-2000:]}")


def _cue_lines(vtt: str) -> list[tuple[str, str]]:
    """Pair each cue's start time with its text, dropping VTT markup."""
    pairs: list[tuple[str, str]] = []
    stamp = None
    for raw in vtt.splitlines():
        match = TIMESTAMP_RE.match(raw.strip())
        if match:
            stamp = match.group(1)
            continue
        line = TAG_RE.sub("", raw).strip()
        if stamp and line and not line.startswith(("WEBVTT", "Kind:", "Language:", "NOTE")):
            pairs.append((stamp, line))
    return pairs


def _dedupe(pairs: list[tuple[str, str]]) -> list[tuple[str, str]]:
    """Collapse YouTube's rolling-caption repetition.

    Auto-generated captions repaint the previous line on every cue, so a raw conversion triples
    the text and buries the content. Keeping only lines not already carried forward restores the
    spoken sequence — without this the transcript is technically complete and practically unusable.
    """
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for stamp, line in pairs:
        if line in seen:
            continue
        seen.add(line)
        out.append((stamp, line))
    return out


def _paragraphs(pairs: list[tuple[str, str]], every: int = 6) -> list[str]:
    """Group lines into timestamped paragraphs so the text stays quotable by position."""
    blocks = []
    for start in range(0, len(pairs), every):
        chunk = pairs[start:start + every]
        text = " ".join(line for _, line in chunk)
        blocks.append(f"**[{chunk[0][0]}]** {text}")
    return blocks


def _meta(workdir: Path) -> dict:
    found = next(workdir.glob("*.info.json"), None)
    if not found:
        sys.exit("yt-dlp produced no metadata; the video may be private or region-locked.")
    raw = json.loads(found.read_text(encoding="utf-8"))
    keep = ("id", "title", "channel", "upload_date", "duration", "webpage_url", "chapters", "description")
    return {key: raw.get(key) for key in keep}


def _render(meta: dict, body: list[str]) -> str:
    head = [
        "---",
        f"title: {meta.get('title')}",
        f"channel: {meta.get('channel')}",
        f"video_date: {meta.get('upload_date')}",
        f"source_url: {meta.get('webpage_url')}",
        "note: raw source material, not a dossier — never catalog: true",
        "---",
        "",
        f"# {meta.get('title')}",
        "",
    ]
    chapters = meta.get("chapters") or []
    if chapters:
        head.append("## Chapters")
        head += [f"- `{int(c.get('start_time', 0))//3600:02d}:"
                 f"{int(c.get('start_time', 0))%3600//60:02d}:"
                 f"{int(c.get('start_time', 0))%60:02d}` {c.get('title')}" for c in chapters]
        head.append("")
    head += _description_block(meta.get("description") or "")
    head.append("## Transcript")
    head.append("")
    return "\n".join(head + body) + "\n"


def _description_block(text: str) -> list[str]:
    """The description, and the links it carries, because that is where the sources live.

    yt-dlp already fetched this; the renderer used to drop it. The cost was measured on
    2026-09-10: a tutorial whose description listed ten arXiv papers, one per tip, produced
    an extraction that recorded six of eleven tips as "asserted without evidence" — the
    extractors read the transcript, and the transcript said the studies were never named.
    They were named, one file over. A source fetched and then hidden is a source not fetched.
    """
    if not text.strip():
        return []
    links = sorted({m.group(0) for m in re.finditer(r"https?://\S+", text)})
    out = ["## Description", "", "```", text.strip(), "```", ""]
    if links:
        out += ["## Links in the description", ""]
        out += [f"- {u.rstrip('.,);')}" for u in links]
        out.append("")
    return out


def _collect(workdir: Path, out: Path) -> Path:
    """Move yt-dlp's output into the canonical layout and return the transcript path."""
    vtt = next(workdir.glob("*.vtt"), None)
    if not vtt:
        sys.exit("No subtitles available for this video — captions are disabled upstream.")
    meta = _meta(workdir)
    source = out / "source"
    source.mkdir(parents=True, exist_ok=True)
    (out / "imgs").mkdir(exist_ok=True)
    transcript = source / "transcript.md"
    body = _paragraphs(_dedupe(_cue_lines(vtt.read_text(encoding="utf-8", errors="replace"))))
    transcript.write_text(_render(meta, body), encoding="utf-8")
    (source / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False), encoding="utf-8")
    thumb = next(workdir.glob("*.jpg"), None)
    if thumb:
        shutil.copy(thumb, out / "imgs" / "cover.jpg")
    return transcript


ROLLING_VTT = """WEBVTT
Kind: captions
Language: en

00:00:01.000 --> 00:00:03.000
hooks are actions

00:00:02.500 --> 00:00:05.000
hooks are actions
that you want to guarantee

00:00:04.500 --> 00:00:07.000
that you want to guarantee
whenever we hit certain <c>events</c>
"""


def selfcheck() -> int:
    """Exercise the parsing pipeline on a synthetic rolling-caption fixture.

    The fetch itself needs the network and a live video, so it stays out of here; what is locked
    instead is the part that silently degrades. YouTube's auto-captions repaint the previous line
    on every cue, and a converter that does not collapse that produces a transcript which is
    technically complete, three times too long, and unreadable — a failure no exit code reports.
    """
    pairs = _cue_lines(ROLLING_VTT)
    assert ("00:00:01", "hooks are actions") in pairs, pairs
    assert not any("WEBVTT" in line or line.startswith("Kind:") for _, line in pairs), pairs
    assert not any("<c>" in line for _, line in pairs), "VTT markup must not survive"

    deduped = _dedupe(pairs)
    texts = [line for _, line in deduped]
    assert len(texts) == len(set(texts)), texts
    assert texts == ["hooks are actions", "that you want to guarantee",
                     "whenever we hit certain events"], texts
    assert len(deduped) < len(pairs), "the fixture must actually contain repetition"

    blocks = _paragraphs(deduped, every=2)
    assert len(blocks) == 2, blocks
    assert blocks[0].startswith("**[00:00:01]** "), blocks[0]
    assert "hooks are actions that you want to guarantee" in blocks[0], blocks[0]

    rendered = _render({"title": "T", "channel": "C", "upload_date": "20260101",
                        "webpage_url": "https://example.test/v",
                        "chapters": [{"start_time": 3725, "title": "Late chapter"}]}, blocks)
    assert "never catalog: true" in rendered, "raw source must never claim catalog ownership"
    assert "`01:02:05` Late chapter" in rendered, rendered
    assert _paragraphs([], every=2) == [], "an empty transcript must not fabricate a paragraph"

    # The description is where a tutorial keeps its sources. Dropping it made an extraction
    # record six of eleven tips as "asserted without evidence" while ten arXiv papers sat in
    # the metadata (2026-09-10). A fetched source that never reaches the reader is not fetched.
    sourced = _render({"title": "T", "channel": "C", "upload_date": "20260101",
                       "webpage_url": "https://example.test/v", "chapters": [],
                       "description": "Studies:\nTip 1: https://arxiv.org/abs/1234.5678\n"
                                      "Tip 2: https://arxiv.org/abs/1234.5678 again\n"
                                      "Repo: https://example.test/repo."}, blocks)
    assert "## Description" in sourced, "the description must reach the reader"
    assert "https://arxiv.org/abs/1234.5678" in sourced, sourced
    assert sourced.count("- https://arxiv.org/abs/1234.5678") == 1, "links must be deduplicated"
    assert "- https://example.test/repo\n" in sourced, "trailing punctuation must not enter the link"
    assert "## Links in the description" not in _render(
        {"title": "T", "channel": "C", "upload_date": "20260101",
         "webpage_url": "https://example.test/v", "chapters": [], "description": "   "}, blocks
    ), "an empty description must not fabricate a section"

    print("SELFCHECK OK — 17 assertions")
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("url", nargs="?")
    parser.add_argument("--out", help="dossier directory; source/ is created inside")
    parser.add_argument("--lang", default="en", help="subtitle language code (default: en)")
    parser.add_argument("--selfcheck", action="store_true", help="run offline assertions and exit")
    args = parser.parse_args(argv)
    if args.selfcheck:
        return selfcheck()
    if not args.url or not args.out:
        parser.error("url and --out are required (or use --selfcheck)")
    out = Path(args.out).expanduser().resolve()
    workdir = out / ".ytdlp"
    workdir.mkdir(parents=True, exist_ok=True)
    try:
        _fetch(args.url, workdir, args.lang)
        transcript = _collect(workdir, out)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
    print(f"OK — {transcript}")
    print("Next: write dossier.md beside source/ using references/schema.md (schema_version 2).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
