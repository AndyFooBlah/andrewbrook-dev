---
title: 'Wind Spirit: balance is measured, not argued'
description: >-
  Before the UI, before the LLM chiefs, a headless harness ran a civilization
  sandbox for hundreds of years across many seeds. Four ways the villages
  collapsed, the fixes, and what the numbers said about the game I thought I
  was designing.
date: 2026-09-12
repos:
  - wind-spirit
draft: false
tags:
  - games
  - simulation
  - claude-code
---

## The idea

Wind Spirit is a civilization sandbox where every village is run by an AI
chief and the player is a spirit who sees everything and can touch almost
nothing. You win chiefs' trust by whispering truths; they build the world with
their hands.

It started as a long brain-dump. Villages with AI chiefs. Stone-age tech. A
tech tree with made-up names so an LLM chief can't just recall the real world
and skip to bronze. Trade emerging from uneven resources, maybe violence, and
the player as a spirit who can only talk to the chiefs. I handed that to
Claude and we spent an evening organizing and critiquing it.

The reframing that made it a game came out of that session: the spirit is
omniscient and impotent, the chief is ignorant and potent. A chief listens to
the spirit because the spirit knows things. Advice that pans out builds trust,
advice that fails erodes it, and trust is the scoreboard.

A lot of the rest fell out of that. A week tick, because my own arithmetic on
walking speeds showed month ticks were too coarse. Paths that emerge from use
and become roads. Boats and coasts. Provisioned versus foraging travel, so a
desert is a real barrier. A scarce "breath" budget for wind and weather as the
spirit's one physical power. Event-sourced history so you can scrub back to
any week. Generated music.

And one suggestion from Claude that I'm glad I took: before any UI or any LLM
chief, build step zero, a headless balance harness with scripted chiefs, run
for hundreds of years across many seeds. Every rate in the design was a guess.
Balance is measured, not argued.

## Why a balancer first

The concept document has a "balance ladder" in it. A village of about 20
should live easily on wild food. Around 50, wild food alone can't sustain it,
so farming has to start. Around 150, one tile's farming isn't enough without
irrigation, husbandry or trade. That ladder pushes villages outward, and if
the rates are wrong the game has no shape: either nobody ever needs to leave,
or everybody starves in year ten.

Regrowth rates, yields per worker-week, spoilage, mortality curves, birth
rates, hard-winter penalties, field fertility: all numbers I typed in because
they felt about right. The Grammar Garden had already taught me that almost
every constant I set by instinct was wrong by a factor of two or three. This
design had fifty of them. So I had Claude build the sim first, with no screen,
and drive it with scripted chiefs.

## How the harness works

The sim is a pure, deterministic weekly tick in TypeScript: no clocks, no
I/O, same seed gives the same world bit for bit. The harness wraps it with
scripted chief policies that stand in for the LLM chiefs. A **forager** hunts,
fishes and gathers and builds a granary at fifteen people. A **farmer** also
clears plots and plants in spring. A **sensible** chief farms, explores, and
sends colonists when its tile gets crowded. Three "legacy" policies and a set
of parameter switches reproduce earlier, broken versions of the rules, so the
failures stay reproducible after they are fixed.

A suite of eleven checks encodes the ladder: 20 people live for 100 years on
wild food, 50 cannot, farming lifts a village past 50 but plateaus, sensible
chiefs colonize and civilization persists 300 years, paths form. Plus
determinism and replay checks. The suite runs in CI on six seeds.

The other tool is a weekly debug tracer for one village: population by life
stage, orders, food produced against mouths to feed, stores, hunger, fields
and fertility, deaths. Every failure below was diagnosed by reading that
trace. Claude did the building and the tuning; my job was to look at the
charts and say "that's not a village, that's a graveyard." Getting the suite
green took eight rounds. Four of the failures are worth reproducing here.

## Collapse 1: a hard winter with no stores

The first forager villages didn't build storage, and the first hard winter
rule halved every food source at once. Combine that with the original
starvation model, in which a few unlucky people starved outright while
everyone else ate, and you get this.

