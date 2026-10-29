/*
 * Tyri Pixel Avatar by Taeyoung Kim (tykimos).
 * Layered renderer: one locked face, independently positioned hand sprites.
 * Distributed under the repository's LICENSE.
 */
(function (root, factory) {
  'use strict';
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  if (root) root.TyriLayeredPlayer = api;
})(typeof globalThis !== 'undefined' ? globalThis : this, function () {
  'use strict';

  const SCHEMA = 'tyri.layered.v1';
  const SIZE = 1024;
  const forbiddenOverrides = new Set([
    'head', 'face', 'headOverride', 'head_override', 'headTransform',
    'head_transform', 'faceOverride', 'face_override', 'faceTransform',
    'face_transform', 'headSprite', 'head_sprite', 'faceSprite', 'face_sprite'
  ]);

  function assert(condition, message) {
    if (!condition) throw new Error('Tyri layers: ' + message);
  }

  function isRecord(value) {
    return value !== null && typeof value === 'object' && !Array.isArray(value);
  }

  function validateTransform(value, where) {
    assert(Array.isArray(value) && value.length === 6 && value.every(Number.isFinite),
      where + ' needs a finite six-number transform.');
    assert(Math.abs(value[0] * value[3] - value[1] * value[2]) > 1e-12,
      where + ' transform must not collapse the sprite.');
  }

  function rejectOverrides(value, where) {
    if (!value || typeof value !== 'object') return;
    for (const key of Object.keys(value)) {
      assert(!forbiddenOverrides.has(key), where + ' must not override the locked face (' + key + ').');
      rejectOverrides(value[key], where + '.' + key);
    }
  }

  function validateManifest(manifest) {
    assert(isRecord(manifest) && manifest.schema === SCHEMA, 'unsupported manifest schema.');
    assert(isRecord(manifest.canvas) && manifest.canvas.width === SIZE && manifest.canvas.height === SIZE,
      'the composition canvas must stay 1024 × 1024.');
    assert(manifest.canvas.alpha === 'straight', 'canvas alpha must be straight.');
    assert(isRecord(manifest.sprites), 'sprites are missing.');
    assert(isRecord(manifest.head), 'the locked face is missing.');
    assert(manifest.head.locked === true, 'head.locked must be true.');
    assert(manifest.head.z === 100, 'the locked face must use z = 100.');
    validateTransform(manifest.head.transform, 'head');

    for (const [id, sprite] of Object.entries(manifest.sprites)) {
      assert(isRecord(sprite), 'invalid sprite ' + id + '.');
      assert(['face', 'hand', 'hand-prop'].includes(sprite.role), 'invalid role for ' + id + '.');
      assert(typeof sprite.path === 'string' && sprite.path.trim().length > 0, 'missing path for ' + id + '.');
      assert(Array.isArray(sprite.source_size) && sprite.source_size.length === 2 &&
        sprite.source_size.every(n => Number.isInteger(n) && n > 0), 'invalid source_size for ' + id + '.');
      if (sprite.pivot !== undefined) {
        assert(Array.isArray(sprite.pivot) && sprite.pivot.length === 2 && sprite.pivot.every(Number.isFinite),
          'invalid pivot for ' + id + '.');
      }
    }

    const headSprite = manifest.sprites[manifest.head.sprite];
    assert(headSprite && headSprite.role === 'face', 'head.sprite must refer to a face sprite.');
    assert(isRecord(manifest.animations) && Object.keys(manifest.animations).length > 0, 'animations are missing.');
    assert(manifest.animations.none, 'a hand-free "none" animation is required.');

    for (const [id, animation] of Object.entries(manifest.animations)) {
      assert(isRecord(animation), 'invalid animation ' + id + '.');
      rejectOverrides(animation, 'animation ' + id);
      assert(Array.isArray(animation.frames) && animation.frames.length > 0, id + ' has no frames.');
      for (let index = 0; index < animation.frames.length; index += 1) {
        const frame = animation.frames[index];
        const where = id + ' frame ' + index;
        assert(isRecord(frame), 'invalid ' + where + '.');
        assert(Number.isFinite(frame.duration_ms) && frame.duration_ms > 0,
          where + ' needs a positive duration_ms.');
        assert(Array.isArray(frame.instances), where + ' needs an instances array.');
        assert(id !== 'none' || frame.instances.length === 0, 'the "none" animation must contain no hands.');
        for (const instance of frame.instances) {
          assert(isRecord(instance), 'invalid instance in ' + where + '.');
          const sprite = manifest.sprites[instance.sprite];
          assert(sprite, where + ' refers to unknown sprite ' + instance.sprite + '.');
          assert(sprite.role !== 'face' && instance.sprite !== manifest.head.sprite,
            where + ' must not reference a face sprite.');
          validateTransform(instance.transform, where + ' ' + instance.sprite);
          assert(Number.isFinite(instance.z) && instance.z !== manifest.head.z,
            where + ' hand z must be below or above the face.');
          if (instance.opacity !== undefined) {
            assert(Number.isFinite(instance.opacity) && instance.opacity >= 0 && instance.opacity <= 1,
              where + ' opacity must be between 0 and 1.');
          }
        }
      }
    }
    return manifest;
  }

  function frameAt(manifest, animationId, elapsedMs, options) {
    const animation = manifest.animations[animationId];
    assert(animation, 'unknown animation ' + animationId + '.');
    const elapsed = elapsedMs === undefined ? 0 : elapsedMs;
    assert(Number.isFinite(elapsed), 'elapsed time must be finite.');
    const durationMs = animation.frames.reduce((sum, frame) => sum + frame.duration_ms, 0);
    assert(Number.isFinite(durationMs), 'animation duration is too large.');
    const loop = !options || options.loop !== false;
    const time = Math.max(0, elapsed);
    const finished = !loop && time >= durationMs;
    const localMs = loop ? time % durationMs : Math.min(time, durationMs);
    let remaining = localMs;
    let index = animation.frames.length - 1;
    if (!finished) {
      for (let i = 0; i < animation.frames.length; i += 1) {
        if (remaining < animation.frames[i].duration_ms) {
          index = i;
          break;
        }
        remaining -= animation.frames[i].duration_ms;
      }
    }
    return {
      animation: animationId,
      index: index,
      frame: animation.frames[index],
      frameCount: animation.frames.length,
      durationMs: durationMs,
      localMs: localMs,
      finished: finished,
      loop: loop
    };
  }

  function getFrameAtTime(manifest, animationId, elapsedMs, options) {
    validateManifest(manifest);
    return frameAt(manifest, animationId, elapsedMs, options);
  }

  function commandFor(manifest, instance, isHead) {
    const sprite = manifest.sprites[instance.sprite];
    return {
      sprite: instance.sprite,
      path: sprite.path,
      role: sprite.role,
      source_size: sprite.source_size.slice(),
      transform: instance.transform.slice(),
      z: instance.z,
      opacity: instance.opacity === undefined ? 1 : instance.opacity,
      isHead: isHead
    };
  }

  function getDrawCommands(manifest, animationId, elapsedMs, options) {
    validateManifest(manifest);
    const settings = options || {};
    const selected = frameAt(manifest, animationId, elapsedMs, settings);
    const commands = [];
    // This is the sole source of face geometry. Nothing in an animation or
    // canvas layout may resize, replace, fit, or recenter this face.
    if (settings.faceVisible !== false) commands.push(commandFor(manifest, manifest.head, true));
    if (settings.handsVisible !== false) {
      selected.frame.instances.forEach(instance => commands.push(commandFor(manifest, instance, false)));
    }
    return commands.sort((a, b) => a.z - b.z);
  }

  function imageFor(images, command) {
    if (images && typeof images.get === 'function') return images.get(command.sprite) || images.get(command.path);
    return images && (images[command.sprite] || images[command.path]);
  }

  function drawContext(ctx, commands, images) {
    assert(ctx && typeof ctx.setTransform === 'function', 'a 2D canvas context is required.');
    assert(ctx.canvas && ctx.canvas.width === SIZE && ctx.canvas.height === SIZE,
      'the drawing canvas must stay 1024 × 1024; resize its CSS box only.');
    assert(Array.isArray(commands), 'draw commands must be an array.');
    ctx.save();
    try {
      ctx.setTransform(1, 0, 0, 1, 0, 0);
      ctx.globalAlpha = 1;
      ctx.globalCompositeOperation = 'source-over';
      ctx.clearRect(0, 0, SIZE, SIZE);
      ctx.imageSmoothingEnabled = false;
      for (const command of commands) {
        const image = imageFor(images, command);
        assert(image, 'image not loaded: ' + command.sprite + '.');
        ctx.setTransform.apply(ctx, command.transform);
        ctx.globalAlpha = command.opacity === undefined ? 1 : command.opacity;
        ctx.drawImage(image, 0, 0);
      }
    } finally {
      // Restores the caller's transform, alpha, and compositing settings.
      ctx.restore();
    }
  }

  return Object.freeze({
    SCHEMA: SCHEMA,
    CANVAS_SIZE: SIZE,
    validateManifest: validateManifest,
    getFrameAtTime: getFrameAtTime,
    getDrawCommands: getDrawCommands,
    drawContext: drawContext
  });
});
