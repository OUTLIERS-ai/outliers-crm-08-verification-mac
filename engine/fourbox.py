"""
fourbox.py - count all four combinations, or do not claim to have learned
anything.

The question this answers: does a signal actually predict an outcome, in YOUR
system, on YOUR people.

The wrong way to answer it, and the way almost everybody does, is to look at the
people who bought and notice what they had in common. Everyone who bought had
replied to a message, so replies cause sales. That reasoning has a hole in it the
size of the whole business: you never looked at the people who replied and did
not buy.

There are four boxes, and you need all four:

                        bought        did not buy
    replied               a                b
    did not reply         c                d

Only a is easy to get. b is the one nobody counts and the one that decides
whether the signal means anything. c is the box that tells you whether the signal
is even necessary. d is the population you forgot you had.

From all four you get two rates that can be compared:

    with the signal     a / (a + b)
    without it          c / (c + d)

And the honest refusals, which matter more than the numbers:

- If b is zero AND a is small, you have not observed enough to say anything.
- If either arm has no people in it at all, there is nothing to compare. An arm
  that totals zero is not a result, it is an absence.
- A rate from a handful of people is not a rate. It is arithmetic performed on
  noise, and putting a percentage sign after it makes it look like evidence.

This module counts. It does not decide, it does not recommend, and where it
cannot honestly answer it says so instead of producing a number.

    python _engine/fourbox.py reply_in meeting_booked
    python _engine/fourbox.py reply_in meeting_booked --within 30 --write

Needs: Python 3.8 or newer. Nothing else.
"""

import json
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import crm_paths

# The command a member types to start Python: `python3` on a Mac, which has no plain
# `python` command, and `python` everywhere else, as the Windows guides print it.
PY = "python3" if sys.platform == "darwin" else "python"


def _typed(name):
    """The program `name` (it sits beside this file) as the member types it from the folder
    they are in: `_engine/<name>` from the CRM folder, `<name>` from inside `_engine`."""
    import os
    path = os.path.join(os.path.dirname(os.path.abspath(__file__)), name)
    try:
        typed = os.path.relpath(path)
    except ValueError:                      # the member is on another drive
        typed = path
    if typed.startswith(".."):
        typed = path
    typed = typed.replace("\\", "/")
    return '"%s"' % typed if " " in typed else typed

# Below this many people in an arm, a percentage is misleading rather than
# informative. Not a statistical test: a blunt floor, chosen so that a rate
# built from three people never appears on a page next to one built from three
# hundred looking equally solid.
TOO_FEW = 10


def read_events(ledger_path=None):
    """Every event, oldest first. A malformed line is skipped, never fatal."""
    path = Path(ledger_path) if ledger_path else crm_paths.ledger_path()
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
            if isinstance(event, dict) and event.get("person"):
                out.append(event)
    return out


def _when(ts):
    try:
        t = datetime.fromisoformat(str(ts).replace("Z", "+00:00"))
    except (ValueError, TypeError):
        return None
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


def count(signal, outcome, within_days=None, ledger_path=None, events=None):
    """Fill in all four boxes. Returns the counts and what can honestly be said.

    `within_days`, if given, only counts an outcome that happened AFTER the
    signal and within that many days of it. Without it, any outcome at any time
    counts, which quietly lets an outcome that happened first be treated as
    though the signal caused it.
    """
    events = events if events is not None else read_events(ledger_path)

    people = set()
    signal_at = {}
    outcome_at = {}
    for event in events:
        person = event.get("person")
        people.add(person)
        when = _when(event.get("ts"))
        if event.get("type") == signal:
            if person not in signal_at or (when and signal_at[person] and when < signal_at[person]):
                signal_at[person] = when
        if event.get("type") == outcome:
            if person not in outcome_at or (when and outcome_at[person] and when < outcome_at[person]):
                outcome_at[person] = when

    a = b = c = d = 0
    for person in people:
        has_signal = person in signal_at
        has_outcome = person in outcome_at
        if has_outcome and has_signal and within_days is not None:
            s, o = signal_at[person], outcome_at[person]
            if s is None or o is None or o < s or (o - s) > timedelta(days=within_days):
                has_outcome = False
        if has_signal and has_outcome:
            a += 1
        elif has_signal and not has_outcome:
            b += 1
        elif not has_signal and has_outcome:
            c += 1
        else:
            d += 1

    return {
        "signal": signal,
        "outcome": outcome,
        "within_days": within_days,
        "population": len(people),
        "signal_and_outcome": a,
        "signal_and_no_outcome": b,
        "no_signal_but_outcome": c,
        "neither": d,
        "with_signal": a + b,
        "without_signal": c + d,
    }


