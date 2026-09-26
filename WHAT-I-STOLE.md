# What I stole

Every idea in this layer is borrowed, and mostly from fields where believing an
uncounted thing had consequences worse than a wasted afternoon.

## The four boxes

**From:** the two-by-two contingency table, which is the oldest tool in
epidemiology and the reason we know what causes what in medicine. Also the
confusion matrix, which is the same object under a different name in machine
learning, where it produces precision and recall.

**Why it is here:** the failure it prevents is universal and invisible. You look
at the customers you won, find something they had in common, and conclude it
works. That is a case-series, and it cannot support the conclusion, because the
comparison group was never assembled. The four boxes are what turns an anecdote
into a comparison.

**What was adapted:** no statistical test. A test would imply a level of rigour
the data does not support, and would produce a p-value that gets quoted as though
it settled something. Instead the tool refuses to produce a rate when the arm is
too small, which is blunter and harder to misuse.

## Refusing to produce a number

**From:** the convention in reporting of suppressing a cell below a threshold,
used by statistical agencies for disclosure control and by anyone reporting rates
from small populations.

**Why it is here:** three out of three is not 100 per cent, it is three. Once a
percentage sign is attached, the sample size falls off in transit and the number
travels on its own. Not producing it at all is the only reliable fix, because a
caveat next to a number is not carried when the number is quoted.

## Requiring the outcome to follow the signal

**From:** the temporality criterion in the Bradford Hill considerations, which is
the one item on that list nobody argues about: a cause has to come before its
effect.

**Why it is here:** without a window, somebody who booked a call and later
replied to something counts as evidence that replies produce bookings. This is
not a subtle error and it is extremely easy to make, because the naive count is
the one every query language makes easiest to write.

## The expectations file the system cannot edit

**From:** the separation between a specification and an implementation. Also, more
directly, the practice of keeping test fixtures and golden files outside the code
that is being tested.

**Why it is here:** the cheapest way to make a failing check pass is to weaken the
check. Anything able to both fail a check and edit the check will eventually do
the second to avoid the first, and nobody will notice because the report will be
green.

## A watchdog that reports and never repairs

**From:** monitoring practice, and the distinction between a monitor and a
controller. Also the reason a test that modifies the code under test is not a
test.

**Why it is here:** self-healing sounds like an improvement and is the opposite.
A component that fixes what it finds is another writer, acting on your records,
that nobody is checking. You then have two things that can be wrong and only one
being watched, and the one being watched is the one that was already working.

## Alerting on absence, not just on errors

**From:** the dead man's switch, and the heartbeat monitor. In railway signalling
the equivalent is a track circuit that fails to detect a train and is therefore
designed to fail towards danger being assumed.

**Why it is here:** this is the check that catches the failure everything else
misses. An automated system that produces nothing exits with a success code,
writes a clean log, and looks exactly like a system with nothing to do. Nothing
in an error-driven monitor will ever fire. Somebody working alone has no
colleague to notice the output stopped, so the absence has to be checked for
directly.

## Writing checks that were red when you wrote them

**From:** test-driven development, specifically the discipline of watching a test
fail before making it pass. A test that has never failed might be asserting
nothing at all.

**Why it is here:** a set of checks that is entirely green on the day it ships is
checking conditions that were never going to break. That set will stay green
forever and will be trusted, which makes it worse than having no checks, because
having no checks does not produce confidence.

## Naming a check by what it catches

**From:** nothing grand. It is the same instinct as naming a test after the
behaviour rather than the function.

**Why it is here:** a check called `check_3` produces a report nobody can act on.
A check called `the-log-is-still-growing`, failing, tells you what is wrong before
you have read the detail line.
