#!/usr/bin/env python3
"""Incident log helper for the sre-incident-response skill.

Commands (Python 3 standard library only; every time is UTC):

  open <log-dir> <slug> [--title TEXT]
      Create the incident folder <log-dir>/<id>/ first (the id starts with the
      date and time), then the log <id>/<id>.md inside it from the template, and
      print the id, the log path and the folder. Everything about the incident
      lives in that folder. Never overwrites: a name that exists gets -2, -3.

  add <log> <tag> <source> <text> [--at TIME]
      Stamp one timeline entry and insert it in event-time order. Without --at
      the event time is the clock now. --at takes a time the human or a skill
      stated: HH:MM, HH:MM:SS (today, UTC) or YYYY-MM-DD HH:MM[:SS]. An entry
      written well after its event time carries "logged <time>" so lateness is
      visible. Source "observed" cannot take --at: an observation is stamped
      when it is made.

  save <log> <source> [--file PATH]
      Save an answer verbatim (from stdin, or --file) as <source>.md beside the
      log, in the incident folder, with a one-line provenance header. The source
      is an investigator's skill name, or "coordinator" for the coordinator's own
      output. Never overwrites: a repeat gets -2, -3. Prints the name to link from
      the log: <source>.md. (A log from before the incident folder existed sits
      directly in the log directory and keeps its answers in a folder named for
      it; the link is then <id>/<source>.md.)

  check <log>
      Validate the state block, the synthesis section, the saved-answer links, the
      tags, the line length and the ordering.

  sort <log>
      Re-sort an out-of-order timeline by event time (stable; text unchanged).

  durations <log>
      Print time to detect, engage, mitigate and resolve from logged entries
      only; an endpoint that was never logged is "not recorded".

  list <log-dir> [--active]
      One line per incident log in the folder, oldest first: id, status,
      severity, next update due and the log path. --active hides closed
      incidents, so "continue" can find what is still being worked.

  watch <log> init --channel ID --thread-ts TS [--canvas ID] [--cron-id ID]
  watch <log> show
  watch <log> update [--last-seen TS] [--cron-id ID] [--own TS ...] [--canvas-file PATH]
                     [--pending | --clear-pending] [--notified]
                     [--analysis-start | --clear-analysis-start]
  watch <log> stop
      Keep the state of the Slack thread watch in <incident folder>/watch.json:
      channel, thread ts, canvas id, the newest thread ts already handled, the
      ts of every message the coordinator posted itself (so the watch can ignore
      them), the scheduled job id, whether the watch is active, and `pending`: set
      while an updated analysis is waiting for other agents to stop (--pending
      stamps the start once, --clear-pending removes it, --notified records that
      the commander was told). --analysis-start stores the clock as a Slack-style ts
      (analysis_started_ts) when an updated analysis begins, so the thread can be
      read for an update posted since; --clear-analysis-start removes it. `show`
      adds pending_minutes, from the clock. --canvas-file
      stores a copy of the canvas text as watch-canvas.md, the baseline the next
      check compares against. `init` refuses to replace an active watch. Only
      the standard library is used; nothing here calls Slack.

  now [--plus MINUTES]
      Print the clock as YYYY-MM-DD HH:MMZ, optionally MINUTES ahead, for the
      "Updated" and "Next update due" lines, so no time in the log is typed by hand.

Set INCIDENT_LOG_NOW to an ISO time (2026-10-07T10:15:00) to fix the clock in a
test. Exit status: 0 ok, 1 check found errors, 2 bad input.
"""
import argparse
import calendar
import datetime as dt
import fcntl
import json
import os
import re
import sys
import tempfile

TAGS = ("impact-start", "alerted", "engaged", "hypothesis", "evidence",
        "decision", "action", "mitigated", "comms", "resolved", "closed", "note")