<figure class="chart">
  <img src="/charts/wind-spirit/collapse-hard-winter.svg" alt="Four stacked weekly panels for one village over 16 years under legacy rules: population dwindles from 20 to 12, weekly food production dips below mouths to feed every winter, stores never exceed 60 person-weeks and hit zero each spring, and in the hard winter of year 15 hunger spikes to eight weeks owed per person and the village dies in 30 weeks. The same village under current rules holds 25 people with stores peaking near 280 every autumn.">
  <figcaption>Seed f20-7, one village, weekly. Legacy rules on the left of each comparison: no granary, hard winter halves everything, selective starvation. The blue lines are the same village under the current rules.</figcaption>
</figure>

Look at the stores panel. Wild plants spoil in four weeks, meat and fish in
two. Without a granary the village cannot carry summer into winter, so stores
saw-tooth between 60 and zero and every spring is a small famine. The village
loses a person or two most winters and drifts from 20 down to 12 over fifteen
years. Then the winter of year 15 rolls "hard": production drops to 5
person-weeks a week against 12 mouths, stores are already at zero, and the
selective starvation rule kills the hungry one after another. Thirty weeks
from the first death to the last. Under these rules 42% of villages made it to
year 100. The same village under the current rules holds 25 people and banks
280 person-weeks every autumn.

Three fixes came out of this. The forager policy builds a granary at
population 15. A hard winter halves foraging but only cuts hunting and fishing
by a quarter, so a village with a spear and a net has something to eat. And
starvation became rationing: everyone eats the same reduced share and hunger
accumulates as a fraction of a week, so deaths still happen but the population
gets time to respond.

## Collapse 2: a chief that will not plant while hungry

The first farmer policy had a rule that sounded prudent: if the village is
hungry in spring, keep everyone on food gathering and skip planting. It
guarantees a famine in autumn.

<figure class="chart">
  <img src="/charts/wind-spirit/collapse-hunger-block.svg" alt="Two panels for one village over 70 years. Population under both policies climbs from 20 to 88 by year 49, then both crash: the current farmer falls to 37 and recovers to 75 by year 70, the legacy farmer falls to zero within the year. The harvest bars show the legacy farmer harvesting nothing after year 49.">
  <figcaption>Seed farm-3, one village, yearly. Identical until the stores run out at the end of the winter of year 49.</figcaption>
</figure>

For 49 years the two runs are the same village. It grows to 88 people on 55
cleared plots, more than those plots can feed, and a poor harvest in year 49
means the stores hit zero in the last weeks of winter. Both chiefs start the
spring of year 50 hungry.

The current farmer plants anyway. It loses half the village to the spring
famine, which is horrible to watch in the weekly trace, but the harvest comes
in and by year 70 it is back to 75 people. The legacy farmer keeps everyone
foraging, fishing and hunting, produces about 60 person-weeks of food a week
for 89 people, harvests nothing, and is gone before the year is out. Across
40 villages, 33 died under the hunger-block rule and 4 under the current
farmer. Planting is the response to hunger, not something to postpone until
you feel better.

## Collapse 3: no plot cap, no rotation, no soil

A farm order runs every week of spring. Without a cap on how many plots to
plant, the farmer plants every cleared plot every year. Each harvest drops a
plot's fertility by 0.15; a fallow season restores 0.05.

<figure class="chart">
  <img src="/charts/wind-spirit/collapse-no-plot-cap.svg" alt="Two panels over 40 years. Mean field fertility under the no-cap farmer falls in a straight line from 1.0 to about 0.05 by year 19; with the plot cap it holds at about 0.94. Harvest bars under no-cap start higher, around 800 person-weeks, but fall below the capped farmer by year 10 and settle near 90.">
  <figcaption>Seed farm-0, one village. Mean fertility of cleared plots and yearly harvest, with and without the plot cap.</figcaption>
</figure>

