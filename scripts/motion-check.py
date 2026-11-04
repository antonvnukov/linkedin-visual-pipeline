#!/usr/bin/env python3
"""
motion-check.py — deterministic gates for an animated card.

    python3 motion-check.py budget   --width W --height H --frames N --fps F [--bytes B]
    python3 motion-check.py seam     --video out.mp4 [--tolerance 0]
    python3 motion-check.py seam-frames --dir frames/      # lossless, pre-encode (render.sh)
    python3 motion-check.py excursion   --dir frames/ [--floor-pct 2]
    python3 motion-check.py          # self-check

Two things ruin a looping feed animation, and neither is a matter of taste:

**Budget.** LinkedIn re-encodes or rejects an oversized GIF. The documented
ceiling is a total pixel budget (width x height x frames) plus a file-size cap.
Checked BEFORE rendering, because discovering it after a 3-minute render and an
upload is the expensive way to learn it.

**Seam.** A loop whose last frame differs from its first visibly jumps on every
repeat. Frame 0 and the closing hold must be pixel-identical.

Both are code, so they cost nothing and run on every artifact.
"""
import math, argparse
import pathlib
import shutil
import subprocess
import sys
import tempfile

# LinkedIn's documented GIF ceiling: width * height * frames.
PIXEL_BUDGET = 36_152_320
SIZE_BUDGET = 5 * 1024 * 1024


def check_budget(width, height, frames, fps, size_bytes=None):
    """Return (ok, problems, facts). Pure arithmetic, safe to run before rendering."""
    problems = []
    pixels = width * height * frames
    facts = {
        "dimensions": f"{width}x{height}",
        "frames": frames,
        "fps": fps,
        "durationSec": round(frames / fps, 2) if fps else None,
        "pixels": pixels,
        "pixelBudget": PIXEL_BUDGET,
        "pixelUsePct": round(100 * pixels / PIXEL_BUDGET, 1),
    }
    if pixels > PIXEL_BUDGET:
        headroom = PIXEL_BUDGET // (width * height) if width and height else 0
        problems.append(
            f"pixel budget exceeded: {width}x{height}x{frames} = {pixels:,} > {PIXEL_BUDGET:,}. "
            f"At this size the ceiling is {headroom} frames "
            f"({round(headroom / fps, 2) if fps else '?'}s at {fps}fps); either cut frames, drop fps, or scale down."
        )
    if size_bytes is not None:
        facts["bytes"] = size_bytes
        facts["sizeBudget"] = SIZE_BUDGET
        if size_bytes > SIZE_BUDGET:
            problems.append(
                f"file size {size_bytes / 1024 / 1024:.2f}MB exceeds the {SIZE_BUDGET / 1024 / 1024:.0f}MB cap"
            )
    return (not problems), problems, facts


def gif_spec(width, height, duration_ms, max_fps=15):
    """Largest budget-compliant GIF derivative of a master of these dimensions.

    The pixel budget is a GIF constraint, NOT a master-video constraint. Gating the
    master on it forbids every card the repo ships (a 1080x1080 master is 532% of
    the GIF ceiling), which is how animate.sh came to exit before Remotion ever ran.
    Returns (width, height, fps, frames).
    """
    ar = height / width
    # Prefer FRAME RATE over pixel width. Buying resolution with fps produces an
    # 8fps GIF that reads as broken; the known-good shipped spec was 552x690 @15fps,
    # i.e. roughly half the master's width at full frame rate. Search fps-first.
    for fps in range(max_fps, 9, -1):
        # render.sh encodes frames 0..N-1 (frame N == frame 0, checked losslessly
        # then dropped since 2026-09-28). ffmpeg's fps filter can still emit one frame
        # past ceil(); the +1 keeps the estimate an upper bound. round() under-counted
        # by one and put a 5.2s card at 100.9% of the budget (2026-09-22).
        frames = max(2, math.ceil(duration_ms / 1000 * fps) + 1)
        for w in range(int(width), 199, -8):
            h = int(round(w * ar / 2) * 2)      # even dims: gif/yuv420p encoders want them
            if w * h * frames <= PIXEL_BUDGET:
                return w, h, fps, frames
    raise ValueError("no compliant GIF spec at this aspect ratio and duration")


def _ffmpeg():
    exe = shutil.which("ffmpeg")
    if not exe:
        raise SystemExit("motion-check: ffmpeg not found (brew install ffmpeg)")
    return exe


