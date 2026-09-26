"""Test: all four boxes get counted, and a rate nobody should trust is refused.

What should be true (Layer 8): counting only the wins is how a system learns a
superstition. The box that decides whether a signal means anything is the one
nobody fills in: the people who had the signal and where nothing happened.

And an arm that totals zero is not a comparison. Neither is an arm with three
people in it. Where the honest answer is "not enough to say", that is what comes
back, rather than a percentage that will be quoted without its caveat.

Run:  python tests/test_fourbox.py
"""

import json
import shutil
import sys
import tempfile
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))

import crm_paths
import fourbox

FAILS = []


def check(label, cond, detail=""):
    ok = bool(cond)
    print(("  PASS  " if ok else "  FAIL  ") + label
          + (("   [" + detail + "]") if detail and not ok else ""))
    if not ok:
        FAILS.append(label)


VAULT = Path(tempfile.mkdtemp(prefix="crm-layer8-fourbox-"))
crm_paths.use_vault(VAULT)
LEDGER = VAULT / "_ledger" / "events.jsonl"
LEDGER.parent.mkdir(parents=True)


def ago(days):
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")


def emit(type_, person, days_ago):
    with open(LEDGER, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps({"ts": ago(days_ago), "type": type_,
                             "person": person, "source": "test"}) + "\n")


print("\n=== 1. all four boxes are counted, not just the winners ===")

# 12 replied and booked, 20 replied and did not, 3 booked without replying,
# 40 did neither. Only the first number is the one people quote.
for i in range(12):
    emit("reply_in", "replied-and-booked-%02d" % i, 40)
    emit("meeting_booked", "replied-and-booked-%02d" % i, 38)
for i in range(20):
    emit("reply_in", "replied-only-%02d" % i, 40)
for i in range(3):
    emit("meeting_booked", "booked-only-%02d" % i, 38)
for i in range(40):
    emit("connected", "neither-%02d" % i, 40)

box = fourbox.count("reply_in", "meeting_booked", ledger_path=LEDGER)
check("the winners box", box["signal_and_outcome"] == 12, str(box))
check("the box nobody counts", box["signal_and_no_outcome"] == 20, str(box))
check("the box that says the signal is not necessary",
      box["no_signal_but_outcome"] == 3, str(box))
check("the population you forgot about", box["neither"] == 40, str(box))
check("the four boxes add up to everybody",
      (box["signal_and_outcome"] + box["signal_and_no_outcome"]
       + box["no_signal_but_outcome"] + box["neither"]) == box["population"],
      str(box))

print("\n=== 2. both rates are produced, and they differ ===")

rate = fourbox.rates(box)
check("the rate with the signal is 12 of 32",
      abs(rate["with_signal"] - 37.5) < 0.01, str(rate["with_signal"]))
check("the rate without it is 3 of 43",
      abs(rate["without_signal"] - 6.98) < 0.05, str(rate["without_signal"]))
check("the difference is reported", rate["difference"] > 0, str(rate["difference"]))
check("and it is described in words", "higher rate" in rate["verdict"], rate["verdict"])

print("\n=== 3. counting only the winners would have said something else ===")

winners_only = 100.0 * box["signal_and_outcome"] / max(
    box["signal_and_outcome"] + box["no_signal_but_outcome"], 1)
check("looking only at people who booked, 80% of them had replied",
      abs(winners_only - 80.0) < 0.01, str(winners_only))
check("but the actual rate for people who replied is far lower",
      rate["with_signal"] < winners_only / 2,
      "%.1f vs %.1f" % (rate["with_signal"], winners_only))

print("\n=== 4. an arm with nobody in it is refused, not reported as zero ===")

empty = VAULT / "_ledger" / "empty.jsonl"
with open(empty, "w", encoding="utf-8", newline="\n") as fh:
    for i in range(30):
        fh.write(json.dumps({"ts": ago(5), "type": "reply_in",
                             "person": "everyone-%02d" % i}) + "\n")

