#!/usr/bin/env python3
"""
check-spec.py — validate this package against the Agent Plugins specification.

    python3 check-spec.py [--root DIR]   # audit
    python3 check-spec.py                # also runs the self-check fixtures

Spec: https://agent-plugins.org/specification (1.0.0, Working Draft)
Skills spec: https://agentskills.io/specification

The two failures worth knowing about, because they are silent:

  * The portable manifest lives at `plugin.json` in the PLUGIN ROOT (§4.1.2,
    §5.1). Claude Code reads `.claude-plugin/plugin.json`. A package that has
    only the latter loads in Claude Code and is invisible to every other client.
  * `$schema` is a REQUIRED field (§5.3), and a missing required field is fatal:
    "Clients MUST reject the plugin and MUST NOT discover or execute any of its
    components." A manifest without it does not partially work. It does not load.

Both are the same class of bug as the font leak this repo was built around: it
looks fine on the machine that made it.
"""
import argparse
import json
import pathlib
import re
import sys

SCHEMA_ID = "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"

# §5.2 the manifest schema is CLOSED - these are the only permitted top-level fields.
PERMITTED = {"$schema", "name", "version", "description", "author",
             "homepage", "repository", "license", "keywords", "extensions"}
REQUIRED = {"$schema", "name"}
AUTHOR_FIELDS = {"name", "email", "url"}                      # §5.4

PLUGIN_NAME = re.compile(r"^[a-z0-9](?:[a-z0-9.-]{0,62}[a-z0-9])?$")   # §5.5
SKILL_NAME = re.compile(r"^[a-z0-9](?:[a-z0-9-]{0,62}[a-z0-9])?$")     # agentskills.io


def audit(root):
    root = pathlib.Path(root)
    errors, warnings, notes = [], [], []

    # ---------------------------------------------------------- §4.1.2 / §5.1
    portable = root / "plugin.json"
    claude = root / ".claude-plugin" / "plugin.json"

    if not portable.is_file():
        errors.append(
            "§4.1.2/§5.1: no `plugin.json` at the plugin root. A conformant client "
            "finds no manifest and cannot load this package. "
            + ("(.claude-plugin/plugin.json exists, but the spec says no other file "
               "can replace root plugin.json.)" if claude.is_file() else "")
        )
        manifest = json.loads(claude.read_text()) if claude.is_file() else None
    else:
        try:
            manifest = json.loads(portable.read_text())
        except json.JSONDecodeError as e:
            return [f"§5.2: plugin.json is not valid JSON: {e}"], warnings, notes

    if manifest is None:
        return errors, warnings, notes

    if not isinstance(manifest, dict):
        errors.append("§5.2: the manifest MUST be a top-level JSON object")
        return errors, warnings, notes

    # ---------------------------------------------------------- §5.2 / §5.3
    for field in sorted(REQUIRED - set(manifest)):
        errors.append(f"§5.3: required field `{field}` is missing (fatal: the client MUST reject the plugin)")

    if manifest.get("$schema") and manifest["$schema"] != SCHEMA_ID:
        errors.append(f"§5.2: `$schema` MUST be exactly {SCHEMA_ID!r}, got {manifest['$schema']!r}")

    for field in sorted(set(manifest) - PERMITTED):
        errors.append(f"§5.2: `{field}` is not a permitted top-level field (the schema is closed)")

    # ---------------------------------------------------------- §5.5
    name = manifest.get("name")
    if isinstance(name, str):
        if not PLUGIN_NAME.fullmatch(name):
            errors.append(f"§5.5: name {name!r} must be 1-64 chars of a-z 0-9 - . and start/end alphanumeric")
        if "--" in name or ".." in name:
            errors.append(f"§5.5: name {name!r} must not contain consecutive hyphens or periods")
    elif "name" in manifest:
        errors.append("§5.3: `name` MUST be a string")

    # ---------------------------------------------------------- §5.4
    author = manifest.get("author")
    if author is not None:
        if not isinstance(author, dict):
            errors.append("§5.4: `author` MUST be an object")
        else:
            for k in sorted(set(author) - AUTHOR_FIELDS):
                errors.append(f"§5.4: author.{k} is not permitted (only name, email, url)")
    for f in ("homepage", "repository"):
        if not manifest.get(f):
            warnings.append(f"§5.4: `{f}` is absent (optional, but it is how people find the source)")

    # ---------------------------------------------------------- §6.1 / §7.1
    skills_dir = root / "skills"
    if skills_dir.exists() and not skills_dir.is_dir():
        errors.append("§6.2: `skills` exists but is not a directory, so the whole component type is invalid")
    elif skills_dir.is_dir():
        found = 0
        for child in sorted(skills_dir.iterdir()):
            if not child.is_dir():
                continue
            sk = child / "SKILL.md"
            if not sk.is_file():
                notes.append(f"§7.1: skills/{child.name}/ has no SKILL.md, so it is not a skill")
                continue
            found += 1
            errors.extend(_audit_skill(child, sk))
        if found == 0:
            warnings.append("§7.1: `skills/` exists but contains no skill (no immediate child has SKILL.md)")

    mcp = root / "mcp.json"
    if mcp.exists() and not mcp.is_file():
        errors.append("§6.2: `mcp.json` exists but is not a regular file")

    # ---------------------------------------------------------- §7 / §8.2
    # Component types outside v1 are not violations; clients MUST ignore them.
    # Flagging them is still useful: they are the non-portable surface.
    for extra in ("commands", "agents", "hooks"):
        if (root / extra).exists():
            notes.append(
                f"§7/§8.2: `{extra}/` is not an Agent Plugins v1 component type. Conformant clients "
                f"MUST ignore it, so this is portable-but-inert, not a violation. The spec's preferred "
                f"shape is a reverse-domain extension directory, but Claude Code reads `{extra}/` at "
                f"the root, so moving it would break the client that actually loads this plugin."
            )

    # ---------------------------------------------------------- drift
    if portable.is_file() and claude.is_file():
        a, b = json.loads(portable.read_text()), json.loads(claude.read_text())
        for key in ("name", "version", "description", "license"):
            if a.get(key) != b.get(key):
                errors.append(
                    f"drift: `{key}` differs between plugin.json ({a.get(key)!r}) and "
                    f".claude-plugin/plugin.json ({b.get(key)!r}). Two manifests means two chances to be stale."
                )
    errors.extend(_loop_drift(root))
    return errors, warnings, notes


