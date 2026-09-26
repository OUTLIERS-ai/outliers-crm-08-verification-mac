"""
Outliers CRM - Layer 8 - Is It True, And Is It Working

Your CRM is fast now, and running on assumptions about which signals matter.
Nothing has tested them. It also cannot tell you whether it is working or quietly
doing nothing, because a run that produces nothing exits exactly as cleanly as
one that produces everything.

This layer installs two things: a way to count properly, and a way to be told.

    python install.py

It finds the CRM you built in Layer 1, asks you two questions in your own words,
and installs the layer into it.

Needs: Python 3.8 or newer. Nothing else.
"""

import json
import os
import sys
from datetime import date
from pathlib import Path

# The command a member types to start Python: `python3` on a Mac, which has no plain
# `python` command, and `python` everywhere else, as the Windows guides print it.
PY = "python3" if sys.platform == "darwin" else "python"

LAYER = 8
LAYER_NAME = "Is It True And Is It Working"
NEEDS_LAYER = 7

HERE = Path(__file__).resolve().parent

MODULES = ["crm_paths.py", "safe_write.py", "fourbox.py", "watchdog.py"]

# ---------------------------------------------------------------- small helpers

# No colour codes anywhere. Plenty of terminals print them as literal gibberish
# and a member's first minute with this must not look broken. Plain text works
# everywhere, which is the whole point of the exercise.
BOLD = DIM = OFF = ""


def say(msg=""):
    print(msg, flush=True)


def ask(question, default=None, helptext=None):
    """One plain question. Enter accepts the default."""
    say()
    say(BOLD + question + OFF)
    if helptext:
        say(DIM + "  " + helptext + OFF)
    prompt = "  > " if default is None else "  [%s] > " % default
    try:
        answer = input(prompt).strip()
    except (EOFError, KeyboardInterrupt):
        say("\nStopped. Nothing was changed.")
        sys.exit(1)
    return answer or (default or "")


def ask_yes(question, default=True):
    d = "Y/n" if default else "y/N"
    a = ask(question, default=d).strip().lower()
    if a in ("y/n", "y/n".upper(), "y", "yes"):
        return True if a != "y/n" else default
    if a in ("n", "no"):
        return False
    return default


def write(path, content):
    """Write a file without ever damaging one that already exists.

    Writes to a temporary file first, then swaps it into place in a single step.
    If anything goes wrong halfway through, the original is untouched.
    """
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + ".tmp")
    with open(tmp, "w", encoding="utf-8", newline="\n") as fh:
        fh.write(content)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(tmp, path)


def copy_in(src, dst):
    write(dst, Path(src).read_text(encoding="utf-8"))


def keep_cache_out_of_history(home):
    """Python leaves compiled cache folders beside any code it runs.

    They are noise, they change constantly, and they do not belong in the history
    of your records. Adding two lines to the ignore file costs nothing and saves a
    confusing first look at what changed.
    """
    path = Path(home) / ".gitignore"
    try:
        current = path.read_text(encoding="utf-8") if path.exists() else ""
    except OSError:
        return
    if "__pycache__" in current:
        return
    head = (current.rstrip() + "\n\n") if current.strip() else ""
    write(path, head
          + "# Python leaves these beside any code it runs. Not part of your CRM.\n"
          + "__pycache__/\n"
          + "*.pyc\n")


# -------------------------------------------------------------- finding the CRM

def config_path(home):
    return Path(home) / "_layers" / "config.json"


def looks_like_a_crm(home):
    try:
        return config_path(home).exists()
    except OSError:
        return False


def find_vault():
    """Find the CRM Layer 1 built, by looking for its config file."""
    tried = []
    env = os.environ.get("OUTLIERS_CRM")
    if env:
        tried.append(Path(env).expanduser())
    # Layer 1 leaves a pointer naming wherever the member chose to put their CRM.
    # Without checking it, anyone who declined the default folder is told they have
    # not done Layer 1 when they have, which reads as the series being broken.
    pointer = Path.home() / ".outliers-crm"
    if pointer.exists():
        try:
            noted = pointer.read_text(encoding="utf-8").strip()
            if noted:
                tried.append(Path(noted))
        except OSError:
            pass
    tried.append(Path.home() / "CRM")
    here = Path.cwd()
    tried.append(here)
    tried.extend(here.parents)

    for candidate in tried:
        if looks_like_a_crm(candidate):
            return Path(candidate)

    say()
    say("  Could not find your CRM automatically.")
    raw = ask("Where is it?",
              default=str(Path.home() / "CRM"),
              helptext="The folder Layer 1 built. It has a _layers folder inside it.")
    candidate = Path(raw.strip().strip('"').strip("'")).expanduser()
    return candidate if looks_like_a_crm(candidate) else None


def load_config(home):
    try:
        return json.loads(config_path(home).read_text(encoding="utf-8"))
    except Exception:
        return {}


def refuse_politely(reason):
    say()
    say("=" * 66)
    say("  Not yet.")
    say("=" * 66)
    say()
    say("  " + reason)
    say()
    return 1


