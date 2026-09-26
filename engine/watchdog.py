"""
watchdog.py - checks what should be true against what is, and says so.

An automated system fails silently by default. Every run exits cleanly whether it
produced everything or nothing, because "produced nothing" is not an error: it is
a successful run of a thing that found nothing to do. A run of those in a row
looks, from every log and every exit code, exactly like a system working
perfectly.

One person working alone has no colleague to lean over and say "that looks
wrong". So the system has to say it itself.

WHAT IT READS. The expectations file, `_schema/expectations.json`. You own that
file. This module reads it and never writes to it, because a system that can
relax its own expectations has none. Weakening a check is a decision, made
deliberately, by a person.

WHAT IT DOES NOT DO. It does not repair anything. A watchdog that fixes what it
finds stops being a measurement and becomes another writer nobody is watching,
and then you have two systems that can be wrong and only one of them is being
checked. Diagnosis and repair belong to you.

A NOTE ON WRITING CHECKS. A check that is green the day you write it is checking
something that was never going to break. Write checks against things you have
actually seen go wrong, or things whose failure you would not notice.

Use:
    python watchdog.py              run every check
    python watchdog.py --quiet      only failures, for an unattended run
    python watchdog.py --json       machine readable
Exit code is the number of failing checks.

Needs: Python 3.8 or newer. Nothing else.
"""

import json
import re
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import crm_paths


def expectations_path():
    return crm_paths.schema_dir() / "expectations.json"


def _result(cid, ok, detail, severity, skipped=False):
    return {"id": cid, "ok": bool(ok), "detail": detail,
            "severity": severity, "skipped": bool(skipped)}


def _front_matter(text):
    lines = text.splitlines()
    if not lines or lines[0].strip() != "---":
        return {}
    out = {}
    for line in lines[1:]:
        if line.strip() == "---":
            break
        if ":" not in line:
            continue
        field, _, value = line.partition(":")
        out[field.strip().lower()] = value.strip().strip('"\'')
    return out


