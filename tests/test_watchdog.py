"""Test: the checks go red on real faults, and the watchdog never repairs.

What should be true (Layer 8):

- Every check that goes red does so because something is actually wrong, and the
  message says what, in words a person can act on.
- Silence is caught. A system producing nothing exits as cleanly as one producing
  everything, so the only thing that notices is a check looking for growth.
- The watchdog reads the expectations file and cannot write to it. A system that
  can relax its own expectations has none.
- A check that breaks is reported as failing, never quietly skipped. A broken
  check that passes is worse than no check, because it produces confidence.
- An expectation you declared and nobody implemented is reported as exactly that,
  rather than passing.

Every check below is proved twice: once red on a real fault, once green when the
fault is fixed. A check that cannot go red is checking nothing.

Run:  python tests/test_watchdog.py
"""

import json
import shutil
import sys
import tempfile
import types
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "engine"))

import crm_paths
import watchdog

FAILS = []


def check(label, cond, detail=""):
    ok = bool(cond)
    print(("  PASS  " if ok else "  FAIL  ") + label
          + (("   [" + detail + "]") if detail and not ok else ""))
    if not ok:
        FAILS.append(label)


VAULT = Path(tempfile.mkdtemp(prefix="crm-layer8-watchdog-"))
crm_paths.use_vault(VAULT)
(VAULT / "_layers").mkdir(parents=True)
(VAULT / "_layers" / "config.json").write_text(
    json.dumps({"layer": 7, "identifier": "linkedin-url"}), encoding="utf-8")
(VAULT / "People").mkdir(parents=True)
(VAULT / "_schema").mkdir(parents=True)
(VAULT / "_engine").mkdir(parents=True)
LEDGER = VAULT / "_ledger" / "events.jsonl"
LEDGER.parent.mkdir(parents=True)

SPEC = json.loads((ROOT / "schema" / "expectations.json").read_text(encoding="utf-8"))
(VAULT / "_schema" / "expectations.json").write_text(
    json.dumps(SPEC, indent=2), encoding="utf-8")


def ago(days):
    return (datetime.now(timezone.utc) - timedelta(days=days)).isoformat(timespec="seconds")


def emit(type_, person, days_ago):
    with open(LEDGER, "a", encoding="utf-8", newline="\n") as fh:
        fh.write(json.dumps({"ts": ago(days_ago), "type": type_,
                             "person": person}) + "\n")


def result(cid):
    return {r["id"]: r for r in watchdog.run()}[cid]


def person(name, body):
    (VAULT / "People" / (name + ".md")).write_text(body, encoding="utf-8")


print("\n=== 1. every declared expectation gets a result ===")

results = watchdog.run()
check("one result per expectation", len(results) == len(SPEC["checks"]),
      "%d vs %d" % (len(results), len(SPEC["checks"])))
check("each result carries a severity",
      all(r.get("severity") for r in results))
check("each result carries a detail somebody could act on",
      all(r.get("detail") for r in results))
check("each result carries what was expected, in plain words",
      all(r.get("expect") for r in results))
check("every expectation shipped here has a check behind it",
      not [c["id"] for c in SPEC["checks"] if c["id"] not in watchdog.CHECKS],
      str([c["id"] for c in SPEC["checks"] if c["id"] not in watchdog.CHECKS]))
check("every expectation says why it is there",
      all(c.get("why") for c in SPEC["checks"]))
check("every expectation says what would turn it red",
      all(c.get("red_when") for c in SPEC["checks"]),
      str([c["id"] for c in SPEC["checks"] if not c.get("red_when")]))

print("\n=== 2. silence is caught ===")

emit("reply_in", "Rowan Ashdown", 40)
r = result("the-log-is-still-growing")
check("a log that stopped a long time ago is red", r["ok"] is False, r["detail"])
check("and the message says how long", "days old" in r["detail"], r["detail"])

emit("reply_in", "Mara Quennell", 0)
r = result("the-log-is-still-growing")
check("and it goes green once something is captured again", r["ok"] is True, r["detail"])

print("\n=== 3. a record with no identifier is caught ===")

person("Rowan Ashdown", "---\nname: Rowan Ashdown\n"
                        "linkedin-url: https://www.linkedin.com/in/rowanashdown\n---\n")
person("Mara Quennell", "---\nname: Mara Quennell\n---\n")