box2 = fourbox.count("reply_in", "meeting_booked", ledger_path=empty)
rate2 = fourbox.rates(box2)
check("everybody had the signal", box2["without_signal"] == 0, str(box2))
check("no rate is produced for the missing arm", rate2["without_signal"] is None)
check("and the reason says there is nothing to compare against",
      "comparison group" in rate2["without_signal_note"], rate2["without_signal_note"])
check("no difference is claimed", rate2["difference"] is None)
check("the verdict is an honest refusal",
      "not enough to say" in rate2["verdict"], rate2["verdict"])

print("\n=== 5. a handful of people is not a rate ===")

tiny = VAULT / "_ledger" / "tiny.jsonl"
with open(tiny, "w", encoding="utf-8", newline="\n") as fh:
    for i in range(3):
        fh.write(json.dumps({"ts": ago(5), "type": "reply_in", "person": "a%d" % i}) + "\n")
        fh.write(json.dumps({"ts": ago(4), "type": "meeting_booked", "person": "a%d" % i}) + "\n")
    for i in range(3):
        fh.write(json.dumps({"ts": ago(5), "type": "connected", "person": "b%d" % i}) + "\n")

box3 = fourbox.count("reply_in", "meeting_booked", ledger_path=tiny)
rate3 = fourbox.rates(box3)
check("three out of three does not become 100 per cent",
      rate3["with_signal"] is None, str(rate3["with_signal"]))
check("and the refusal says why in words",
      "noise" in rate3["with_signal_note"], rate3["with_signal_note"])
check("the other arm is refused too", rate3["without_signal"] is None)

print("\n=== 6. an outcome that happened first does not count ===")

order = VAULT / "_ledger" / "order.jsonl"
with open(order, "w", encoding="utf-8", newline="\n") as fh:
    for i in range(15):
        # booked LONG before they ever replied
        fh.write(json.dumps({"ts": ago(90), "type": "meeting_booked",
                             "person": "backwards-%02d" % i}) + "\n")
        fh.write(json.dumps({"ts": ago(2), "type": "reply_in",
                             "person": "backwards-%02d" % i}) + "\n")
    for i in range(15):
        fh.write(json.dumps({"ts": ago(2), "type": "connected",
                             "person": "control-%02d" % i}) + "\n")

loose = fourbox.count("reply_in", "meeting_booked", ledger_path=order)
strict = fourbox.count("reply_in", "meeting_booked", within_days=30, ledger_path=order)
check("counted loosely, the signal looks perfect",
      loose["signal_and_outcome"] == 15, str(loose))
check("counted with a window, none of them count",
      strict["signal_and_outcome"] == 0, str(strict))
check("they move into the box nobody counts",
      strict["signal_and_no_outcome"] == 15, str(strict))

print("\n=== 7. the report says what it is and what it is not ===")

text = fourbox.render(box)
check("it shows all four numbers",
      all(str(n) in text for n in (12, 20, 3, 40)), text)
check("it names both the signal and the outcome",
      "reply_in" in text and "meeting_booked" in text)
check("it says the population it counted over", "75" in text, text)
check("it says counting is not explaining",
      "does not explain" in text, text)
check("it warns that a third thing could be moving both",
      "third thing" in text, text)

check("the window is stated when one is used",
      "within 30 days" in fourbox.render(strict))
check("and when one is not", "at any time" in text)

print("\n=== 8. a damaged log does not take the count with it ===")

with open(LEDGER, "a", encoding="utf-8") as fh:
    fh.write("not json\n")
    fh.write('{"ts": "%s", "type": "reply_in"}\n' % ago(1))
after = fourbox.count("reply_in", "meeting_booked", ledger_path=LEDGER)
check("the counts are unchanged by an unreadable line",
      after["population"] == box["population"], "%d vs %d" % (after["population"],
                                                              box["population"]))
check("an event naming nobody is not counted as a person",
      after["population"] == 75, str(after["population"]))

shutil.rmtree(VAULT, ignore_errors=True)

print("\n%s" % ("ALL PASS" if not FAILS else "FAILURES: " + ", ".join(FAILS)))
sys.exit(1 if FAILS else 0)
