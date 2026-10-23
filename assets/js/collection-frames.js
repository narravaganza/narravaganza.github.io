// One responsive carved-gilt renderer. A procedural height field supplies the
// relief, normals and metal lighting; each painting has its own finish and weight.
(() => {
  const hash = (value) => Array.from(value).reduce((seed, char) =>
    Math.imul(seed ^ char.charCodeAt(0), 16777619) >>> 0, 2166136261);
  const randomFrom = (seed) => () => {
    seed = (seed + 0x6D2B79F5) | 0;
    let n = Math.imul(seed ^ (seed >>> 15), 1 | seed);
    n ^= n + Math.imul(n ^ (n >>> 7), 61 | n);
    return ((n ^ (n >>> 14)) >>> 0) / 4294967296;
  };
  const number = (value) => Math.round(value * 100) / 100;

  // Hue, saturation, tonal offset, moulding width, engraving, gilding richness.
  // Impressionist works get broad, luminous gold with raised geometric relief.
  // Cooler finishes still complement monochrome stone and architecture.
  const finishes = {
    vincent_van_gogh:           [41, 49,  3, 1.20, 'reeded',    .90],
    edgar_degastation:         [39, 47,  2, 1.38, 'fluted',    .96],
    candinsky:                [43, 26, 10,  .85, 'linear',    .80],
    mondrianna:               [42, 18, 10,  .85, 'linear',    .80],
    francis_bacon_sandwich:    [30, 30, -7,  .98, 'reeded',    .55],
    frida_kahlories:           [35, 43, -2, 1.16, 'guilloche', .80],
    paul_kleenex:             [39, 36,  8,  .88, 'linear',    .80],
    mc_escher:                [39,  9,  5,  .86, 'reeded',    .78],
    gericault_of_duty:        [38, 40, -3, 1.18, 'fluted',    .88],
    hieronymus_bosch:         [40, 36, -2, 1.12, 'guilloche', .82],
    max_bill:                 [42, 11, 14,  .76, 'linear',    .78],
    michael_jackson_pollock:  [40, 32,  3,  .92, 'linear',    .80],
    michelangelo_david_bowie: [42, 21, 12,  .92, 'fluted',    .82],
    pablo_pikachu:            [36, 26, -3,  .90, 'reeded',    .80],
    salvador_dolly:           [37, 39, -1, 1.10, 'guilloche', .85],
    claude_monet_laundering:  [43, 48,  7, 1.55, 'fluted',   1.00],
  };
  const finishFor = (source, seed) => {
    const [hue, saturation, tone, weight, detail, gilding] = finishes[source] || [40, 36, 4, 1, 'reeded', .6];
    const random = randomFrom(seed);
    return {
      hue: hue + (random() - .5) * 2,
      saturation, tone, weight, detail, gilding,
    };
  };

  const frames = [...document.querySelectorAll('.fine-art-collection .collection-frame')];
  const profiles = new WeakMap();
  frames.forEach((frame) => {
    const image = frame.querySelector('img');
    if (!image) return;
    const source = image.getAttribute('src').split('/').pop().replace(/(?:-\d+)?\.(?:avif|png|jpe?g|webp)$/i, '');
    const seed = hash(source);
    const finish = finishFor(source, seed);
    profiles.set(frame, finish);
    frame.dataset.frameSeed = seed;
    frame.dataset.frameFinish = finish.detail;
    frame.style.setProperty('--frame-weight', finish.weight);
    frame.style.setProperty('--frame-base', `hsl(${finish.hue} ${finish.saturation}% ${50 + finish.tone}%)`);
  });

  const workerURL = document.currentScript?.dataset.frameWorker;
  if (!workerURL || !window.Worker || !window.OffscreenCanvas
      || !window.IntersectionObserver || !window.ResizeObserver) return;

  const active = new Set();
  const pending = new Set();
  const ornaments = new WeakMap();
  let worker;
  let job;
  let scheduled = false;
  let failed = false;
  let sequence = 0;

  const dimensions = (frame) => {
    const { width, height } = frame.getBoundingClientRect();
    const moulding = parseFloat(getComputedStyle(frame).paddingTop);
    const ratio = Math.min(window.devicePixelRatio || 1, 1.5);
    return { width, height, moulding, ratio,
      key: [width, height, moulding, ratio].map(number).join(',') };
  };
  const schedule = () => {
    if (scheduled || job || failed || !pending.size) return;
    scheduled = true;
    requestAnimationFrame(renderNext);
  };
  const queue = (frame) => {
    if (!active.has(frame) || failed) return;
    pending.add(frame);
    schedule();
  };
  const fallback = () => {
    failed = true;
    pending.clear();
    worker?.terminate();
    visibility.disconnect();
    resizing.disconnect();
    frames.forEach(frame => ornaments.get(frame)?.remove());
  };
  const receive = ({ data: { id, bitmap } }) => {
    const finished = job;
    job = null;
    if (finished?.id === id && active.has(finished.frame)) {
      const { frame, key } = finished;
      if (dimensions(frame).key === key) {
        const canvas = ornaments.get(frame);
        canvas.width = bitmap.width;
        canvas.height = bitmap.height;
        canvas.getContext('2d').drawImage(bitmap, 0, 0);
        canvas.dataset.size = key;
      } else {
        queue(frame);
      }
    }
    bitmap.close();
    schedule();
  };
  function renderNext() {
    scheduled = false;
    if (job || failed) return;
    for (const frame of pending) {
      pending.delete(frame);
      if (!active.has(frame)) continue;
      const size = dimensions(frame);
      const canvas = ornaments.get(frame);
      if (!size.width || !size.height || !Number.isFinite(size.moulding)
          || size.moulding < 1 || canvas.dataset.size === size.key) continue;
      try {
        if (!worker) {
          worker = new Worker(workerURL);
          worker.onmessage = receive;
          worker.onerror = fallback;
          worker.onmessageerror = fallback;
        }
        job = { id: ++sequence, frame, key: size.key };
        worker.postMessage({ id: job.id, width: size.width, height: size.height,
          moulding: size.moulding, ratio: size.ratio,
          seed: Number(frame.dataset.frameSeed), finish: profiles.get(frame) });
      } catch {
        fallback();
      }
      break;
    }
  }

  // Keep offscreen artwork cheap, including when the whole viewport is resized.
  const visibility = new IntersectionObserver((entries) => {
    for (const { target: frame, isIntersecting } of entries) {
      if (isIntersecting) {
        active.add(frame);
        queue(frame);
      } else {
        active.delete(frame);
        pending.delete(frame);
      }
    }
  }, { rootMargin: '400px 0px' });
  const resizing = new ResizeObserver(entries => entries.forEach(({ target }) => queue(target)));
  window.addEventListener('resize', () => active.forEach(queue), { passive: true });
  frames.forEach((frame, index) => {
    if (!profiles.has(frame)) return;
    const ornament = document.createElement('canvas');
    ornament.id = `collection-frame-${index}`;
    ornament.classList.add('collection-frame-ornament');
    ornament.setAttribute('aria-hidden', 'true');
    ornament.setAttribute('focusable', 'false');
    frame.append(ornament);
    ornaments.set(frame, ornament);
    visibility.observe(frame);
    resizing.observe(frame);
  });
})();