# ------------------------------------------------------------------ the interview

def interview(cfg):
    say()
    say("=" * 66)
    say("  OUTLIERS CRM   LAYER %d   VERIFICATION" % LAYER)
    say("=" * 66)
    say()
    say("  Two problems left, and they are the same problem.")
    say()
    say("  You are ordering your attention by rules nobody tested. And your")
    say("  system cannot tell you it has stopped, because a run that produces")
    say("  nothing exits just as cleanly as one that produces everything.")
    say()
    say("  Almost every published conversion figure is a supplier reporting its")
    say("  own winners, including the one behind the ordering you installed.")
    say("  Counting your own, properly, is the only way past that.")
    say()
    say(DIM + "  Two questions, in your own words." + OFF)

    always = ask("What should always be true about your system?",
                 default="",
                 helptext="Plain sentences. The things that, if they stopped being "
                          "true, would mean something is wrong. You get a starter "
                          "set of checks either way; this is for the ones only you "
                          "would know.")

    broken = ask("What would tell you it had stopped working?",
                 default="",
                 helptext="The signs. Not the causes. What would you notice, or "
                          "fail to notice, if the whole thing quietly died?")

    return {"always": always.strip(), "broken": broken.strip()}


# ------------------------------------------------------------------ what we build

def personalise(spec, answers):
    """Add the member's own words to the expectations file, unimplemented.

    They are added as real entries, which the watchdog will report as declared
    and unchecked. That is deliberate. Seeing your own sentence come back with
    "nothing checks this yet" next to it is the shortest route to understanding
    what an expectation actually is.
    """
    for text, sev in ((answers["always"], "high"), (answers["broken"], "critical")):
        if not text:
            continue
        spec["checks"].append({
            "id": "your-own-" + str(len([c for c in spec["checks"]
                                         if str(c.get("id", "")).startswith("your-own-")]) + 1),
            "severity": sev,
            "expect": text,
            "why": "You wrote this when you installed the layer.",
            "red_when": "you tell it how to know. Until then the watchdog will "
                        "report it as declared and unchecked, which is honest."
        })
    return spec


def readme(answers, cfg):
    return """# Is it true, and is it working

Two questions, one layer.

## Is it true

    %s _engine/fourbox.py reply_in meeting_booked --within 30

Counts all four combinations of a signal and an outcome:

                        outcome      no outcome
    had the signal          a             b
    did not                 c             d

Only `a` is easy to get, and `a` on its own is how a system learns a
superstition. Everyone who bought had replied to something, so replies must work.
That reasoning has a hole in it the size of the business: you never counted the
people who replied and did not buy.

The tool refuses to produce a rate when an arm has too few people in it, and says
why in words. "Not enough to say" is a complete answer, and a better one than a
number nobody should trust.

It counts. It does not explain. Two things travelling together says nothing about
which one moved the other, or whether a third thing moved both.

## Is it working

    %s _engine/watchdog.py

Reads `_schema/expectations.json`, which is yours, and reports the difference
between what you said should be true and what is. It never repairs anything. A
watchdog that fixes what it finds becomes another writer nobody is watching, and
then you have two things that can be wrong and only one being checked.

Silence is not health. A system that produces nothing exits cleanly, every time,
and looks identical in every log to one that is working. That is what the
still-growing check is for, and it is the most important line in the file.

## Your own expectations

The two sentences you wrote at install are in the file, marked as declared and
unchecked. The watchdog will keep saying so. To make one real, give it an id the
watchdog knows, or write a check for it in `_engine/watchdog.py` and add it to
the list at the bottom.

## Break something on purpose

The only way to know a check works is to make it go red. Rename a person's
identifier field, or put somebody who is held onto the page by hand, then run the
watchdog. Watch it catch you. Then put it back.

A check you have never seen fail is a check you are trusting on faith.

## This loops back

What you learn here changes the rules in Layer 2 and the collectors in Layer 4.
A signal that turns out not to predict anything should stop being ranked in Layer
7. That is not the system being wrong; it is the system being finished, in the
sense that a garden is finished.
""" % (PY, PY)


def layer_note(answers, cfg):
    return """# Layer {n} - Is it true, and is it working

**What it built.** A counter that fills in all four boxes of signal against
outcome, and refuses to produce a rate it cannot honestly produce. An
expectations file you own and the system never edits. A watchdog that checks
them and reports, and cannot repair.

**What it does.** It replaces belief with counting, and silence with a report.
Before this, the ordering in Layer 7 was a plausible story and nobody had tested
it, and a system that had quietly stopped looked exactly like a system that was
working.

**The idea worth keeping.** Counting only the wins is how a system learns a
superstition. The box nobody fills in is the one where the signal was present and
nothing happened, and it is the box that decides whether the signal means
anything at all.

**The second idea.** A watchdog that repairs is another writer nobody is
watching. It reports. You diagnose.

**What this now creates.** What you learn here changes the rules in Layer 2 and
the collectors in Layer 4. The ladder loops back to the bottom, and that does not
stop.
""".format(n=LAYER)


