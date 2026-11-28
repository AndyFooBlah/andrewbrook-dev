---
title: 'Shopkeeper: the bots were playing the simulation, not the game'
description: >-
  A difficulty harness ran six thousand games and said Easy was 95% winnable.
  I played Easy twice and lost both times. The bug was not in the numbers —
  every scripted player could see something the game never showed a human.
date: 2026-11-28
repos:
  - shopkeeper
draft: true
tags:
  - games
  - simulation
  - evals
  - llm
---

## The game

Shopkeeper is a business game for children, roughly seven to fourteen. An aunt
you have never met leaves you a general store in a small California town in
1883, along with $500 and a letter. You have one month of trading to show her a
profit. You buy from six suppliers, you chalk prices on a sign board, you learn
trades out of library books, and when somebody actually wants to talk you talk
to them.

![The shop floor: a customer at the counter asking for two calico dresses, the notice that a computer writes what customers say, and the sign board below](/images/shopkeeper/shop-floor.jpg)

It is a toy for one specific child in my house, built almost entirely by Claude
across a few weeks of evenings. This post is about the single worst mistake we
made, which I like because the mistake was invisible, the symptom was a number
that looked excellent, and the fix was not where either of us was looking.

## Why there is a harness at all

Every constant in an economy game is a guess until something measures it.
Shopkeeper has about fifty of them: how many people come through the door, what
fraction stop to talk, how much a quilt costs to make against what the town
will pay, how fast reputation moves, what the aunt expects by day twenty.

So, as with [Wind Spirit](/writing/wind-spirit-balancer/), the simulation was
built first and framework-free — no React, no rendering, nothing it cannot do
in a loop — and a harness drives it with scripted players. Ten of them, from
`idle` (does nothing, must always lose) through `sensible` and `diligent` to
`greedy` (prices at three times cost, must also lose, because a game that
rewards gouging teaches the opposite of what this one is for). Two hundred
seeds, three difficulties: six thousand complete games in about forty seconds,
with no model calls anywhere in it.

The harness is the only reason to believe anything about the difficulty curve.
It runs in CI, and the claims in the design document are assertions in a test
file rather than opinions.

## 95%, and I lost twice

The sweep printed 95% on Easy for the diligent bot and healthy numbers for
everything else. Easy was declared calibrated and I went and played it.

I lost. I played again more carefully and lost again — not dramatically, just
ending the month a few dollars short of where the aunt wanted me, both times,
having felt busy throughout.

Two games is not evidence of anything. But there is a particular feeling when
your own harness is confident and you are not, and the useful instinct is to
distrust the harness rather than yourself, because the harness is the thing
making claims. I asked Claude to work out what the bots knew that I did not.

## The bots were reading the event log

Here is the answer, and it is embarrassing in hindsight.

Shopkeeper is event-sourced: a seed, an ordered log of events, and a snapshot
at each day boundary. Every arrival in the town is an event, including the
people who never speak. The scripted players decided what to make by tallying
those events — every customer, every day, perfectly remembered, from the
beginning of the game.

The player has no such list. On Easy, 39 people come through the door a day and
the player actually speaks to about **one in seven** of them. The rest is
over-the-counter trade: they read the sign board, they pay it or they don't,
and they leave a line in a feed that scrolls away while you are at the back of
the shop making soap.

![The day's trade, most of it wordless: six short exchanges in a feed, four of them 'Have you any work shirts?' answered 'Not today, I'm afraid'](/images/shopkeeper/wordless-trade.jpg)

That feed is where the town was telling me what it wanted, four hundred times a
day, in a list I could not read fast enough and the game did not keep.

So the bots were not better players than me. They were playing a different
game — one with a demand report in it. The harness was measuring the designer's
understanding of the simulation, not a player's experience of the game.

## The ablation

A hypothesis like that is worth exactly nothing until you can isolate it, and
isolating it in a deterministic sim is cheap. Take the beginner as they were
before any of this existed, and add one habit at a time, 200 seeds each, Easy
only.

