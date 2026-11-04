---
description: Animate a branded card into a feed-ready loop (master MP4 + LinkedIn GIF)
argument-hint: "[config.json | brief] [--remotion|--quick]"
---

Use the **visual-motion** skill.

1. Resolve the config (or map the brief to one via the visual-pipeline format catalog).
2. Require the design stage: `python3 "${CLAUDE_PLUGIN_ROOT:-.}/scripts/storyboard.py" init <config>` if none exists,
   and do not render until the thesis and timing are filled in.
3. Check the GIF budget BEFORE rendering: `python3 "${CLAUDE_PLUGIN_ROOT:-.}/scripts/motion-check.py" budget ...`.
4. Render: `bash "${CLAUDE_PLUGIN_ROOT:-.}/scripts/animate.sh" <config> <base> <outdir>` (Remotion, frame-accurate)
   or `render.sh` with `motion: true` for the quick Playwright path.
5. Assert the loop seam: `python3 "${CLAUDE_PLUGIN_ROOT:-.}/scripts/motion-check.py" seam --video <mp4>`.
6. Run Taste Loop B with the storyboard's motion rules folded into the artifact gates.
7. Report: MP4 is the video post, the PNG is its custom thumbnail (frame 0 is empty),
   the GIF is for comments and DMs.

$ARGUMENTS
