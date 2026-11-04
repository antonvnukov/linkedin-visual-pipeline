export const meta = {
  name: 'taste-loop-b',
  description: 'Blind, checksummed, gate-scored review loop. Each round freezes a candidate, hands independent critics an evidence bundle and numbered gates, and iterates v1..vN until it scores >=9.0 with no high-severity issue. The best-GRADED candidate ships, so a bad final-round fix cannot regress it.',
  phases: [
    { title: 'Author gates', detail: 'artifact-specific gates for this piece' },
    { title: 'Review', detail: 'independent critics score the frozen candidate' },
    { title: 'Fix', detail: 'apply required fixes, re-render, re-gate' },
  ],
}

// args: { candidate, configPath, format, theme, outdir, brief, pluginDir, brandPath,
//         evidence[], motion, claimsPath, storyboardPath, critics, maxRounds, passScore }
const a = typeof args === 'string' ? JSON.parse(args) : (args || {})

// `process` is undeclared in the Workflow sandbox, and optional chaining does not
// guard an undeclared identifier: `process?.env` throws ReferenceError.
const PLUGIN = a.pluginDir || (typeof process !== 'undefined' ? process.env?.LV_PLUGIN_DIR : null) || '.'
const S = `${PLUGIN}/scripts`

const BUILDERS = {
  'card-bar': 'bar-card.py',
  'card-dashboard': 'dashboard-card.py',
  'card-flow': 'flow-card.py',
  'card-quote': 'quote-card.py',
  // These two silhouettes existed for weeks while this map did not know them, so
  // a taste-loop run on either would silently fall back to bar-card.py and review
  // a DIFFERENT card than the one being shipped. card-flow had the same gap once.
  'card-before-after': 'before-after-card.py',
  'card-email': 'email-card.py',
  // Portrait reference sheets (1080x1350 and taller). Missing until 2026-10-04, so
  // every portrait card threw here. scripts/check-spec.py now fails CI when a
  // format render.sh builds is absent from this map.
  'card-infographic': 'infographic-card.py',
  carousel: 'carousel-card.py',
}

const format = a.format || 'card-bar'
const theme = a.theme || 'dark'
if (!BUILDERS[format]) {
  throw new Error(
    `taste-loop: no builder for format "${format}". Falling back would review a ` +
    `DIFFERENT card than the one shipping. Add it to BUILDERS.`)
}
const builder = `${S}/${BUILDERS[format]}`
const work = a.outdir || '/tmp/taste-loop-b'
const brandArg = a.brandPath ? ` --brand ${a.brandPath}` : ''
// render.sh hands qa-visual the <config>.qa.json beside the config. Without it QA
// assumes a 1080x1080 artboard, so every portrait or tall card (card-infographic
// at 1350 or 2160) fails the dimension check on re-render. The shell test keeps
// formats that ship no manifest working exactly as before.
const qaManifest = `${(a.configPath || '').replace(/\.json$/, '')}.qa.json`
const manifestArg = ` $([ -f ${qaManifest} ] && echo --manifest ${qaManifest})`
// Routing: the loop must honour pipeline.json, not silently inherit the session
// model. The first live run executed every agent on the session's model, which
// made the entire cost design inert.
const ROUTES = a.routes || {}
const on = (stage) => (ROUTES[stage] ? { model: ROUTES[stage].alias, effort: ROUTES[stage].effort } : {})

const critics = a.critics || 3
const maxRounds = a.maxRounds || 3
const passScore = a.passScore ?? 9.0
const brief = a.brief || ''

const VERDICT = {
  type: 'object',
  properties: {
    checksumVerified: { type: 'boolean', description: 'true only if the artifact hash matched the brief' },
    score: { type: 'number' },
    pass: { type: 'boolean' },
    gates: {
      type: 'array',
      items: {
        type: 'object',
        properties: {
          number: { type: 'number' },
          verdict: { type: 'string', enum: ['PASS', 'FAIL'] },
          note: { type: 'string' },
        },
        required: ['number', 'verdict'],
      },
    },
    required: {
      type: 'array',
      description: 'fixes that must happen before shipping',
      items: {
        type: 'object',
        properties: {
          severity: { type: 'string', enum: ['high', 'medium'] },
          target: { type: 'string', enum: ['config', 'layout'] },
          desc: { type: 'string' },
          fix: { type: 'string' },
        },
        required: ['severity', 'target', 'desc', 'fix'],
      },
    },
    optional: { type: 'array', items: { type: 'string' } },
  },
  required: ['checksumVerified', 'score', 'pass', 'gates', 'required'],
}

const ARTIFACT_GATES = {
  type: 'object',
  properties: {
    gates: {
      type: 'array',
      minItems: 3,
      maxItems: 6,
      items: { type: 'string', description: 'one imperative, checkable assertion about THIS artifact' },
    },
  },
  required: ['gates'],
}