def _loop_drift(root):
    """Every format render.sh builds must be reviewable by Taste Loop B, with the SAME
    builder. card-infographic was missing from the loop's BUILDERS map, so every
    portrait card threw `no builder for format` (2026-10-04)."""
    rs = root / "scripts" / "render.sh"
    tl = root / "skills" / "visual-pipeline" / "taste-loop.js"
    if not (rs.is_file() and tl.is_file()):
        return []
    built = dict(re.findall(r"^\s*([a-z-]+)\)\s+BUILDER=([\w.-]+\.py)", rs.read_text(), re.M))
    loop = dict(re.findall(r"^\s*'?([a-z-]+)'?:\s*'([\w.-]+\.py)'", tl.read_text(), re.M))
    if not built or not loop:
        return [f"loop drift: parsed 0 formats from {'scripts/render.sh' if not built else 'taste-loop.js BUILDERS'}; "
                f"the parser no longer matches the file, so this check checks nothing"]
    errs = [f"loop drift: render.sh builds `{f}` but skills/visual-pipeline/taste-loop.js BUILDERS has no "
            f"entry, so Taste Loop B throws on it. Add '{f}': '{b}'." for f, b in sorted(built.items()) if f not in loop]
    errs += [f"loop drift: `{f}` builds with {b} in render.sh but {loop[f]} in taste-loop.js; the loop would "
             f"review a different card than the one shipping" for f, b in sorted(built.items()) if f in loop and loop[f] != b]
    return errs


def _audit_skill(directory, skill_md):
    """agentskills.io: name (<=64, a-z0-9-, no leading/trailing/double hyphen, == dirname), description (<=1024)."""
    out = []
    text = skill_md.read_text()
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n", text, re.S)
    if not m:
        return [f"agentskills: skills/{directory.name}/SKILL.md has no YAML frontmatter"]
    fm = m.group(1)

    nm = re.search(r"^name:\s*(.+?)\s*$", fm, re.M)
    if not nm:
        out.append(f"agentskills: skills/{directory.name} has no `name` in frontmatter")
    else:
        n = nm.group(1).strip().strip("\"'")
        if not SKILL_NAME.fullmatch(n) or "--" in n:
            out.append(f"agentskills: skill name {n!r} must be 1-64 chars of a-z 0-9 -, no leading/trailing/double hyphen")
        if n != directory.name:
            out.append(f"agentskills: skill name {n!r} MUST match its directory name {directory.name!r}")

    # description may be a folded/blocked scalar, so measure the whole block
    dm = re.search(r"^description:\s*(?:[>|][-+]?\s*\n((?:[ \t]+.*\n?)*)|(.+))", fm, re.M)
    if not dm:
        out.append(f"agentskills: skills/{directory.name} has no `description` in frontmatter")
    else:
        desc = (dm.group(1) or dm.group(2) or "").strip()
        if not desc:
            out.append(f"agentskills: skills/{directory.name} description is empty")
        elif len(desc) > 1024:
            out.append(f"agentskills: skills/{directory.name} description is {len(desc)} chars (max 1024)")
    return out


