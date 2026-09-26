**This is the Mac version.** On Windows, use [outliers-crm-08-verification](https://github.com/OUTLIERS-ai/outliers-crm-08-verification).

# Outliers CRM - Layer 8 - Is It True, And Is It Working

Two problems are left, and they turn out to be the same problem.

Your system is fast now, and it is ordering your attention by rules nobody
tested. And it cannot tell you it has stopped, because a run that produces
nothing exits exactly as cleanly as one that produces everything.

Both are cases of believing something without counting it.

## Install it

    python3 install.py

One command. It finds the CRM you built in Layer 1, installs into it, and runs
the checks once so the first thing you see is a real result. Two questions:

- **What should always be true about your system?**
- **What would tell you it had stopped working?**

Both answers go into your expectations file as real entries, marked as declared
and unchecked. The watchdog keeps saying so until you make one real. That is not
an oversight, it is the fastest way to understand what an expectation is.

## What it needs beneath it

Layer 7. The installer checks and stops politely if it is not there.

## What it installs

| Path in your CRM | What it is |
|---|---|
| `_schema/expectations.json` | What should be true. Yours. The system reads it and never edits it. |
| `_engine/watchdog.py` | Checks them and reports. Cannot repair. |
| `_engine/fourbox.py` | Counts all four combinations of a signal and an outcome. |
| `Reports/` | Where counts get written when you ask for them. |

## Is it true

Almost every conversion figure in the industry is a supplier reporting its own
winners, including the response-time study behind the ordering you installed in
Layer 7. Those numbers cannot steer your system, because they were not measured
on your system, on your people, and usually not measured honestly at all.

So count your own. In Terminal, from your CRM folder (if your CRM is not at `~/CRM`, put your own folder in the `cd` line):

    cd ~/CRM
    python3 _engine/fourbox.py reply_in meeting_booked --within 30

                        outcome      no outcome
    had the signal          a             b
    did not                 c             d

Only `a` is easy to get, and `a` on its own is how a system learns a
superstition. Everyone who bought had replied to a message, so replies work. The
hole in that is the size of the whole business: nobody counted the people who
replied and did not buy.

`b` decides whether the signal means anything. `c` says whether it is even
necessary. `d` is the population you forgot you had.

The tool refuses to produce a rate when an arm is too small or empty, and says
why in words. **"Not enough to say" is a complete answer**, and a better one than
a number that will be quoted without its caveat.

It counts. It does not explain. Two things travelling together says nothing about
which one moved the other, or whether a third thing moved both, and the report
says so every time.

## Is it working

    python3 _engine/watchdog.py

It reads your expectations file, compares each one against what is actually true,
and reports the difference.

**It never repairs.** A watchdog that fixes what it finds stops being a
measurement and becomes another writer nobody is watching, and then you have two
things that can be wrong and only one being checked. Diagnosis and repair belong
to you.

**Silence is not health.** The most important check in the file is the one asking
whether anything has been captured recently. Nothing else would notice a system
that had quietly stopped: every other check is perfectly happy with a system that
has nothing left to do.

The checks that ship with it:

| Check | What it catches |
|---|---|
| `the-log-is-still-growing` | A system that runs, exits cleanly and does nothing. |
| `every-record-has-an-identifier` | A record nothing can match, hold or count. |
| `one-record-per-person` | Two half-histories and no way to tell which is right. |
| `events-name-a-person` | History the system cannot use. |
| `held-people-are-not-on-the-page` | The hold quietly not working. |
| `holds-carry-an-identifier` | A hold invisible to anything holding a link. |
| `nothing-writes-unsafely` | Code that empties a file it meant to update. |

## Now use it: break something on purpose

The only way to know a check works is to watch it go red.

Take the identifier off one record and run the watchdog. Or put somebody who is
held onto today's page by hand and run it again. Then put it back.

**A check you have never seen fail is a check you are trusting on faith.** For
the same reason, a set of checks that is entirely green the day you write it is
checking things that were never going to break.

## Run the tests

From the folder you downloaded:

    cd ~/outliers-crm-08-verification-mac
    python3 tests/test_fourbox.py
    python3 tests/test_watchdog.py

Each check in the watchdog is proved twice in there: once red on a real fault,
once green when the fault is fixed. Standard library only.

## What this creates

What you learn here changes the rules in Layer 2 and the collectors in Layer 4. A
signal that turns out not to predict anything should stop being ranked in Layer
7, and a check that goes red repeatedly is usually telling you the layer beneath
it is wrong rather than that the check is too strict.

The ladder loops back to the bottom, and that does not stop.

This repo is made automatically from outliers-crm-08-verification@7c7a167. To report a problem or suggest a change, use that repo, not this one.
