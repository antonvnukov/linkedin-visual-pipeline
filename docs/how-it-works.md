# How it works, and why it is built this way

## What this is for

You have something worth posting: a statistic, a comparison, an argument. This turns it into a
visual that looks like it came from one consistent brand, and it refuses to let you ship a
version that is sloppy, off-brand, or overstating its evidence.

It is not a template gallery. The whole design is about a pipeline that **checks its own work
hard enough that you can trust it**, and is cheap enough that those checks actually run every
time instead of being skipped when you are busy.

## The one idea worth understanding

Rigor that costs too much does not happen.

An earlier version of this loop was documented at around 600k tokens per visual. One live run of
this one (session token accounting, 2026-08-07, not committed to the repo) recorded 994,505 tokens
for a single card across two rounds, which is roughly $6 on the top tier and roughly $3.20 routed.
That is one observed data point, not a benchmark. So the honest position is that the full protocol is not cheap; what the
routing buys is roughly half, and what pushing checks into code buys is that the other twenty-odd
assertions cost nothing and therefore always run.

So the pipeline is split along a single line: **anything a computer can decide is code, and
only genuine judgment pays for a model.** Code is free, so it runs on every artifact forever
and no one ever has to weigh whether it is worth it. That is why the QA gate has seven
assertions instead of three, why the claims ledger is arithmetic instead of a rule in a
document, and why two of the three critic-gate layers are static files.

---

## Stage 1 — Brief to config

**In:** a rough brief, or a JSON config.
**Out:** a validated config naming a format, a theme, and the content.
**Runs on:** Haiku at low effort, then validated by code.

**Why a config and not freehand HTML.** Hand-authored HTML has nothing for a gate to hold onto:
no declared format, no separable content, no way to re-render after a fix. Every downstream
stage here (gate, claims, loop, motion) exists because the artifact is *structured*. The moment
you hand-write a card, you have opted out of all of it, which is why the skill says to extend a
builder instead.

**Why the cheap model.** This is schema-constrained extraction, and code validates the result
immediately afterwards. There is nothing here worth paying a reasoning model for.

## Stage 2 — Brand resolution

**In:** `brand.json`.
**Out:** every colour, typeface, and footer value the builders will use.
**Runs on:** code. Free.

**Why one file.** This plugin exists because of a specific bug. A service-brand font was the
*default* on the light theme in the system this grew out of, so it quietly appeared in months
of personal-brand renders that were never meant to carry it. Nobody chose that; it was just
what the default was.

So there is exactly one place a brand is defined, nothing else may name a colour or a font, and
a builder containing a literal hex is treated as a bug rather than a shortcut. The failure mode
being designed out is not "wrong colour" but "a default nobody chose."

## Stage 3 — Render

**In:** config plus brand.
**Out:** HTML, then PNG, PDF, or MP4.
**Runs on:** code (Python, Playwright, ffmpeg). Free.

**Why HTML instead of a drawing library.** Real typography. `text-wrap: balance` on headlines,
proper font loading and weight selection, real layout. A drawing library gets you boxes and
baselines and you rebuild text layout badly. It also means the exact same markup can be
animated later without a second implementation.

## Stage 4 — The QA gate

**In:** the built HTML.
**Out:** pass or fail, plus a review bundle, in an immutable checksummed directory.
**Runs on:** code. Free, therefore always on.

Seven assertions: artboard dimensions, images actually loaded, the **computed** font per weight
in use, allowed and forbidden colours, text escaping the artboard, ancestor clipping, plus
manifest checks for required text, forbidden text, occurrence counts and geometry.

**Why it fails instead of warning.** A gate that warns is a gate that gets scrolled past. If a
check is not worth failing on, it should not be a check.

**Why it is strictly separate from taste.** These are all questions with objectively correct
answers. Mixing them with judgment makes both worse: the mechanical checks become negotiable,
and the taste review wastes its attention on things a script already knows.

**Why the review bundle.** It renders a `feed-preview.png` at the real feed width, because a
card judged at full size is judged at a size no reader will ever see. The human and the critic
then look at identical evidence.

Two of these assertions have already earned their place. `images-loaded` catches a broken
avatar that a human notices only by looking carefully. `font-loaded` is exactly the check that
would have caught the original font leak, and it is now the regression test for it.

## Stage 5 — The claims ledger

**In:** the config.
**Out:** a per-claim record of what each figure is and where it came from.
**Runs on:** Haiku to draft, code to enforce. Effectively free.

Every figure gets an id, a classification, a source, and a cap on how many times it may appear
prominently.