def _report(root):
    errors, warnings, notes = audit(root)
    for e in errors:
        print(f"  FAIL  {e}")
    for w in warnings:
        print(f"  warn  {w}")
    for n in notes:
        print(f"  note  {n}")
    if errors:
        print(f"\nNOT CONFORMANT: {len(errors)} error(s). A conformant client would reject or degrade this package.")
    else:
        print(f"\nCONFORMANT with Agent Plugins 1.0.0 ({len(warnings)} warning(s), {len(notes)} note(s)).")
    return 1 if errors else 0


def _demo():
    """Two-sided: the checker must FAIL a seeded-broken package and PASS a clean one."""
    import tempfile, shutil, os

    def build(tmp, **mutate):
        r = pathlib.Path(tmp)
        man = {"$schema": SCHEMA_ID, "name": "demo-plugin", "version": "1.0.0",
               "description": "d", "license": "MIT"}
        man.update(mutate.get("manifest") or {})
        for k in mutate.get("drop_manifest") or []:
            man.pop(k, None)
        if not mutate.get("no_root_manifest"):
            (r / "plugin.json").write_text(json.dumps(man))
        sd = r / "skills" / mutate.get("skill_dir", "demo-skill")
        sd.mkdir(parents=True)
        (sd / "SKILL.md").write_text(
            f"---\nname: {mutate.get('skill_name', 'demo-skill')}\ndescription: {mutate.get('desc', 'does a thing, use when asked')}\n---\n\nbody\n")
        if "loop" in mutate:
            (r / "scripts").mkdir()
            (r / "scripts" / "render.sh").write_text(
                "case \"$FORMAT\" in\n  card-bar)       BUILDER=bar-card.py ;;\n"
                "  card-infographic) BUILDER=infographic-card.py ;;\nesac\n")
            (r / "skills" / "visual-pipeline").mkdir()
            (r / "skills" / "visual-pipeline" / "taste-loop.js").write_text(
                "const BUILDERS = {\n" + "".join(f"  {k}: '{v}',\n" for k, v in mutate["loop"].items()) + "}\n")
        return r

    cases = [
        ("clean", {}, True),
        ("no-root-manifest", {"no_root_manifest": True}, False),
        ("missing-$schema", {"drop_manifest": ["$schema"]}, False),
        ("wrong-$schema", {"manifest": {"$schema": "https://example.com/other.json"}}, False),
        ("unknown-top-level-field", {"manifest": {"dependencies": {"x": "1"}}}, False),
        ("bad-plugin-name", {"manifest": {"name": "Demo--Plugin"}}, False),
        ("bad-author-field", {"manifest": {"author": {"name": "a", "twitter": "@x"}}}, False),
        ("skill-name-mismatch", {"skill_name": "other-name"}, False),
        ("skill-desc-empty", {"desc": ""}, False),
        ("loop-covers-render", {"loop": {"'card-bar'": "bar-card.py", "'card-infographic'": "infographic-card.py"}}, True),
        ("loop-missing-format", {"loop": {"'card-bar'": "bar-card.py"}}, False),
        ("loop-wrong-builder", {"loop": {"'card-bar'": "bar-card.py", "'card-infographic'": "flow-card.py"}}, False),
    ]
    failed = 0
    for label, mut, should_pass in cases:
        tmp = tempfile.mkdtemp()
        try:
            build(tmp, **mut)
            errs, _, _ = audit(tmp)
            ok = (not errs) == should_pass
            failed += not ok
            detail = "" if not errs else f"  [{errs[0][:58]}...]"
            print(f"  {'ok  ' if ok else 'FAIL'}  {label:24} expected {'PASS' if should_pass else 'FAIL'}, "
                  f"got {'PASS' if not errs else 'FAIL'}{detail}")
        finally:
            shutil.rmtree(tmp, ignore_errors=True)
    print("check-spec self-test: OK (catches every seeded violation, passes a clean package)"
          if not failed else f"check-spec self-test: {failed} case(s) wrong")
    return 1 if failed else 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default=str(pathlib.Path(__file__).resolve().parent.parent))
    ap.add_argument("--self-test", action="store_true")
    a = ap.parse_args()
    sys.exit(_demo() if a.self_test else _report(a.root))
