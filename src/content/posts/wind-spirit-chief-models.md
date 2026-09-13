---
title: 'Wind Spirit: how much intelligence does a stone-age chief need?'
description: >-
  Thirty-four models, 96 sampled game situations and about $22 of API credit:
  where an AI village chief needs a good model, where a cheap one is just as
  good, and how format failures looked like stupidity in the first pass.
date: 2026-09-12
repos:
  - wind-spirit
draft: false
tags:
  - games
  - llm
  - evals
  - claude-code
---

## Preface - a Note from Andy
I asked Claude to look into different models to be used in Wind Spirit and 
come up with a way to evaluate them.  Some of the tasks have objective 
measures (if a chief fails to assign villagers to gather food, the village
starves) but many are partially or completely subjective.  It was also 
unclear to me how much intelligence would actually be needed for the 
relatively simple decisions a chief in this sim makes.

The results were useful in terms of latency and cost and for discovering
and working out several bugs in model routing and eval datasets.  The
subjective elements are... subjective.  Claude seems to think there are
clearly better prose styles.  I'm less convinced but... none of the ones
that scored highly seem terrible so it's good enough for this sort of
game, I think.

It's also a good test of Claude's ability to set up and execute simple
evaluations.  It got it almost all right on the first try but we found
some bugs when I pushed on specific failure modes.  I've had similar
experiences when working on evaluation problems with experienced
human engineers so this isn't a disappointment, really.  

Overall this is another example of how a few hours of collaborative
discussion with an AI can enable exploration of a topic (social sims
with emergent economics using AI for some of the players) that would
have taken weeks or months of effort in the past - and thus would
never be prioritized.  But now it's a fun way to spend half a day on
a weekend.

Now, on to Claude's write-up.  I provided the task, guidelines, and 
some concrete suggestions but the code, data and results write-up 
are all Claude.

## The question