For the first eight years the no-cap farmer looks like the better chief: it
harvests 800 person-weeks a year against 450. Then fertility crosses 0.5
around year 10, harvests fall below the capped farmer, and by year 19 the soil
is at its floor and every harvest is about 90 person-weeks from 55 plots. It
never recovers, because the policy never stops planting.

The fix: a farm order carries a plot count, the policy asks for half the
cleared plots, and the sim plants the most fertile plots first. That gives a
one-in-two rotation for free and fertility settles at 0.94. Nothing in the
game tells a chief about fallow. A curious chief will notice rested plots
recover, or the spirit will tell it. That is exactly the kind of knowledge the
spirit is supposed to trade for trust.

## Collapse 4: the demographic spiral

The slowest and hardest to see. Births were gated on "calm weeks": any hunger
at all reset the counter and stopped births. And adults worked from 15 to 55.

<figure class="chart">
  <img src="/charts/wind-spirit/collapse-demographic.svg" alt="Two stacked-area panels of one village by life stage over 100 years. Under legacy rules the village slides from 20 to about 14 by year 25, drops to 6 by year 30, limps along under 10 and dies in year 67. Under current rules the same village grows to 55, with children roughly half the population.">
  <figcaption>Seed f20-4, one village, yearly. Left: the legacy birth gate and a 15 to 55 working life. Right: the current rules.</figcaption>
</figure>

Mild winter hunger happened every year, so births ran below replacement every
year. Meanwhile the short working life meant that by year 15 a typical village
had sixteen children and four elders resting on nine adults. Four workers
feeding ten people cannot bank a winter, which makes the hunger worse, which
stops more births. The village in the chart takes 67 years to die and never
looks dramatic in any single year.

The fix has two parts. Births now scale with a 25-week moving average of the
shortfall and stop only when the village has been about 40% short on average:
a smooth Malthusian regulator rather than a switch. And adulthood is 14 to 60.
The age change alone moved forager survival from 78% to 93%, which surprised
me more than anything else here.

## The stages, one fix at a time

The legacy switches let me replay the tuning history as a single chart:
forager villages of 20, 100 years, 40 villages per stage, adding one fix at a
time in the order the lessons were learned.

<figure class="chart">
  <img src="/charts/wind-spirit/tuning-stages.svg" alt="Bar chart of forager survival at 100 years across six stages: 18% with every legacy rule, 72% after adding a granary, 50% after switching starvation to rationing, 68% after births scale with hardship, 85% after adults work 14 to 60, 92% after hard winter spares hunting and fishing.">
  <figcaption>Each bar adds one change to the one before it. The dashed line is the suite's 90% target.</figcaption>
</figure>

Two honest notes. The "every legacy rule" bar is a reconstruction: the sim
never actually ran with all five broken rules at once, so 18% is what the
worst version would have done rather than what it did. And rationing on its
own made things worse, 72% down to 50%. Sharing the shortfall meant everybody
was a little hungry every winter, and the birth gate of the time stopped
births on any hunger at all. The starvation fix exposed the birth model. That
is the harness doing its job: a change that is obviously right in isolation
had a side effect I would have argued about for an hour and been wrong.

## The calibrated ladder

With all the fixes in, here is what the suite measures.

<figure class="chart">
  <img src="/charts/wind-spirit/ladder-forager.svg" alt="Line chart over 100 years: median forager village starting at 20 climbs to about 47 with a 10 to 90 percent band; a village starting at 50 falls to about 42 within 15 years and stays there.">
  <figcaption>Forager policy, 40 villages each. Median village with the 10 to 90% band; dead villages count as zero.</figcaption>
</figure>

A village of 20 grows for forty years and settles around 45 to 50, the
wild-food ceiling the concept asked for. A village of 50 loses a fifth of its
people in fifteen years and sits at about 42. Both curves end in the same
place, which is the point: on wild food the land, not the starting population,
decides the size. 92% of villages of 20 survive the century.