def _frame_count(video):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
         "-show_entries", "stream=nb_read_frames", "-of", "default=nw=1:nk=1", str(video)],
        capture_output=True, text=True,
    )
    return int(out.stdout.strip() or 0)


def check_seam(video, tolerance=0, max_changed_pct=None):
    """Extract the first and last frames and compare them pixel by pixel.

    `tolerance` gates the PEAK channel delta, which is the strict default and the
    right measure for flat graphics. It is the wrong measure for a text-heavy card:
    frame 0 is an I-frame and the closing frame is a P-frame hundreds of frames
    later, so H.264 residual drift on thin antialiased glyph edges reaches a peak
    delta of ~240 while the animation itself resets exactly. Raising `tolerance`
    far enough to absorb that would also swallow a genuine jump.

    `max_changed_pct` gates AREA instead, which separates the two cleanly: encoder
    drift is a sparse scatter along glyph edges (well under 1% of the frame), while
    a real seam break moves a large contiguous region. Set it only for a lossy
    master, and say so, because it deliberately stops asserting peak fidelity.
    """
    ff = _ffmpeg()
    video = pathlib.Path(video)
    if not video.is_file():
        return False, [f"video not found: {video}"], {}
    n = _frame_count(video)
    if n < 2:
        return False, [f"video has {n} frame(s); a loop needs at least 2"], {"frames": n}

    with tempfile.TemporaryDirectory() as td:
        first = pathlib.Path(td) / "first.png"
        last = pathlib.Path(td) / "last.png"
        subprocess.run([ff, "-y", "-i", str(video), "-vf", "select=eq(n\\,0)",
                        "-vsync", "0", "-frames:v", "1", str(first)],
                       capture_output=True)
        subprocess.run([ff, "-y", "-sseof", "-0.5", "-i", str(video),
                        "-update", "1", "-q:v", "1", str(last)],
                       capture_output=True)
        if not first.is_file() or not last.is_file():
            return False, ["could not extract first/last frames"], {"frames": n}

        try:
            from PIL import Image, ImageChops
        except ImportError:
            # Fall back to an exact byte compare: weaker (encoders differ) but honest.
            same = first.read_bytes() == last.read_bytes()
            return same, ([] if same else ["first and last frames differ (byte compare; install Pillow for a pixel diff)"]), {"frames": n, "method": "bytes"}

        a = Image.open(first).convert("RGB")
        b = Image.open(last).convert("RGB")
        if a.size != b.size:
            return False, [f"frame sizes differ: {a.size} vs {b.size}"], {"frames": n}
        diff = ImageChops.difference(a, b)
        bbox = diff.getbbox()
        max_diff = max(diff.getextrema(), key=lambda t: t[1])[1] if bbox else 0
        lum = diff.convert("L")
        changed = (lum.size[0] * lum.size[1]) - lum.histogram()[0] if bbox else 0
        total = a.size[0] * a.size[1]
        changed_pct = round(100.0 * changed / total, 4) if total else 0.0
        facts = {"frames": n, "method": "pixel", "changedPixels": changed,
                 "maxChannelDelta": max_diff, "size": list(a.size),
                 "changedPct": changed_pct}
        if max_changed_pct is not None:
            facts["gate"] = f"area (max {max_changed_pct}% changed)"
            if changed_pct > max_changed_pct:
                return False, [
                    f"loop seam is not clean: {changed:,} pixel(s) differ between frame 0 and "
                    f"the closing frame ({changed_pct}% of the frame, limit {max_changed_pct}%). "
                    f"The loop will visibly jump on every repeat."
                ], facts
            return True, [], facts
        facts["gate"] = f"peak channel delta (tolerance {tolerance})"
        if max_diff > tolerance:
            return False, [
                f"loop seam is not clean: {changed:,} pixel(s) differ between frame 0 and the "
                f"closing frame (max channel delta {max_diff}, tolerance {tolerance}). "
                f"The loop will visibly jump on every repeat."
            ], facts
        return True, [], facts


def _frames(frames_dir):
    return sorted(pathlib.Path(frames_dir).glob("f*.png"))