<div class="table-scroll">

| The beginner, one habit added at a time | Easy |
|---|---|
| can only see the people they personally served | **0%** |
| + sees the last week on a demand board | **62%** |
| + buys three days of supplies a trip instead of one | 81% |
| + reliably chalks a price up for what is in stock | 82% |
| + works the evening instead of going to bed | 82% |
| + ranks trades by margin rather than by who asked most | 71% |

</div>

Zero to 62 on one change. Nothing else is close, and the two habits I would
have guessed mattered most — pricing diligence and working late — are worth a
single point between them.

It holds from the other end too. The competent `sensible` bot passes 83% of
months on Easy with its log access; blindfold that same bot so it only
remembers the people it spoke to, change nothing else, and it drops to **12%**.
Competence is not the variable. Information is.

The last row is the one I did not expect. Ranking trades by margin — the
obviously smarter policy — *costs* a one-line beginner eleven points. With only
one product line you had better make the thing the town keeps asking for, even
if a fussier product pays better per hour, because a high margin on something
nobody wants is a shop full of stock and an empty till. That is a real lesson
about small businesses and it fell out of a sweep rather than out of my head.

## The fix was not to soften Easy

The tempting fix is the dial: drop the aunt's target, raise the customer count,
and watch the beginner's pass rate climb. It would have worked, and it would
have been a lie — the game would still have been asking a child to infer demand
from a feed that scrolls, and it would simply have stopped punishing them for
failing.

The design document had claimed since its first draft that **listening is the
rewarded skill**. It had never actually given the player a way to listen. So we
built the thing the design had been promising:

![The 'What people ask for' board: five goods with columns for asked for, sold, too dear, missed and have. Work shirts asked for 254 times, none sold, 164 missed](/images/shopkeeper/demand-board.jpg)

**What people ask for**, a first-class screen rather than a statistic. Over the
last week, per good: how many were asked for, how many you sold, how many
baulked at your price, how many you missed entirely — with the misses split
into "you had none" and the far more annoying "you had them but never chalked
up a price". Plus, on the town map, a plain count of who rang the bell while
you were out walking to a supplier.

The shop in that screenshot has been asked for work shirts 254 times and has
sold none, because it never learned to sew. You can read that in about two
seconds. You could not read it at all in the version my harness called
calibrated.

With the board in the game, the beginner bots go from 0% to 62% and 82% on
Easy, and — this matters more — those numbers now describe something a child
can actually do.

## Two rules, and a tripwire

The general lessons, which I think apply to any agent or bot you use to measure
a human experience:

**1. A scripted player may only use information the interface actually shows.**
A bot with privileged access measures your understanding of the system, not the
player's experience of it. This one is easy to violate by accident, because the
bot lives inside the code and the state is right there, uncommented and free.

**2. The beginner is the calibration.** Competent bots passing Easy never meant
a child would. The beginners are now first-class members of the sweep:
`novice`, who reads the demand board and ignores every other hint the shop
gives, and `learner`, who also acts on the two warnings it shows. The gap
between them is what those warnings are worth, measured rather than asserted.

And the part I would recommend to anyone: keep the broken version as a
**tripwire**. `blindfolded` is still in the sweep, still unable to see demand,
and the test suite asserts it stays at or below 5% on Easy. If it ever starts
passing, something has gone soft and no other number in the file can be
trusted until somebody explains why. A fixed bug with no test is a bug waiting
for its second appearance.

![The progress chart: what the shop is worth against the pace it needs to keep, ahead by $22.55 with 11 trading days to go](/images/shopkeeper/progress-chart.jpg)

## An aside on letting a child talk to a model

Most of Shopkeeper needs no AI at all, and the game is deliberately complete
without an API key: the engine understands a price you type, and the customers
answer from written period lines. Everything above was measured with zero model
calls. But when a key is present, the customer at the counter is played by a
model, and that is the best part of the game.