LEGACY_TAGS = ("detected",)
STATUSES = ("open", "closed")
# Statuses written before the log had only open and closed; they still read.
LEGACY_STATUSES = {"monitoring": "open", "mitigated": "open", "resolved": "closed"}
STATE_FIELDS = ("Status", "Severity", "Impact", "Leading hypothesis",
                "Actions taken", "Owner", "Next update due")
MAX_TEXT = 240
MAX_STATE_LINE = 200
MAX_SYNTH_LINE = 300
SYNTH_LABELS = ("Combined reading", "Open", "Next evidence needed")
LATE_SECONDS = 60
FUTURE_SECONDS = 120

ENTRY_RE = re.compile(r"^- (\d{4}-\d{2}-\d{2} \d{2}:\d{2}(?::\d{2})?)Z \[([a-z-]+)\] ")
SLUG_RE = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
SOURCE_RE = re.compile(r"^[a-z0-9][a-z0-9-]*$")
CLOCK_RE = re.compile(r"^(\d{1,2}):(\d{2})(?::(\d{2}))?$")
FULL_RE = re.compile(r"^(\d{4})-(\d{2})-(\d{2}) (\d{1,2}):(\d{2})(?::(\d{2}))?$")

TEMPLATE = """# {id}: {title}

## State
Status: open
Severity: not yet proposed
Impact: unknown
Leading hypothesis: none yet
Actions taken: none
Owner: unassigned
Next update due: not set

## Synthesis
Updated: not yet
| Source | Finding | Confidence | Does not cover |
|---|---|---|---|
Combined reading: no evidence yet
Open: not yet assessed
Next evidence needed: none yet

## Timeline
"""


class Bad(Exception):
    """Invalid input: reported as ERROR and exit status 2."""


def now_utc():
    override = os.environ.get("INCIDENT_LOG_NOW")
    if override:
        return dt.datetime.strptime(override.rstrip("Z"), "%Y-%m-%dT%H:%M:%S")
    return dt.datetime.utcnow().replace(microsecond=0)


def parse_at(value, now):
    """Return (datetime, has_seconds) for a stated UTC time, or raise Bad."""
    v = value.strip().rstrip("Zz").strip().replace("T", " ")
    m = CLOCK_RE.match(v)
    if m:
        h, mi, s = int(m.group(1)), int(m.group(2)), m.group(3)
        try:
            when = now.replace(hour=h, minute=mi, second=int(s or 0))
        except ValueError:
            raise Bad("--at %r is not a valid time" % value)
        if (when - now).total_seconds() > FUTURE_SECONDS:
            raise Bad("--at %r is later than now (%s UTC); give the full date "
                      "(YYYY-MM-DD HH:MM) if it was on an earlier day"
                      % (value, now.strftime("%H:%M:%S")))
        return when, s is not None
    m = FULL_RE.match(v)
    if m:
        y, mo, d, h, mi, s = m.groups()
        try:
            when = dt.datetime(int(y), int(mo), int(d), int(h), int(mi), int(s or 0))
        except ValueError:
            raise Bad("--at %r is not a valid date and time" % value)
        if (when - now).total_seconds() > FUTURE_SECONDS:
            raise Bad("--at %r is in the future (now is %s UTC)"
                      % (value, now.strftime("%Y-%m-%d %H:%M:%S")))
        return when, s is not None
    raise Bad("--at %r: use HH:MM, HH:MM:SS or YYYY-MM-DD HH:MM[:SS], in UTC "
              "(no zone offsets)" % value)


def fmt(when, has_seconds):
    return when.strftime("%Y-%m-%d %H:%M:%S" if has_seconds else "%Y-%m-%d %H:%M")


def sort_key(ts):
    """Pad a minute-precision stamp so minute and second stamps compare."""
    return ts if len(ts) == 19 else ts + ":00"


def to_dt(ts):
    return dt.datetime.strptime(sort_key(ts), "%Y-%m-%d %H:%M:%S")


