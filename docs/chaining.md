# Chaining: where the words come from

This plugin renders a visual. It does not decide what to say. That is deliberate, and it is
why `README.md` closes with "what it does not do: generated imagery, copywriting, or posting."

Most people arrive here with a post already drafted. This page documents the seam so a content
pipeline and this one compose cleanly, **without either depending on the other**.

## Why this is a chain, not a dependency

A content stack (audience research, voice capture, content pillars, copywriting) produces
**words**. This plugin produces a **picture**. Nothing in `brandkit.py`, `qa-visual.cjs`,
`gates.py`, or any builder calls a content skill, or could: a bar card needs a figure, a
headline, a source and a takeaway. It does not need to know your ideal customer profile.

Wiring them as a hard dependency would be actively harmful:

- It inverts this plugin's stated scope boundary.
- It makes a stranger build an audience profile and a voice profile before they can render a
  chart, turning a five-minute tool into a multi-hour onboarding.
- Content stacks have their own internal dependencies, so requiring one imports a whole second
  tree that this repo would then have to ship and keep working.

Keep the sequence in your own harness (a chain file, a runbook, a habit). Keep the seam here.

## The seam

The interface is the **config**, not a skill. A finished post carries everything a card needs:

| Post element | Config field | Notes |
|---|---|---|
| The claim in the hook | `headline` | One sentence. The card is not the post; do not paste the hook verbatim if it only works with the body under it. |
| The number the claim rests on | `stat` (+ `stat_count` for motion) | Exactly one hero figure. Two competing figures is a different format. |
| Where the number came from | `source` | Also goes in the claims ledger with a classification. |
| The part-to-whole split | `green_label` / `green_pct`, `gray_label` / `gray_pct` | Must sum to 100. |
| The "so what" line | `note` | Base gate 12: this must add an interpretation the numbers do not state on their own. |
| The window or scope | `pill`, `window_title` | Keep them informative; an eyebrow that says nothing fails base gate 7. |

Everything else (`format`, `theme`, `motion`) is a rendering decision, not content.

## What does not transfer

**Voice does not survive the jump wholesale.** A post has paragraphs, rhythm, and a body that
earns the hook. A card has roughly twelve words of running text. Copy that reads well in a feed
post usually needs cutting, not porting.

**The hook is usually the wrong headline.** A hook is engineered to make someone stop scrolling
into a body. A card headline has to stand alone next to the number. They are different jobs.

**Claims tighten at the boundary.** A post can hedge in a sentence. A card renders one figure
at 140px with no room for a caveat, which is exactly why the claims ledger exists and why the
`publicationBoundary` field is required.

## The one soft input worth wiring

If you maintain a voice profile, the single string it can legitimately sharpen is the
takeaway (`note`) line, because that is copy that renders on the card and base gate 12 already
judges it. An optional `voice` block in `brand.json`, handed to the critic when present, would
give that gate a concrete standard instead of a generic one.

That is an **optional input**, not a required skill. Absent it, the gate still runs.

## Practical order

```
[your content pipeline]  ->  post draft (hook, claim, number, source, takeaway)
                                    |
                                    v
                        map the claim into a config  (see the table above)
                                    |
                                    v
   render -> QA gate -> claims ledger -> Taste Loop B -> [Paper/Figma] -> ship
```

The post and the visual ship together. Neither tool has to know the other exists.
