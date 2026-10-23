// Carved relief runs off the main thread; only completed bitmaps reach the page.
// The carving is a height field, lit in three dimensions. Shading the relief
// avoids the flat outlines and identical highlight on every vector ornament.
function generateFrame(width, height, moulding, seed, canvas, finish, ratio) {
  const cw = Math.ceil((width + 20) * ratio);
  const ch = Math.ceil((height + 20) * ratio);
  canvas.width = cw;
  canvas.height = ch;
  const context = canvas.getContext('2d');
  const relief = new Float32Array(cw * ch);
  const mask = new Uint8Array(cw * ch);
  const m = moulding;
  const { hue, saturation, tone, detail, gilding } = finish;
  const tau = Math.PI * 2;
  const clamp = (v, lo, hi) => Math.max(lo, Math.min(hi, v));
  const ridge = (v, radius) => {
    const t = Math.max(0, 1 - Math.abs(v) / radius);
    return t * t * (3 - 2 * t);
  };
  const noise = (x, y) => {
    let n = Math.imul(x ^ seed, 374761393) ^ Math.imul(y, 668265263);
    n = Math.imul(n ^ (n >>> 13), 1274126177);
    return ((n ^ (n >>> 16)) >>> 0) / 4294967295;
  };
  const smoothNoise = (x, y, size) => {
    const xx = x / size, yy = y / size;
    const ix = Math.floor(xx), iy = Math.floor(yy);
    const fx = xx - ix, fy = yy - iy;
    const sx = fx * fx * (3 - 2 * fx), sy = fy * fy * (3 - 2 * fy);
    return (noise(ix, iy) * (1 - sx) + noise(ix + 1, iy) * sx) * (1 - sy)
      + (noise(ix, iy + 1) * (1 - sx) + noise(ix + 1, iy + 1) * sx) * sy;
  };
  // Ovolo, deep cove, carved frieze, torus, beaded fillet, inner scotia.
  const profile = [[0,.05],[.025,.49],[.055,.71],[.085,.73],[.12,.53],
    [.145,.23],[.17,.22],[.19,.47],[.215,.54],[.24,.31],[.27,.28],
    [.63,.28],[.66,.31],[.69,.64],[.715,.77],[.74,.68],[.765,.32],
    [.79,.31],[.815,.52],[.84,.55],[.865,.27],[.89,.19],[.92,.48],
    [.945,.53],[.975,.39],[1,.02]];
  const depthAt = new Float32Array(Math.ceil(m * ratio) + 2);
  for (let i = 0; i < depthAt.length; i++) {
    const t = clamp(i / (m * ratio), 0, 1);
    let p = 1;
    while (p < profile.length - 1 && profile[p][0] < t) p++;
    const [a, av] = profile[p - 1], [b, bv] = profile[p];
    const mix = (t - a) / (b - a);
    depthAt[i] = av + (bv - av) * (mix * mix * (3 - 2 * mix));
  }
  const pitch = m * (detail === 'guilloche' ? .48 : detail === 'fluted' ? .37 : .42);
  const radius = Math.max(.45, m * .009);
  const phase = (seed % 997) / 997 * tau;
  const carve = (x, y) => {
    const nx = Math.min(x, width - x), ny = Math.min(y, height - y);
    const d = Math.min(nx, ny);
    if (d < 0 || d >= m) return null;
    let u, length;
    if (ny <= nx) {
      u = y < height / 2 ? x : width - x;
      length = width;
    } else {
      u = x > width / 2 ? y : height - y;
      length = height;
    }
    const t = d / m;
    let z = depthAt[Math.min(depthAt.length - 1, Math.round(d * ratio))];
    const usable = Math.max(m, length - 2 * m);
    const count = Math.max(1, Math.round(usable / pitch));
    const step = usable / count;
    const p = ((u - m) / step) * tau;
    const centre = m * .45;
    const local = ((u - m) / step - Math.floor((u - m) / step) - .5) * step;
    // Double interwoven ribbons, with an engraved line down each raised band.
    if (t > .265 && t < .645) {
      const amp = m * .125;
      const wave = detail === 'guilloche'
        ? Math.sin(p) * (.82 + .18 * Math.cos(p * 2))
        : detail === 'linear' ? Math.sin(p) * .74 : Math.sin(p);
      for (const sign of [-1, 1]) {
        const offset = d - centre - sign * amp * wave;
        const band = ridge(offset, m * .033);
        z += .28 * band - .07 * ridge(offset, radius);
        z -= .045 * ridge(Math.abs(offset) - m * .037, radius);
      }
      // Small chased ovals/lozenges fill the spaces between the ribbons.
      const ellipse = detail === 'fluted'
        ? Math.hypot(local / (step * .21), (d - centre) / (m * .075))
        : Math.abs(local / (step * .25)) + Math.abs((d - centre) / (m * .09));
      z += .20 * ridge(ellipse - 1, .24);
      z += .10 * ridge(ellipse, .72);
      z -= .045 * ridge(ellipse - .68, .12);
      // Concentric chased seals and tiny engine-turned rays inside each unit.
      const sealAngle = Math.atan2((d - centre) / (m * .075), local / (step * .21));
      z += .075 * ridge(ellipse - .43 - Math.sin(sealAngle * 8) * .055, .085);
      if (detail === 'reeded') {
        z += .035 * Math.cos(sealAngle * 16) * ridge(ellipse - .79, .17);
      }
      // Fine cross ties articulate the interlace into individual carved panels.
      z += .07 * ridge(Math.abs(local) - step * .43, m * .008)
        * ridge(d - centre, m * .14);
      // A fine diaper ground is visible only in the recesses of the carving.
      const lattice = Math.sin((u + d) * 1.8) * Math.sin((u - d) * 1.8);
      z += lattice * .009 * (1 - ridge(d - centre, m * .035));
    }
    // Tiny rope-twist borders, alternating pearls, and fine gadroons.
    if (t > .12 && t < .24) {
      const rope = d - m * .185 - Math.sin(u / (m * .048) * tau) * m * .014;
      z += .15 * ridge(rope, m * .017);
      z -= .025 * ridge(rope, m * .004);
    }
    if (t > .755 && t < .84) {
      const pearlPitch = m * .058;
      const beadX = ((u / pearlPitch + .5) % 1 - .5) * pearlPitch;
      const r = Math.hypot(beadX, d - m * .797) / (m * .021);
      z += .23 * Math.sqrt(Math.max(0, 1 - r * r));
    }
    if (t > .02 && t < .11) {
      const flutes = Math.pow(.5 + .5 * Math.cos(u / (m * .044) * tau + t * 9), 4);
      z += .055 * flutes * Math.sin((t - .02) / .09 * Math.PI);
    }
    // Engraved hairline fillets, rather than broad painted stripes.
    for (const line of [.115, .247, .655, .746, .857, .966]) {
      z -= .045 * ridge(d - m * line, m * .005);
    }
    // Corner cartouches are geometric oval seals with engine-turned rays.
    if (nx < m && ny < m) {
      const a = (nx + ny - m * .83) * Math.SQRT1_2;
      const b = (nx - ny) * Math.SQRT1_2;
      const er = Math.hypot(a / (m * .30), b / (m * .15));
      const angle = Math.atan2(b, a);
      const surround = ridge(er - 1, .15);
      z += .26 * surround + .12 * ridge(er - .72, .10);
      if (er < .63) {
        z += .16 * (1 - er / .63);
        z += .035 * Math.cos(angle * 24 + phase) * ridge(er - .4, .22);
      }
    }
    // Uneven gesso and minute leaf wrinkles soften mathematically perfect relief.
    z += (smoothNoise(x, y, 3.8) - .5) * .008;
    z += (noise(Math.floor(x * 2), Math.floor(y * 2)) - .5) * .003;
    return z * m * (.095 + gilding * .015);
  };
  // Only evaluate the border; the painting opening stays fully transparent.
  for (let py = 0; py < ch; py++) {
    const y = (py + .5) / ratio - 10;
    for (let px = 0; px < cw; px++) {
      const x = (px + .5) / ratio - 10;
      if (x < 0 || y < 0 || x > width || y > height) continue;
      if (x >= m && x <= width - m && y >= m && y <= height - m) continue;
      const z = carve(x, y);
      if (z === null) continue;
      const index = py * cw + px;
      relief[index] = z;
      mask[index] = 255;
    }
  }
  // Convert the artwork's chosen finish to metal reflectance. Antiqued gold
  // uses warm shadows, pale highlights, and cooler reflections across the cove.
  const metal = (h, s, l) => {
    const a = s / 100 * Math.min(l / 100, 1 - l / 100);
    const f = (n) => {
      const k = (n + h / 30) % 12;
      return 255 * (l / 100 - a * Math.max(-1, Math.min(k - 3, 9 - k, 1)));
    };
    return [f(0), f(8), f(4)];
  };
  const base = metal(hue - 2, Math.max(12, saturation * .83), 52 + tone * .35);
  const pixels = context.createImageData(cw, ch);
  const out = pixels.data;
  for (let py = 1; py < ch - 1; py++) {
    const y = py / ratio - 10;
    for (let px = 1; px < cw - 1; px++) {
      const index = py * cw + px;
      if (!mask[index]) continue;
      const x = px / ratio - 10;
      const z = relief[index];
      const dx = (relief[index + 1] - relief[index - 1]) * ratio * .5;
      const dy = (relief[index + cw] - relief[index - cw]) * ratio * .5;
      const normal = Math.hypot(dx, dy, 1);
      const nnx = -dx / normal, nny = -dy / normal, nnz = 1 / normal;
      const diffuse = Math.max(0, nnx * -.43 + nny * -.57 + nnz * .70);
      const reflection = Math.max(0, nnx * -.23 + nny * -.31 + nnz * .923);
      const specular = Math.pow(reflection, 38) * .65;
      const leaf = smoothNoise(x, y, m * .48);
      const mottling = smoothNoise(x, y, 5);
      const grain = noise(px, py) - .5;
      const recess = clamp(z / (m * .075), 0, 1);
      const patina = (.78 + recess * .22) * (.93 + leaf * .12);
      const brightness = (.35 + diffuse * .91) * patina;
      const foil = (mottling - .5) * 7 + grain * 3;
      const o = index * 4;
      out[o] = clamp(base[0] * brightness + specular * 170 + foil, 0, 255);
      out[o + 1] = clamp(base[1] * brightness + specular * 167 + foil, 0, 255);
      out[o + 2] = clamp(base[2] * brightness + specular * 150 + foil, 0, 255);
      out[o + 3] = mask[index];
    }
  }
  context.putImageData(pixels, 0, 0);
}

self.onmessage = ({ data }) => {
  const { id, width, height, moulding, seed, finish, ratio } = data;
  const canvas = new OffscreenCanvas(1, 1);
  generateFrame(width, height, moulding, seed, canvas, finish, ratio);
  const bitmap = canvas.transferToImageBitmap();
  self.postMessage({ id, bitmap }, [bitmap]);
};