**Why the occurrence cap.** The same statistic rendered twice reads as two independent
findings. That is a quiet way to overstate evidence, and it is invisible when you are staring
at a layout you have been tuning for an hour. The cap is enforced by counting rendered strings,
so it is arithmetic, not intention.

**Why a generated draft cannot satisfy it.** Every generated claim lands as `unverified` and
the check fails while any remain. If a model could both write and satisfy the ledger, the
ledger would be theatre. A human has to say where each number came from.

## Stage 6 — Taste Loop B

**In:** a frozen candidate plus its evidence bundle.
**Out:** a verdict per numbered gate, and eventually a shipped version.
**Runs on:** the calibrated critic tier, at high effort. The one irreducible cost.

**What "taste" means here, since the word is overloaded.** It is a review *protocol* — freeze,
checksum, brief blind critics against numbered gates, iterate, ship the best-graded version. It
is not the [taste-skill](https://github.com/leonxlnx/taste-skill) pack, which is an anti-slop
framework for web interfaces and is neither loaded nor vendored by this plugin. The judgement
criteria are the `gates/` files, written for a fixed canvas someone scrolls past in a feed.

**Why the candidate is frozen and checksummed.** The critic verifies the SHA-256 before
reviewing. Otherwise a review can silently be of bytes that have since changed, and you get a
verdict that describes nothing that exists.

**Why the critic is blind.** No source, no prior candidates, no earlier verdicts, no chat
history. A reviewer who has seen the last three rounds is anchored to them and starts grading
the delta instead of the artifact.

**Why numbered gates instead of open critique.** Open critique produces plausible prose. Gates
produce PASS or FAIL per numbered item, which is checkable and comparable across rounds.

**Why gates come in three layers.** Hand-writing twelve bespoke gates per artifact is the right
quality bar and the wrong ergonomics: nobody does it twice, so the protocol dies. Base gates
(every artifact) and format gates (per format) are static files, written once and free forever.
Only three to six artifact-specific gates are generated per run. A typical brief is thirteen
gates of which twelve cost nothing.

**Why the best-graded candidate ships, not the last one.** A final-round fix can make things
worse. Keeping the highest-scoring version means an unlucky last edit cannot regress what you
ship.

**Why it escalates after two stalled rounds.** If a cheaper reviewer is going in circles, that
is the signal that the judgment is genuinely hard, which is the only case where the expensive
tier is worth its price.

## Stage 7 — Motion

**In:** config, storyboard, timing.
**Out:** master MP4, poster PNG, budget-compliant GIF.
**Runs on:** code for the checks, Sonnet to draft a storyboard.

**Why a storyboard is required rather than suggested.** Motion fails in time, and a screenshot
cannot show it. Authoring the timing as a document costs one paragraph; discovering it through
render cycles costs six. `animate.sh` refuses without one, because "we will tune it once we see
it" is how that happens.

**Why one timing contract feeds two renderers.** The builders emit four data attributes and
both Playwright and Remotion consume them, so a new card format gets an animation for free with
no React written. The contract is documented rather than implied because it has already caused
a real bug: `data-wipe` returned early without clearing the `opacity: 0` that the motion CSS
sets on every animated element, so the bar in every animated bar card was permanently
invisible, in both renderers, silently.

**Why the GIF has a pixel budget.** LinkedIn caps a GIF by width times height times frames,
plus file size. Over the cap it is re-encoded to mush or rejected. It is checked before
rendering, and when it fails it reports the frame ceiling at your current dimensions, so the
fix is arithmetic rather than another guess.

**Why frame 0 must equal the closing hold.** A loop that ends one pixel from where it started
jumps on every repeat, and in a feed that repeat is constant. It is a pixel comparison, not an
opinion.

## Stage 8 — Handoff and ship

**Why gated output only.** Pushing a card into Paper or Figma keeps it editable, which is
genuinely useful. Authoring one *inside* those tools skips the palette check, the claims ledger
and the loop entirely. The handoff is a final-tuning layer, never a generator.

**Why a single frame ships as a PNG.** A one-page PDF is not a carousel, and LinkedIn treats it
differently and worse.

**Why a video needs the PNG as its custom thumbnail.** Frame 0 is the empty pre-animation
state, so a video without a custom cover previews as a blank card in the feed.

---

## What this deliberately does not do

- **Generated imagery.** No photoreal, illustration, or text-inside-image generation. This
  renders typographic, data-driven cards from structured config. Those are different problems
  with different tools.
- **Copywriting.** It will not invent your hook. It checks that the words you chose are honest,
  legible, and on-brand.
- **Posting.** Nothing here touches an API that publishes. The last step is always a human.
- **Rescuing a bad idea.** A card that clears every gate can still be worth nothing to read.
  The pipeline guarantees craft and honesty. It cannot supply a point.