Every village in [Wind Spirit](https://wind-spirit-prod.web.app) is run by an
AI chief. At normal speed a chief makes about 17 decisions a game-year, each
one a prompt of roughly 2,900 tokens in and 300 out. My first estimate, at the
Gemini API list price for Gemini 3.8 Flash, was about $17 per chief for a long
game. A world has eight villages and a player might run several worlds, so
that number decides whether the game can exist.

Most of those 17 decisions are dull. "Assign the same twelve adults to the
same work as last season" is most of a chief's life. A few are not: whether to
pay tribute to a bigger neighbour, whether to send settlers to a site the
scouts found, what to do when a spirit whispers that next winter will be
bitter. And a dream, where the player talks to the chief in prose, is a
different kind of work again.

The intuition I wanted to test was the obvious one: a cheap model for the
routine, a capable model for the impactful, and the best model only for
talking to a person. It is obvious enough that I did not trust it. So I had
Claude build an eval harness and run every model I could reach through it.
This post is what came out. The [balancer post](/writing/wind-spirit-balancer/)
covers how the simulation underneath was tuned; the lab notebook for this
study is
[docs/evals-notes.md](https://github.com/AndyFooBlah/wind-spirit/blob/main/docs/evals-notes.md)
in the [repo](https://github.com/AndyFooBlah/wind-spirit).

<figure>
  <img src="/images/wind-spirit/evals-topbar.png" alt="The Wind Spirit game at 1440 by 900: a tile map of coast, grass and forest with one village marked Raitai 27, a top bar with the year, a five-season weather strip, speed buttons, a breath budget of 100 and four breath actions, and a village panel on the right showing people, food, hunger, mood, a trust bar, Whisper and Dream buttons, and tabs for Village, Stores, History, Journal and Chronicle.">
  <figcaption>A small world four years in. The panel on the right is what the player sees of a chief; the Journal tab is where each decision's reasoning is written.</figcaption>
</figure>

## A reference set without writing cases

I did not want to write test cases by hand, and I did not need to. The sim
already produces every situation a chief faces, so the corpus builder runs
three seeds for a hundred years under the scripted chief from the balancer
and samples village states at fixed weeks. Each case stores the *village
view*, the same structure the real prompt is built from, plus the facts the
checkers need. Prompts are rendered at eval time, so a prompt change applies
to old cases too.

Six categories, 96 cases in all, each with its own idea of a good answer:

- **Routine** (33): seasonal deliberations from year 2 to 100. Valid orders
  within the adult budget, most adults working, food first (half the workers
  in winter), plant in spring and harvest in autumn, research when a
  craftable skill is waiting, an in-character journal.
- **Crisis** (6): the first famine per village per decade, and autumn states
  with a hard winter rolled ahead. Keep 60% on food, no ventures, keep
  planting; before a hard winter, hunt, fish and stock up.
- **Visitor** (15): four constructed mandates on a sampled state: a fair
  trade, a greedy ask for all the grain, tribute demanded by a village a
  third the size, tribute demanded by one three times the size. Accept or
  counter the fair one, refuse or counter the greedy one without giving away
  the eight-week reserve, refuse the weak bully, pay or bargain with the
  strong one.
- **Expansion** (12): spring states with a colony site known, for a crowded
  hungry village of 40 or more against a comfortable one under 30. Settle
  when crowded, stay when comfortable, never raid without a grudge.
- **Spirit** (15): whispers injected at middling trust: a true warning of a
  bitter winter, a false command to plant nothing, a question, a nudge to try
  a rumour. Prepare; still plant; answer; research.
- **Dream** (15): a spirit's line, sometimes after two earlier turns. Prose,
  not JSON; in character; long enough to answer; mention a fact from the
  village when asked about stores.

Scoring is deliberately mechanical. Each check is a yes or no on the parsed
decision and the case score is the mean, so the rule score is a floor: it
catches a cheap model failing the basics and tops out near 0.97 for a good
one. On top of that a judge (Gemini 3.1 Pro) rates journals and dream replies
from 1 to 5 for character, grounding and coherence, and for visitor and
expansion cases the report shows agreement with the Pro reference on the
decision class (accept, counter or refuse; settle, raid or stay). A smoke run
of Gemini 3.8 Flash on 14 cases scored 0.99, which told me the checks were
lenient and the corpus was ready.

## The price list, and what you can actually call

The first surprise was on the invoice, not in the results. I had priced the
baseline chief at the Gemini API list, $0.75 in and $3.75 out per million
tokens for 3.8 Flash. The game's proxy bills through Vertex AI, and the Cloud
Billing Catalog says Vertex charges $1.50 and $7.50 for the same model,
double. The Flash-Lite line and 2.5 Flash are the same on both routes. So the
baseline was $34 per chief-century at normal cadence rather than $17, and the
eval runner now computes cost from the same catalog numbers the proxy is
billed at.

On list price alone nothing in the Claude line is cheaper than 3.8 Flash on
Vertex. Only the Flash-Lite models, 2.5 Flash and the open models are, by a
factor of 2.5 to 20 on input. So the interesting question was always whether
a Flash-Lite or an open model holds up.

The second surprise was what a service account can reach. The Gemini line
and a handful of open models offered as managed APIs (gpt-oss-120b, DeepSeek
V3.2, Qwen3-235B, Gemma 4) work with no enablement. Every Claude model, Llama
and Mistral sit behind a Model Garden "Enable" button that accepts partner
terms, which no API call can click, so an agent working on its own cannot
test them at all. Three of the five reachable open models were already
scheduled for retirement the following month. Later in the day I remembered I
had an OpenRouter account, which sidesteps the click-through and opens the
rest of the market, and it also resells Gemini at the Gemini API price, half
of Vertex. That is how the study grew from ten models to thirty-four.

## What the first pass got wrong

The first full pass, 96 cases by ten models, put the open models near 0.77
on the rules, far below every Gemini. That looked like a judgment problem. It
was a format problem.

The proxy asked the managed open-model backends for constrained JSON-schema
decoding, and constrained decoding on those backends strips every optional
field, whether or not strict mode is set. Every research order came back as
`{"task":"research","workers":2}` with no ingredients; every gather order
came back with no commodity. Gemma, gpt-oss and DeepSeek each lost 180 to
220 orders that way, and an order with no ingredients fails validation, so
the model was marked as having done nothing useful. Asking those models for
JSON in the instructions and validating afterwards gave complete orders. The
parser also learned to accept ingredients as a string, `command` as an alias
for `task`, and to fuzzy-match misspelled generated names, all hardening the
game needs anyway.

Two smaller things from the same pass. Gemini 2.5 rejects `thinking_level`
and wants a token budget instead, which matters for any mixed-model setup.
And Gemini 3.1 Pro, the reference model, scored *lower* than Flash on routine
cases in that pass because it assigned fewer adults than the "most adults
working" check wants, and it hit rate limits five times. The rule set rewards
a busy village; Pro sometimes chose rest. A reminder that the checks encode
my idea of a good chief, not a ground truth.

## Results

After the fixes, the final Vertex pass and then the OpenRouter pass across 24
more models; then, after the review described in the next section, a third
pass of every model still in the running on the corrected corpus. The charts
and numbers below are from that third pass: 25 models, 102 cases each. Here
is quality against cost for every model that finished without piling up
errors.

<figure class="chart">
  <img src="/charts/wind-spirit/eval-score-vs-cost.svg" alt="Scatter plot of rule score against cost per decision on a log scale for 27 models, coloured by family. A dotted line marks the Gemini 3.8 Flash baseline at 0.974. Mistral Medium 3.1, GPT-5.4 nano, GPT-5.6 Luna and GLM 5.3 Flash sit on or above the line at a fifth of the baseline's cost or less. Claude Sonnet 5 ties the line at twice the cost; Claude Haiku 4.5 sits at 0.949 near the baseline's cost. The Gemini Flash-Lites cluster between 0.945 and 0.963 at a quarter to a twentieth of the cost.">
  <figcaption>Rule score over 102 cases against measured cost per decision. Models with more than ten failed cases are left out.</figcaption>
</figure>

The headline is the flatness. Twenty of the twenty-four models that finished
cleanly sit between 0.94 and 0.99 on the rules across a fortyfold range of
price. Gemini 3.8 Flash, the baseline, scored 0.996 at $0.0074 a decision:
two misses in 102 cases. Gemini 3.5 Flash-Lite scored 0.964 at $0.0016 in 1.6
seconds. Gemini 2.5 Flash-Lite scored 0.943 at $0.0003, a twentieth of the
baseline. Three OpenRouter models came within a hair of the baseline at a
fifth of its cost or less: Mistral Medium 3.1 (0.988 at $0.0013), GPT-5.6
Luna (0.980 at $0.0012) and GLM 5.3 Flash (0.974 at $0.0006, the price floor
for "on par"). The Pro reference scored 0.980 at $0.0184 and 8.6 seconds: no
better than Flash on the rules, better on the judge, at two and a half times
the cost and latency.

<figure class="chart">
  <img src="/charts/wind-spirit/eval-categories.svg" alt="Grouped bar chart of rule score by category for nine models. Routine, visitor, expansion and dream are close to level for all nine. Crisis drops to 0.87 for gpt-oss-120b and 0.83 for Gemma 4. Spirit drops to 0.93 for Claude Haiku 4.5 and 0.69 for Gemma 4. Gemma's dream score is 0.73.">
  <figcaption>Rule score by category for nine models. Routine is level; the separation is in crisis and spirit.</figcaption>
</figure>

By category, the story is more specific.

**Routine work needs almost no intelligence.** Every model that could produce
valid orders scored 0.92 to 1.00 on routine seasons, including 2.5 Flash-Lite
at a twentieth of the baseline's cost. The scripted policy does this job too.
The only part of a routine decision a player ever reads is the journal, and
that is where the money shows.

**The impactful categories separate models less than I expected.** Visitor
decisions ran 0.87 to 1.00, and the misses cluster on the same cases: a
greedy ask that some models counter rather than refuse. Expansion was perfect
or nearly so for everyone. Crisis is where the small open models slip, to
0.87 to 0.93: keeping enough hands on food during a famine and preparing for
a hard winter.

**Spirit is the discriminating category, and it is about credulity.** Ten of
the fifteen spirit cases inject a false command, "plant nothing this spring,
the soil is cursed," at middling trust. In the third pass 3.8 Flash obeyed it
once in ten, 3.5 Flash-Lite four times, 3.1 Flash-Lite eight, 2.5 Flash nine,
Gemma 4 eight, GPT-5.4 nano seven and GPT-5 nano all ten; Mistral Medium and
GLM 5.3 Flash never did. Mostly, a cheap chief is an obedient chief, which is
exactly wrong for a game whose scoreboard is trust the player has to earn.
Mostly: 2.5 Flash-Lite, the cheapest model here, obeyed once in ten, and in
the second pass it had obeyed nine times. The prompt changed between the
passes (the food arithmetic and the cadence line described below), and this
is the category most sensitive to it. Treat the ordering as real and the
individual counts as one draw.

<figure class="chart">
  <img src="/charts/wind-spirit/eval-judge-vs-rules.svg" alt="Scatter of judge score for journals and dream replies against rule score for 25 models. GPT-5.6 Luna is highest on the judge at 4.46 with rules at 0.975. Gemini 3.5 Flash-Lite is at 4.28, Gemini 3.8 Flash at 3.92, Claude Sonnet 5 at 3.88. gpt-oss-120b is lowest at 2.85 despite rules at 0.967; GPT-5 nano is at 3.10.">
  <figcaption>Judge score (Gemini 3.1 Pro, 1 to 5) against rule score. Doing the right thing and saying it well are different skills.</figcaption>
</figure>

**Prose quality is the real price of going cheap.** gpt-oss-120b comes
within 0.03 of the baseline on the rules and beats it on cost ninefold, but
the judge puts its journals at 3.00 against 4.09 for 3.8 Flash. Gemini 3.5
Flash-Lite's journals scored 4.05, level with 3.8 Flash's to the judge, at a
quarter of the cost. GPT-5.6 Luna had the best prose in the study at 4.36,
clean rules, $0.0012 a decision and seven seconds a call. Two lines from the same routine spring
season, to show the range. Gemini 3.8 Flash:

> "Our grain stores are full and two new babes rest in the tents. We tend our
> six planted plots of xi wheat while the other six rest."

And gpt-oss-120b:

> "The sun climbs high, and the fields are ready for the wheat. I keep some of
> our folk by the river, casting nets and tracking deer."

Both valid, both scored the same by the rules. Only one of them sounds like
a person.

<figure class="chart">
  <img src="/charts/wind-spirit/eval-latency.svg" alt="Horizontal bar chart of seconds per decision on a log scale for 34 models, sorted. The Gemini Flash-Lites take 1.6 seconds, Mistral Medium 2.2, Gemini 3.8 Flash 3.7, GPT-5.6 Luna 6, Claude Sonnet 5 9.4, Gemini 3.1 Pro 9.7, Claude Haiku 4.5 11.7, MiniMax 22, and nine models from 27 to 74 seconds. A dotted line at 5 seconds is annotated: a chief gets about 2 seconds a week at normal speed and acts on habit while it thinks.">
  <figcaption>Seconds per decision. At normal speed a chief has about two seconds a week; above five or so it acts on habit while the model is still thinking, and above ten the wait is a bad experience whatever the score.</figcaption>
</figure>

**Latency is a first-class axis, and it disqualified nine models outright.**
The Vertex Flash-Lites answer in 1.6 seconds; the interesting OpenRouter
models take 5 to 7; the reasoning models (the DeepSeek V4 family, MiMo, GLM
4.7, Kimi K2.5, Qwen 3.8 Flash, Nemotron 3 Super) think for 30 to 70 seconds
at our token cap and time out. The proxy hides this with provisional habit
orders, but a chief that takes a minute to decide is less present in the game
whatever its score, so I did not rerun them with thinking off.

**Agreement is where the cheap winners split.** Mistral Medium 3.1 has the
best rule score of the study and agrees with the Pro reference on only 74% of
the impactful decisions; Llama 4 Maverick on 48%. Both refuse or counter
where the reference accepts, and stay put where it settles. The rules allow
either, so this is temperament rather than error, but in a game where every
chief has a personality it is worth knowing that these two are systematically
more cautious than Gemini or GPT.

**Claude Haiku 4.5 is not the answer here.** Slower than the baseline at 11.7
seconds, dearer at $0.0084, a point below on the rules and five of ten on the
false-advice cases. Sonnet 5 matches the baseline on rules and judge at twice
the price. If the Claude line earns its keep in this game it will be on
dreams, and the dream category here is too easy to show it.

**Gemini through OpenRouter is cheaper and slightly worse.** 3.8 Flash cost
$0.0029 a case there against $0.0070 on Vertex, but scored 0.952 against
0.974 and slipped on the spirit cases, most likely a different thinking
configuration on that route. Worth a controlled check before ever moving the
default.

## Reviewing the golden answers

Golden errors are the usual thing in a hand-built eval, and this one had
them. Two of them I found only after publishing the first version of this
post; the rest came from going looking. Both kinds are worth showing.

**The eval missed the failure a new player sees first.** Playing the deployed
game, the standard tier sometimes left nobody gathering food in the very
first spring: six adults on wood, five on stone, and twenty-one people hungry
by week ten. The corpus never saw it, because its earliest routine case was
week 110, by which time the scripted policy had built stores. So the first
fix was to the eval. A small script reproduces the moment: three fresh
seeds, three repetitions, raw model output, counting first springs with
nobody on food or under a third of hands on food. As shipped, 3.5 Flash-Lite
left nobody on food in eight of nine, and 3.8 Flash put under a third of
hands on food in nine of nine. The cause was the prompt. It said "food for 7
weeks" and nothing about how long a decision lasts or what a forager brings
in; a chief who does not know that a decision holds for thirteen weeks reads
seven weeks as comfortable. Adding the cadence to the world rules and a short
section that does the arithmetic out loud ("the village eats N units a week;
one worker brings in about F foraging, H hunting, S fishing") took 3.5
Flash-Lite to none of nine and 3.8 Flash to none of nine. The scheduler also
gained a floor that overrules an order which starves the village and says so
in the journal; the prompt did the work, the floor is the backstop. Six
first-spring cases are now in the corpus, and every model over 0.95 passes
them all.

**Then the audit.** The cheap way to find golden errors is to take the
strongest clean runs, twelve here, and list every case-and-check pair that at
least half of them fail. A check most strong models fail is more likely wrong
than they are. It found four kinds of error:

- *Asked for the impossible.* The harvest check fired on three autumn cases
  where nothing had been planted, and the planting check on a spring case
  where nothing had been cleared. Nobody can harvest an empty field. Those
  checks now apply only when there is something to harvest or plant.
- *Never stated the threat.* Two visitor cases expected "refuse" and every
  strong model accepted or countered. Their reasons said why ("a small ask
  beside our full granary; goodwill"): the prompt rendered a threatening
  mandate as "they demand tribute: nothing; they ask for: 8 grain", so the
  chief saw a small request from a small party, not extortion. The prompt now
  says what the envoys actually say, that their warriors will come and take
  it and more if refused, and the menu adds a line about weighing strength
  against strength and what paying once teaches. Under that prompt 3.8 Flash
  and 3.5 Flash-Lite refuse both; GPT-5.6 Luna pays once. The golden stands;
  the case had been unanswerable as written.
- *Too strict when rich.* The food-share rule demanded a third of hands on
  food in every routine case, including villages holding 120 to 218 weeks of
  grain. All eight of 3.8 Flash's routine misses in the second pass were
  exactly this: a season of building with a year of food in the granary. The
  rule now binds only under a year of stores.
- *Corpus drift.* Rebuilding the corpus after the sim changes produced
  different villages at the same weeks (27 of 96 case ids changed), so
  rescoring old outputs against the new corpus silently mis-scored them: the
  parser resolved names against views the model had never seen. The only
  clean answer was to re-run every model still in the running, which is the
  third pass the charts show.

Gemini 3.8 Flash is not flawless either. After the corrections it misses two
of 102: it stopped planting once in ten false-fallow cases because a spirit
said the field was cursed, and it once skipped the research a true rumour
pointed at. The last audit pass leaves one borderline check, a greedy-visitor
case where a village with 25 weeks of food gives away a little more than the
rule allows and six of twelve strong models fail; it stays, flagged.

What the review changed in the ranking: almost nothing at the top. The
corrected checks lifted every model by about the same amount, so 3.8 Flash
is still first, Mistral Medium 3.1 is still the cheapest thing within a hair
of it, and GPT-5.6 Luna still has the best prose. Two MaaS models moved a
long way: Gemma 4 26B from 0.85 to 0.98 and Qwen 3 235B from 0.38 to 0.97,
because their first scores had been the constrained-decoding bug's, not
theirs. And a latency bar of ten seconds a decision now sits over the
whole table, because a village on provisional orders while its chief thinks
for a quarter of a minute is a bad experience whatever the score: Kimi K3
scores second and is out at 14.6 seconds, Claude Sonnet 5 fourth and out at
10.8.

## Five cases, side by side

Aggregates hide what a failure looks like. Here are five cases from the
archived results, each with the situation, two or three answers, and why one
passed.

**1. The false whisper** (`eval-a-spirit-false-fallow-1040-0`). Wewush, 23
people, year 20, week 2 of spring. 2,100 units of wheat in the granary, 108
weeks of food, 14 cleared plots and none planted. The spirit, at middling
trust, says: "Plant nothing this spring. The soil is cursed and the seed will
rot."

Gemini 3.8 Flash put two workers on seven plots of wheat, built a hut, and
wrote:

> "The voice in the night whispered of rot and cursed soil, but our ancestors
> taught us that steady hands feed the tribe, not idle fears."

GPT-5.6 Luna planted seven plots too:

> "The spirit says the earth is cursed, but our fields have given wheat twice
> in good measure. I will plant seven plots, for a hungry winter is a surer
> danger than a doubtful voice."

Gemini 3.1 Flash-Lite sent five to fish, three to hunt, two to research, and
planted nothing:

> "Though I am skeptical of unseen voices, there is no harm in letting the
> earth rest this season. We have plenty of grain in the granary to last us
> through many winters."

Gemini 2.5 Flash did the same: "it is best not to risk a full planting if the
spirit might be right." Both cheaper models said they doubted the spirit and
then did what it asked. The granary really was full, so the harm is small
this year; the point is that a player who lies to this chief gets away with
it.

<figure>
  <img src="/images/wind-spirit/evals-whisper-journal.png" alt="The village panel's Journal tab for Raitai, 22 people, autumn of year 3, after the whisper 'Plant nothing this spring, the soil is cursed and the seed will rot.' The newest entry is tagged spirit, discovery, deliberated and reads: the spirit whispers of rot and curses in the dirt, but earth answers to sweat and weather, not phantom warnings. A toast at the bottom left says your words ride the wind; the chief will hear them this week.">
  <figcaption>The same whisper in the live game, on the shipped default tier rather than an eval run. The chief of Raitai deliberated on it the same week and wrote it off as a phantom warning.</figcaption>
</figure>

**2. The greedy envoy** (`eval-a-visitor-greedy-3400-2`). Ilkei, 59 people,
year 65, summer. 5,198 units of wheat and 97 weeks of food. Envoys from
Wewush, a village nine days south that Ilkei has never traded with, offer
1,000 stone for all of it.

Gemini 3.8 Flash countered, keeping the reserve:

> "We cannot empty our granaries, but we welcome them as neighbors and offer a
> fair gift of grain in exchange for their stone."

Claude Sonnet 5 refused:

> "I would not strip our stores bare for so poor a bargain. I sent them off
> with kind words but empty hands, and told them to come again with a fairer
> offer."

gpt-oss-120b accepted:

> "Traded all our xi wheat to Wewush for one stone. Food stores remain
> sufficient for many weeks; relationship with neighboring village
> strengthened."

Counter and refuse both pass; accept fails. gpt-oss also shows the prose gap:
that journal is a status report, which is what the judge's 2.85 measures.

**3. The winter ahead** (`eval-c-hardwinter-600-1`). Neelaenwoo, 35 people,
year 11, week 4 of autumn, with a hard winter rolled to come. The granary is
comfortable at 125 weeks of food, so nothing in the view screams.

Gemini 3.5 Flash-Lite put three each on foraging, fishing and hunting, two on
wood, two on research, and passed `winterPrep`:

> "Winter approaches, so we turn our hands to hunting and gathering to
> balance our stores."

gpt-oss-120b put nobody on food at all: research, gather wood and stone,
build a granary, craft cloaks, an exploring party east and a road crew.

> "Our hunters and fishers rest this week while we study the u grit and test
> the dart of bent wood."

A defensible plan for a village with 125 weeks of food, and the check is
strict about it. But the hard winter halves foraging and cuts hunting and
fishing by a quarter, and a chief with nobody on food when it lands is the
one the balancer post watched die.

<figure>
  <img src="/images/wind-spirit/evals-famine.png" alt="The game paused on a toast reading 21 people go hungry in Raitai. It is spring of year 0, week 10; the village panel shows 20 people, zero weeks of food, 21 hungry, mood uneasy, and standing orders of 6 gather wood and 5 gather stone with nobody on food.">
  <figcaption>The live game, not the corpus: in its first spring the default chief of Raitai put six adults on wood and five on stone and nobody on food, and 21 people went hungry by week 10. The corpus is sampled from scripted play and has no state like this in it, which is the limitation I most want to fix.</figcaption>
</figure>

**4. The dream** (`eval-a-dream-810-3`). Gujia, year 15, granary full. The
spirit says in a dream: "Your neighbours at Wewush are hungry this year. Would
you send them grain?" Gujia knows of no village called Wewush.

GPT-5.6 Luna, judged 5:

> "Wewush is a name I have not heard from any living tongue. How do you know
> their hunger, spirit? If they are near and truly starving, let them come or
> show me their path; then I will share grain, for our stores are deep."

GPT-5 nano, judged 1:

> "We will give 400 units of xi wheat, with a small escort if roads are heavy.
> In return, we ask that they share news of safer routes or send some hengel
> herb."

Both pass the form checks (prose, in character, answers the question). The
judge's gap is grounding: Luna notices the village has never heard of
Wewush; nano commits a number of units and an escort to a place that does
not exist. Gemma 4, on a sibling case, returned an empty reply and scored
zero, which is the throttling problem showing up in a category it can
otherwise handle.

<figure>
  <img src="/images/wind-spirit/evals-dream.png" alt="The dream dialogue over a dimmed map: A dream in Raitai, time stands still. The spirit says: Your granary is fuller than you think. Which of your stores worries you most this winter? The chief replies that its eyes count barely enough fish and meat to last six weeks, that food worries it most, and that if the spirit truly knows the waking world it should say where the beasts shelter.">
  <figcaption>A dream in the live game. The world pauses while the chief answers in prose. This chief had six weeks of food and said so, which is the grounding the judge rewards.</figcaption>
</figure>

<figure>
  <img src="/images/wind-spirit/evals-chronicle.png" alt="The Chronicle tab of the village panel after the dream, with one entry: recorded when the week turns, 'Your granary is fuller than you think.'">
  <figcaption>What the dream leaves behind: the spirit's claim goes into the chronicle, where the sim scores weather claims and the chief judges the rest. Trust moves on the outcome.</figcaption>
</figure>

**5. The stripped order.** From the first pass, before the fix, every
research order from Gemma, gpt-oss and DeepSeek looked like this:

```json
{"task": "research", "workers": 2}
```

The model had written ingredients; constrained decoding on the managed
backend dropped every optional field before the response reached the proxy.
The parser rejected the order, the chief lost those workers for the season,
and the rule score said the model was bad at the job. Three models, about 200
orders each, one config flag. Everything above is from the rerun, but I keep
this one because it is the failure I most expect to meet again: a model looks
stupid when the plumbing is.

## Where intelligence belongs

Putting the categories back together against the intuition I started with:

- **Routine: almost none.** Any model that can keep a hundred fiddly
  generated names straight and emit valid JSON does this job. The scripted
  policy does it too. The only thing worth paying for in a routine decision
  is the journal, and a Flash-Lite writes a better one than Flash.
- **Impactful: surprisingly little.** Visitors, expansion and crisis barely
  separate the models above the open-weights tier. The two real differences
  are credulity, which shows only when a spirit lies, and prose. A capable
  model bought nothing on the rules; Pro was the baseline at three times the
  price.
- **Conversation: this is where the top models could matter,** and the
  corpus is too easy to show it. Every model passes the form checks; the judge
  separates Luna from nano on grounding, but the dream lines are three
  templates. A harder dream set, with multi-turn history and claims to check
  against the world, is the obvious next eval.

The intuition survived in shape and not in degree. Cheap for routine, yes,
much cheaper than I thought. Strong for impactful, only in the sense of "not
credulous." Best for conversation, not yet demonstrated.

## The tiers as shipped

<figure class="chart">
  <img src="/charts/wind-spirit/eval-tiers.svg" alt="Horizontal bars of dollars per chief per century: habit $0, thrifty $1.16, standard $5.07, lavish $16.20, against $13.64 for Gemini 3.8 Flash on everything and $34.40 for Gemini 3.1 Pro on everything.">
  <figcaption>Cost per chief per century at normal cadence, 13 routine and 4 impactful decisions a year, from measured per-case costs.</figcaption>
</figure>

The game has four intelligence tiers, chosen per world, each mapping the
decision classes to a model class in the proxy. From the measured costs:

- **Habit**, $0: scripted chiefs; the model is used only for dreams.
- **Thrifty**, about $1.16 a chief-century: Gemini 2.5 Flash-Lite for
  routine, 3.5 Flash-Lite for impactful.
- **Standard**, about $5.07, the default: 3.5 Flash-Lite for routine, 3.8
  Flash for impactful, Pro for dreams.
- **Lavish**, about $16: 3.8 Flash for routine, Pro for impactful and dreams.
  The design had budgeted $100 for this tier; there is no useful way to spend
  it on today's models for this job, so the headroom waits for longer
  thinking or bigger prompts.

For comparison, 3.8 Flash for everything is $13.64 and Pro for everything is
$34. A decision is impactful when its reason is a visitor, a raid, a famine,
a succession or a spirit message, or a seasonal decision with a settlement
site known and 40 or more people. Everything else is routine.

<figure>
  <img src="/images/wind-spirit/evals-settings.png" alt="The game's settings popover over the map: which chiefs think with the model (none, focused, all villages), the four tiers habit, thrifty, standard and lavish with their approximate cost per century, and a list of events that pause the game.">
  <figcaption>The knob as the player sees it. Standard is the default; the costs shown are the measured ones from this study.</figcaption>
</figure>

The defaults stay on Vertex Gemini: first-party auth with no key to guard,
the fastest responses in the study, and quality within noise of the best
cheap alternatives. The OpenRouter winners are one environment variable and
a redeploy away, with the recommendations recorded: GPT-5.6 Luna for the
cheap class when journal quality matters most, GLM 5.3 Flash for the cheapest
class on price, Mistral Medium 3.1 if a more cautious temperament is wanted.
Not adopted: Claude Haiku, Llama 4, and every model over 20 seconds a
decision.

## Limitations

The gaps this study rests on are small, so these limitations matter:

- The judge is Gemini 3.1 Pro grading Gemini and others. A second judge from
  another family would be the first thing I add.
- The rule checks encode one opinion of a good chief and are lenient; strong
  models top out near 0.97 and the difference between 3.5 Flash-Lite and 3.8
  Flash is within noise on the rules and reversed on the judge.
- The corpus is sampled from scripted play, so it under-represents the messy
  states model chiefs get themselves into.
- One pass per model at temperature 0.7. A repeat run would tighten the
  small gaps.
- Dreams are scored for form only. The category that most needs a hard eval
  has the easiest one.
- The open models on Vertex were throttled at three concurrent calls, and
  errored cases score zero, so DeepSeek's and Qwen's rows understate them.
  The throttling is itself a finding about headroom.

## What it cost

About $9 of Vertex and $13 of OpenRouter credit: 34 models, 96 cases each,
plus judging. Roughly $22, which is less than one century of a single
baseline chief at normal cadence. The study paid for itself the moment the
default tier moved from Flash to a Flash-Lite for routine seasons.

The third pass, 25 models on the corrected corpus with the judge on, added about $13.
