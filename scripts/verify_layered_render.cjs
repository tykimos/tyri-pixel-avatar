#!/usr/bin/env node
'use strict';

/*
 * Exercise the real layered player and generated sprites in a canvas renderer.
 * Optional developer dependency: npm install --no-save @napi-rs/canvas
 * Run: node scripts/verify_layered_render.cjs [--output /path/to/report.json]
 * No images or reports are written unless --output is supplied.
 */
const fs = require('node:fs');
const path = require('node:path');
const crypto = require('node:crypto');
const assert = require('node:assert/strict');

function argumentsFor(argv) {
  const options = {repo: path.resolve(__dirname, '..'), output: null};
  for (let i = 0; i < argv.length; i += 1) {
    const name = argv[i];
    if (name === '--help' || name === '-h') {
      process.stdout.write('Usage: node scripts/verify_layered_render.cjs [--repo PATH] [--output PATH]\n');
      process.exit(0);
    }
    assert(['--repo', '--output'].includes(name), 'Unknown option: ' + name);
    assert(argv[i + 1] && !argv[i + 1].startsWith('--'), 'Missing value for ' + name);
    options[name.slice(2)] = path.resolve(argv[++i]);
  }
  return options;
}

function canvasLibrary() {
  try {
    return require('@napi-rs/canvas');
  } catch (firstError) {
    const runtimeModules = process.env.CODEX_PRIMARY_RUNTIME_NODE_MODULES;
    if (runtimeModules) {
      try {
        return require(path.join(runtimeModules, '@napi-rs/canvas'));
      } catch (_) { /* Give a portable installation instruction below. */ }
    }
    throw new Error('The optional pixel-verification dependency @napi-rs/canvas is unavailable. ' +
      'Install it in the development environment with npm install --no-save @napi-rs/canvas. ' +
      'No pixel verification was performed. Original error: ' + firstError.message);
  }
}

function hashPixels(data) {
  return crypto.createHash('sha256')
    .update(Buffer.from(data.buffer, data.byteOffset, data.byteLength)).digest('hex');
}

function visiblePixels(data) {
  let count = 0;
  for (let i = 3; i < data.length; i += 4) if (data[i] > 0) count += 1;
  return count;
}

function getPixels(ctx, width, height) {
  return ctx.getImageData(0, 0, width, height).data;
}

function compareUncoveredPixels(composite, face, hands) {
  let checked = 0;
  let mismatches = 0;
  let firstMismatch = null;
  for (let i = 0; i < composite.length; i += 4) {
    if (hands[i + 3] !== 0) continue;
    checked += 1;
    if (composite[i] !== face[i] || composite[i + 1] !== face[i + 1] ||
        composite[i + 2] !== face[i + 2] || composite[i + 3] !== face[i + 3]) {
      mismatches += 1;
      if (firstMismatch === null) firstMismatch = i / 4;
    }
  }
  return {checked_pixels: checked, mismatch_pixels: mismatches, first_mismatch_pixel: firstMismatch};
}

