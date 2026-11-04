# Paper (paper.design) adapter rules

Learned by debugging, not from documentation. Each one cost real time.

- **No rich text.** An inline accent span cannot be a coloured run inside a paragraph.
  Every accent word becomes its own text node.
- **`<img>` needs explicit `width` AND `height`.** Height alone renders at zero width and
  the image silently disappears. This one cost three debug rounds.
- **SVG-as-image-fill does not render.** Any vector mark ships as a rasterized transparent
  PNG. Render it with Playwright and `omitBackground: true`, never `qlmanage`/QuickLook,
  which forces a white background and makes a white wordmark invisible.
- **Never use `margin`.** The tool schema rejects it. Use `gap` or `padding` on the parent,
  even for a one-off divider spacer. This is easy to slip back into.
- **Local JPG and PNG load fine** via `paper-asset:///abs/path`. No conversion needed.
- **Set design tokens once per file** (`create_tokens`): background, surface, border, text,
  accent, font and sizes as CSS variables every later card references. Change the token and
  every card in the file updates.
- **Reuse the existing Paper file.** One file per card multiplies the token setup and loses
  the shared system.
- **Dark background means the dark asset variant, checked every time.** A light-variant image
  loads without any error and simply renders illegible. Treat it as a checklist item for
  every dark card, in every pipeline, not as a thing you will remember.
