'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const player = require('../layered-player.js');

function fixture() {
  return {
    schema: 'tyri.layered.v1',
    character: '타이리 (Tyri)',
    canvas: { width: 1024, height: 1024, alpha: 'straight' },
    head: { sprite: 'face.neutral', transform: [0.9, 0, 0, 0.9, 332, 128], z: 100, locked: true },
    sprites: {
      'face.neutral': { path: 'sprites/face.png', role: 'face', source_size: [400, 500] },
      'face.other': { path: 'sprites/other-face.png', role: 'face', source_size: [400, 500] },
      'hand.front': { path: 'sprites/front.png', role: 'hand', source_size: [200, 240], side: 'right' },
      'hand.back': { path: 'sprites/back.png', role: 'hand', source_size: [180, 260], side: 'left' }
    },
    animations: {
      none: { label: '손 없음', frames: [{ duration_ms: 3200, instances: [] }] },
      wave: { label: '손 흔들기', frames: [
        { duration_ms: 100, instances: [{ sprite: 'hand.front', transform: [1, 0, 0, 1, 650, 360], z: 200 }] },
        { duration_ms: 200, instances: [
          { sprite: 'hand.front', transform: [1, 0, 0, 1, 620, 330], z: 200 },
          { sprite: 'hand.back', transform: [-1, 0, 0, 1, 310, 360], z: 50 }
        ] }
      ] },
      peace: { label: '브이', frames: [{ duration_ms: 300, instances: [
        { sprite: 'hand.front', transform: [0.6, 0, 0, 0.6, 620, 400], z: 200 }
      ] }] }
    }
  };
}

function face(commands) { return commands.find(command => command.isHead); }

test('all gestures and loop frames retain exactly the same face asset and transform', () => {
  const manifest = fixture();
  const baseline = face(player.getDrawCommands(manifest, 'none', 0));
  for (const animation of Object.keys(manifest.animations)) {
    for (const time of [0, 99, 100, 299, 300, 450, 3200, 10000000]) {
      assert.deepEqual(face(player.getDrawCommands(manifest, animation, time)), baseline);
    }
  }
  const copied = player.getDrawCommands(manifest, 'wave', 150);
  face(copied).transform[0] = 42;
  assert.deepEqual(face(player.getDrawCommands(manifest, 'wave', 150)), baseline);
});

test('layer visibility changes only which commands are included', () => {
  const manifest = fixture();
  const full = player.getDrawCommands(manifest, 'wave', 150);
  assert.deepEqual(player.getDrawCommands(manifest, 'wave', 150, { handsVisible: false }), [face(full)]);
  assert.deepEqual(player.getDrawCommands(manifest, 'wave', 150, { faceVisible: false }), full.filter(c => !c.isHead));
  assert.deepEqual(player.getDrawCommands(manifest, 'wave', 150, { faceVisible: false, handsVisible: false }), []);
  assert.deepEqual(face(player.getDrawCommands(manifest, 'none', 150)), face(full));
});

test('back hands render below the face and front hands above it', () => {
  const commands = player.getDrawCommands(fixture(), 'wave', 150);
  assert.deepEqual(commands.map(c => [c.sprite, c.z]), [
    ['hand.back', 50], ['face.neutral', 100], ['hand.front', 200]
  ]);
});

test('face instances and nested face overrides are rejected', () => {
  const faceInstance = fixture();
  faceInstance.animations.wave.frames[0].instances[0].sprite = 'face.other';
  assert.throws(() => player.validateManifest(faceInstance), /must not reference a face sprite/);
  for (const override of ['head', 'headOverride', 'faceTransform']) {
    const manifest = fixture();
    manifest.animations.wave.frames[0][override] = { transform: [1, 0, 0, 1, 0, 0] };
    assert.throws(() => player.getDrawCommands(manifest, 'wave', 0), /must not override the locked face/);
  }
  const unlocked = fixture();
  unlocked.head.locked = false;
  assert.throws(() => player.validateManifest(unlocked), /head.locked must be true/);
});

test('frame timing uses milliseconds, exact boundaries and infinite looping by default', () => {
  const manifest = fixture();
  const index = time => player.getFrameAtTime(manifest, 'wave', time).index;
  assert.equal(index(-1), 0);
  assert.equal(index(0), 0);
  assert.equal(index(99.999), 0);
  assert.equal(index(100), 1);
  assert.equal(index(299.999), 1);
  assert.equal(index(300), 0);
  assert.equal(index(400), 1);
  assert.equal(index(600), 0);
  const stopped = player.getFrameAtTime(manifest, 'wave', 600, { loop: false });
  assert.equal(stopped.index, 1);
  assert.equal(stopped.finished, true);
  assert.equal(stopped.durationMs, 300);
  assert.throws(() => player.getFrameAtTime(manifest, 'wave', Infinity), /elapsed time must be finite/);
});

test('renderer clears at identity, uses exact layer matrices and restores caller state', () => {
  const manifest = fixture();
  const commands = player.getDrawCommands(manifest, 'wave', 150);
  const calls = [];
  const ctx = {
    canvas: { width: 1024, height: 1024 },
    save() { calls.push(['save']); },
    restore() { calls.push(['restore']); },
    setTransform(...args) { calls.push(['matrix', ...args]); },
    clearRect(...args) { calls.push(['clear', ...args]); },
    drawImage(image, ...args) { calls.push(['draw', image.id, ...args]); }
  };
  const images = Object.fromEntries(commands.map(c => [c.sprite, { id: c.sprite }]));
  player.drawContext(ctx, commands, images);
  assert.deepEqual(calls[0], ['save']);
  assert.deepEqual(calls[1], ['matrix', 1, 0, 0, 1, 0, 0]);
  assert.deepEqual(calls[2], ['clear', 0, 0, 1024, 1024]);
  assert.deepEqual(calls.filter(c => c[0] === 'matrix').slice(1), commands.map(c => ['matrix', ...c.transform]));
  assert.deepEqual(calls.filter(c => c[0] === 'draw'), commands.map(c => ['draw', c.sprite, 0, 0]));
  assert.deepEqual(calls.at(-1), ['restore']);
  assert.equal(ctx.globalCompositeOperation, 'source-over');
  calls.length = 0;
  assert.throws(() => player.drawContext(ctx, commands, {}), /image not loaded/);
  assert.deepEqual(calls.at(-1), ['restore']);
  ctx.canvas.width = 512;
  assert.throws(() => player.drawContext(ctx, commands, images), /resize its CSS box only/);
});
