// Minimal SVG path sampler for M/L/C/Z paths: point + tangent at fraction t.
function tokenize(d) {
  return d.match(/[MLCZmlcz]|-?\d*\.?\d+(?:e-?\d+)?/g) || [];
}
function cubic(p0, p1, p2, p3, t) {
  const u = 1 - t;
  return u*u*u*p0 + 3*u*u*t*p1 + 3*u*t*t*p2 + t*t*t*p3;
}
function cubicDer(p0, p1, p2, p3, t) {
  const u = 1 - t;
  return 3*u*u*(p1-p0) + 6*u*t*(p2-p1) + 3*t*t*(p3-p2);
}
// Returns {pts: [{x,y,len}], total} - polyline samples with cumulative length.
export function samplePath(d, per = 24) {
  const tk = tokenize(d);
  let i = 0, x = 0, y = 0, sx = 0, sy = 0;
  const pts = [];
  let total = 0;
  const push = (nx, ny) => {
    const dx = nx - x, dy = ny - y;
    total += Math.hypot(dx, dy);
    pts.push({x: nx, y: ny, len: total});
    x = nx; y = ny;
  };
  while (i < tk.length) {
    const cmd = tk[i++];
    if (cmd === 'M') { x = +tk[i++]; y = +tk[i++]; sx = x; sy = y; pts.push({x, y, len: total}); }
    else if (cmd === 'L') { push(+tk[i++], +tk[i++]); }
    else if (cmd === 'Z') { push(sx, sy); }
    else if (cmd === 'C') {
      const x1 = +tk[i++], y1 = +tk[i++], x2 = +tk[i++], y2 = +tk[i++], x3 = +tk[i++], y3 = +tk[i++];
      for (let k = 1; k <= per; k++) {
        const t = k / per;
        push(cubic(x, x1, x2, x3, t), cubic(y, y1, y2, y3, t));
      }
    }
  }
  return {pts, total};
}
export function pointAt(samples, frac) {
  const {pts, total} = samples;
  const target = frac * total;
  let lo = 0, hi = pts.length - 1;
  while (lo < hi) { const mid = (lo + hi) >> 1; (pts[mid].len < target) ? lo = mid + 1 : hi = mid; }
  const b = pts[Math.max(1, lo)], a = pts[Math.max(0, lo - 1)];
  const seg = b.len - a.len || 1;
  const f = Math.min(1, Math.max(0, (target - a.len) / seg));
  const x = a.x + (b.x - a.x) * f, y = a.y + (b.y - a.y) * f;
  const ang = Math.atan2(b.y - a.y, b.x - a.x) * 180 / Math.PI;
  return {x, y, ang};
}
