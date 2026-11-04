---
description: Build a social visual from a brief or a config, gate it, taste-loop it, ship it.
argument-hint: "[brief text | path/to/config.json] [--carousel|--motion|--remotion]"
---

Run the `visual-pipeline` skill for: $ARGUMENTS

Follow its loop in order and do not skip a step:

1. Resolve the input to a config. If the input is a brief, map it to a format and confirm the
   honest-data call before building. Fact-check the core claim against a primary source.
2. Pick `format`, `theme` and `motion`.
3. Render with `"${CLAUDE_PLUGIN_ROOT:-.}/scripts/render.sh"` (or `"${CLAUDE_PLUGIN_ROOT:-.}/scripts/animate.sh"` when Remotion is requested).
4. Read the resulting PNG and taste-loop it through all three lenses until it converges.
   Show only the converged result.
5. Report which file is the deliverable and how it should be posted.

If no `brand.json` exists yet, stop and tell the user to copy `brand.example.json` first.