Two things about that turned out to be worth knowing, and neither was obvious
from inside the code.

**The provider's terms decide this before you do.** Shopkeeper ran on Google's
Gemini until November. Then I actually read the terms: the Gemini API Additional
Terms ("Age Requirements") and Google Cloud's Service Specific Terms §20(d) bar
their generative AI from any service "directed towards or is likely to be
accessed by individuals under the age of 18". No exception, no approval route,
no parental-consent path. A game for seven-year-olds is not a borderline case,
and limiting it to people I know does not change what the service is directed
towards. Anthropic's Usage Policy permits products serving minors subject to
[additional guidelines](https://support.claude.com/en/articles/9307344-responsible-use-of-anthropic-s-models-guidelines-for-organizations-serving-minors),
so the game moved to Claude Haiku. If you are building anything a child might
touch, read the age clause first; it is a shorter conversation than rewriting
your provider layer afterwards.

That move came with homework, which is now a
[public page](https://github.com/AndyFooBlah/shopkeeper/blob/main/docs/child-safety.md)
written for a parent rather than for a compliance file: what is sent, what is
never kept, a child-safety block on every prompt that generates prose, an
undismissable notice on the title screen and above the counter saying a
computer writes the customers, and each of the provider's guidelines with how
it is met — including the two I deliberately do not do, and why.

![The title screen: a notice reading 'When you talk to a customer at the counter, a computer writes what they say back — there is no person on the other end'](/images/shopkeeper/title.jpg)

**And it costs less than I assumed, in the ordinary case.** Measured on the live
API rather than estimated: a counter exchange is about 2,115 tokens in and 78
out, a diary entry 937 and 85. That is roughly **six cents per player-month** and
**eighteen cents for a complete three-month game**. My pre-measurement estimate
was out by a factor of two, because I had carried the token counts across from
the old provider and ignored both a different tokenizer and the safety block I
had added to every prompt in the same change.

The interesting number is not the average, though. Input outweighs output
twenty-five to one, because the persona and the safety rules are re-sent on
every turn, and the exposure is not the typical player but the atypical one. My
rate limiter was a counter in process memory — per instance, not per user — so
an autoscaling host multiplies it, and saturating three instances is about
$5/hour. That is the number that matters when you put a key on the internet
behind a children's game.

## So it is open source rather than a public site

Which brings me to why there is no link here to a page where you can play it.

Hosting this publicly means a key, a bill with a long tail, and me becoming the
data controller for whatever other people's children type into a text box. None
of that is unmanageable, but none of it is what this project is for. So the
[code is on GitHub](https://github.com/AndyFooBlah/shopkeeper) under Apache-2.0,
it runs on `npm install && npm run dev` with no key and no account, and the
README has a section called "Before you host this for anyone else" that says
the three things above plainly. A few friends and family play my own instance
behind a password.

One more reason to hold off on a public launch, and it is the honest one:
1880s California is a content minefield. The Chinese Exclusion Act is 1882.
Generated "plausible local news" wanders into lynchings and anti-Chinese
violence without being asked to, and the name pool is full of real places whose
history is not Easy-mode material without context — the data file carries an
`easy_ok` flag per entry and a note explaining each exclusion. That curation
pass is unfinished, and a password is not a substitute for finishing it.

## Who did what

Claude wrote essentially all of the code: the event-sourced engine, the
harness, the demand board, the server, the compliance work, and 253 tests.
I set the direction, made the calls, and played the game.

The useful division of labour turned out to be exactly that. The harness was
Claude's idea and a good one. The ablation was Claude's work and I could not
have done it as quickly. But the bug started with a human sitting down on a
Sunday evening, playing the thing on its easiest setting, losing, and being
annoyed about it — and then not dismissing the annoyance, because an agent with
a green test suite has no way to feel that something is wrong.

Six thousand simulated games said Easy was fine. Two real ones said it wasn't.
The real ones were right.