r = result("every-record-has-an-identifier")
check("it is red", r["ok"] is False, r["detail"])
check("and names who is missing one", "Mara Quennell" in r["detail"], r["detail"])

person("Mara Quennell", "---\nname: Mara Quennell\n"
                        "linkedin-url: https://www.linkedin.com/in/maraquennell\n---\n")
check("it goes green when the identifier is added",
      result("every-record-has-an-identifier")["ok"] is True)

print("\n=== 4. the same person twice is caught ===")

person("Mara Q", "---\nname: Mara Q\n"
                 "linkedin-url: https://www.linkedin.com/in/maraquennell/\n---\n")
r = result("one-record-per-person")
check("two records with one identifier is red", r["ok"] is False, r["detail"])
check("and the message names both", "Mara Q" in r["detail"], r["detail"])
check("even though the trailing slash differs", "share one identifier" in r["detail"])

(VAULT / "People" / "Mara Q.md").unlink()
check("it goes green when the duplicate is gone",
      result("one-record-per-person")["ok"] is True)

print("\n=== 5. events nobody can attribute are caught ===")

for i in range(12):
    with open(LEDGER, "a", encoding="utf-8") as fh:
        fh.write(json.dumps({"ts": ago(1), "type": "reply_in", "person": None}) + "\n")
r = result("events-name-a-person")
check("a pile of unattributable events is red", r["ok"] is False, r["detail"])
check("and the message gives the percentage", "%" in r["detail"], r["detail"])

print("\n=== 6. a hold with nothing but a name is caught ===")

fake_holds = types.ModuleType("holds")
fake_holds._rows = [{"person": "Tobias Fenwick", "aliases": []},
                    {"person": "https://www.linkedin.com/in/deliamarchetti"}]
fake_holds.held = lambda: fake_holds._rows
fake_holds.is_held_person = lambda *ids: any(
    str(i).strip().lower() == "tobias fenwick" for i in ids)
sys.modules["holds"] = fake_holds
try:
    r = result("holds-carry-an-identifier")
    check("a name-only hold is red", r["ok"] is False, r["detail"])
    check("and it names them", "Tobias Fenwick" in r["detail"], r["detail"])
    check("the hold that has a link is not counted against it",
          "1 of 2" in r["detail"], r["detail"])

    print("\n=== 7. a held person on the page is caught ===")

    (VAULT / "Today.md").write_text(
        "# Today\n\n| # | Who | Why they are here | When |\n|---|---|---|---|\n"
        "| 1 | Rowan Ashdown | replied | 2 hours ago |\n"
        "| 2 | Tobias Fenwick | replied | 3 hours ago |\n", encoding="utf-8")
    r = result("held-people-are-not-on-the-page")
    check("somebody held appearing on the page is red", r["ok"] is False, r["detail"])
    check("and the message names them", "Tobias Fenwick" in r["detail"], r["detail"])
    check("it does not accuse the person who is not held",
          "Rowan Ashdown" not in r["detail"], r["detail"])

    (VAULT / "Today.md").write_text(
        "# Today\n\n| # | Who | Why they are here | When |\n|---|---|---|---|\n"
        "| 1 | Rowan Ashdown | replied | 2 hours ago |\n", encoding="utf-8")
    check("it goes green when they are off the page",
          result("held-people-are-not-on-the-page")["ok"] is True)
finally:
    del sys.modules["holds"]

print("\n=== 8. a write that could empty a file is caught ===")

(VAULT / "_engine" / "a_quick_script.py").write_text(
    'from pathlib import Path\n'
    'def stamp(note, text):\n'
    '    with open(note, "w", encoding="utf-8") as fh:\n'
    '        fh.write(text)\n', encoding="utf-8")
r = result("nothing-writes-unsafely")
check("a direct write is red", r["ok"] is False, r["detail"])
check("and the message says which file and which line",
      "a_quick_script.py line 3" in r["detail"], r["detail"])

(VAULT / "_engine" / "a_quick_script.py").write_text(
    'import os\n'
    'from pathlib import Path\n'
    'def stamp(note, text):\n'
    '    tmp = Path(str(note) + ".tmp")\n'
    '    with open(tmp, "w", encoding="utf-8") as fh:\n'
    '        fh.write(text)\n'
    '    os.replace(tmp, note)\n', encoding="utf-8")