def status_of(state):
    """The log's Status as 'open' or 'closed' (or the raw word if unknown), and
    whether it was a legacy word."""
    raw = state.get("Status", "").split(" ")[0].strip(",;:")
    if raw in LEGACY_STATUSES:
        return LEGACY_STATUSES[raw], True
    return raw, False


def read_lines(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return fh.readlines()
    except OSError as exc:
        raise Bad("cannot read %s: %s" % (path, exc.strerror))


def write_atomic(path, lines):
    directory = os.path.dirname(os.path.abspath(path))
    mode = os.stat(path).st_mode & 0o777
    fd, tmp = tempfile.mkstemp(dir=directory, prefix=".tmp-incident-")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            fh.writelines(lines)
            fh.flush()
            os.fsync(fh.fileno())
        os.chmod(tmp, mode)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


class Locked(object):
    """Exclusive lock on the log's directory, so parallel adds do not clobber."""

    def __init__(self, path):
        self.fd = os.open(os.path.dirname(os.path.abspath(path)), os.O_RDONLY)

    def __enter__(self):
        fcntl.flock(self.fd, fcntl.LOCK_EX)
        return self

    def __exit__(self, *exc):
        fcntl.flock(self.fd, fcntl.LOCK_UN)
        os.close(self.fd)


def timeline_blocks(lines):
    """Return (header_index, blocks, section_end).

    A block is [start, end) over the lines of one entry (an entry line plus any
    continuation lines). Trailing blank lines are not part of the last block.
    """
    header = None
    for i, line in enumerate(lines):
        if line.rstrip() == "## Timeline":
            header = i
            break
    if header is None:
        raise Bad("no '## Timeline' heading in the log")
    end = len(lines)
    for i in range(header + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break
    starts = [i for i in range(header + 1, end) if lines[i].startswith("- ")]
    blocks = []
    for n, s in enumerate(starts):
        e = starts[n + 1] if n + 1 < len(starts) else end
        while e > s + 1 and not lines[e - 1].strip():
            e -= 1
        blocks.append((s, e))
    return header, blocks, end


def block_key(lines, block):
    m = ENTRY_RE.match(lines[block[0]])
    return sort_key(m.group(1)) if m else None


def cmd_open(args):
    if not SLUG_RE.match(args.slug) or len(args.slug) > 40:
        raise Bad("slug must be lower-case kebab-case, at most 40 characters")
    now = now_utc()
    os.makedirs(args.log_dir, exist_ok=True)
    base = "%s-%s" % (now.strftime("%Y-%m-%d-%H%M"), args.slug)
    n = 1
    while True:
        ident = base if n == 1 else "%s-%d" % (base, n)
        folder = os.path.join(args.log_dir, ident)
        if os.path.exists(folder + ".md"):
            n += 1
            continue
        try:
            os.mkdir(folder)
            break
        except FileExistsError:
            n += 1
    path = os.path.join(folder, ident + ".md")
    title = " ".join((args.title or args.slug.replace("-", " ")).split())
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(TEMPLATE.format(id=ident, title=title))
    print("id=%s" % ident)
    print("log=%s" % path)
    print("folder=%s" % folder)
    print("opened=%s" % fmt(now, True) + "Z")


def answers_location(log):
    """Where this log keeps its saved answers, and the prefix its links carry.

    An incident folder holds the log and the answers together: the log's parent
    folder is named for the log, and a link is just <source>.md. A log from before
    the incident folder existed sits directly in the log directory with its answers
    in a folder named for it: the link is <id>/<source>.md.
    """
    path = os.path.abspath(log)
    stem = os.path.splitext(os.path.basename(path))[0]
    parent = os.path.dirname(path)
    if os.path.basename(parent) == stem:
        return stem, parent, ""
    return stem, os.path.join(parent, stem), stem + "/"


def cmd_add(args):
    tag = args.tag
    if tag in LEGACY_TAGS:
        raise Bad("tag 'detected' was split: use 'alerted' (the monitor or alert "
                  "fired) or 'engaged' (a person or this skill started on it)")
    if tag not in TAGS:
        raise Bad("unknown tag %r; use one of: %s" % (tag, ", ".join(TAGS)))
    if not SOURCE_RE.match(args.source):
        raise Bad("source must be 'observed', 'reported' or a skill name "
                  "(lower-case letters, digits, hyphens)")
    text = " ".join(args.text.split())
    if not text:
        raise Bad("text is empty")
    if len(text) > MAX_TEXT:
        raise Bad("text is %d characters; the limit is %d. One event per line: "
                  "keep the fact, put the detail in the investigator's saved "
                  "answer and link its file name" % (len(text), MAX_TEXT))
    if args.source == "observed" and args.at:
        raise Bad("an 'observed' entry is stamped now and cannot be backdated; "
                  "use source 'reported' for a time a person gave, or the skill "
                  "name for a time it stated")
    now = now_utc()
    if args.at:
        when, has_sec = parse_at(args.at, now)
    else:
        when, has_sec = now, True
    suffix = ""
    if (now - when).total_seconds() > LATE_SECONDS:
        same_day = when.date() == now.date()
        suffix = "; logged " + now.strftime("%H:%M:%S" if same_day else "%Y-%m-%d %H:%M:%S") + "Z"
    entry = "- %sZ [%s] %s  (source: %s%s)\n" % (fmt(when, has_sec), tag, text,
                                                  args.source, suffix)
    new_key = sort_key(fmt(when, has_sec))

    with Locked(args.log):
        lines = read_lines(args.log)
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        header, blocks, _ = timeline_blocks(lines)
        at_index = None
        for n, block in enumerate(blocks):
            key = block_key(lines, block)
            if key is not None and key <= new_key:
                at_index = n + 1
        if not blocks:
            insert_at, position = header + 1, 1
        elif at_index is None:
            insert_at, position = blocks[0][0], 1
        else:
            insert_at, position = blocks[at_index - 1][1], at_index + 1
        lines.insert(insert_at, entry)
        write_atomic(args.log, lines)
    total = len(blocks) + 1
    print("added entry %d of %d%s" % (position, total,
          "" if position == total else " (inserted before %d later %s by event time)"
          % (total - position, "entry" if total - position == 1 else "entries")))
    print(entry.rstrip())


def cmd_save(args):
    if not SOURCE_RE.match(args.source):
        raise Bad("source must be a skill or tool name (lower-case letters, digits, hyphens)")
    if not os.path.isfile(args.log):
        raise Bad("log not found: %s" % args.log)
    if args.file:
        try:
            with open(args.file, encoding="utf-8") as fh:
                body = fh.read()
        except OSError as exc:
            raise Bad("cannot read %s: %s" % (args.file, exc.strerror))
    else:
        body = sys.stdin.read()
    if not body.strip():
        raise Bad("the answer is empty; nothing saved")
    stem, folder, prefix = answers_location(args.log)
    os.makedirs(folder, exist_ok=True)
    n = 1
    while True:
        name = "%s.md" % args.source if n == 1 else "%s-%d.md" % (args.source, n)
        path = os.path.join(folder, name)
        try:
            fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            break
        except FileExistsError:
            n += 1
    header = ("<!-- Saved by the incident coordinator for incident %s from %s at %sZ. "
              "Verbatim; not edited. -->\n\n" % (stem, args.source, fmt(now_utc(), True)))
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(header + body if body.endswith("\n") else header + body + "\n")
    print("link=%s%s" % (prefix, name))
    print("saved=%s" % path)


def parse_log(lines):
    """Return (state dict, entries) where entries are (lineno, ts, tag, text)."""
    state = {}
    in_state = False
    entries = []
    for i, line in enumerate(lines, 1):
        s = line.rstrip("\n")
        if s.startswith("## "):
            in_state = s.strip() == "## State"
            continue
        if in_state and ":" in s:
            label, _, value = s.partition(":")
            state[label.strip()] = value.strip()
        m = ENTRY_RE.match(s)
        if m:
            entries.append((i, m.group(1), m.group(2), s))
    return state, entries


def synthesis_lines(lines):
    """Lines of the '## Synthesis' section, or None when the log has none."""
    for i, line in enumerate(lines):
        if line.rstrip() == "## Synthesis":
            out = []
            for later in lines[i + 1:]:
                if later.startswith("## "):
                    break
                out.append(later)
            return out
    return None


def entry_sources(entries):
    """The source word of each timeline entry (observed, reported, or a skill)."""
    found = []
    for _, _, _, text in entries:
        m = re.search(r"\(source: ([a-z0-9-]+)", text)
        if m:
            found.append(m.group(1))
    return found


def cmd_check(args):
    lines = read_lines(args.log)
    errors, warns = [], []
    if not any(l.rstrip() == "## State" for l in lines):
        errors.append("no '## State' heading")
    try:
        _, blocks, _ = timeline_blocks(lines)
    except Bad as exc:
        errors.append(str(exc))
        blocks = []
    state, entries = parse_log(lines)
    for field in STATE_FIELDS:
        if field not in state:
            errors.append("state block lacks '%s:'" % field)
        elif len(state[field]) > MAX_STATE_LINE:
            warns.append("state '%s' is %d characters; keep each state field to "
                         "one short line (limit %d)" % (field, len(state[field]), MAX_STATE_LINE))
    synth = synthesis_lines(lines)
    if synth is None:
        if any(src not in ("observed", "reported") for src in entry_sources(entries)):
            warns.append("investigators are logged but there is no '## Synthesis' "
                         "section (the combined evidence table)")
    else:
        text = [l.rstrip("\n") for l in synth]
        for label in SYNTH_LABELS:
            if not any(t.startswith(label + ":") for t in text):
                warns.append("synthesis lacks '%s:'" % label)
        for t in text:
            if len(t) > MAX_SYNTH_LINE:
                warns.append("synthesis line of %d characters; one short line per row "
                             "(limit %d): %s..." % (len(t), MAX_SYNTH_LINE, t[:40]))
    stem, answers, prefix = answers_location(args.log)
    link_re = re.compile(r"(?<![A-Za-z0-9/-])" + re.escape(prefix)
                         + r"([a-z0-9][a-z0-9-]*\.md)(?![A-Za-z0-9])")
    linked = set()
    for _, _, tag, text in entries:
        found = [f for f in link_re.findall(text) if f != stem + ".md"]
        linked.update(found)
        m = re.search(r"\(source: ([a-z0-9-]+)", text)
        if tag == "hypothesis" and m and m.group(1) not in ("observed", "reported") and not found:
            warns.append("a hypothesis from %s has no saved-answer link (%s<source>.md); "
                         "run: save" % (m.group(1), prefix))
    for name in sorted(linked):
        if not os.path.isfile(os.path.join(answers, name)):
            warns.append("the log links %s%s, which does not exist" % (prefix, name))
    status, legacy = status_of(state)
    if "Status" in state and status not in STATUSES:
        errors.append("Status %r is not one of: %s" % (state["Status"], ", ".join(STATUSES)))
    elif legacy:
        warns.append("Status %r is an old status; read as %r. Use open or closed"
                     % (state["Status"], status))
    for block in blocks:
        line = lines[block[0]].rstrip("\n")
        n = block[0] + 1
        m = ENTRY_RE.match(line)
        if not m:
            errors.append("line %d: not a valid entry ('- YYYY-MM-DD HH:MM[:SS]Z [tag] text')" % n)
            continue
        tag = m.group(2)
        if tag in LEGACY_TAGS:
            warns.append("line %d: legacy tag 'detected' (now 'alerted' or 'engaged')" % n)
        elif tag not in TAGS:
            errors.append("line %d: unknown tag %r" % (n, tag))
        if "(source:" not in line:
            warns.append("line %d: no '(source: ...)'" % n)
        if len(line) > MAX_TEXT + 120:
            warns.append("line %d: %d characters; entries are one short line each" % (n, len(line)))
    keys = [(sort_key(ts), ln) for ln, ts, _, _ in entries]
    for prev, cur in zip(keys, keys[1:]):
        if cur[0] < prev[0]:
            warns.append("line %d is earlier than line %d: timeline is not in event-time "
                         "order (run: sort)" % (cur[1], prev[1]))
            break
    for msg in errors:
        print("ERROR: " + msg)
    for msg in warns:
        print("WARN:  " + msg)
    print("%d error(s), %d warning(s), %d timeline entries" % (len(errors), len(warns), len(entries)))
    return 1 if errors else 0


def cmd_sort(args):
    with Locked(args.log):
        lines = read_lines(args.log)
        if lines and not lines[-1].endswith("\n"):
            lines[-1] += "\n"
        header, blocks, _ = timeline_blocks(lines)
        if not blocks:
            print("nothing to sort")
            return
        keyed = []
        last = "0000-00-00 00:00:00"
        for block in blocks:
            key = block_key(lines, block)
            if key is None:
                key = last
            last = key
            keyed.append((key, block))
        ordered = sorted(keyed, key=lambda kb: kb[0])  # stable
        if [b for _, b in ordered] == [b for _, b in keyed]:
            print("already in order")
            return
        first, last_end = blocks[0][0], blocks[-1][1]
        body = []
        for _, (s, e) in ordered:
            body.extend(lines[s:e])
        write_atomic(args.log, lines[:first] + body + lines[last_end:])
        print("sorted %d entries by event time" % len(blocks))


def human(seconds):
    seconds = int(seconds)
    if seconds < 60:
        return "%d s" % seconds
    if seconds < 3600:
        m, s = divmod(seconds, 60)
        return "%d min" % m if not s else "%d min %d s" % (m, s)
    h, rest = divmod(seconds, 3600)
    return "%d h %d min" % (h, rest // 60)


def cmd_durations(args):
    _, entries = parse_log(read_lines(args.log))
    first, last = {}, {}
    legacy = 0
    for _, ts, tag, _ in entries:
        if tag in LEGACY_TAGS:
            legacy += 1
        first.setdefault(tag, ts)
        last[tag] = ts

    def span(label, start_tag, end_tag, use_last=False):
        a = first.get(start_tag)
        b = (last if use_last else first).get(end_tag)
        what = "%s -> %s" % (start_tag, end_tag)
        if not a or not b:
            missing = start_tag if not a else end_tag
            note = ""
            if missing == "alerted" and legacy:
                note = "; the log has %d legacy 'detected' entries, decide which one " \
                       "was the alert and say so in Needs review" % legacy
            print("%-9s not recorded (%s: no '%s' entry%s)" % (label, what, missing, note))
            return
        delta = (to_dt(b) - to_dt(a)).total_seconds()
        if delta < 0:
            print("%-9s not computable (%s: end %sZ is before start %sZ)" % (label, what, b, a))
            return
        print("%-9s %s (%s: %sZ -> %sZ)" % (label, human(delta), what, a, b))

    span("detect", "impact-start", "alerted")
    span("engage", "alerted", "engaged")
    span("mitigate", "impact-start", "mitigated")
    span("resolve", "impact-start", "resolved", use_last=True)


def find_logs(log_dir):
    """Yield the path of every incident log under log_dir, oldest id first."""
    try:
        names = sorted(os.listdir(log_dir))
    except OSError as exc:
        raise Bad("cannot read %s: %s" % (log_dir, exc.strerror))
    for name in names:
        if name.startswith("."):
            continue
        full = os.path.join(log_dir, name)
        if os.path.isdir(full):
            full = os.path.join(full, name + ".md")
        elif not name.endswith(".md"):
            continue
        if os.path.isfile(full):
            yield full


def cmd_list(args):
    shown = 0
    if args.thread_ts:
        check_ts(args.thread_ts, "--thread-ts")
    for path in find_logs(args.log_dir):
        if args.thread_ts:
            try:
                with open(watch_paths(path)[0], encoding="utf-8") as fh:
                    if json.load(fh).get("thread_ts") != args.thread_ts:
                        continue
            except (OSError, ValueError):
                continue
        state, _ = parse_log(read_lines(path))
        status, _ = status_of(state)
        status = status or "unknown"
        if args.active and status == "closed":
            continue
        print("%s  %-10s %s  next update: %s  %s" % (
            os.path.splitext(os.path.basename(path))[0], status,
            state.get("Severity", "unknown").split(" (")[0],
            state.get("Next update due", "unknown"), path))
        shown += 1
    if not shown:
        print("no incidents" + (" in progress" if args.active else "")
              + (" for thread " + args.thread_ts if args.thread_ts else "") + " in " + args.log_dir)


def watch_paths(log):
    stem, folder, _ = answers_location(log)
    return os.path.join(folder, "watch.json"), os.path.join(folder, "watch-canvas.md")


def load_watch(path):
    try:
        with open(path, encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        raise Bad("no watch for this incident (%s); run: watch <log> init" % path)
    except (OSError, ValueError) as exc:
        raise Bad("cannot read %s: %s" % (path, exc))


def save_watch(path, data):
    fd, tmp = tempfile.mkstemp(dir=os.path.dirname(path), prefix=".tmp-watch-")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=2, sort_keys=True)
        fh.write("\n")
    os.replace(tmp, path)


TS_RE = re.compile(r"^\d{10}\.\d{6}$")


def check_ts(value, what):
    if not TS_RE.match(value):
        raise Bad("%s %r is not a Slack ts (like 1791394574.025299)" % (what, value))
    return value


def cmd_watch(args):
    if not os.path.isfile(args.log):
        raise Bad("log not found: %s" % args.log)
    path, canvas_path = watch_paths(args.log)
    if args.action == "init":
        if not args.channel or not args.thread_ts:
            raise Bad("init needs --channel and --thread-ts")
        if os.path.isfile(path) and load_watch(path).get("active"):
            raise Bad("a watch is already active for this incident; use update or stop")
        data = {"active": True, "channel": args.channel,
                "thread_ts": check_ts(args.thread_ts, "--thread-ts"),
                "canvas_id": args.canvas or "",
                "last_seen_ts": args.thread_ts, "own_ts": [args.thread_ts],
                "cron_id": args.cron_id or "",
                "owner": args.owner == "yes",
                "started": now_utc().strftime("%Y-%m-%d %H:%MZ")}
        save_watch(path, data)
        print("watch=%s" % path)
        return 0
    data = load_watch(path)
    if args.action == "show":
        out = dict(data)
        pending = data.get("pending")
        if pending:
            since = dt.datetime.strptime(pending["since"], "%Y-%m-%d %H:%MZ")
            out["pending_minutes"] = max(0, int((now_utc() - since).total_seconds() // 60))
        print(json.dumps(out, indent=2, sort_keys=True))
        return 0
    if args.action == "stop":
        data["active"] = False
        data["stopped"] = now_utc().strftime("%Y-%m-%d %H:%MZ")
        save_watch(path, data)
        print("stopped")
        return 0
    if args.action != "update":
        raise Bad("action must be init, show, update or stop")
    if args.last_seen:
        data["last_seen_ts"] = check_ts(args.last_seen, "--last-seen")
    if args.cron_id is not None:
        data["cron_id"] = args.cron_id
    if args.owner:
        data["owner"] = args.owner == "yes"
    for ts in args.own or []:
        if check_ts(ts, "--own") not in data["own_ts"]:
            data["own_ts"].append(ts)
    if args.pending and args.clear_pending:
        raise Bad("use --pending or --clear-pending, not both")
    if args.pending and not data.get("pending"):
        data["pending"] = {"since": now_utc().strftime("%Y-%m-%d %H:%MZ"), "notified": False}
    if args.clear_pending:
        data.pop("pending", None)
    if args.analysis_start and args.clear_analysis_start:
        raise Bad("use --analysis-start or --clear-analysis-start, not both")
    if args.analysis_start:
        data["analysis_started_ts"] = "%d.000000" % calendar.timegm(now_utc().timetuple())
    if args.clear_analysis_start:
        data.pop("analysis_started_ts", None)
    if args.notified:
        if not data.get("pending"):
            raise Bad("--notified needs a pending analysis (use --pending first)")
        data["pending"]["notified"] = True
    if args.canvas_file:
        try:
            with open(args.canvas_file, encoding="utf-8") as src, \
                    open(canvas_path, "w", encoding="utf-8") as dst:
                dst.write(src.read())
        except OSError as exc:
            raise Bad("cannot copy the canvas text: %s" % exc.strerror)
    save_watch(path, data)
    print("updated")
    return 0


def cmd_now(args):
    when = now_utc() + dt.timedelta(minutes=args.plus)
    print(when.strftime("%Y-%m-%d %H:%M") + "Z")


def main(argv):
    p = argparse.ArgumentParser(description="Incident log helper (UTC).")
    sub = p.add_subparsers(dest="cmd", required=True)
    o = sub.add_parser("open")
    o.add_argument("log_dir")
    o.add_argument("slug")
    o.add_argument("--title")
    o.set_defaults(fn=cmd_open)
    a = sub.add_parser("add")
    a.add_argument("log")
    a.add_argument("tag")
    a.add_argument("source")
    a.add_argument("text")
    a.add_argument("--at")
    a.set_defaults(fn=cmd_add)
    sv = sub.add_parser("save")
    sv.add_argument("log")
    sv.add_argument("source")
    sv.add_argument("--file")
    sv.set_defaults(fn=cmd_save)
    n = sub.add_parser("now")
    n.add_argument("--plus", type=int, default=0, metavar="MINUTES")
    n.set_defaults(fn=cmd_now)
    w = sub.add_parser("watch")
    w.add_argument("log")
    w.add_argument("action", choices=("init", "show", "update", "stop"))
    w.add_argument("--channel")
    w.add_argument("--thread-ts")
    w.add_argument("--canvas")
    w.add_argument("--cron-id")
    w.add_argument("--owner", choices=("yes", "no"),
                   help="yes when the coordinator posted the incident post, no when adopted")
    w.add_argument("--last-seen")
    w.add_argument("--own", action="append")
    w.add_argument("--canvas-file")
    w.add_argument("--pending", action="store_true")
    w.add_argument("--clear-pending", action="store_true")
    w.add_argument("--notified", action="store_true")
    w.add_argument("--analysis-start", action="store_true")
    w.add_argument("--clear-analysis-start", action="store_true")
    w.set_defaults(fn=cmd_watch)
    li = sub.add_parser("list")
    li.add_argument("log_dir")
    li.add_argument("--active", action="store_true")
    li.add_argument("--thread-ts", help="only the incident whose watch follows this thread")
    li.set_defaults(fn=cmd_list)
    for name, fn in (("check", cmd_check), ("sort", cmd_sort), ("durations", cmd_durations)):
        s = sub.add_parser(name)
        s.add_argument("log")
        s.set_defaults(fn=fn)
    args = p.parse_args(argv)
    try:
        return args.fn(args) or 0
    except Bad as exc:
        sys.stderr.write("ERROR: %s\n" % exc)
        return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