// ---------------------------------------------------------------- author gates
// The base and format layers are static files and cost nothing. Only these 3-6
// artifact-specific gates need a model, which is what keeps the full protocol
// cheap enough that running it is never a decision.
phase('Author gates')
const authored = await agent(
  `Read these and write gates for THIS specific artifact.\n` +
    `  config: ${a.configPath}\n` +
    (a.claimsPath ? `  claims: ${a.claimsPath}\n` : '') +
    (a.storyboardPath ? `  storyboard: ${a.storyboardPath}\n` : '') +
    `  brief: ${brief}\n\n` +
    `Write 3-6 gates that a reviewer could mark PASS or FAIL by LOOKING at the artifact. ` +
    `They must be specific to this piece: name its actual figures, labels, transitions and claims. ` +
    `Generic craft, palette, legibility, footer and anti-slop gates are already covered by a ` +
    `static base layer, so do not restate them, or the brief becomes ceremony.\n\n` +
    `Good: "The 62.1% hero stat and the green segment label state the same figure, and no other ` +
    `percentage appears." Bad: "The card looks professional."`,
  { label: 'author:artifact-gates', phase: 'Author gates', schema: ARTIFACT_GATES, ...on('author') },
)
const artifactGates = (authored?.gates || [])
log(`Artifact gates authored: ${artifactGates.length}`)

// ---------------------------------------------------------------- the loop
let best = { candidate: a.candidate, score: -1, round: 0, version: 'v1' }
let converged = false
let stalls = 0
const rounds = []
let current = a.candidate