<figure class="chart">
  <img src="/charts/wind-spirit/farmer-150y.svg" alt="Two panels over 150 years for the farmer policy. Median village population rises from 20 to about 70 by year 60 and plateaus near 60 to 70 with a wide band. Stacked food by source shows forage, hunting and fishing flat at about 2,000 person-weeks a year while farming adds about 1,500 on top from year 40.">
  <figcaption>Farmer policy (farm and build, never expand), 40 villages over 150 years.</figcaption>
</figure>

Farming lifts the median village to 60 or 70 and the best villages to about
110, then it stops, because one tile has only so many plots and the policy
does not know about irrigation yet. Wild food stays flat at about 2,000
person-weeks a year while the fields add 1,500 on top. Hunger is 46% of
deaths, which is high on purpose: a village that cannot expand is supposed to
feel the ceiling.

<figure class="chart">
  <img src="/charts/wind-spirit/sensible-300y.svg" alt="Two panels over 300 years for the sensible policy. World population rises from 80 to about 5,400 along an S-curve; villages alive stays at 4 until year 40 then climbs to about 122 by year 300.">
  <figcaption>Sensible policy (farm, explore, colonize), 10 seeds, median with the 10 to 90% band.</figcaption>
</figure>

Sensible chiefs colonize. The first colony lands at a median of year 43, and
by year 300 a 64 by 64 world has about 120 living villages and 5,400 people,
with 700 to 950 tiles of path worn between them. Every seed persists. Growth
is about 1.3% a year, and the flattening at the end is the map filling up.
That is the intended pressure, and it says larger worlds or slower growth will
matter once the map is on a screen.

<figure class="chart">
  <img src="/charts/wind-spirit/sensible-deaths.svg" alt="Stacked area of deaths per year by cause over 300 years under the sensible policy: age deaths rise smoothly to about 130 a year, hunger deaths are spiky and rise to about 80 a year, travel deaths are negligible. Hunger is 41% of all deaths.">
  <figcaption>World-wide deaths per year, median across 10 seeds.</figcaption>
</figure>

Even with room to expand, hunger is 41% of deaths. The spikes are hard winters
and droughts hitting many villages at once. I'm fine with that for now: the
spirit sees the weather four seasons ahead, and those spikes are the moments
where a whispered warning is worth trust.

## What the balancer taught me about the game

None of this is new to anyone who has built an ecological model, but I had to
learn each one from a trace of a village dying.

- **Storage is the first survival technology.** Fresh food cannot build
  stores. Summer surplus is wasted and every winter is a shortfall until
  something slows spoilage. The granary is the difference between 42% and 72%
  survival.
- **Starvation is rationing, not selection.** Killing the unlucky few while
  everyone else eats produces cliffs. Sharing the shortfall produces slopes,
  and slopes give a chief time to act.
- **Births regulate before deaths do.** A birth gate that trips on any hunger
  shrinks a population for decades without anyone noticing. A regulator tied
  to average hardship gives a Malthusian curve instead of a spiral.
- **Working life sets the ceiling.** The ratio of workers to mouths is the
  most sensitive number in the sim. Six years of adult life moved survival by
  fifteen points.
- **Farming needs rotation.** Without a plot cap the soil is gone in twenty
  years and nobody notices until the harvest is a tenth of what it was. Chiefs
  will need to learn this or be told, and being told is the game.
- **Never let hunger block planting.** The prudent-sounding rule is the fatal
  one. Planting is the response to hunger.

One more, about the process: the sim pushed back on almost every rule I
wrote, and the failures were legible. I would not have found the demographic
spiral by watching a map, because nothing dramatic happens in any single year.

## What's next

The harness is now the sim's permanent regression test; it runs on every
commit. On top of it, in order: the tech tree generator with its obfuscated
names and hints, so villages have something to discover; the LLM chief, which
gets the same view the scripted policies get, including expected yield per
food source each season; and then, finally, a screen.

I expect the LLM chiefs to find new ways to collapse that the scripted
policies never did. When they do, the trace will be waiting.