def check_seam_frames(frames_dir):
    """Lossless seam: record.js's frame N (t = motion_ms) must equal frame 0 exactly.

    Runs on the PNGs BEFORE encoding, so no H.264 drift to tolerate: tolerance 0.
    render.sh then drops frame N (it is frame 0 again) so the loop never stalls.
    """
    from PIL import Image, ImageChops
    fs = _frames(frames_dir)
    if len(fs) < 2:
        return False, [f"{len(fs)} frame(s) in {frames_dir}; a loop needs at least 2"], {}
    a, b = Image.open(fs[0]).convert("RGB"), Image.open(fs[-1]).convert("RGB")
    bbox = ImageChops.difference(a, b).getbbox()
    facts = {"frames": len(fs), "first": fs[0].name, "last": fs[-1].name, "diffBox": bbox}
    if bbox:
        return False, [f"loop seam is not clean: {fs[-1].name} differs from {fs[0].name} in box {bbox}. "
                       f"motion_ms ends before the animation returns to frame 0."], facts
    return True, [], facts


# Report-only until calibrated on the shipped cards (plan R1, 2026-09-28): a floor
# guessed before measuring would false-fail subtle cards.
EXCURSION_FLOOR_PCT = 2.0


def check_excursion(frames_dir, floor_pct=EXCURSION_FLOOR_PCT, step=3):
    """Largest share of the frame that ever differs from frame 0. ~0 = nothing moves.

    Pairs with the seam check: seam must be 0, excursion must be above a floor.
    """
    from PIL import Image, ImageChops
    fs = _frames(frames_dir)
    if not fs:
        return False, [f"no frames in {frames_dir}"], {}
    a = Image.open(fs[0]).convert("L")
    total = a.size[0] * a.size[1]
    peak, at = 0.0, fs[0].name
    for f in fs[::step]:
        h = ImageChops.difference(a, Image.open(f).convert("L")).histogram()
        pct = 100.0 * (total - h[0]) / total
        if pct > peak:
            peak, at = pct, f.name
    facts = {"excursionPct": round(peak, 2), "peakFrame": at, "floorPct": floor_pct}
    if peak < floor_pct:
        return False, [f"excursion {peak:.2f}% < floor {floor_pct}%: the animation barely moves"], facts
    return True, [], facts


# che-video-brain MOTION.md "Before showing Anton": pixel-change > 0.2% per 1.5s.
DEAD_HOLD_WINDOW_S, DEAD_HOLD_FLOOR_PCT = 1.5, 0.2


