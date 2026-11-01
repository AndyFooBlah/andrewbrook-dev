---
title: 'Five years of one view: timelapses from casual phone photos'
description: >-
  Turning several years of handheld, unplanned photos of a hilltop vista into
  four timelapses, ordered by date and by the height of the sun, with music
  made in Suno. Who did what, and roughly how long it took.
date: 2026-10-31
repos:
  - handheld-timelapse
draft: false
tags:
  - photography
  - video
  - music
  - claude-code
---

## Preface - a Note from Andy

I like to go for frequent walks and runs and many of them pass a hilltop vista
looking East over San Francisco Bay to the Diablo Range beyond. For several years I've been
stopping to take a picture of the view, thinking I might do something with
them one day. They were casual phone shots: facing slightly different directions,
different zooms, standing a few steps left or right of last time, in whatever light
there was. Pre-dawn, midday, fog, sunset.

When I finally decided to turn them into timelapses, that casualness became
the problem. The photos weren't aligned, the lighting was wildly different from
one to the next, and they were mixed in with thousands of other pictures:
people, pets, other nearby scenes. So before there was any video there was a list
of chores: find the right photos, filter out the ones with people in them,
line them up, crop them, choose one per day, and decide what order to put them
in. Then I wanted music, which meant learning to get Suno to write what I had
in my head.

Below is Claude's write-up of how that went. The code and the write-up are
Claude's; the photos, the ideas for the variants, the taste calls and the
music brief are mine, plus some light editing of the prompts; Suno generated
the music itself.

## The problem with casual photos

A timelapse is normally shot from a tripod: same position, same lens, same
exposure, one frame every few seconds. These photos have none of that. Across
five years there are wide-angle and telephoto shots, two standing spots a few
metres apart (one framed by an oak, one open), and lighting from starlit
pre-dawn to midday haze. Each of those differences, left alone, turns into
flicker and jitter on screen.

The work was in seven steps.

1. **Finding them.** The candidates came out of the photo library by location:
   everything taken near the spot, about 2,000 items. Andy chose to export
   them by hand from Photos rather than give Claude access to his whole disk,
   so the pipeline only ever saw that one folder.
2. **Filtering.** The camera's compass heading weeds out photos facing the
   wrong way, though not reliably (front-camera headings turned out to be
   meaningless). The real test is whether a photo matches the view at all,
   which threw out selfies, pets and other nearby scenes.
3. **Aligning.** Each photo is matched to a reference shot using learned
   feature matching, and warped so the horizon, ridgeline and buildings land
   in the same place. Photos that couldn't match the reference directly, like
   pre-dawn shots with almost no detail, were matched to an aligned neighbour
   from the same morning and chained through it. That took the usable set from
   about 300 photos to about 800.
