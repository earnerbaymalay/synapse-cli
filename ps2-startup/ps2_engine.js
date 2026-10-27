// ==============================================================================
// PlayStation 2 // XFCE 4.20 Visual Engine
// Pure mathematical 3D perspective projection on 2D HTML5 Canvas.
// 0 dependencies, 60 FPS deterministic rendering, authentic PS2 aesthetic.
// ==============================================================================

const WIDTH = 1920;
const HEIGHT = 1080;
const DURATION = 12.0;

// Deterministic Pseudo-Random Generator (LCG)
let seed = 1337;
function lcg() {
  seed = (seed * 1664525 + 1013904223) % 4294967296;
  return seed / 4294967296;
}

// -------------------------------------------------------------
// 1. Monolith Pillars Generation (PS2 BIOS Memory Save Towers)
// -------------------------------------------------------------
function flightPathX(z) {
  if (z >= -60) {
    const p = (50 - z) / 110;
    const t = p * 4.5;
    return Math.sin(t * 0.5) * 8.0;
  } else if (z >= -480) {
    const p = (-60 - z) / 420;
    const ease = p * p * (3 - 2 * p);
    const bankS = Math.sin(ease * Math.PI);
    return Math.sin(4.5 * 0.5) * 8.0 + bankS * 32.0;
  }
  return 6.22;
}

const towers = [];
const TOWER_COUNT = 115;

for (let i = 0; i < TOWER_COUNT; i++) {
  const side = lcg() > 0.5 ? 1 : -1;
  const z = -lcg() * 580 + 15;
  const fx = flightPathX(z);
  const corridor = 22 + lcg() * 8;
  const spread = lcg() * 95;
  const x = fx + (corridor + spread) * side;

  const baseDist = Math.max(35, 50 - z);
  const heightFactor = 0.35 + 0.65 * Math.pow(lcg(), 0.8);
  let h = (12 + 0.54 * baseDist) * heightFactor;
  h = Math.max(25, Math.min(175, h));

  const w = 8 + lcg() * 10;
  const d = 8 + lcg() * 10;
  const phase = lcg() * Math.PI * 2;
  const delay = lcg() * 0.4;
  const hue = 195 + Math.floor(lcg() * 30); // 195 - 225 cyan to sapphire

  towers.push({
    x, y: 0, z,
    w, h, d,
    phase,
    delay,
    hue
  });
}

// -------------------------------------------------------------
// 2. Luminous Energy Orbs (Floating Sparks & Speed Motes)
// -------------------------------------------------------------
const orbs = [];
const ORB_COUNT = 360;
const orbColors = [
  '#38bdf8', // Cyan
  '#0284c7', // Ocean Blue
  '#c084fc', // Mauve / Violet
  '#f8fafc', // Starlight White
  '#34d399', // Emerald
];

for (let i = 0; i < ORB_COUNT; i++) {
  orbs.push({
    x: (lcg() - 0.5) * 260,
    y: lcg() * 120 - 10,
    z: -lcg() * 600 + 40,
    radius: 2.0 + lcg() * 3.5,
    orbitSpeed: 0.6 + lcg() * 1.2,
    orbitRadius: 8 + lcg() * 25,
    orbitPhase: lcg() * Math.PI * 2,
    color: orbColors[Math.floor(lcg() * orbColors.length)]
  });
}