def _events():
    path = crm_paths.ledger_path()
    if not path.exists():
        return []
    out = []
    with open(path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except ValueError:
                continue
            if isinstance(event, dict):
                out.append(event)
    return out


# --------------------------------------------------------------------- checks
#
# Each takes the whole expectation, so an expectation can carry its own numbers
# rather than having them buried in the code where you cannot change them.

def check_every_record_has_an_identifier(spec):
    field = crm_paths.config().get("identifier", "linkedin-url")
    folder = crm_paths.people_dir()
    if not folder.exists():
        return _result(spec["id"], True, "no people folder yet", spec["severity"], True)
    missing, total = [], 0
    for note in sorted(folder.glob("*.md")):
        total += 1
        front = _front_matter(note.read_text(encoding="utf-8", errors="replace")[:2000])
        if not front.get(field):
            missing.append(note.stem)
    if not total:
        return _result(spec["id"], True, "no records yet", spec["severity"], True)
    return _result(spec["id"], not missing,
                   "%d of %d records carry no %s%s"
                   % (len(missing), total, field,
                      (": " + ", ".join(missing[:3])) if missing else ""),
                   spec["severity"])


def check_one_record_per_person(spec):
    field = crm_paths.config().get("identifier", "linkedin-url")
    folder = crm_paths.people_dir()
    if not folder.exists():
        return _result(spec["id"], True, "no people folder yet", spec["severity"], True)
    seen, clashes = {}, []
    for note in sorted(folder.glob("*.md")):
        front = _front_matter(note.read_text(encoding="utf-8", errors="replace")[:2000])
        value = (front.get(field) or "").strip().rstrip("/").lower()
        if not value:
            continue
        if value in seen:
            clashes.append("%s and %s" % (seen[value], note.stem))
        else:
            seen[value] = note.stem
    return _result(spec["id"], not clashes,
                   "%d pair(s) of records share one identifier%s"
                   % (len(clashes), (": " + "; ".join(clashes[:3])) if clashes else ""),
                   spec["severity"])


def check_events_name_a_person(spec):
    events = _events()
    if not events:
        return _result(spec["id"], True, "the event log is empty", spec["severity"], True)
    floor = float(spec.get("at_least_percent", 80))
    named = sum(1 for e in events if e.get("person"))
    rate = 100.0 * named / len(events)
    return _result(spec["id"], rate >= floor,
                   "%.0f%% of %d events name somebody (you asked for %.0f%%)"
                   % (rate, len(events), floor),
                   spec["severity"])


def check_the_log_is_still_growing(spec):
    """Silence is not health.

    This is the check that catches the failure everything else misses: a system
    that runs, exits cleanly, and does nothing. Nothing else in this file would
    notice, because every other check would be perfectly happy with a system
    that had stopped.
    """
    quiet_days = float(spec.get("quiet_days", 7))
    events = _events()
    if not events:
        return _result(spec["id"], False,
                       "the event log is empty. Either nothing has been captured "
                       "yet, or capture has stopped and nothing said so.",
                       spec["severity"])
    newest = None
    for event in events:
        try:
            t = datetime.fromisoformat(str(event.get("ts", "")).replace("Z", "+00:00"))
        except (ValueError, TypeError):
            continue
        if not t.tzinfo:
            t = t.replace(tzinfo=timezone.utc)
        if newest is None or t > newest:
            newest = t
    if newest is None:
        return _result(spec["id"], False, "no event carries a readable date",
                       spec["severity"])
    quiet = (datetime.now(timezone.utc) - newest).total_seconds() / 86400.0
    return _result(spec["id"], quiet <= quiet_days,
                   "the newest event is %.1f days old (you said %.0f is too long)"
                   % (quiet, quiet_days),
                   spec["severity"])


def check_held_people_are_not_on_the_page(spec):
    page = crm_paths.today_page()
    if not page.exists():
        return _result(spec["id"], True, "no page has been built yet",
                       spec["severity"], True)
    try:
        sys.path.insert(0, str(crm_paths.vault() / "_engine"))
        import holds
    except Exception:
        return _result(spec["id"], True,
                       "no hold list is installed, so nobody can be held",
                       spec["severity"], True)
    on_page = []
    for line in page.read_text(encoding="utf-8", errors="replace").splitlines():
        if not line.startswith("|") or re.match(r"^\|[\s:\-|]+\|$", line):
            continue
        cells = [c.strip() for c in line.strip("|").split("|")]
        if len(cells) >= 2 and cells[0].isdigit():
            on_page.append(cells[1])
    breaches = [n for n in on_page if holds.is_held_person(n)]
    return _result(spec["id"], not breaches,
                   "%d of %d people on the page are held%s"
                   % (len(breaches), len(on_page),
                      (": " + ", ".join(breaches[:3])) if breaches else ""),
                   spec["severity"])


def check_holds_carry_an_identifier(spec):
    try:
        sys.path.insert(0, str(crm_paths.vault() / "_engine"))
        import holds
    except Exception:
        return _result(spec["id"], True, "no hold list is installed",
                       spec["severity"], True)
    rows = holds.held()
    if not rows:
        return _result(spec["id"], True, "nobody is held", spec["severity"], True)
    blind = []
    for entry in rows:
        candidates = [entry.get("person", "")] + list(entry.get("aliases") or [])
        if not any("/" in str(c) or "@" in str(c) for c in candidates):
            blind.append(entry.get("person", "?"))
    return _result(spec["id"], not blind,
                   "%d of %d holds are recorded under a name with no identifier%s"
                   % (len(blind), len(rows),
                      (": " + ", ".join(blind[:3])) if blind else ""),
                   spec["severity"])


def check_nothing_writes_unsafely(spec):
    """Flags any code in your CRM that could empty a file it meant to update.

    Opening a file for writing empties it immediately. A write that only happens
    when the file is absent cannot destroy anything, so it is not reported:
    a watchdog that flags safe code is one you learn to ignore, and an ignored
    watchdog is the same as no watchdog.
    """
    folder = crm_paths.vault() / "_engine"
    if not folder.exists():
        return _result(spec["id"], True, "no engine folder", spec["severity"], True)
    bad = []
    for f in sorted(folder.glob("*.py")):
        if f.name in ("safe_write.py", "watchdog.py"):
            continue
        for i, line in enumerate(f.read_text(encoding="utf-8", errors="replace").splitlines(), 1):
            s = line.strip()
            if s.startswith("#") or "open(" not in s:
                continue
            if not any(mode in s for mode in ('"w"', "'w'", '"w+"', "'w+'")):
                continue
            if "fdopen(" in s:
                # A file descriptor, not a path. It came from a create-if-absent
                # call that already refused to touch an existing file, so it
                # cannot truncate one. Reporting it would be a watchdog crying
                # wolf, and an ignored watchdog is the same as no watchdog.
                continue
            target = s.split("open(")[1].split(",")[0].strip().lower()
            if any(word in target for word in ("tmp", "temp")):
                continue                     # writing beside the file, then swapping
            bad.append("%s line %d" % (f.name, i))
    return _result(spec["id"], not bad,
                   "%d place(s) write straight over a file%s"
                   % (len(bad), (": " + ", ".join(bad[:4])) if bad else ""),
                   spec["severity"])


CHECKS = {
    "every-record-has-an-identifier": check_every_record_has_an_identifier,
    "one-record-per-person": check_one_record_per_person,
    "events-name-a-person": check_events_name_a_person,
    "the-log-is-still-growing": check_the_log_is_still_growing,
    "held-people-are-not-on-the-page": check_held_people_are_not_on_the_page,
    "holds-carry-an-identifier": check_holds_carry_an_identifier,
    "nothing-writes-unsafely": check_nothing_writes_unsafely,
}


def load_expectations(path=None):
    path = Path(path) if path else expectations_path()
    return json.loads(path.read_text(encoding="utf-8"))


def run(path=None):
    spec = load_expectations(path)
    out = []
    for entry in spec.get("checks", []):
        fn = CHECKS.get(entry.get("id"))
        if not fn:
            out.append(_result(
                entry.get("id", "(unnamed)"), True,
                "you wrote this expectation and nothing checks it yet. Either "
                "write the check or take the line out; an expectation nobody "
                "tests is a note to yourself.",
                entry.get("severity", "medium"), skipped=True))
        else:
            try:
                result = fn(entry)
            except Exception as err:
                result = _result(entry["id"], False, "the check itself broke: %s" % err,
                                 entry.get("severity", "medium"))
            out.append(result)
        out[-1]["expect"] = entry.get("expect", "")
    return out


def render(results, quiet=False):
    order = {"critical": 0, "high": 1, "medium": 2, "low": 3}
    rows = sorted(results, key=lambda r: (r["ok"], order.get(r["severity"], 9)))
    lines = []
    for r in rows:
        if quiet and (r["ok"] or r["skipped"]):
            continue
        mark = "SKIP" if r["skipped"] else ("ok  " if r["ok"] else "FAIL")
        lines.append("%s  [%-8s] %-34s %s"
                     % (mark, r["severity"], r["id"], r["detail"]))
    failing = [r for r in results if not r["ok"] and not r["skipped"]]
    if not quiet:
        lines.append("")
        lines.append("%d failing, %d passing, %d not checked."
                     % (len(failing),
                        sum(1 for r in results if r["ok"] and not r["skipped"]),
                        sum(1 for r in results if r["skipped"])))
        if failing:
            lines.append("")
            lines.append("This reports. It does not repair. Each failure above needs")
            lines.append("a cause you can name before anything is changed, because a")
            lines.append("change made without one is a guess that will look like a fix.")
    return "\n".join(lines)


def main(argv):
    try:
        results = run()
    except FileNotFoundError:
        print("No expectations file at %s." % expectations_path())
        print("That file is yours to write. Install Layer 8 to get a starting one.")
        return 2
    if "--json" in argv:
        failing = [r for r in results if not r["ok"] and not r["skipped"]]
        print(json.dumps({"failing": len(failing), "results": results}, indent=2))
        return len(failing)
    print(render(results, quiet="--quiet" in argv))
    return len([r for r in results if not r["ok"] and not r["skipped"]])


if __name__ == "__main__":
    sys.exit(main(sys.argv))