4. **Locking the ridge.** For the tight crop of the distant bay and hills, small
   alignment errors are magnified, so the crop is locked to the profile of the
   far ridgeline (Andy's idea). Frames where cloud hides the ridge, or an oak
   branch drifts into the sky, are dropped.
5. **Removing people.** A segmentation model finds people in every photo. The
   "without people" versions drop any frame where someone shows up in the
   crop. It needed two passes at different scales: one finds distant walkers,
   the other close-up faces that fill the frame.
6. **Choosing and evening out.** Where there are several shots on one day, the
   best is chosen by how sharp it is, how well exposed, and how clearly the
   ridge shows. Then the brightness is evened out from frame to frame, so the
   video changes with the seasons instead of flickering with each exposure.
7. **Ordering.** Two orders: by date, so you watch the seasons and years go by,
   and by the height of the sun, which Andy suggested. That one ignores the
   calendar and runs from pre-dawn darkness with city lights, through sunrise
   and midday, to evening, with dates jumbled. Sun height works better than
   "minutes since sunrise", because day length changes by hours over the year.

## The music

Andy wanted classical music, with something like Vivaldi for the sun-height
versions: quiet at first, rising to something awake and exuberant. For the
date versions he wanted something flowing and changing. Italian Baroque fits
both moods: dawn energy, and Vivaldi has form when it comes to seasons. There's
also a Buddhist temple near the vista, so Andy asked whether a Japanese
Buddhist colour could join the Baroque: temple bell, shakuhachi, koto.

Getting Suno to do that took some learning:

- **No composer names.** Suno blocks artist names in prompts, so "Vivaldi" had
  to become a description: Italian Baroque concerto, solo violin, rushing runs,
  harpsichord.
- **One prompt box.** The tutorials describe separate style and structure
  boxes; the current interface has a single prompt. Structure had to be written
  as prose ("opens almost in silence… just past halfway it breaks into a bright
  Allegro").
- **Structure is a suggestion.** Suno blends a prompt into one overall sound
  rather than following it in order. Asked for a temple bell and then violins,
  it opened with violins every time. Generating the opening as its own short
  track and extending it with a second prompt is the workaround.

Andy generated takes from the Baroque-only and temple-and-koto prompts, then
blended them into one track per video. Claude can't listen to music. It
measured the tracks instead and found they're full-voiced from the first bars,
with no quiet-to-loud arc to land the sunrise on. So the photos are spread
evenly over each track, and each video is exactly as long as its music.

## The four videos

**The bay at sunrise.** The distant bay and hills, ordered by the height of
the sun.

<div class="video"><iframe src="https://www.youtube-nocookie.com/embed/bMdZtu_sQAA" title="The bay at sunrise: timelapse ordered by the height of the sun" loading="lazy" allow="encrypted-media; picture-in-picture; fullscreen" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe></div>

**The whole view at sunrise.** The full vista, same order.

<div class="video four-three"><iframe src="https://www.youtube-nocookie.com/embed/q0LIyEFSFxg" title="The whole view at sunrise: timelapse ordered by the height of the sun" loading="lazy" allow="encrypted-media; picture-in-picture; fullscreen" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe></div>

**The bay through the years.** The tight crop in date order.

<div class="video"><iframe src="https://www.youtube-nocookie.com/embed/ptUxP_SEx7U" title="The bay through the years: timelapse in date order" loading="lazy" allow="encrypted-media; picture-in-picture; fullscreen" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe></div>

**The whole view through the years.** The full vista in date order.

<div class="video four-three"><iframe src="https://www.youtube-nocookie.com/embed/v-OLdfaz6d4" title="The whole view through the years: timelapse in date order" loading="lazy" allow="encrypted-media; picture-in-picture; fullscreen" referrerpolicy="strict-origin-when-cross-origin" allowfullscreen></iframe></div>

## Who did what, and how long it took

<div class="table-scroll">

| | Andy | Claude | Suno |
|---|---|---|---|
| Photos | Took them, on walks and runs over five years | | |
| Getting the photos | Picked the area on the Photos map and exported them; chose not to grant disk-wide access | Wrote the location and heading filters | |
| Ideas for the variants | Oak vs open, with and without people, sun-height order, the tight bay crop, locking to the ridgeline | Sun elevation rather than minutes from sunrise; which frames to keep for each variant | |
| Alignment, cropping, filtering | Spotted a jumping ridgeline and a frame of a family member that slipped through | All the code and the methods (feature matching, chaining, ridge lock, people detection, frame scoring, deflicker) | |
| Look of the result | Final say on every preview; 4K | Crop shapes, hold and crossfade timing | |
| Music | The brief: classical, Vivaldi-like, flowing; the temple influence; chose and blended the takes | Prompts, and fitting the video to each track | Composed and performed it |

</div>

Andy's time was about **five hours** spread over four sittings in one week. About an hour of that was spent in Suno and maybe half
an hour on the photo export; the rest was answering questions and watching
previews. That doesn't count five years of taking the photos, which happened
on walks he was going on anyway. Claude's sessions ran about five hours of
active work. Unattended runs (alignment, people detection, 4K rendering) added
several more on a laptop GPU.

Claude made most of the technical decisions without asking: which models to
use, how to align, where to set thresholds. It surfaced the ones it was unsure
about with an example to look at. The decisions about what the videos should be
and how they should feel were Andy's. Suno made every musical decision Andy
didn't put in a prompt, which is most of them.

## The code

The scripts are in [handheld-timelapse](https://github.com/AndyFooBlah/handheld-timelapse),
without the photos, their metadata or the location. They expect a folder of
your own photos of one view and a reference shot, and include notes on the
Suno side.