async function verify(options) {
  const manifestPath = path.join(options.repo, 'data', 'layers.json');
  assert(fs.existsSync(manifestPath), 'Generated manifest is missing: ' + manifestPath +
    '. Generate actual layered assets before running pixel verification.');
  const manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf8'));
  const api = require(path.join(options.repo, 'layered-player.js'));
  for (const name of ['validateManifest', 'getFrameAtTime', 'getDrawCommands', 'drawContext']) {
    assert.equal(typeof api[name], 'function', 'Player export is missing: ' + name);
  }
  api.validateManifest(manifest);
  const {createCanvas, loadImage} = canvasLibrary();
  const {width, height} = manifest.canvas;
  const images = Object.create(null);
  const repoPrefix = options.repo + path.sep;
  for (const [id, sprite] of Object.entries(manifest.sprites)) {
    const filename = path.resolve(options.repo, sprite.path);
    assert(filename.startsWith(repoPrefix), 'Sprite path escapes repository: ' + id);
    assert(fs.existsSync(filename), 'Actual generated sprite is missing: ' + filename);
    images[id] = await loadImage(filename);
    assert.deepEqual([images[id].width, images[id].height], sprite.source_size,
      'Actual image dimensions disagree with source_size: ' + id);
  }

  // Build an independent reference directly from the sole canonical face.
  // Do not let a player that incorrectly renders an empty face pass by hashing
  // the same empty output for every animation.
  const reference = createCanvas(width, height).getContext('2d');
  reference.imageSmoothingEnabled = false;
  reference.globalAlpha = 1;
  reference.globalCompositeOperation = 'source-over';
  reference.setTransform(...manifest.head.transform);
  reference.drawImage(images[manifest.head.sprite], 0, 0);
  const faceReference = getPixels(reference, width, height);
  const referenceHash = hashPixels(faceReference);
  assert(visiblePixels(faceReference) > 0, 'The canonical face renders no visible pixels.');
  const headSnapshot = JSON.stringify(manifest.head);
  const contexts = {
    face: createCanvas(width, height).getContext('2d'),
    hands: createCanvas(width, height).getContext('2d'),
    composite: createCanvas(width, height).getContext('2d'),
    hidden: createCanvas(width, height).getContext('2d'),
  };
  function render(kind, animation, time, flags) {
    const commands = api.getDrawCommands(manifest, animation, time, flags);
    api.drawContext(contexts[kind], commands, images);
    return {commands, pixels: getPixels(contexts[kind], width, height)};
  }

  const results = [];
  let sampleCount = 0;
  for (const [animationId, animation] of Object.entries(manifest.animations)) {
    let elapsed = 0;
    const samples = animation.frames.map((frame, index) => {
      const sample = {time_ms: elapsed, expected_frame: index, boundary: 'frame-start'};
      elapsed += frame.duration_ms;
      return sample;
    });
    samples.push({time_ms: elapsed, expected_frame: 0, boundary: 'loop-start'});
    let maxHandPixels = 0;
    const frameResults = [];
    for (const sample of samples) {
      const label = animationId + ' at ' + sample.time_ms + 'ms';
      const selected = api.getFrameAtTime(manifest, animationId, sample.time_ms);
      assert.equal(selected.index, sample.expected_frame, 'Incorrect frame boundary: ' + label);
      const faceOnly = render('face', animationId, sample.time_ms,
        {faceVisible: true, handsVisible: false});
      assert.equal(faceOnly.commands.length, 1, 'Face-only view must contain one draw command: ' + label);
      assert.equal(faceOnly.commands[0].sprite, manifest.head.sprite, 'Face source changed: ' + label);
      assert.deepEqual(faceOnly.commands[0].transform, manifest.head.transform, 'Face transform changed: ' + label);
      assert.equal(hashPixels(faceOnly.pixels), referenceHash, 'Face RGBA pixels changed: ' + label);

      const handsOnly = render('hands', animationId, sample.time_ms,
        {faceVisible: false, handsVisible: true});
      assert(handsOnly.commands.every(command => command.role !== 'face' &&
        command.sprite !== manifest.head.sprite), 'Hands-only view contains a face: ' + label);
      const handPixels = visiblePixels(handsOnly.pixels);
      maxHandPixels = Math.max(maxHandPixels, handPixels);
      if (animationId === 'none') assert.equal(handPixels, 0, 'The none state contains visible hands.');

      const composite = render('composite', animationId, sample.time_ms,
        {faceVisible: true, handsVisible: true});
      assert.equal(composite.commands.filter(command => command.role === 'face').length, 1,
        'Composite must contain exactly one face: ' + label);
      const comparison = compareUncoveredPixels(composite.pixels, faceReference, handsOnly.pixels);
      assert(comparison.checked_pixels > 0, 'No uncovered pixels remain to verify: ' + label);
      assert.equal(comparison.mismatch_pixels, 0,
        'Pixels outside the hand alpha mask changed: ' + label + ' ' + JSON.stringify(comparison));

      // Seed this canvas with the visible scene before hiding everything, so
      // stale pixels cannot pass merely because the canvas began transparent.
      api.drawContext(contexts.hidden, composite.commands, images);
      const hidden = render('hidden', animationId, sample.time_ms,
        {faceVisible: false, handsVisible: false});
      assert.equal(hidden.commands.length, 0, 'Both hidden switches must remove every layer: ' + label);
      assert.equal(visiblePixels(hidden.pixels), 0, 'Hidden layers left stale pixels: ' + label);
      assert.equal(JSON.stringify(manifest.head), headSnapshot, 'The player mutated the locked head.');
      frameResults.push({
        time_ms: sample.time_ms,
        frame_index: selected.index,
        boundary: sample.boundary,
        face_rgba_sha256: referenceHash,
        hand_visible_pixels: handPixels,
        uncovered_checked_pixels: comparison.checked_pixels,
        uncovered_mismatch_pixels: comparison.mismatch_pixels,
      });
      sampleCount += 1;
    }
    if (animationId !== 'none') {
      assert(maxHandPixels > 0, animationId + ' never displays a visible hand; the layer may be empty or off canvas.');
    }
    results.push({animation: animationId, duration_ms: elapsed, samples: frameResults});
  }
  return {
    schema: 'tyri.layered-render-verification.v1',
    status: 'passed',
    canvas: [width, height],
    canonical_face: manifest.head.sprite,
    canonical_face_transform: manifest.head.transform,
    canonical_face_rgba_sha256: referenceHash,
    animation_count: results.length,
    frame_boundary_samples: sampleCount,
    face_rgba_identical_in_all_states: true,
    uncovered_composite_rgba_identical_to_face: true,
    hidden_layers_leave_no_stale_pixels: true,
    note: 'The face-layer hash is identical even when a hand overlaps it. Composite comparisons exclude pixels where the rendered hand layer has nonzero alpha.',
    animations: results,
  };
}

function finish(report, output) {
  const json = JSON.stringify(report, null, 2) + '\n';
  if (output) {
    fs.mkdirSync(path.dirname(output), {recursive: true});
    fs.writeFileSync(output, json);
  }
  process.stdout.write(json);
}

(async () => {
  let options;
  try {
    options = argumentsFor(process.argv.slice(2));
    finish(await verify(options), options.output);
  } catch (error) {
    const report = {
      schema: 'tyri.layered-render-verification.v1',
      status: 'failed',
      error: error && error.message ? error.message : String(error),
      verification_completed: false,
      face_rgba_identical_in_all_states: null,
    };
    try { finish(report, options && options.output); }
    catch (writeError) {
      process.stdout.write(JSON.stringify({...report, report_write_error: writeError.message}, null, 2) + '\n');
    }
    process.exitCode = 1;
  }
})();