// -------------------------------------------------------------
// 3. 3D Camera & Projection Math
// -------------------------------------------------------------
function getCamera(t) {
  let cx = 0, cy = 12, cz = 50;
  let tx = 0, ty = 22, tz = -80;
  let roll = 0;

  if (t < 4.5) {
    // Phase 1: Slow atmospheric glide
    const p = t / 4.5;
    cx = Math.sin(t * 0.5) * 8.0;
    cy = 12 + Math.sin(t * 0.35) * 3.0;
    cz = 50 - p * 110;
    tx = cx * 0.5;
    ty = 22;
    tz = cz - 120;
    roll = Math.sin(t * 0.4) * 0.03;
  } else if (t < 7.2) {
    // Phase 2: High-speed acceleration & banking curve
    const p = (t - 4.5) / 2.7;
    const ease = p * p * (3 - 2 * p);
    const bankS = Math.sin(ease * Math.PI);

    cx = Math.sin(4.5 * 0.5) * 8.0 + bankS * 32.0;
    cy = 15 + ease * 16.0;
    cz = -60 - ease * 420;
    tx = bankS * 20.0;
    ty = 22 + ease * 12.0;
    tz = cz - 140;
    roll = -bankS * 0.28; // Dynamic banking roll
  } else {
    // Phase 3 & 4: Logo reveal phase
    cx = 0; cy = 0; cz = 100;
    tx = 0; ty = 0; tz = 0;
    roll = 0;
  }

  // Camera forward, right, up orthonormal vectors
  let fx = tx - cx, fy = ty - cy, fz = tz - cz;
  const fLen = Math.hypot(fx, fy, fz) || 1;
  fx /= fLen; fy /= fLen; fz /= fLen;

  // Approximate world up = (0, 1, 0)
  // R = F x W = (-fz, 0, fx)
  let rx = -fz, ry = 0, rz = fx;
  const rLen = Math.hypot(rx, rz) || 1;
  rx /= rLen; rz /= rLen;

  // U = R x F
  let ux = ry * fz - rz * fy;
  let uy = rz * fx - rx * fz;
  let uz = rx * fy - ry * fx;

  // Apply camera roll around forward axis
  if (roll !== 0) {
    const cosR = Math.cos(roll), sinR = Math.sin(roll);
    const nrx = rx * cosR + ux * sinR;
    const nry = ry * cosR + uy * sinR;
    const nrz = rz * cosR + uz * sinR;
    const nux = -rx * sinR + ux * cosR;
    const nuy = -ry * sinR + uy * cosR;
    const nuz = -rz * sinR + uz * cosR;
    rx = nrx; ry = nry; rz = nrz;
    ux = nux; uy = nuy; uz = nuz;
  }

  return { cx, cy, cz, fx, fy, fz, rx, ry, rz, ux, uy, uz };
}

function projectPoint(x, y, z, cam) {
  // Vector from camera to point
  const dx = x - cam.cx;
  const dy = y - cam.cy;
  const dz = z - cam.cz;

  // Transform into camera space
  const camX = dx * cam.rx + dy * cam.ry + dz * cam.rz;
  const camY = dx * cam.ux + dy * cam.uy + dz * cam.uz;
  const camZ = dx * cam.fx + dy * cam.fy + dz * cam.fz;

  if (camZ <= 1.0) return null; // Behind or clipping plane

  const fov = 1050; // Focal length
  const sx = 960 + (camX / camZ) * fov;
  const sy = 540 - (camY / camZ) * fov;

  return { sx, sy, camZ, scale: fov / camZ };
}

