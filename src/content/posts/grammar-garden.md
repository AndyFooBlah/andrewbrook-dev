---
title: 'Grammar Garden: evolving plants from tiny recipes, thirty years later'
description: >-
  A Saturday-night return to L-systems: a browser game where plants grow from
  a few rewrite rules, fall over if they can't hold themselves up, and get bred
  by bees and butterflies under two different climates. I wrote no code.
date: 2026-09-06
repos:
  - grammar-garden
draft: false
tags:
  - simulation
  - agents
  - complexity
---

![A garden after 750 ticks: a dry, sunny climate on the left, a rainy one on the right, woody shrubs with pink flowers, and a bee at work](/images/grammar-garden.jpg)

*Tick 750 of a run with the default settings. Play it at
[andyfooblah.github.io/grammar-garden](https://andyfooblah.github.io/grammar-garden/);
the code is on [GitHub](https://github.com/AndyFooBlah/grammar-garden).*

## Where this came from

In the mid-to-late 90s I took a class where we learned about L-systems and
production grammars, and how a handful of rewrite rules could mimic biological
geometry. A classmate and I built a project to simulate different grammars,
drawing the results as simple green lines on a black screen. For the writeup we
put photographs of leaves next to the grammar rules that generated similar
shapes, especially the branching of the veins. It was a little startling how
few rules it took.

I've been fascinated ever since by systems where simple rules, iterated many
times, produce complex results. The natural world is full of them, but it's not
easy to build an intuition for how they behave, because the interesting part is
what happens over thousands of steps, not what any single rule says. As an
undergrad and in grad school in the late 90s I read everything I could find on
chaos and complexity theory, and when Wolfram's *A New Kind of Science* came
out in 2002 it added more ideas (and some great illustrations) to the pile.

Then, for a long time, not much. Even a small simulation takes hours or days
to code up, and my visualization skills are limited, so the ideas stayed on
the shelf for the better part of three decades.

What changed is the cost. With coding agents, building a simulation is cheap
enough that I can pick these topics up again on a whim. Last night (a Saturday)
I decided it would be fun to revisit L-systems and make something slightly more
elaborate: L-systems plus selective pressure, to see whether plants would
evolve different forms.

## What I asked for

I wrote a couple of paragraphs describing how I wanted the simulation to work.
Every plant would have a recipe: a start symbol `A` and a set of rewrite
rules. Capital letters are variables that get replaced each step; lower-case
letters drive a pen. `f` moves forward drawing a line, `l` and `r` turn by
fifteen degrees, `+` and `-` double or halve the step, `g` and `w` switch the
pen to green tissue or wood, and `y` and `p` place a yellow or pink flower.
This one is a woody trunk with pink flowering side shoots:

```
A=wf[lB][rB]wfA
B=gf[lgf][rgf]p
```

The field starts as a row of seeds. When it rains, the recipes run one step at
a time and the plants grow as lines. Then the physics kicks in: a plant
collapses if its lines cross, if a green stem is holding up more plant than it
can bear, or if it grows into the dirt. When the sun comes out, bees visit
yellow flowers and butterflies visit pink ones, carrying a recipe from one
plant to the next. When a bug arrives carrying pollen, the two recipes are
combined (roughly half the rules from each parent), a few random copying
mistakes are added, and a new seed drops.

That's the whole idea. Simple rules, iterated, plus something that kills the
recipes that don't work.

## What Claude did

Claude read the description and came back in about ten minutes with a game
summary and a design. It suggested a few things I'd forgotten or hadn't
thought of, most usefully the `[` and `]` bracket notation for branches (the
standard L-system convention, which I'd let slip in thirty years), flowers as
dots rather than colored lines, and a load-based rule for the wood: every
segment is asked how much plant it's holding up, and green snaps past a
threshold while wood holds far more. I said yes to all of it.

About an hour after my first message there was a working game deployed to
GitHub Pages, with unit tests, save and load, synthesized sound effects, and
a recipe editor with a live preview. I found exactly one minor UI bug.

Then I played it for a couple of hours, staying up later than I should have,
and kept sending feedback. Each round was a paragraph or two from me and a
deployed change from Claude:

- The plants needed an **energy balance**. Sunlight now falls in narrow
  columns; each green segment catches half of what reaches it and passes half
  down, wood blocks everything, and the shade is drawn on the sky and dirt.
  Wood and flowers cost energy every tick; a plant that runs out starves.
- The field needed **two climates**. The left and right halves now have their
  own rain, soil that soaks and dries, and a water need per plant that green
  and flowers drive up. In a dry climate, thirst is what kills you. Bugs only
  work where the sun is out.
- "Who is winning?" needed a better answer than exact-recipe matching once
  mutations were common, so recipes are now clustered into **families** by
  edit distance, and every plant is sorted into grass, herb, bush, shrub or
  tree from its height, width and woodiness, with a chart of the mix over
  time.
- A **family tree** back four generations, a bigger world with pan and zoom,
  mutations that can invent a new letter or duplicate a rule under a new name
  (gene duplication, more or less), seeds that fall near their parents, a
  softer rain sound. And so on.

I wrote exactly zero code. Claude handled the design, the code, the tests,
the deployment, and the balance tuning, which it did by running the
simulation headless for thousands of ticks across several random seeds and
adjusting the numbers until both climates stayed alive. I gave a handful of
paragraph-sized inputs and some minor bits of feedback, and Claude did the
rest. I then wrote a sketch of this post and Claude fleshed it out. After some
light edits, this is also now live.

## What the garden taught me

The most interesting moments were the ones where the simulation pushed back.

Trees kept disappearing. Under a harsh desert on one side and a rainforest on
the other, the population drifted over a couple of thousand ticks toward small
flowery grass and bushes, and the woody plants vanished. The reasons were
legible once Claude traced them: on the dry side, big leafy plants died of
thirst; on the wet side, where they would have thrived, almost nothing was
born, because bugs only fly in sunshine and the wet side is sunny a fifth of
the time. The rainforest had plenty of plants and no pollinators. That's not a
bug in the code; it's a consequence of a rule I wrote, and it took a
simulation to show me.

Flowers, it turns out, are the whole game. Bugs choose plants in proportion to
how many flowers they have, so the recipes that win are the ones that put out
the most flowers they can afford. Everything else, height, wood, canopy width,
is negotiated against that.

And the numbers matter more than the rules. Almost every parameter I set by
instinct was wrong by a factor of two or three in one direction or another,
and the difference between "a garden" and "a wasteland" was usually one
constant.

None of this is new to anyone who works on ecological or evolutionary models.
But I hadn't felt it since the 90s, and I'd forgotten how much fun it is.

## Why I'm optimistic

This is a very different sort of problem from the ones I solve in my day job,
which lives at the intersection of agents and enterprise data, automating
existing large-scale workflows while keeping security and governance intact.
That work is careful by necessity.

A Saturday-night garden is not careful. It's a toy, built in an evening, that
let me reconnect with ideas I hadn't touched in almost three decades because
the cost of trying them finally dropped below the threshold of a whim. That's
one of the things that makes me optimistic about AI: not just that it does the
work, but that it makes a whole category of curiosity affordable again.

The garden is running now. Go plant something and see what the bugs make of
it.