check("writing beside the file and swapping is not reported",
      result("nothing-writes-unsafely")["ok"] is True,
      result("nothing-writes-unsafely")["detail"])

# A descriptor from a create-if-absent call cannot truncate anything, because the
# call already refused to touch an existing file. Reporting it would be the
# watchdog crying wolf, and a watchdog people learn to ignore is no watchdog.
(VAULT / "_engine" / "a_lock.py").write_text(
    'import os\n'
    'def take(path):\n'
    '    fd = os.open(str(path), os.O_CREAT | os.O_EXCL | os.O_WRONLY)\n'
    '    with os.fdopen(fd, "w", encoding="utf-8") as fh:\n'
    '        fh.write("taken")\n', encoding="utf-8")
check("a create-if-absent lock is not reported as a truncating write",
      result("nothing-writes-unsafely")["ok"] is True,
      result("nothing-writes-unsafely")["detail"])

print("\n=== 9. an expectation nobody implemented is reported as exactly that ===")

spec = json.loads((VAULT / "_schema" / "expectations.json").read_text(encoding="utf-8"))
spec["checks"].append({"id": "your-own-1", "severity": "high",
                       "expect": "every enquiry gets an answer the same day",
                       "why": "You wrote this when you installed the layer.",
                       "red_when": "you tell it how to know."})
(VAULT / "_schema" / "expectations.json").write_text(json.dumps(spec, indent=2),
                                                     encoding="utf-8")
r = result("your-own-1")
check("it is not reported as passing", r["skipped"] is True, str(r))
check("and the message says nothing checks it yet",
      "nothing checks it yet" in r["detail"], r["detail"])
check("your own words are carried through", r["expect"].startswith("every enquiry"))

print("\n=== 10. a check that breaks fails loudly rather than passing quietly ===")

real = watchdog.CHECKS["the-log-is-still-growing"]
watchdog.CHECKS["the-log-is-still-growing"] = \
    lambda spec: (_ for _ in ()).throw(RuntimeError("this check is broken"))
try:
    r = result("the-log-is-still-growing")
    check("a check that raises is reported as failing",
          r["ok"] is False and r["skipped"] is False, str(r))
    check("and the reason is carried", "this check is broken" in r["detail"], r["detail"])
finally:
    watchdog.CHECKS["the-log-is-still-growing"] = real

print("\n=== 11. it reports, and cannot repair ===")

before = (VAULT / "_schema" / "expectations.json").read_text(encoding="utf-8")
watchdog.run()
check("running the checks does not alter the expectations file",
      (VAULT / "_schema" / "expectations.json").read_text(encoding="utf-8") == before)

people_before = sorted(p.name for p in (VAULT / "People").glob("*.md"))
ledger_before = LEDGER.read_text(encoding="utf-8")
watchdog.run()
check("it does not touch the records",
      sorted(p.name for p in (VAULT / "People").glob("*.md")) == people_before)
check("it does not touch the event log",
      LEDGER.read_text(encoding="utf-8") == ledger_before)

src = (ROOT / "engine" / "watchdog.py").read_text(encoding="utf-8")
mutations = []
for i, line in enumerate(src.splitlines(), 1):
    s = line.strip()
    if s.startswith("#") or s.startswith('"'):
        continue
    if any(m in s for m in ("os.replace", ".unlink(", ".rename(", ".write_text(",
                            ".mkdir(")):
        mutations.append("%d: %s" % (i, s[:60]))
    if "open(" in s and any(mode in s for mode in ('"w"', "'w'", '"a"', "'a'")):
        mutations.append("%d: %s" % (i, s[:60]))
check("there is no code in it that could change what it measures", not mutations,
      "; ".join(mutations[:3]))

print("\n=== 12. the report reads like something a person would act on ===")

text = watchdog.render(watchdog.run())
check("failures sort to the top",
      text.splitlines()[0].startswith("FAIL"), text.splitlines()[0])
check("it counts what failed, passed and was not checked",
      "failing" in text and "not checked" in text)
check("it says plainly that it does not repair", "does not repair" in text)
check("the quiet form prints only failures",
      "ok  " not in watchdog.render(watchdog.run(), quiet=True))

shutil.rmtree(VAULT, ignore_errors=True)

print("\n%s" % ("ALL PASS" if not FAILS else "FAILURES: " + ", ".join(FAILS)))
sys.exit(1 if FAILS else 0)
