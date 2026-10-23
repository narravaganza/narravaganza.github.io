const test = require('node:test');
const assert = require('node:assert/strict');
const { readFileSync } = require('node:fs');
const { join } = require('node:path');
const vm = require('node:vm');

const source = readFileSync(join(__dirname, '../assets/js/collection-frames.js'), 'utf8');

function page({ workerSupport = true } = {}) {
  const animationTasks = [];
  const workers = [];
  const draws = [];
  let intersection, resize;
  const frames = Array.from({ length: 16 }, (_, i) => ({
    width: 980, height: 680, dataset: {}, style: { setProperty() {} },
    querySelector: () => ({ getAttribute: () => `/assets/images/artists/painting-${i}.png` }),
    append(canvas) { this.canvas = canvas; },
    getBoundingClientRect() { return { width: this.width, height: this.height }; },
  }));
  class Worker {
    constructor() { this.messages = []; workers.push(this); }
    postMessage(message) { this.messages.push(message); }
    terminate() { this.terminated = true; }
  }
  class IntersectionObserver {
    constructor(callback) { intersection = callback; }
    observe() {}
    disconnect() {}
  }
  class ResizeObserver {
    constructor(callback) { resize = callback; }
    observe() {}
    disconnect() {}
  }
  const context = {
    document: {
      currentScript: { dataset: { frameWorker: '/worker.js' } },
      querySelectorAll: () => frames,
      createElement: () => ({
        dataset: {}, classList: { add() {} }, setAttribute() {},
        getContext: () => ({ drawImage: bitmap => draws.push(bitmap) }),
        remove() { this.removed = true; },
      }),
    },
    window: { Worker: workerSupport ? Worker : undefined, OffscreenCanvas: class {},
      IntersectionObserver, ResizeObserver, devicePixelRatio: 1, addEventListener() {} },
    Worker, IntersectionObserver, ResizeObserver,
    getComputedStyle: () => ({ paddingTop: '60px' }),
    requestAnimationFrame: callback => animationTasks.push(callback),
  };
  vm.runInNewContext(source, context);
  return {
    frames, workers, draws,
    visible(index, isIntersecting = true) {
      intersection([{ target: frames[index], isIntersecting }]);
    },
    resize(index, width) {
      frames[index].width = width;
      resize([{ target: frames[index] }]);
    },
    flush() { while (animationTasks.length) animationTasks.shift()(); },
    complete() {
      const worker = workers[0];
      const { id } = worker.messages.shift();
      const bitmap = { width: 1000, height: 700, close() { this.closed = true; } };
      worker.onmessage({ data: { id, bitmap } });
      return bitmap;
    },
  };
}

test('offscreen frames do no rendering; nearby frames use one worker job at a time', () => {
  const p = page();
  p.flush();
  assert.equal(p.workers.length, 0);
  p.visible(0); p.visible(1); p.flush();
  assert.equal(p.workers.length, 1);
  assert.equal(p.workers[0].messages.length, 1);
  p.resize(15, 600); p.flush();
  assert.equal(p.workers[0].messages.length, 1);
  p.complete(); p.flush();
  assert.equal(p.draws.length, 1);
  assert.equal(p.workers[0].messages.length, 1);
  p.complete(); p.flush();
  assert.equal(p.draws.length, 2);
  assert.equal(p.workers[0].messages.length, 0);
});

test('resizing during a render discards the stale bitmap and uses the latest size', () => {
  const p = page();
  p.visible(0); p.flush();
  p.resize(0, 500); p.resize(0, 600);
  const stale = p.complete(); p.flush();
  assert.equal(stale.closed, true);
  assert.equal(p.draws.length, 0);
  assert.equal(p.workers[0].messages[0].width, 600);
  p.complete(); p.flush();
  assert.equal(p.draws.length, 1);
});

test('scrolling a frame away cancels its pending work and discards an in-flight result', () => {
  const p = page();
  p.visible(0); p.visible(1); p.flush();
  p.visible(0, false); p.visible(1, false);
  const discarded = p.complete(); p.flush();
  assert.equal(discarded.closed, true);
  assert.equal(p.draws.length, 0);
  assert.equal(p.workers[0].messages.length, 0);
  p.resize(0, 550); p.visible(0); p.flush();
  assert.equal(p.workers[0].messages[0].width, 550);
});

test('unsupported or failed workers leave the CSS frame available', () => {
  const unsupported = page({ workerSupport: false });
  assert.equal(unsupported.workers.length, 0);
  assert.equal(unsupported.frames[0].canvas, undefined);
  const p = page();
  p.visible(0); p.flush();
  p.workers[0].onerror();
  assert.equal(p.workers[0].terminated, true);
  assert.ok(p.frames.every(frame => frame.canvas.removed));
  p.visible(1); p.flush();
  assert.equal(p.workers.length, 1);
});

test('the worker renders and transfers a bitmap without window or document', () => {
  const workerSource = readFileSync(join(__dirname, '../assets/js/collection-frame-worker.js'), 'utf8');
  let result;
  class OffscreenCanvas {
    constructor(width, height) { this.width = width; this.height = height; }
    getContext() {
      return {
        createImageData: (width, height) => ({ data: new Uint8ClampedArray(width * height * 4) }),
        putImageData() {},
      };
    }
    transferToImageBitmap() { return { width: this.width, height: this.height }; }
  }
  const context = { OffscreenCanvas, self: {
    postMessage: (message, transfers) => { result = { message, transfers }; },
  } };
  vm.runInNewContext(workerSource, context);
  context.self.onmessage({ data: { id: 7, width: 30, height: 40, moulding: 5,
    seed: 42, ratio: 1.5, finish: { hue: 40, saturation: 30, tone: 3,
      detail: 'linear', gilding: 0.8 } } });
  assert.equal(result.message.id, 7);
  assert.equal(result.message.bitmap.width, 75);
  assert.equal(result.message.bitmap.height, 90);
  assert.equal(result.transfers[0], result.message.bitmap);
});
