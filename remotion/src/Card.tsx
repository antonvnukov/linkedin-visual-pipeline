import React, { useEffect, useRef, useState } from "react";
import { gsap } from "gsap";
import {
  AbsoluteFill,
  continueRender,
  delayRender,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

/**
 * Renders a card built by the static pipeline, animated by Remotion.
 *
 * The Python builders emit `--motion` HTML that carries BOTH halves of the
 * animation: the timing contract as data attributes (data-s / data-d /
 * data-count / data-wipe) and the runtime that drives them, inlined as a
 * <script> (scripts/motion-runtime.js). Scripts injected via innerHTML never
 * execute, so this component extracts that exact script from the document,
 * runs it, and seeks its `window.render(t)` per frame — the recorder and
 * Remotion animate with literally the same code, and a new card format gets a
 * Remotion animation with no React work.
 */

export type CardProps = {
  /** file in remotion/public/, written by scripts/animate.sh */
  htmlFile: string;
  width: number;
  height: number;
  durationMs: number;
};

/** Pull <style> blocks, body markup and the embedded runtime out of a built document. */
const splitDocument = (doc: string) => {
  const styles = [...doc.matchAll(/<style[^>]*>([\s\S]*?)<\/style>/gi)]
    .map((m) => m[1])
    .join("\n");
  const body = doc.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
  const runtime = [...doc.matchAll(/<script[^>]*>([\s\S]*?)<\/script>/gi)]
    .map((m) => m[1])
    .join("\n");
  return { styles, body: body ? body[1] : doc, runtime };
};

export const Card: React.FC<CardProps> = ({ htmlFile }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const hostRef = useRef<HTMLDivElement>(null);
  const [doc, setDoc] = useState<{ styles: string; body: string; runtime: string } | null>(
    null
  );
  const [handle] = useState(() => delayRender(`loading ${htmlFile}`));

  useEffect(() => {
    fetch(staticFile(htmlFile))
      .then((r) => {
        if (!r.ok) throw new Error(`${htmlFile}: HTTP ${r.status}`);
        return r.text();
      })
      .then((text) => setDoc(splitDocument(text)))
      .catch((err) => {
        // Fail loud: a silently empty composition looks like a Remotion bug.
        throw new Error(`Card could not load ${htmlFile}: ${(err as Error).message}`);
      });
  }, [htmlFile]);

  // Fonts, in a SEPARATE effect, because this one only runs after React has
  // committed the <style> block that carries the @import. Awaiting
  // document.fonts.ready in the fetch chain above resolved against an EMPTY
  // pending set, since the stylesheet did not exist yet, so continueRender fired
  // while Space Grotesk was still downloading and Remotion captured an unknown
  // number of frames in the fallback face. Measured on the flow card: 155 of 156
  // frames disagreed with frame 0 across the static window chrome, which no
  // element animates. It looks exactly like the header jittering on every loop.
  // The Playwright recorder never showed it because it waits on networkidle plus
  // an explicit font delay.
  useEffect(() => {
    if (!doc) return;
    const family = /font-family:\s*'([^']+)'/.exec(doc.styles)?.[1];
    const weights = [...doc.styles.matchAll(/wght@([\d;]+)/g)]
      .flatMap((m) => m[1].split(";"))
      .filter(Boolean);
    if (!family) {
      continueRender(handle);
      return;
    }
    const wanted = (weights.length ? weights : ["400", "700"]).map(
      (w) => `${w} 16px "${family}"`
    );

    // Poll rather than await once. The @font-face rules arrive through an
    // @import inside the injected <style>, which is a SECOND async hop, so on a
    // cold tab document.fonts.load() matches no face yet and resolves instantly
    // against an empty set. That left frame 0 rendered in the fallback face
    // while frames 1..N used Space Grotesk, and it reproduced on roughly every
    // other render, which is what made it look like flaky encoder noise instead
    // of a font race. document.fonts.check() only reports true once the face is
    // genuinely usable, so poll that.
    let stop = false;
    const deadline = performance.now() + 15000;
    const settle = () => {
      if (stop) return;
      Promise.all(wanted.map((f) => document.fonts.load(f).catch(() => {})))
        .then(() => document.fonts.ready)
        .then(() => {
          if (stop) return;
          if (wanted.every((f) => document.fonts.check(f))) return continueRender(handle);
          // Never hang the render on a font: a fallback face is bad, a stuck
          // render is worse. Give up loudly rather than silently.
          if (performance.now() > deadline) {
            console.warn(`Card: ${family} never loaded; rendering in a fallback face`);
            return continueRender(handle);
          }
          setTimeout(settle, 100);
        })
        .catch(() => continueRender(handle));
    };
    settle();
    return () => {
      stop = true;
    };
  }, [doc, handle]);

  // Execute the runtime the document itself carries (it defines window.render).
  // The document carries the choreography; the ENGINE comes from here, so the
  // gated card HTML never contains vendored library source. record.js injects
  // the same build via addScriptTag, which is what keeps the two renderers
  // frame-identical. Must be assigned BEFORE the runtime's first seek.
  useEffect(() => {
    if (!doc) return;
    if (!doc.runtime.trim()) {
      // Fail loud: without the runtime the video would be a silent still.
      throw new Error(`${htmlFile} carries no motion runtime — build it with --motion`);
    }
    (window as unknown as { gsap: typeof gsap }).gsap = gsap;
    new Function(doc.runtime)();
  }, [doc, htmlFile]);

  // Seek on every frame. Remotion renders frames out of order across threads,
  // so window.render(t) must stay a pure function of t, never incremental.
  useEffect(() => {
    if (hostRef.current && doc) {
      (window as { render?: (t: number) => void }).render?.((frame / fps) * 1000);
    }
  }, [frame, fps, doc]);

  return (
    <AbsoluteFill style={{ background: "transparent" }}>
      {doc ? (
        <>
          <style dangerouslySetInnerHTML={{ __html: doc.styles }} />
          <div ref={hostRef} dangerouslySetInnerHTML={{ __html: doc.body }} />
        </>
      ) : null}
    </AbsoluteFill>
  );
};
