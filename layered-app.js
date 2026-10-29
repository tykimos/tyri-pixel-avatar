/* Tyri Pixel Avatar by Taeyoung Kim (tykimos). See LICENSE. */
(function () {
  'use strict';

  const $ = id => document.getElementById(id);
  const status = $('status');
  const engine = window.TyriLayeredPlayer;
  const manifest = window.TYRI_LAYERS;
  const baseline = $('baseline-canvas');
  const preview = $('preview-canvas');
  const baselineCtx = baseline.getContext('2d');
  const previewCtx = preview.getContext('2d');
  const labels = { none: '손 없음', wave: '손 흔들기', peace: '브이', shush: '쉿', heart: '하트', write: '쓰기', think: '생각' };
  const images = Object.create(null);
  const motionQuery = window.matchMedia ? window.matchMedia('(prefers-reduced-motion: reduce)') : null;
  let selected = 'none';
  let mode = 'composite';
  let elapsedMs = 0;
  let playing = !(motionQuery && motionQuery.matches);
  let lastTimestamp = null;
  let ready = false;
  let previousDownloads = '';
  let lastFrameLabel = '';
  let raf = 0;

  function showError(error) {
    playing = false;
    ready = false;
    cancelAnimationFrame(raf);
    status.classList.add('error');
    status.textContent = '미리보기를 불러오지 못했습니다. 전체 폴더를 함께 내려받았는지 확인해 주세요.\n' + error.message;
    $('play-toggle').disabled = true;
    $('restart').disabled = true;
  }

  function labelFor(id) {
    return manifest.animations[id].label || labels[id] || id;
  }

  function setPressed(container, attribute, value) {
    container.querySelectorAll('button').forEach(button => {
      button.setAttribute('aria-pressed', String(button.getAttribute(attribute) === value));
    });
  }

  function loadSprite(id, sprite) {
    return new Promise((resolve, reject) => {
      const image = new Image();
      image.onload = function () {
        if (image.naturalWidth !== sprite.source_size[0] || image.naturalHeight !== sprite.source_size[1]) {
          reject(new Error('PNG 크기가 좌표 기록과 다릅니다: ' + sprite.path));
          return;
        }
        images[id] = image;
        resolve();
      };
      image.onerror = () => reject(new Error('PNG를 읽을 수 없습니다: ' + sprite.path));
      image.src = sprite.path;
    });
  }

  function faceBounds() {
    const sprite = manifest.sprites[manifest.head.sprite];
    const m = manifest.head.transform;
    const box = sprite.content_bbox || [0, 0, sprite.source_size[0], sprite.source_size[1]];
    const [left, top, width, height] = box;
    const points = [[left, top], [left + width, top], [left, top + height], [left + width, top + height]].map(([x, y]) =>
      [m[0] * x + m[2] * y + m[4], m[1] * x + m[3] * y + m[5]]);
    const xs = points.map(point => point[0]);
    const ys = points.map(point => point[1]);
    return { x: Math.min.apply(null, xs), y: Math.min.apply(null, ys),
      width: Math.max.apply(null, xs) - Math.min.apply(null, xs),
      height: Math.max.apply(null, ys) - Math.min.apply(null, ys) };
  }

  function drawGuides(ctx) {
    if (!$('show-guides').checked) return;
    const bounds = faceBounds();
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.globalAlpha = 1;
    ctx.strokeStyle = '#c05b19';
    ctx.lineWidth = 3;
    ctx.setLineDash([12, 10]);
    ctx.strokeRect(bounds.x, bounds.y, bounds.width, bounds.height);
    ctx.setLineDash([]);
    ctx.strokeStyle = 'rgba(192,91,25,.7)';
    const x = bounds.x + bounds.width / 2;
    const y = bounds.y + bounds.height / 2;
    ctx.beginPath();
    ctx.moveTo(x - 16, y); ctx.lineTo(x + 16, y);
    ctx.moveTo(x, y - 16); ctx.lineTo(x, y + 16);
    ctx.stroke();
    ctx.restore();
  }

  function handLinkLabel(id, index, count) {
    const sprite = manifest.sprites[id];
    const side = { right: '오른손', left: '왼손', both: '양손' }[sprite.side] || '손';
    const surface = { palm: '손바닥', back: '손등', mixed: '' }[sprite.surface];
    const part = sprite.role === 'hand-prop' ? ' · 소품 포함' : '';
    return side + (surface ? ' · ' + surface : '') + part + (count > 1 ? ' ' + (index + 1) : '') + ' PNG';
  }

  function updateDownloads(frame) {
    const ids = Array.from(new Set(frame.instances.map(instance => instance.sprite)));
    const key = ids.join('|');
    if (key === previousDownloads) return;
    previousDownloads = key;
    const container = $('hand-downloads');
    container.replaceChildren();
    if (!ids.length) {
      const empty = document.createElement('span');
      empty.className = 'empty';
      empty.textContent = '이 동작에는 손 레이어가 없습니다.';
      container.append(empty);
      return;
    }
    ids.forEach((id, index) => {
      const link = document.createElement('a');
      const sprite = manifest.sprites[id];
      link.href = sprite.path;
      link.download = sprite.path.split('/').pop();
      link.className = 'download';
      link.textContent = handLinkLabel(id, index, ids.length);
      link.title = id;
      container.append(link);
    });
  }

  function renderBaseline() {
    engine.drawContext(baselineCtx, engine.getDrawCommands(manifest, 'none', 0), images);
    drawGuides(baselineCtx);
  }

  function renderPreview() {
    if (!ready) return;
    const frame = engine.getFrameAtTime(manifest, selected, elapsedMs);
    const commands = engine.getDrawCommands(manifest, selected, elapsedMs, {
      faceVisible: mode !== 'hands',
      handsVisible: mode !== 'face'
    });
    engine.drawContext(previewCtx, commands, images);
    drawGuides(previewCtx);
    const frameLabel = (frame.index + 1) + '/' + frame.frameCount + ' 프레임 · ' + (frame.durationMs / 1000).toFixed(2) + '초 반복';
    if (lastFrameLabel !== frameLabel) {
      $('timing').textContent = frameLabel;
      lastFrameLabel = frameLabel;
    }
    $('progress').style.width = (frame.localMs / frame.durationMs * 100).toFixed(2) + '%';
    updateDownloads(frame.frame);
  }

  function tick(timestamp) {
    if (!ready || !playing) return;
    if (lastTimestamp !== null) elapsedMs += Math.max(0, timestamp - lastTimestamp);
    lastTimestamp = timestamp;
    try {
      renderPreview();
      raf = requestAnimationFrame(tick);
    } catch (error) {
      showError(error);
    }
  }

  function schedulePlayback() {
    cancelAnimationFrame(raf);
    lastTimestamp = null;
    $('play-toggle').textContent = playing ? '일시정지' : '재생';
    $('play-toggle').setAttribute('aria-label', playing ? '애니메이션 일시정지' : '애니메이션 재생');
    if (playing && ready) raf = requestAnimationFrame(tick);
  }

  function selectAnimation(id) {
    selected = id;
    elapsedMs = 0;
    lastTimestamp = null;
    previousDownloads = '\u0000';
    setPressed($('animation-choices'), 'data-animation', id);
    $('selected-label').textContent = labelFor(id);
    preview.setAttribute('aria-label', '타이리 ' + labelFor(id) + ' 미리보기');
    renderPreview();
  }

  function setupControls() {
    const order = ['none', 'wave', 'peace', 'shush', 'heart', 'write', 'think'];
    const animationIds = Object.keys(manifest.animations).sort((a, b) => {
      const ai = order.includes(a) ? order.indexOf(a) : order.length;
      const bi = order.includes(b) ? order.indexOf(b) : order.length;
      return ai - bi;
    });
    animationIds.forEach(id => {
      const button = document.createElement('button');
      button.type = 'button';
      button.className = 'choice';
      button.dataset.animation = id;
      button.textContent = labelFor(id);
      button.setAttribute('aria-pressed', 'false');
      button.addEventListener('click', () => selectAnimation(id));
      $('animation-choices').append(button);
    });
    $('layer-modes').addEventListener('click', event => {
      const button = event.target.closest('button[data-mode]');
      if (!button) return;
      mode = button.dataset.mode;
      setPressed($('layer-modes'), 'data-mode', mode);
      $('mode-label').textContent = { composite: '같은 얼굴 + 독립 손', face: '고정된 얼굴 레이어', hands: '독립된 손 레이어' }[mode];
      $('active-layer-label').textContent = { composite: '합성', face: '얼굴만', hands: '손만' }[mode];
      renderPreview();
    });
    $('backgrounds').addEventListener('click', event => {
      const button = event.target.closest('button[data-background]');
      if (!button) return;
      const background = button.dataset.background;
      setPressed($('backgrounds'), 'data-background', background);
      document.querySelectorAll('.stage').forEach(stage => { stage.dataset.background = background; });
    });
    $('play-toggle').addEventListener('click', () => {
      playing = !playing;
      schedulePlayback();
    });
    $('restart').addEventListener('click', () => {
      mode = 'composite';
      setPressed($('layer-modes'), 'data-mode', mode);
      $('mode-label').textContent = '같은 얼굴 + 독립 손';
      $('active-layer-label').textContent = '합성';
      selectAnimation('none');
    });
    $('show-guides').addEventListener('change', () => {
      renderBaseline();
      renderPreview();
    });
    // Backgrounding a mobile tab does not fast-forward a gesture when it opens.
    document.addEventListener('visibilitychange', () => { lastTimestamp = null; });
    const faceSprite = manifest.sprites[manifest.head.sprite];
    const faceLink = $('face-download');
    faceLink.href = faceSprite.path;
    faceLink.download = faceSprite.path.split('/').pop();
    faceLink.removeAttribute('aria-disabled');
    const m = manifest.head.transform;
    const bounds = faceBounds();
    const nice = n => Number(n.toFixed(2));
    $('head-geometry').textContent = '투명 여백을 제외한 얼굴 영역 ' + nice(bounds.width) + ' × ' + nice(bounds.height) +
      ' px · 위치 (' + nice(bounds.x) + ', ' + nice(bounds.y) + ') · 고정 변환 [' + m.map(nice).join(', ') + ']';
    $('play-toggle').disabled = false;
    $('restart').disabled = false;
  }

  async function start() {
    if (!engine) throw new Error('layered-player.js가 없습니다.');
    if (!manifest) throw new Error('data/layers.js가 없습니다.');
    engine.validateManifest(manifest);
    await Promise.all(Object.entries(manifest.sprites).map(([id, sprite]) => loadSprite(id, sprite)));
    ready = true;
    setupControls();
    renderBaseline();
    selectAnimation(manifest.animations.wave ? 'wave' : 'none');
    status.textContent = playing ? '' : '동작 줄이기 설정에 따라 일시정지했습니다. 재생 버튼으로 시작할 수 있습니다.';
    schedulePlayback();
  }

  start().catch(showError);
})();