def check_dead_hold(frames_dir, fps, window_s=DEAD_HOLD_WINDOW_S, floor_pct=DEAD_HOLD_FLOOR_PCT):
    """Find the stillest window: the one where the least of the frame ever changes.

    A card that builds, then freezes for 3 seconds before the loop, reads as dead in
    the feed. Excursion cannot see that (it takes the max over the whole clip).
    """
    from PIL import Image, ImageChops
    fs = _frames(frames_dir)
    w = max(2, round(window_s * fps))
    if len(fs) <= w:
        return False, [f"{len(fs)} frames is shorter than one {window_s}s window"], {}
    L = [Image.open(f).convert("L") for f in fs]
    total = L[0].size[0] * L[0].size[1]
    worst, at = 100.0, 0
    for i in range(0, len(L) - w, max(1, fps // 2)):
        peak = 0.0
        for j in range(i + 3, i + w + 1, 3):
            h = ImageChops.difference(L[i], L[j]).histogram()
            peak = max(peak, 100.0 * (total - sum(h[:9])) / total)   # ignore <=8-level drift
        if peak < worst:
            worst, at = peak, i
    facts = {"stillestWindowPct": round(worst, 3), "windowStartS": round(at / fps, 2),
             "windowS": window_s, "floorPct": floor_pct}
    if worst < floor_pct:
        return False, [f"dead hold: {window_s}s from {at / fps:.1f}s changes only {worst:.3f}% "
                       f"of the frame (floor {floor_pct}%)"], facts
    return True, [], facts


def _report(ok, problems, facts, label):
    print(f"{label}: {'OK' if ok else 'FAIL'}")
    for k, v in facts.items():
        print(f"  {k}: {v}")
    for p in problems:
        print(f"  - {p}")
    return 0 if ok else 1


def _demo():
    # budget: the real GIF spec from a shipped artifact must pass
    ok, probs, facts = check_budget(552, 690, 94, 15)
    assert ok, probs
    assert facts["pixelUsePct"] < 100

    # ...and an obviously over-budget one must fail, with actionable headroom
    ok, probs, _ = check_budget(1080, 1350, 188, 30)
    assert not ok and "pixel budget exceeded" in probs[0], probs
    assert "ceiling is" in probs[0], "must say what WOULD fit, not just that it does not"

    ok, probs, _ = check_budget(552, 690, 94, 15, size_bytes=6 * 1024 * 1024)
    assert not ok and any("file size" in p for p in probs), probs

    ok, _, _ = check_budget(552, 690, 94, 15, size_bytes=2 * 1024 * 1024)
    assert ok

    # gif-spec: must return a COMPLIANT spec for every master this repo ships,
    # including the two that the old master-gating logic rejected outright.
    for w, h in ((1080, 1080), (1080, 1350)):
        gw, gh, fps, frames = gif_spec(w, h, 5500)
        ok, probs, _ = check_budget(gw, gh, frames, fps)
        assert ok, f"gif_spec({w}x{h}) returned a non-compliant spec: {probs}"
        assert abs(gh / gw - h / w) < 0.02, "gif_spec must preserve aspect ratio"
    assert gif_spec(1080, 1080, 5500)[0] > 200, "gif_spec should not collapse to a thumbnail"
    assert gif_spec(1080, 1080, 5500)[2] >= 12, "gif_spec must not buy width with frame rate"

    # seam: build a clean loop and a deliberately broken one, and confirm the
    # check separates them. A seam test that has never failed proves nothing.
    if shutil.which("ffmpeg") and shutil.which("ffprobe"):
        try:
            from PIL import Image
        except ImportError:
            print("motion-check OK (budget only; install Pillow to self-test the seam)")
            return
        with tempfile.TemporaryDirectory() as td:
            d = pathlib.Path(td)
            # A real loop returns to its opening state: first and last are identical.
            values = [40, 60, 80, 100, 120, 140, 120, 100, 60, 40]
            for i, v in enumerate(values):
                Image.new("RGB", (64, 64), (v, v, v)).save(d / f"f{i:03d}.png")
            clean = d / "clean.mp4"
            subprocess.run(["ffmpeg", "-y", "-framerate", "10", "-i", str(d / "f%03d.png"),
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "0", str(clean)],
                           capture_output=True)
            ok, probs, _ = check_seam(clean, tolerance=2)
            assert ok, f"clean loop must pass: {probs}"

            Image.new("RGB", (64, 64), (200, 30, 30)).save(d / "f009.png")  # seam deliberately broken
            broken = d / "broken.mp4"
            subprocess.run(["ffmpeg", "-y", "-framerate", "10", "-i", str(d / "f%03d.png"),
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "0", str(broken)],
                           capture_output=True)
            ok, probs, _ = check_seam(broken, tolerance=2)
            assert not ok and "seam is not clean" in probs[0], f"broken loop must fail: {probs}"

            # The area gate exists so a lossy text-heavy master is not failed by
            # encoder drift. It must still catch a real break, or it is a bypass
            # wearing a flag's clothing: this break moves the whole frame.
            ok, probs, _ = check_seam(broken, max_changed_pct=1.0)
            assert not ok and "seam is not clean" in probs[0], \
                f"area gate must still catch a real seam break: {probs}"
            ok, probs, _ = check_seam(clean, max_changed_pct=1.0)
            assert ok, f"area gate must pass a clean loop: {probs}"

            # gif_spec's frame count must bound what ffmpeg ACTUALLY emits from a
            # render.sh master (frames 0..N-1 at 30fps). round() under-counted by one
            # and a 5.2s card shipped at 100.9% of the budget (2026-09-22).
            dur_ms = 5200
            n_master = dur_ms * 30 // 1000
            for i in range(n_master):
                Image.new("RGB", (32, 32), (i % 250, 0, 0)).save(d / f"m{i:04d}.png")
            master = d / "master.mp4"
            subprocess.run(["ffmpeg", "-y", "-framerate", "30", "-i", str(d / "m%04d.png"),
                            "-c:v", "libx264", "-pix_fmt", "yuv420p", str(master)], capture_output=True)
            sw, sh, sfps, sframes = gif_spec(1080, 1080, dur_ms)
            gif = d / "out.gif"
            subprocess.run(["ffmpeg", "-y", "-i", str(master), "-vf", f"fps={sfps}", str(gif)],
                           capture_output=True)
            real = int(subprocess.run(["ffprobe", "-v", "error", "-count_frames", "-select_streams", "v:0",
                                       "-show_entries", "stream=nb_read_frames", "-of", "csv=p=0", str(gif)],
                                      capture_output=True, text=True).stdout.strip() or 0)
            assert real and real <= sframes, \
                f"gif_spec predicts {sframes} frames but ffmpeg emits {real}: spec would breach the budget"

            # seam-frames + excursion on raw PNG dirs, both sides each.
            loop = d / "loop"; loop.mkdir()
            for i, v in enumerate([40, 90, 200, 90, 40]):
                im = Image.new("RGB", (40, 40), (40, 40, 40))
                im.paste((v, v, v), (0, 0, 40, 20))
                im.save(loop / f"f{i:04d}.png")
            ok, probs, _ = check_seam_frames(loop)
            assert ok, f"clean frame loop must pass: {probs}"
            ok, probs, facts = check_excursion(loop, floor_pct=10, step=1)
            assert ok and facts["excursionPct"] == 50.0, f"moving loop must clear the floor: {facts}"
            Image.new("RGB", (40, 40), (41, 40, 40)).save(loop / "f0004.png")   # 1-level drift
            ok, probs, _ = check_seam_frames(loop)
            assert not ok and "seam is not clean" in probs[0], "lossless seam must catch a 1-level drift"
            frozen = d / "frozen"; frozen.mkdir()
            for i in range(4):
                Image.new("RGB", (40, 40), (40, 40, 40)).save(frozen / f"f{i:04d}.png")
            ok, probs, _ = check_excursion(frozen, floor_pct=1, step=1)
            assert not ok and "barely moves" in probs[0], "a frozen animation must fail excursion"
            # dead-hold: 10 fps, a clip that moves every frame passes; one frozen for 2s fails.
            live = d / "live"; live.mkdir()
            for i in range(40):
                im = Image.new("RGB", (40, 40), (40, 40, 40))
                im.paste((200, 200, 200), (i % 20, 0, i % 20 + 10, 10))
                im.save(live / f"f{i:04d}.png")
            ok, probs, _ = check_dead_hold(live, 10)
            assert ok, f"a clip that always moves must pass dead-hold: {probs}"
            for i in range(10, 32):
                Image.new("RGB", (40, 40), (40, 40, 40)).save(live / f"f{i:04d}.png")
            ok, probs, _ = check_dead_hold(live, 10)
            assert not ok and "dead hold" in probs[0], "a 2s freeze must fail dead-hold"
        print("motion-check OK (budget + seam peak/area + seam-frames + excursion + dead-hold, both sides)")
    else:
        print("motion-check OK (budget only; ffmpeg absent so the seam side was not exercised)")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="cmd")
    g = sub.add_parser("gif-spec")
    g.add_argument("--width", type=int, required=True)
    g.add_argument("--height", type=int, required=True)
    g.add_argument("--duration-ms", type=int, required=True)
    b = sub.add_parser("budget")
    b.add_argument("--width", type=int, required=True)
    b.add_argument("--height", type=int, required=True)
    b.add_argument("--frames", type=int, required=True)
    b.add_argument("--fps", type=int, required=True)
    b.add_argument("--bytes", type=int)
    s = sub.add_parser("seam")
    s.add_argument("--video", required=True)
    s.add_argument("--tolerance", type=int, default=0)
    s.add_argument("--max-changed-pct", type=float, default=None,
                   help="gate on changed AREA instead of peak delta; for lossy text-heavy masters")
    sf = sub.add_parser("seam-frames")
    sf.add_argument("--dir", required=True)
    ex = sub.add_parser("excursion")
    ex.add_argument("--dir", required=True)
    ex.add_argument("--floor-pct", type=float, default=EXCURSION_FLOOR_PCT)
    dh = sub.add_parser("dead-hold")
    dh.add_argument("--dir", required=True)
    dh.add_argument("--fps", type=int, required=True)
    a = ap.parse_args()
    if a.cmd == "dead-hold":
        sys.exit(_report(*check_dead_hold(a.dir, a.fps), "Dead hold"))

    if a.cmd == "seam-frames":
        sys.exit(_report(*check_seam_frames(a.dir), "Loop seam (lossless frames)"))
    if a.cmd == "excursion":
        sys.exit(_report(*check_excursion(a.dir, a.floor_pct), "Excursion"))

    if a.cmd == "gif-spec":
        w, h, fps, frames = gif_spec(a.width, a.height, a.duration_ms)
        print(f"{w} {h} {fps} {frames}")
        sys.exit(0)
    if a.cmd == "budget":
        sys.exit(_report(*check_budget(a.width, a.height, a.frames, a.fps, a.bytes), "GIF budget"))
    if a.cmd == "seam":
        sys.exit(_report(*check_seam(a.video, a.tolerance, a.max_changed_pct), "Loop seam"))
    _demo()


if __name__ == "__main__":
    main()