def rates(box):
    """The two rates, or an honest refusal for each.

    A rate is only returned when there are enough people in that arm to make one
    mean anything. Otherwise the reason is returned instead, in words, because a
    number with a caveat next to it gets quoted without the caveat.
    """
    out = {}
    with_n, without_n = box["with_signal"], box["without_signal"]

    if with_n == 0:
        out["with_signal"] = None
        out["with_signal_note"] = ("nobody at all had this signal, so there is "
                                   "nothing to measure. An arm that totals zero "
                                   "is not a comparison.")
    elif with_n < TOO_FEW:
        out["with_signal"] = None
        out["with_signal_note"] = ("only %d %s had this signal. A rate built "
                                   "from that many is arithmetic on noise."
                                   % (with_n, "person" if with_n == 1 else "people"))
    else:
        out["with_signal"] = 100.0 * box["signal_and_outcome"] / with_n
        out["with_signal_note"] = "%d of %d" % (box["signal_and_outcome"], with_n)

    if without_n == 0:
        out["without_signal"] = None
        out["without_signal_note"] = ("everybody had this signal, so there is no "
                                      "comparison group. This is the most common "
                                      "way a system convinces itself of something.")
    elif without_n < TOO_FEW:
        out["without_signal"] = None
        out["without_signal_note"] = ("only %d %s lacked this signal, which is "
                                      "too few to compare against."
                                      % (without_n, "person" if without_n == 1 else "people"))
    else:
        out["without_signal"] = 100.0 * box["no_signal_but_outcome"] / without_n
        out["without_signal_note"] = "%d of %d" % (box["no_signal_but_outcome"], without_n)

    if out["with_signal"] is not None and out["without_signal"] is not None:
        out["difference"] = out["with_signal"] - out["without_signal"]
        out["verdict"] = ("the signal goes with a higher rate"
                          if out["difference"] > 0 else
                          "the signal goes with a lower rate"
                          if out["difference"] < 0 else
                          "no difference either way")
    else:
        out["difference"] = None
        out["verdict"] = ("not enough to say. That is a complete answer, and a "
                          "better one than a number nobody should trust.")
    return out


def render(box, rate=None):
    rate = rate or rates(box)
    window = ("within %d days of it" % box["within_days"]) if box["within_days"] \
        else "at any time"
    lines = [
        "Does %r go with %r?" % (box["signal"], box["outcome"]),
        "Counted over %d people, outcome counted %s." % (box["population"], window),
        "",
        "                        %-14s %-14s" % (box["outcome"], "no " + box["outcome"]),
        "  had the signal        %-14d %-14d" % (box["signal_and_outcome"],
                                                 box["signal_and_no_outcome"]),
        "  did not               %-14d %-14d" % (box["no_signal_but_outcome"],
                                                 box["neither"]),
        "",
    ]
    for arm, label in (("with_signal", "with the signal   "),
                       ("without_signal", "without it        ")):
        value = rate.get(arm)
        note = rate.get(arm + "_note", "")
        if value is None:
            lines.append("  %s  no rate    (%s)" % (label, note))
        else:
            lines.append("  %s  %5.1f%%    (%s)" % (label, value, note))
    lines += ["", "  " + rate["verdict"]]
    lines += ["",
              "This counts. It does not explain. A difference here says the two",
              "things travel together, and says nothing at all about which one",
              "moved the other, or whether a third thing moved both."]
    return "\n".join(lines)


def main(argv):
    args = [a for a in argv[1:] if not a.startswith("--")]
    if len(args) < 2:
        print(__doc__.replace("    python _engine/fourbox.py", "    python " + _typed("fourbox.py"))
              .replace("    python ", "    %s " % PY))
        return 2
    within = None
    if "--within" in argv:
        try:
            within = int(argv[argv.index("--within") + 1])
        except (IndexError, ValueError):
            print("--within needs a number of days after it")
            return 2
    box = count(args[0], args[1], within_days=within)
    rate = rates(box)
    text = render(box, rate)
    print(text)
    if "--write" in argv:
        import safe_write
        target = crm_paths.reports_dir() / ("does-%s-go-with-%s.md" % (args[0], args[1]))
        safe_write.write_text(target, "# Four boxes\n\n```\n" + text + "\n```\n")
        print("")
        print("written: %s" % target)
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