for (let round = 1; round <= maxRounds; round++) {
  const version = `v${round}`

  // Every critic reviews the SAME frozen bytes. gates.py stamps the SHA-256 into
  // the brief and the critic must verify it before reviewing, so a candidate that
  // changed underneath the review cannot be silently graded as if it had not.
  const briefPath = `${work}/${version}/critic-brief-r${round}.md`
  // Evidence must describe THIS version. Handing round 2 the round 1 QA report
  // means every machine check it certifies was proven on a different render.
  // `motion: true` makes gates.py add the motion gates (sequencing, loop seam,
  // spatial stability, GIF budget). Those cannot be judged from a poster PNG, and
  // critics correctly refuse to certify what they cannot see: a live run scored 8
  // of 26 gates FAIL for missing evidence in all three rounds and burned the whole
  // token budget rediscovering that every round. Motion gates without motion
  // evidence is an unwinnable brief, so refuse it at launch instead.
  // Critics view images with the Read tool, so pass extracted FRAMES (frame 0, one
  // per reveal, the closing hold) or a contact sheet, not the MP4 itself.
  const motionEvidence = a.motion ? (a.motionEvidence || []) : []
  if (a.motion && motionEvidence.length === 0) {
    throw new Error(
      'taste-loop: motion:true adds motion gates, but motionEvidence[] is empty. ' +
      'Pass frame stills or a contact sheet (PNG paths) so those gates can be judged, ' +
      'or drop motion:true to review the still alone.'
    )
  }
  const evidenceList = round === 1
    ? [...(a.evidence || []), ...motionEvidence]
    : [`${work}/${version}/qa/qa-report.json`, `${work}/${version}/qa/feed-preview.png`, ...motionEvidence]
  const evidence = evidenceList.map((e) => `--evidence ${e}`).join(' ')
  const gatesArgs = artifactGates.map((g) => g.replace(/"/g, "'")).map((g, i) => `${i + 1}. ${g}`).join('\n')

  await agent(
    `Assemble the critic brief. Run exactly:\n` +
      `  mkdir -p ${work}/${version}\n` +
      `  cat > ${work}/${version}/artifact-gates.md <<'GATES'\n${gatesArgs}\nGATES\n` +
      `  python3 ${S}/gates.py assemble --format ${format}${a.motion ? ' --motion' : ''} ` +
      `--artifact ${work}/${version}/artifact-gates.md --candidate ${current} ${evidence} ` +
      `--round ${round} --title "${(a.title || format).replace(/"/g, '')}" -o ${briefPath}\n` +
      `Then print the number of gates it reported.`,
    { label: `assemble:r${round}`, phase: 'Review', ...on('extract') },
  )

  const verdicts = (await parallel(
    Array.from({ length: critics }, (_, i) => () =>
      agent(
        `You are an independent reviewer. Read the brief at ${briefPath} and follow it exactly.\n\n` +
          `First: compute the SHA-256 of the frozen artifact (shasum -a 256 <path>) and compare it to ` +
          `the brief. Set checksumVerified accordingly. If it does not match, report that and stop.\n\n` +
          `Then VIEW the artifact with the Read tool and any evidence images. Judge only what you can ` +
          `see plus the listed evidence. Do not read source code, prior rounds, or verdicts.\n\n` +
          `Report every gate by number as PASS or FAIL, score out of 10, pass only at ${passScore}+ ` +
          `with no high-severity issue, and separate required fixes from optional polish.` +
          (i > 0 ? `\n\nYou are reviewer ${i + 1}; form your own view rather than a consensus one.` : ''),
        { label: `critic:r${round}-${i + 1}`, phase: 'Review', schema: VERDICT, ...on(stalls >= 2 ? 'escalate' : 'critic') },
      ),
    ),
  )).filter(Boolean)

  if (!verdicts.length) {
    log(`Round ${round}: every critic failed to return a verdict, stopping`)
    break
  }

  const unverified = verdicts.filter((v) => !v.checksumVerified)
  if (unverified.length) {
    // A review of bytes nobody confirmed is not a review.
    log(`Round ${round}: ${unverified.length}/${verdicts.length} critic(s) could not verify the checksum — discarding`)
  }
  const valid = verdicts.filter((v) => v.checksumVerified)
  if (!valid.length) {
    rounds.push({ round, version, candidate: current, error: 'no checksum-verified verdicts' })
    break
  }

  const avg = valid.reduce((s, v) => s + v.score, 0) / valid.length
  const required = valid.flatMap((v) => v.required || [])
  const highs = required.filter((r) => r.severity === 'high')
  const allPass = valid.every((v) => v.pass)
  const failedGates = valid.flatMap((v) => (v.gates || []).filter((g) => g.verdict === 'FAIL').map((g) => g.number))

  rounds.push({
    round, version, candidate: current, briefPath,
    scores: valid.map((v) => v.score), avgScore: Number(avg.toFixed(2)),
    failedGates: [...new Set(failedGates)].sort((x, y) => x - y),
    requiredCount: required.length, highCount: highs.length,
    required, optional: valid.flatMap((v) => v.optional || []),
  })
  log(`Round ${round} (${version}): avg ${avg.toFixed(2)} [${valid.map((v) => v.score).join(', ')}], ` +
      `${required.length} required (${highs.length} high), gates failed: ${[...new Set(failedGates)].join(', ') || 'none'}`)

  // The best-GRADED candidate ships, not the last one produced.
  if (avg > best.score) best = { candidate: current, score: avg, round, version }
  else stalls += 1

  if (allPass && avg >= passScore && highs.length === 0) { converged = true; break }
  if (round === maxRounds) break

  const nextVersion = `v${round + 1}`
  const nextHtml = `${work}/${nextVersion}/card.html`
  const fixList = required
    .map((r) => `- [${r.severity}][${r.target}] ${r.desc}  ->  FIX: ${r.fix}`)
    .join('\n')

  await agent(
    `Apply ONLY the required fixes below, then re-render and re-gate.\n\n` +
      `Setup (ignore errors if already present):\n` +
      `  mkdir -p ${work}/${nextVersion}\n` +
      `  cp -n ${a.configPath} ${work}/work-config.json\n` +
      `  cp -n ${builder} ${work}/work-builder.py\n\n` +
      `  target=config -> edit ${work}/work-config.json structurally only: shorten a field to fit, ` +
      `remove a duplicated stat, fill a genuinely missing required field. Keep the user's own words.\n` +
      `  target=layout -> edit ${work}/work-builder.py CSS (spacing, hierarchy)\n\n` +
      `HARD CONSTRAINTS: never hardcode a colour, font or footer string into the builder; all of ` +
      `those read from brand.json through brandkit and must keep doing so. Never introduce an em or ` +
      `en dash. Never change a figure to make a gate pass, that is falsifying the claim. Never ` +
      `rephrase, reword or invent the user's copy: this loop checks the words they chose, it does ` +
      `not write them. Do not restructure beyond the listed fixes.\n\n${fixList}\n\n` +
      `Then run exactly:\n` +
      // PYTHONPATH: the builder copy lives outside scripts/, and every builder
      // imports brandkit from its own directory, so the copy could not import it.
      `  PYTHONPATH=${S} python3 ${work}/work-builder.py --config ${work}/work-config.json --theme ${theme}${brandArg} --out ${nextHtml}\n` +
      // Same floor render.sh runs before QA (palette, dashes, wrap, font, impeccable):
      // the fixer edits builder CSS, which is exactly where a literal hex would leak.
      `  bash ${S}/gate.sh ${nextHtml} ${theme}${a.brandPath ? ` ${a.brandPath}` : ''}\n` +
      `  node ${S}/qa-visual.cjs --html ${nextHtml} --theme ${theme}${brandArg}${manifestArg}` +
      (a.claimsPath ? ` --claims ${a.claimsPath}` : '') + ` --outdir ${work}/${nextVersion}/qa --force\n` +
      `gate.sh and the QA gate must both exit 0. Report any WARN line gate.sh printed, what you changed, ` +
      `and confirm ${work}/${nextVersion}/qa/final.png exists.`,
    { label: `fix:r${round}`, phase: 'Fix', ...on('fixer') },
  )

  current = `${work}/${nextVersion}/qa/final.png`
  rounds[rounds.length - 1].fixedTo = current
}

return {
  converged,
  bestCandidate: best.candidate,
  bestScore: best.score,
  bestRound: best.round,
  bestVersion: best.version,
  roundsRun: rounds.length,
  stalls,
  // Two stalled rounds is the documented trigger to escalate to the expensive tier.
  escalationSuggested: stalls >= 2 && !converged,
  rounds,
}
