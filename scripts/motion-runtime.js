// Shared seekable animation runtime for LinkedIn visuals.
// Deterministic: record.js and Remotion's Card.tsx both seek window.render(t)
// per frame (no wall-clock). Elements opt in via data attributes:
//   data-s / data-d                      fade + rise (start & duration, ms; d defaults 600)
//   data-count [data-suffix] [data-dec]  count a number 0 -> value (also fades/rises)
//   data-wipe                            animate width 0% -> 100% (bar reveal; no fade)
//   data-fx="left|right|scale|pop|unroll|type|blur"  named entrance instead of the default rise
//   data-out [data-outd]                 fade back out (start & duration, ms; outd defaults 380)
//   #slide-1[data-return="reverse"]      data-out plays each entrance BACKWARDS to its own start
//                                        state (rise sinks, left slides back, a pen un-draws)
//                                        instead of a flat fade. Frame N == frame 0 either way.
//   data-live="start,end"                hold-life: a small pulse while the card holds, so the
//                                        hold is never frozen; settles to rest by `end`
//   data-morph-to="#id" data-morph="start,end"   the element changes shape into #id's box
//                                        (GSAP Flip), a faint ghost stays where it began,
//                                        then it returns home by `end`
//
// data-out exists for the loop seam. A build-up ends fully lit while frame 0 is
// empty, so a looping post jumps on every repeat; dissolving back to the opening
// state makes the last frame equal the first, which motion-check.py seam asserts.
//
// The choreography lives here; the ENGINE is supplied by the host as window.gsap
// (record.js addScriptTag, Card.tsx import). Keeping 72KB of vendored library out
// of the card document matters: gate.sh greps every literal hex in the HTML it is
// handed, and animate.sh hands it the motion build. Inlining GSAP would drown that
// check in a library's own colour constants.
(function () {
  var tl = null;
  // One element the timeline targets, kept so we can tell whether the markup the
  // timeline was built against is still the markup on screen.
  var sentinel = null;

  // Signature easing: decelerate on entrance, zero overshoot. That is the
  // Corporate motion personality in che-motion-design, and what the house rules
  // mean by banning spring and bounce. Replaces easeOutExpo, whose snap reads as
  // the Energetic archetype.
  //
  // GSAP core does NOT parse "cubic-bezier(...)" strings: gsap.parseEase returns
  // undefined and the tween silently falls back to the default, so writing the
  // MD3 curve literally would have been a comment, not an ease. power2.out is
  // cubic, and at the midpoint it lands on 0.875 against MD3 standard
  // (0.2,0,0,1) at 0.878, inside 0.3%, with no CustomEase plugin to load.
  var EASE_IN_VIEW = "power2.out";
  // Exits accelerate away, and run shorter than entrances: viewers care about
  // what appears, not what leaves.
  var EASE_OUT_VIEW = "power1.in";
  var RISE_PX = 18;

  function countText(el, v) {
    var dec = el.dataset.dec ? +el.dataset.dec : 1;
    return v.toFixed(dec) + (el.dataset.suffix || "");
  }

  // Per-card easing. A card may carry data-ease="x1,y1,x2,y2" on its root to use a
  // MEASURED curve (e.g. the aimindset grammar 0.2,0.8,0.2,1) instead of the house
  // default. GSAP core ignores "cubic-bezier(...)" strings (see above), but it
  // accepts a FUNCTION as an ease, so we solve the bezier here: no plugin, no
  // change to record.js or Remotion. Newton steps with a bisection fallback.
  function bezierEase(x1, y1, x2, y2) {
    function a(p1, p2) { return 1 - 3 * p2 + 3 * p1; }
    function b(p1, p2) { return 3 * p2 - 6 * p1; }
    function c(p1) { return 3 * p1; }
    function calc(t, p1, p2) { return ((a(p1, p2) * t + b(p1, p2)) * t + c(p1)) * t; }
    function slope(t, p1, p2) { return 3 * a(p1, p2) * t * t + 2 * b(p1, p2) * t + c(p1); }
    function tForX(x) {
      var t = x;
      for (var i = 0; i < 8; i++) {
        var s = slope(t, x1, x2);
        if (Math.abs(s) < 1e-6) break;
        t -= (calc(t, x1, x2) - x) / s;
      }
      if (t < 0 || t > 1 || Math.abs(calc(t, x1, x2) - x) > 1e-4) {
        var lo = 0, hi = 1; t = x;
        for (var j = 0; j < 30; j++) {
          var v = calc(t, x1, x2);
          if (Math.abs(v - x) < 1e-6) break;
          if (v < x) lo = t; else hi = t;
          t = (lo + hi) / 2;
        }
      }
      return t;
    }
    return function (x) { return x <= 0 ? 0 : x >= 1 ? 1 : calc(tForX(x), y1, y2); };
  }
  // Exposed for the self-check only (motion-runtime has no other public surface).
  window.__bezierEase = bezierEase;

  function build() {
    var gsap = window.gsap;
    if (!gsap) {
      // Fail loud. A silently missing engine renders every frame as the empty
      // pre-animation state, which looks like a Remotion bug rather than a
      // wiring bug and cost real debugging the last time it happened.
      throw new Error("motion-runtime: window.gsap is missing. The host must provide it.");
    }
    gsap.ticker.lagSmoothing(0);

    var root = document.querySelector("[data-ease]");
    var ease = EASE_IN_VIEW, rise = RISE_PX;
    if (root) {
      var q = root.dataset.ease.split(",").map(Number);
      if (q.length !== 4 || q.some(isNaN)) {
        throw new Error("motion-runtime: data-ease must be four numbers x1,y1,x2,y2, got " + root.dataset.ease);
      }
      ease = bezierEase(q[0], q[1], q[2], q[3]);
      if (root.dataset.rise) rise = +root.dataset.rise;
    }

    // Named entrances (data-fx). Every one starts from opacity 0 or a fully
    // clipped box, so frame 0 stays identical to the dissolved last frame and
    // the loop seam holds. "rise" is the default and needs no attribute.
    // The start state of each entrance, which a reverse exit returns to.
    var FROM = {
      rise:   { opacity: 0, y: rise },
      left:   { opacity: 0, x: -40 },
      right:  { opacity: 0, x: 40 },
      scale:  { opacity: 0, scale: 0.96 },
      pop:    { opacity: 0, scale: 0.9 },
      unroll: { clipPath: "inset(0% 0% 100% 0%)" },
      type:   { clipPath: "inset(0% 100% 0% 0%)" },
      blur:   { opacity: 0, filter: "blur(6px)" }
    };
    var FX = {
      left:   function (t, el, s, d, e) { t.fromTo(el, { opacity: 0, x: -40 }, { opacity: 1, x: 0, duration: d, ease: e }, s); },
      right:  function (t, el, s, d, e) { t.fromTo(el, { opacity: 0, x: 40 }, { opacity: 1, x: 0, duration: d, ease: e }, s); },
      scale:  function (t, el, s, d, e) { t.fromTo(el, { opacity: 0, scale: 0.96 }, { opacity: 1, scale: 1, duration: d, ease: e }, s); },
      pop:    function (t, el, s, d, e) {
        t.fromTo(el, { opacity: 0, scale: 0.9 }, { opacity: 1, scale: 1.03, duration: d * 0.6, ease: e }, s);
        t.to(el, { scale: 1, duration: d * 0.4, ease: e }, s + d * 0.6);
      },
      unroll: function (t, el, s, d, e) {
        t.fromTo(el, { opacity: 1, clipPath: "inset(0% 0% 100% 0%)" },
                     { opacity: 1, clipPath: "inset(0% 0% 0% 0%)", duration: d, ease: e }, s);
      },
      type:   function (t, el, s, d) {
        t.fromTo(el, { opacity: 1, clipPath: "inset(0% 100% 0% 0%)" },
                     { opacity: 1, clipPath: "inset(0% 0% 0% 0%)", duration: d, ease: "steps(" + Math.max(4, Math.round(d * 30)) + ")" }, s);
      },
      blur:   function (t, el, s, d, e) { t.fromTo(el, { opacity: 0, filter: "blur(6px)" }, { opacity: 1, filter: "blur(0px)", duration: d, ease: e }, s); }
    };
    var slide = document.getElementById("slide-1");
    var reverse = !!(slide && slide.dataset.return === "reverse");

    // Morph geometry is measured BEFORE any tween exists: a fromTo renders its
    // from-state immediately (scale 0.9 on a pop), and measuring after that gives
    // Flip a wrong origin box.
    var morphs = [];
    document.querySelectorAll("[data-morph-to]").forEach(function (el) {
      if (!window.Flip) throw new Error("motion-runtime: data-morph-to needs window.Flip (record.js injects it)");
      gsap.registerPlugin(window.Flip);
      var target = document.querySelector(el.dataset.morphTo);
      if (!target) throw new Error("motion-runtime: data-morph-to " + el.dataset.morphTo + " not found");
      var win = el.dataset.morph.split(",").map(Number);
      // The FLYER is a copy on the slide root, so no ancestor (overflow, clip-path,
      // stacking) can hide it mid-flight; the original dims to 0.3 and IS the ghost.
      var host = document.getElementById("slide-1") || document.body;
      var fly = el.cloneNode(true);
      Array.prototype.slice.call(fly.attributes).forEach(function (a) {
        if (a.name.indexOf("data-") === 0 || a.name === "id") fly.removeAttribute(a.name);
      });
      var er = el.getBoundingClientRect(), hr = host.getBoundingClientRect();
      fly.style.cssText += ";position:absolute;margin:0;z-index:5;pointer-events:none;opacity:0;" +
        "box-sizing:border-box;left:" + (er.left - hr.left) + "px;top:" + (er.top - hr.top) +
        "px;width:" + er.width + "px;height:" + er.height + "px;";
      host.appendChild(fly);
      var vars = window.Flip.fit(fly, target, { scale: true, getVars: true });
      morphs.push({ el: el, vars: vars, fly: fly, s: win[0] / 1000, e: win[1] / 1000 });
    });

    var t = gsap.timeline({ paused: true });
    // A timeline with no children has zero duration, and seeking it is a no-op.
    // Give it a floor so an empty card still seeks cleanly instead of throwing.
    t.set({}, {}, 0);

    sentinel = document.querySelector("[data-s]");
    document.querySelectorAll("[data-s]").forEach(function (el) {
      var start = +el.dataset.s / 1000;
      var dur = +(el.dataset.d || 600) / 1000;

      // The wipe IS the reveal, so it must also clear the opacity:0 that the
      // motion CSS puts on every [data-s]. Without it the bar stayed
      // permanently invisible in both renderers.
      if ("draw" in el.dataset) {
        // A pen drawing an SVG path at CONSTANT speed (ease "none": a mechanical
        // pen, not a flourish). Optional data-tip="#id" moves a marker along the
        // path head; a child .ring in that marker pulses while the pen moves.
        var len = el.getTotalLength();
        el.style.strokeDasharray = len + " " + len;
        // Visibility flips ON only at the start time. Putting opacity:1 in the
        // from-vars made GSAP render it at t=0 (immediateRender), and the dash
        // boundary left a 1x2 px sliver at the path's start on frame 0, which the
        // closing frame (dissolved) does not have: a real loop-seam break.
        t.set(el, { opacity: 1 }, start);
        t.fromTo(el, { strokeDashoffset: len },
                     { strokeDashoffset: 0, duration: dur, ease: "none" }, start);
        if (el.dataset.tip) {
          var tip = document.querySelector(el.dataset.tip);
          if (!tip) throw new Error("motion-runtime: data-tip " + el.dataset.tip + " not found");
          var place = function (pr) {
            var pt = el.getPointAtLength(len * pr);
            tip.setAttribute("transform", "translate(" + pt.x + " " + pt.y + ")");
          };
          var drive = { p: 0 };
          t.fromTo(drive, { p: 0 }, { p: 1, duration: dur, ease: "none",
                   onUpdate: function () { place(drive.p); } }, start);
          t.fromTo(tip, { opacity: 0 }, { opacity: 1, duration: 0.12 }, start);
          t.to(tip, { opacity: 0, duration: 0.2 }, start + dur);
          var ring = tip.querySelector(".ring");
          if (ring) {
            var beats = Math.max(1, Math.floor(dur / 0.9));
            t.fromTo(ring, { attr: { r: 0 }, opacity: 0.6 },
                           { attr: { r: 15 }, opacity: 0, duration: 0.9, ease: "none",
                             repeat: beats - 1 }, start);
          }
        }
      } else if ("wipe" in el.dataset) {
        t.fromTo(el, { width: "0%", opacity: 1 },
                     { width: "100%", opacity: 1, duration: dur, ease: ease }, start);
      } else if (el.dataset.fx && el.dataset.fx !== "rise") {
        var fx = FX[el.dataset.fx];
        if (!fx) throw new Error("motion-runtime: unknown data-fx " + el.dataset.fx + " (known: rise, " + Object.keys(FX).join(", ") + ")");
        fx(t, el, start, dur, ease);
      } else {
        t.fromTo(el, { opacity: 0, y: rise },
                     { opacity: 1, y: 0, duration: dur, ease: ease }, start);

        if ("count" in el.dataset) {
          var proxy = { v: 0 };
          el.textContent = countText(el, 0);
          t.to(proxy, {
            v: parseFloat(el.dataset.count), duration: dur, ease: ease,
            onUpdate: function () { el.textContent = countText(el, proxy.v); }
          }, start);
        }
      }

      // Optional dissolve back to the opening state, so the loop seam holds.
      if ("out" in el.dataset) {
        var od = +(el.dataset.outd || 380) / 1000, os = +el.dataset.out / 1000;
        if (reverse && "draw" in el.dataset) {
          // The pen un-draws, then hides: a dash boundary left visible is a 1x2 px seam break.
          t.to(el, { strokeDashoffset: el.getTotalLength(), duration: od, ease: EASE_OUT_VIEW }, os);
          t.set(el, { opacity: 0 }, os + od);
        } else if (reverse && "wipe" in el.dataset) {
          t.to(el, { width: "0%", duration: od, ease: EASE_OUT_VIEW }, os);
        } else if (reverse) {
          var from = FROM[el.dataset.fx || "rise"];
          t.to(el, Object.assign({ duration: od, ease: EASE_OUT_VIEW }, from), os);
        } else {
          t.to(el, { opacity: 0, duration: od, ease: EASE_OUT_VIEW }, os);
        }
      }
    });

    // Hold-life: an even number of yoyo halves ends exactly at rest.
    document.querySelectorAll("[data-live]").forEach(function (el) {
      var w = el.dataset.live.split(",").map(Number), a = w[0] / 1000, b = w[1] / 1000;
      var beat = 0.9, n = Math.floor((b - a) / beat);
      if (n < 1) return;
      // A ring spreading off the accent, the same pulse the pen tip wears. It ends
      // fully transparent, so the hold's last frame is pixel-identical to rest.
      var c = getComputedStyle(el).backgroundColor.match(/\d+/g).slice(0, 3).join(",");
      t.fromTo(el, { boxShadow: "0 0 0 0px rgba(" + c + ",0.75)" },
                   { boxShadow: "0 0 0 16px rgba(" + c + ",0)", duration: beat, ease: "power1.out",
                     repeat: n - 1 }, a);
      t.set(el, { boxShadow: "none" }, a + n * beat);
    });

    morphs.forEach(function (m) {
      var go = Math.min(0.7, (m.e - m.s) / 3);
      t.set(m.fly, { opacity: 1 }, m.s);
      t.set(m.el, { opacity: 0.3 }, m.s);
      t.to(m.fly, Object.assign({}, m.vars, { duration: go, ease: ease }), m.s);
      t.to(m.fly, { x: 0, y: 0, scaleX: 1, scaleY: 1, duration: go, ease: ease }, m.e - go);
      t.set(m.fly, { opacity: 0 }, m.e);
      t.set(m.el, { opacity: 1 }, m.e);
    });
    return t;
  }

  // Seek to an absolute time. Events stay ON: the count-up writes its text from
  // an onUpdate, and suppressing events would freeze every counter at zero.
  //
  // The timeline is rebuilt whenever the markup it targets has been replaced.
  // Remotion reuses a browser tab across frames and React re-injects the card
  // body, so a timeline cached across that boundary animates DETACHED nodes
  // while the elements actually on screen keep the CSS opacity:0 they start
  // with. That renders a perfectly valid, perfectly empty video, and it passes
  // a loop-seam check because empty equals empty. A single-frame `remotion
  // still` never reproduces it, and neither does the Playwright recorder, which
  // mounts exactly once.
  window.render = function (ms) {
    if (!tl || !sentinel || !sentinel.isConnected) {
      if (tl) tl.kill();
      tl = build();
    }
    tl.time(Math.max(0, +ms || 0) / 1000);
  };
})();