// -------------------------------------------------------------
// 4. Main Rendering Function at Time t (0 <= t <= 12.0)
// -------------------------------------------------------------
function renderPS2Frame(ctx, t) {
  const cam = getCamera(t);

  // Background gradient: Deep ocean void with atmospheric twilight
  if (t < 7.2) {
    const bgGrad = ctx.createLinearGradient(0, 0, 0, HEIGHT);
    bgGrad.addColorStop(0, '#000208');
    bgGrad.addColorStop(0.55, '#020b1e');
    bgGrad.addColorStop(1, '#00040f');
    ctx.fillStyle = bgGrad;
    ctx.fillRect(0, 0, WIDTH, HEIGHT);
  } else {
    ctx.fillStyle = '#000208';
    ctx.fillRect(0, 0, WIDTH, HEIGHT);
  }

  // -----------------------------------------------------------
  // A. Render Monoliths (Phase 1 & 2)
  // -----------------------------------------------------------
  if (t < 7.5) {
    // Calculate monolith distances and sort back-to-front
    const sortedTowers = [];
    for (let i = 0; i < towers.length; i++) {
      const tow = towers[i];
      // Rise progress: smooth cubic ease-out over 2.6 seconds
      const riseP = Math.max(0.0, Math.min(1.0, (t - tow.delay) / 2.6));
      const rise = 1.0 - Math.pow(1.0 - riseP, 3);
      const curH = tow.h * rise;
      if (curH <= 0.2) continue;

      const dist = Math.hypot(tow.x - cam.cx, (curH * 0.5) - cam.cy, tow.z - cam.cz);
      // Cull towers behind camera
      const fDist = (tow.x - cam.cx) * cam.fx + (tow.z - cam.cz) * cam.fz;
      if (fDist > 1.0 && dist < 700) {
        sortedTowers.push({ tow, curH, dist });
      }
    }
    sortedTowers.sort((a, b) => b.dist - a.dist);

    // Draw sorted monoliths
    for (let i = 0; i < sortedTowers.length; i++) {
      const { tow, curH, dist } = sortedTowers[i];
      const hw = tow.w / 2, hd = tow.d / 2;
      const verts = [
        [-hw, 0, -hd], [hw, 0, -hd], [hw, 0, hd], [-hw, 0, hd],
        [-hw, curH, -hd], [hw, curH, -hd], [hw, curH, hd], [-hw, curH, hd]
      ];

      // Project all 8 box vertices
      const p = [];
      let allValid = true;
      for (let j = 0; j < 8; j++) {
        const v = verts[j];
        const proj = projectPoint(tow.x + v[0], v[1], tow.z + v[2], cam);
        if (!proj) { allValid = false; break; }
        p.push(proj);
      }
      if (!allValid) continue;

      // Distance fog opacity (smooth falloff)
      const fog = Math.max(0, Math.min(1, 1 - (dist / 520) ** 1.6));
      if (fog <= 0.01) continue;

      const pulse = 0.75 + 0.25 * Math.sin(t * 2.0 + tow.phase);
      const isSpeeding = t > 4.5 && t < 7.2;

      ctx.save();

      // Monolith body silhouette
      // We fill front, left, right faces
      const faces = [
        [3, 2, 6, 7], // front
        [0, 3, 7, 4], // left
        [1, 2, 6, 5], // right
      ];

      for (const f of faces) {
        ctx.beginPath();
        ctx.moveTo(p[f[0]].sx, p[f[0]].sy);
        ctx.lineTo(p[f[1]].sx, p[f[1]].sy);
        ctx.lineTo(p[f[2]].sx, p[f[2]].sy);
        ctx.lineTo(p[f[3]].sx, p[f[3]].sy);
        ctx.closePath();

        const grad = ctx.createLinearGradient(0, p[f[2]].sy, 0, p[f[0]].sy);
        grad.addColorStop(0, `rgba(2, 24, 56, ${0.75 * fog})`);
        grad.addColorStop(0.5, `rgba(1, 14, 36, ${0.85 * fog})`);
        grad.addColorStop(1, `rgba(0, 4, 14, ${0.92 * fog})`);
        ctx.fillStyle = grad;
        ctx.fill();
      }

      // Top glowing cap
      ctx.beginPath();
      ctx.moveTo(p[4].sx, p[4].sy);
      ctx.lineTo(p[5].sx, p[5].sy);
      ctx.lineTo(p[6].sx, p[6].sy);
      ctx.lineTo(p[7].sx, p[7].sy);
      ctx.closePath();
      ctx.fillStyle = `rgba(56, 189, 248, ${0.45 * fog * pulse})`;
      ctx.fill();

      // Iconic PS2 Crystal Monolith Edge Bevels (Cyan wireframe glow)
      ctx.strokeStyle = `rgba(56, 189, 248, ${0.85 * fog * pulse})`;
      ctx.lineWidth = Math.max(1.0, Math.min(2.8, (350 / dist)));
      ctx.beginPath();

      // Top perimeter
      ctx.moveTo(p[4].sx, p[4].sy);
      ctx.lineTo(p[5].sx, p[5].sy);
      ctx.lineTo(p[6].sx, p[6].sy);
      ctx.lineTo(p[7].sx, p[7].sy);
      ctx.lineTo(p[4].sx, p[4].sy);

      // Vertical edges
      ctx.moveTo(p[0].sx, p[0].sy); ctx.lineTo(p[4].sx, p[4].sy);
      ctx.moveTo(p[1].sx, p[1].sy); ctx.lineTo(p[5].sx, p[5].sy);
      ctx.moveTo(p[2].sx, p[2].sy); ctx.lineTo(p[6].sx, p[6].sy);
      ctx.moveTo(p[3].sx, p[3].sy); ctx.lineTo(p[7].sx, p[7].sy);

      ctx.stroke();

      ctx.restore();
    }
  }

  // -----------------------------------------------------------
  // B. Render Luminous Energy Orbs & Speed Streaks
  // -----------------------------------------------------------
  if (t < 7.6) {
    for (let i = 0; i < orbs.length; i++) {
      const orb = orbs[i];
      let ox = orb.x, oy = orb.y, oz = orb.z;

      if (t < 4.5) {
        ox += Math.sin(t * orb.orbitSpeed + orb.orbitPhase) * orb.orbitRadius;
        oy += Math.cos(t * orb.orbitSpeed + orb.orbitPhase) * (orb.orbitRadius * 0.4);
      } else {
        // Spiraling into central vortex during flight
        const p = (t - 4.5) / 2.7;
        const spiralSpeed = 3.0 + p * 8.0;
        ox = ox * (1 - p * 0.5) + Math.sin(t * spiralSpeed + orb.orbitPhase) * (18 * (1 - p * 0.7));
        oy = oy * (1 - p * 0.5) + Math.cos(t * spiralSpeed + orb.orbitPhase) * (14 * (1 - p * 0.7));
      }

      const proj = projectPoint(ox, oy, oz, cam);
      if (!proj) continue;

      const dist = proj.camZ;
      const fog = Math.max(0, Math.min(1, 1 - (dist / 480) ** 1.5));
      if (fog <= 0.02) continue;

      const r = Math.max(1.2, Math.min(12, orb.radius * proj.scale * 0.015));

      ctx.save();
      if (t > 4.8 && t < 7.2) {
        // High speed motion streak
        const streakLen = Math.min(60, (t - 4.5) * 24 * (proj.scale * 0.02));
        ctx.strokeStyle = orb.color;
        ctx.globalAlpha = 0.8 * fog;
        ctx.lineWidth = Math.max(1.0, r * 0.6);
        ctx.beginPath();
        ctx.moveTo(proj.sx, proj.sy);
        // Streak backwards along camera trajectory
        ctx.lineTo(proj.sx - (cam.cx - ox) * 0.04 * streakLen, proj.sy + (cam.cy - oy) * 0.04 * streakLen);
        ctx.stroke();
      } else {
        // Glowing radial orb
        ctx.globalAlpha = 0.9 * fog;
        ctx.fillStyle = orb.color;
        ctx.beginPath();
        ctx.arc(proj.sx, proj.sy, r, 0, Math.PI * 2);
        ctx.fill();

        // Soft outer glow
        ctx.globalAlpha = 0.25 * fog;
        ctx.beginPath();
        ctx.arc(proj.sx, proj.sy, r * 2.8, 0, Math.PI * 2);
        ctx.fill();
      }
      ctx.restore();
    }
  }

  // -----------------------------------------------------------
  // C. Celestial Burst / Supernova Flash (7.2s - 8.0s)
  // -----------------------------------------------------------
  if (t >= 7.15 && t <= 8.1) {
    const flashAlpha = t < 7.45 ? (t - 7.15) / 0.30 : 1.0 - (t - 7.45) / 0.65;
    const a = Math.max(0, Math.min(1, flashAlpha * 1.1));
    if (a > 0) {
      ctx.fillStyle = `rgba(224, 246, 255, ${a})`;
      ctx.fillRect(0, 0, WIDTH, HEIGHT);
    }
  }

  // -----------------------------------------------------------
  // D. Iconic PlayStation 2 // XFCE 4.20 Presentation (7.8s - 12.0s)
  // -----------------------------------------------------------
  if (t >= 7.8) {
    const p = Math.min(1.0, (t - 7.8) / 0.7);
    ctx.save();
    ctx.globalAlpha = p;

    // Deep cosmic PS2 radial twilight void
    const radGrad = ctx.createRadialGradient(WIDTH / 2, HEIGHT / 2 - 20, 100, WIDTH / 2, HEIGHT / 2, 850);
    radGrad.addColorStop(0, 'rgba(4, 20, 52, 0.60)');
    radGrad.addColorStop(0.6, 'rgba(1, 8, 26, 0.90)');
    radGrad.addColorStop(1, '#000208');
    ctx.fillStyle = radGrad;
    ctx.fillRect(0, 0, WIDTH, HEIGHT);

    // Drifting celestial stardust motes in background
    for (let i = 0; i < 45; i++) {
      const sx = (Math.sin(i * 12.3 + t * 0.25) * 0.5 + 0.5) * WIDTH;
      const sy = (Math.cos(i * 8.7 + t * 0.2) * 0.5 + 0.5) * HEIGHT;
      const sa = 0.2 + 0.3 * Math.sin(t * 1.5 + i);
      ctx.fillStyle = `rgba(186, 230, 253, ${sa})`;
      ctx.beginPath();
      ctx.arc(sx, sy, 1.2 + (i % 3) * 0.6, 0, Math.PI * 2);
      ctx.fill();
    }

    // --- Corner HUD Details ---
    ctx.font = '600 11px "JetBrains Mono", monospace';
    ctx.fillStyle = 'rgba(148, 163, 184, 0.6)';
    ctx.textAlign = 'left';
    ctx.fillText('BIOS 2.20 // KABY LAKE-R', 48, 48);
    ctx.fillText('ENDEAVOUROS // ARCH LINUX', 48, HEIGHT - 48);

    ctx.textAlign = 'right';
    ctx.fillText('SYSTEM MEMORY: 24 GB DUAL-CH', WIDTH - 48, 48);
    ctx.fillText('DISPLAY: eDP-1 1080p 60Hz', WIDTH - 48, HEIGHT - 48);

    // --- Central Emblem & Typography ---
    const cx = WIDTH / 2;
    const cy = HEIGHT / 2 - 22;

    // 1. 3D Crystal Hexagon Monolith Prism (XFCE / PS2 Emblem)
    const symX = cx - 250;
    const symY = cy - 14;
    const sRad = 48;

    ctx.save();
    ctx.shadowColor = '#38bdf8';
    ctx.shadowBlur = 24;
    ctx.lineWidth = 2.8;
    ctx.strokeStyle = 'rgba(56, 189, 248, 0.95)';
    ctx.fillStyle = 'rgba(2, 132, 199, 0.25)';

    ctx.beginPath();
    for (let k = 0; k < 6; k++) {
      const ang = (Math.PI / 3) * k - Math.PI / 6;
      const px = symX + Math.cos(ang) * sRad;
      const py = symY + Math.sin(ang) * sRad;
      if (k === 0) ctx.moveTo(px, py);
      else ctx.lineTo(px, py);
    }
    ctx.closePath();
    ctx.fill();
    ctx.stroke();

    // Internal 3D facets
    ctx.lineWidth = 1.4;
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.7)';
    ctx.beginPath();
    ctx.moveTo(symX, symY - sRad);
    ctx.lineTo(symX, symY + sRad);
    ctx.moveTo(symX - Math.cos(Math.PI/6) * sRad, symY - Math.sin(Math.PI/6) * sRad);
    ctx.lineTo(symX, symY);
    ctx.lineTo(symX + Math.cos(Math.PI/6) * sRad, symY - Math.sin(Math.PI/6) * sRad);
    ctx.stroke();

    // Inner glowing cyan core
    ctx.beginPath();
    ctx.arc(symX, symY, 9, 0, Math.PI * 2);
    ctx.fillStyle = '#38bdf8';
    ctx.shadowColor = '#38bdf8';
    ctx.shadowBlur = 18;
    ctx.fill();
    ctx.restore();

    // 2. Main "XFCE" PS2 Iconic Typography
    ctx.save();
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    ctx.font = '900 108px "Arial Black", "Helvetica Neue", sans-serif';

    const textX = cx - 170;
    const textY = cy - 14;

    // Glowing cyan drop shadow
    ctx.shadowColor = 'rgba(56, 189, 248, 0.9)';
    ctx.shadowBlur = 38;

    // Vertical linear gradient (White -> Electric Cyan -> Deep Blue)
    const textGrad = ctx.createLinearGradient(textX, textY - 60, textX, textY + 60);
    textGrad.addColorStop(0.0, '#ffffff');
    textGrad.addColorStop(0.28, '#7dd3fc');
    textGrad.addColorStop(0.68, '#0284c7');
    textGrad.addColorStop(1.0, '#0369a1');

    ctx.fillStyle = textGrad;
    ctx.fillText('XFCE', textX, textY);

    // Beveled white hairline stroke
    ctx.shadowBlur = 0;
    ctx.lineWidth = 1.8;
    ctx.strokeStyle = 'rgba(255, 255, 255, 0.7)';
    ctx.strokeText('XFCE', textX, textY);

    // "4.20" Super-Script Badge
    ctx.font = '900 32px "Arial Black", sans-serif';
    const badgeGrad = ctx.createLinearGradient(textX + 310, textY - 48, textX + 310, textY - 14);
    badgeGrad.addColorStop(0, '#ffffff');
    badgeGrad.addColorStop(1, '#38bdf8');
    ctx.fillStyle = badgeGrad;
    ctx.shadowColor = 'rgba(56, 189, 248, 0.95)';
    ctx.shadowBlur = 16;
    ctx.fillText('4.20', textX + 312, textY - 26);
    ctx.restore();

    // 3. Shimmering Light Sheen across "XFCE"
    const sheenP = (t - 8.3) / 2.2;
    if (sheenP >= 0 && sheenP <= 1.25) {
      ctx.save();
      ctx.beginPath();
      ctx.rect(textX - 10, textY - 75, 450, 130);
      ctx.clip();

      const sheenX = (textX - 140) + sheenP * 620;
      const sGrad = ctx.createLinearGradient(sheenX - 60, textY - 60, sheenX + 60, textY + 60);
      sGrad.addColorStop(0, 'rgba(255, 255, 255, 0)');
      sGrad.addColorStop(0.5, 'rgba(255, 255, 255, 0.9)');
      sGrad.addColorStop(1, 'rgba(255, 255, 255, 0)');

      ctx.fillStyle = sGrad;
      ctx.transform(1, 0, -0.4, 1, 0, 0);
      ctx.fillRect(sheenX - 45, textY - 80, 90, 160);
      ctx.restore();
    }

    // 4. Subtitle: "DESKTOP ENVIRONMENT" (Classic Sony PS2 Spaced Sans)
    ctx.save();
    ctx.textAlign = 'center';
    ctx.font = '600 20px "Segoe UI", "Inter", sans-serif';
    ctx.letterSpacing = '0.64em';
    ctx.fillStyle = '#94a3b8';
    ctx.shadowColor = 'rgba(148, 163, 184, 0.45)';
    ctx.shadowBlur = 12;
    ctx.fillText('DESKTOP ENVIRONMENT', cx + 18, cy + 68);
    ctx.restore();

    // 5. Glowing Divider Line
    ctx.save();
    const divGrad = ctx.createLinearGradient(cx - 300, 0, cx + 300, 0);
    divGrad.addColorStop(0, 'rgba(56, 189, 248, 0)');
    divGrad.addColorStop(0.5, 'rgba(56, 189, 248, 0.9)');
    divGrad.addColorStop(1, 'rgba(56, 189, 248, 0)');
    ctx.fillStyle = divGrad;
    ctx.shadowColor = 'rgba(56, 189, 248, 0.7)';
    ctx.shadowBlur = 12;
    ctx.fillRect(cx - 300, cy + 98, 600, 1.5);
    ctx.restore();

    // 6. OS & Machine Subheading
    ctx.save();
    ctx.textAlign = 'center';
    ctx.font = '600 13px "JetBrains Mono", monospace';
    ctx.letterSpacing = '0.36em';
    ctx.fillStyle = '#cbd5e1';
    ctx.fillText('ENDEAVOUROS LINUX • DELL LATITUDE 7490', cx + 10, cy + 128);
    ctx.restore();

    // 7. Hardware & System Status Badge
    const badgeY = cy + 174;
    const bW = 580;
    const bH = 38;
    ctx.save();
    ctx.fillStyle = 'rgba(15, 23, 42, 0.76)';
    ctx.strokeStyle = 'rgba(56, 189, 248, 0.32)';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.roundRect(cx - bW / 2, badgeY - bH / 2, bW, bH, 6);
    ctx.fill();
    ctx.stroke();

    // Pulsing Green LED
    const ledPulse = 0.65 + 0.35 * Math.sin(t * 4);
    ctx.beginPath();
    ctx.arc(cx - 245, badgeY, 4.5, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(16, 185, 129, ${ledPulse})`;
    ctx.shadowColor = '#10b981';
    ctx.shadowBlur = 10;
    ctx.fill();

    // Badge Text
    ctx.shadowBlur = 0;
    ctx.font = '600 11px "JetBrains Mono", monospace';
    ctx.fillStyle = '#64748b';
    ctx.letterSpacing = '0.12em';
    ctx.textAlign = 'left';
    ctx.textBaseline = 'middle';
    ctx.fillText('SYSTEM READY', cx - 232, badgeY);

    ctx.fillStyle = '#475569';
    ctx.fillText('|', cx - 90, badgeY);

    ctx.fillStyle = '#64748b';
    ctx.fillText('VA-API ACCELERATED', cx - 70, badgeY);

    ctx.fillStyle = '#475569';
    ctx.fillText('|', cx + 115, badgeY);

    ctx.fillStyle = '#64748b';
    ctx.fillText('PIPEWIRE 1.6', cx + 135, badgeY);
    ctx.restore();

    ctx.restore();
  }
}

// Export for browser or node
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { renderPS2Frame, WIDTH, HEIGHT, DURATION };
}