def build(home, answers, cfg):
    say()
    say("Installing Layer %d into %s" % (LAYER, home))
    say()

    def note(path, what):
        say("  built  %-36s %s" % (str(Path(path).relative_to(home)), what))

    for name in MODULES:
        copy_in(HERE / "engine" / name, home / "_engine" / name)
    say("  built  %-36s %s" % ("_engine/fourbox.py", "counts all four boxes"))
    say("  built  %-36s %s" % ("_engine/watchdog.py", "checks, and never repairs"))

    target = home / "_schema" / "expectations.json"
    if target.exists():
        say("  kept   %-36s %s" % ("_schema/expectations.json",
                                   "already there, and it is yours; left alone"))
    else:
        spec = json.loads((HERE / "schema" / "expectations.json").read_text(encoding="utf-8"))
        spec["updated"] = date.today().isoformat()
        spec = personalise(spec, answers)
        write(target, json.dumps(spec, indent=2, ensure_ascii=False) + "\n")
        note(target, "what should be true. Yours, and never edited by the system")

    (home / "Reports").mkdir(parents=True, exist_ok=True)
    say("  built  %-36s %s" % ("Reports/", "where counts get written when you ask"))

    p = home / "_verification" / "README.md"
    write(p, readme(answers, cfg))
    note(p, "how to count, and how to be told")

    p = home / "_layers" / ("Layer %d - Verification.md" % LAYER)
    write(p, layer_note(answers, cfg))
    note(p, "what this layer did, for when you forget")

    keep_cache_out_of_history(home)

    cfg["layer"] = max(int(cfg.get("layer", 0) or 0), LAYER)
    cfg["expectations"] = "_schema/expectations.json"
    cfg["layer-%d-installed" % LAYER] = date.today().isoformat()
    write(config_path(home), json.dumps(cfg, indent=2) + "\n")


def first_run(home):
    """Run the watchdog once, so the first thing they see is a real result."""
    say()
    say("Running the checks for the first time.")
    say()
    sys.path.insert(0, str(home / "_engine"))
    try:
        import crm_paths
        import watchdog
        crm_paths.use_vault(home)
        results = watchdog.run()
        text = watchdog.render(results)
    except Exception as err:
        say("  Could not run them yet (%s)." % err)
        say("  Run them yourself with: %s _engine/watchdog.py" % PY)
        return 0
    for line in text.splitlines():
        say("  " + line)
    failing = len([r for r in results if not r["ok"] and not r["skipped"]])
    return failing


def finish(home, answers, failing):
    say()
    say("=" * 66)
    say("  Done. Your CRM can now tell you when it is wrong.")
    say("=" * 66)
    say()
    if failing:
        say("  %d check(s) are failing right now. That is the normal result on a" % failing)
        say("  first run and it is the point: they are telling you something true")
        say("  about the state of the system. Nothing has been repaired, because")
        say("  the watchdog does not repair.")
    else:
        say("  Nothing is failing. Treat that with some suspicion: a set of checks")
        say("  that is green the day it is written is checking things that were")
        say("  never going to break.")
    say()
    say("  From inside %s:" % home)
    say()
    say("      %s _engine/watchdog.py" % PY)
    say("      %s _engine/fourbox.py reply_in meeting_booked --within 30" % PY)
    say()
    say("  What to do now: break something on purpose. Take the identifier off a")
    say("  record, or put somebody who is held onto the page by hand. Run the")
    say("  watchdog. Watch it catch you. Then put it back.")
    say()
    say("  A check you have never seen fail is a check you are trusting on faith.")
    say()
    say("  One last thing. What you learn here changes the rules in Layer 2 and")
    say("  the collectors in Layer 4. The ladder loops back to the bottom, and")
    say("  that does not stop.")
    say()


def main():
    home = find_vault()
    if not home:
        return refuse_politely(
            "Layer %d needs Layer 1 first. Run that one and come back." % LAYER)

    cfg = load_config(home)
    have = int(cfg.get("layer", 0) or 0)
    if have < NEEDS_LAYER:
        return refuse_politely(
            "Layer %d needs Layer %d first. Run that one and come back.\n\n"
            "  Your CRM at %s is on Layer %d."
            % (LAYER, NEEDS_LAYER, home, have))

    answers = interview(cfg)
    say()
    say("  Installing into:      %s" % home)
    say("  Should always be true: %s"
        % (answers["always"] or "(left blank; you get the starter checks)"))
    say("  Would mean it broke:   %s"
        % (answers["broken"] or "(left blank; you get the starter checks)"))
    if not ask_yes("Go ahead?", default=True):
        say("\nStopped. Nothing was changed.")
        return 1
    build(home, answers, cfg)
    failing = first_run(home)
    finish(home, answers, failing)
    return 0


if __name__ == "__main__":
    sys.exit(main())
