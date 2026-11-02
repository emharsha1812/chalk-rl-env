// The eight drawings and spring movement are adapted from the supplied cube reference.
(() => {
  const setupCube = () => {
    const figure = document.querySelector('.anatomy-figure');
    const viewport = document.getElementById('cubeViewport');
    const cubeSvg = document.getElementById('cubeSvg');
    const toggle = figure?.querySelector('.diagram-toggle');
    const label = toggle?.querySelector('.toggle-label');
    const symbol = toggle?.querySelector('.toggle-symbol');
    const status = document.getElementById('cube-status');
    if (!figure || !viewport || !cubeSvg || !toggle || !label || !symbol || !status) return;

    const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
    const state = {
      isDissected: false,
      isDragging: false,
      dragStartX: 0,
      dragStartY: 0,
      dragStartYaw: -32,
      dragStartPitch: 28,
      activePointerId: null,
      orbitYaw: -32,
      orbitPitch: 28,
      simTime: 0
    };
    const springs = {
      dissect: { val: 0.0, vel: 0, target: 0.0, stiffness: 110, damping: 16 },
      yaw:     { val: -32, vel: 0, target: -32, stiffness: 150, damping: 19 },
      pitch:   { val: 28,  vel: 0, target: 28, stiffness: 150, damping: 19 },
      press:   { val: 0.0, vel: 0, target: 0.0, stiffness: 280, damping: 16 }
    };
    function stepSpring(s, dt) {
      const force = -s.stiffness * (s.val - s.target);
      const damp = -s.damping * s.vel;
      s.vel += (force + damp) * dt;
      s.val += s.vel * dt;
    }

    const ROOM_COMPONENTS = [
      {
        id: 'observations',
        index: '01',
        shortName: 'OBSERVATIONS',
        badge: true,
        // Compact position capping the top of the cubic room
        homePos: { x: 0, y: 0, z: 78 },
        // Dissected showcase offset on screen (Top-Center)
        dissectScreenOffset: { sx: 0, sy: -210 },
        dissectScale: 0.92,
        labelOffset: { lx: 155, ly: -18, side: 'right' },
        subSpecs: ['Messages and tool results', 'What the agent receives']
      },
      {
        id: 'agent',
        index: '02',
        shortName: 'AGENT',
        badge: true,
        // Compact position inside room on left floor tile
        homePos: { x: -32, y: 34, z: -20 },
        // Dissected showcase offset on screen (Middle-Left)
        dissectScreenOffset: { sx: -375, sy: 65 },
        dissectScale: 1.25,
        labelOffset: { lx: -75, ly: 10, side: 'left' },
        subSpecs: ['Uses a model to work', 'Acts through messages and tools']
      },
      {
        id: 'task',
        index: '03',
        shortName: 'TASK',
        badge: false,
        // Compact position at the center of the room floor
        homePos: { x: 6, y: 6, z: -20 },
        // Dissected showcase offset on screen (Center Heart of Room)
        dissectScreenOffset: { sx: 0, sy: -45 },
        dissectScale: 1.25,
        labelOffset: { lx: 95, ly: -28, side: 'right' },
        subSpecs: ['Instructions and steps', 'The work to be done']
      },
      {
        id: 'judge',
        index: '04',
        shortName: 'JUDGE',
        badge: true,
        // Compact position inside room on right floor tile
        homePos: { x: 48, y: -14, z: -20 },
        // Dissected showcase offset on screen (Middle-Right)
        dissectScreenOffset: { sx: 365, sy: 65 },
        dissectScale: 1.22,
        labelOffset: { lx: 70, ly: 6, side: 'right' },
        subSpecs: ['Checks the work', 'Returns a score']
      },
      {
        id: 'tools',
        index: '05',
        shortName: 'TOOLS',
        badge: true,
        // Compact position: Back-Left Wall of the Cubic Room
        homePos: { x: -78, y: 0, z: 28 },
        // Dissected showcase offset on screen (Upper-Left)
        dissectScreenOffset: { sx: -320, sy: -135 },
        dissectScale: 0.92,
        labelOffset: { lx: -105, ly: -15, side: 'left' },
        subSpecs: ['Actions available to the agent', 'Shell and file tools']
      },
      {
        id: 'data',
        index: '06',
        shortName: 'DATA',
        badge: false,
        // Compact position: Back-Right Wall of the Cubic Room
        homePos: { x: 4, y: -78, z: 28 },
        // Dissected showcase offset on screen (Upper-Right)
        dissectScreenOffset: { sx: 320, sy: -135 },
        dissectScale: 0.92,
        labelOffset: { lx: 105, ly: -15, side: 'right' },
        subSpecs: ['Files and dependencies', 'Inputs used by the task']
      },
      {
        id: 'workspace',
        index: '07',
        shortName: 'WORKSPACE',
        badge: false,
        // Compact position: Base Floor Slab of the Cubic Room
        homePos: { x: 0, y: 0, z: -26 },
        // Dissected showcase offset on screen (Lower-Center)
        dissectScreenOffset: { sx: 0, sy: 120 },
        dissectScale: 0.88,
        labelOffset: { lx: -145, ly: 10, side: 'left' },
        subSpecs: ['An isolated place to work', 'One sandbox for a run']
      },
      {
        id: 'runtime',
        index: '08',
        shortName: 'RUNTIME',
        badge: true,
        // Compact position: Under-Room Server Basement
        homePos: { x: 0, y: 0, z: -54 },
        // Dissected showcase offset on screen (Bottom-Center)
        dissectScreenOffset: { sx: 0, sy: 265 },
        dissectScale: 0.88,
        labelOffset: { lx: 150, ly: 12, side: 'right' },
        subSpecs: ['Runs the sandbox', 'Container or virtual machine']
      }
    ];
    const SVG_CENTER_X = 640;
    const SVG_CENTER_Y = 415;

    function projectPoint(x, y, z, yawDeg, pitchDeg, offsetX = 0, offsetY = 0, scale = 1.0) {
      const effectiveYaw = ((yawDeg + 72) * Math.PI) / 180;
      const pitch = (pitchDeg * Math.PI) / 180;

      const rx = (x * Math.cos(effectiveYaw) - y * Math.sin(effectiveYaw)) * scale;
      const ry = (x * Math.sin(effectiveYaw) + y * Math.cos(effectiveYaw)) * scale;
      const rz = z * scale;

      const sx = SVG_CENTER_X + offsetX + rx;
      const sy = SVG_CENTER_Y + offsetY + ry * Math.sin(pitch) - rz * Math.cos(pitch);
      const depth = ry * Math.cos(pitch) + rz * Math.sin(pitch);
      return { x: sx, y: sy, depth };
    }

    function ptsToPoly(pts) {
      return pts.map(p => `${p.x.toFixed(1)},${p.y.toFixed(1)}`).join(' ');
    }

    function buildIsoBox(cx, cy, cz, wx, wy, h, yaw, pitch, offX, offY, scale, opts = {}) {
      const hw = wx / 2;
      const hd = wy / 2;
      const zTop = cz + h / 2;
      const zBot = cz - h / 2;

      const t0 = projectPoint(cx - hw, cy - hd, zTop, yaw, pitch, offX, offY, scale);
      const t1 = projectPoint(cx + hw, cy - hd, zTop, yaw, pitch, offX, offY, scale);
      const t2 = projectPoint(cx + hw, cy + hd, zTop, yaw, pitch, offX, offY, scale);
      const t3 = projectPoint(cx - hw, cy + hd, zTop, yaw, pitch, offX, offY, scale);

      const b0 = projectPoint(cx - hw, cy - hd, zBot, yaw, pitch, offX, offY, scale);
      const b1 = projectPoint(cx + hw, cy - hd, zBot, yaw, pitch, offX, offY, scale);
      const b2 = projectPoint(cx + hw, cy + hd, zBot, yaw, pitch, offX, offY, scale);
      const b3 = projectPoint(cx - hw, cy + hd, zBot, yaw, pitch, offX, offY, scale);

      const stroke = opts.stroke || 'var(--stroke-main)';
      const strokeW = opts.strokeWidth || 1.3;
      const topFill = opts.topFill || 'var(--surface-top)';
      const leftFill = opts.leftFill || 'var(--surface-left)';
      const rightFill = opts.rightFill || 'var(--surface-right)';

      const effectiveYawRad = ((yaw + 72) * Math.PI) / 180;
      const sideFaces = [
        { pts: [t3, t2, b2, b3], nx: 0, ny: 1, fill: leftFill },
        { pts: [t1, t2, b2, b1], nx: 1, ny: 0, fill: rightFill },
        { pts: [t0, t3, b3, b0], nx: -1, ny: 0, fill: leftFill },
        { pts: [t0, t1, b1, b0], nx: 0, ny: -1, fill: rightFill }
      ];

      const visibleSides = sideFaces.filter(f => {
        const camDot = f.nx * Math.sin(effectiveYawRad) + f.ny * Math.cos(effectiveYawRad);
        return camDot > -0.05;
      });

      let svg = '';
      visibleSides.forEach(f => {
        svg += `<polygon points="${ptsToPoly(f.pts)}" fill="${f.fill}" stroke="${stroke}" stroke-width="${strokeW}" stroke-linejoin="round" />`;
      });
      svg += `<polygon points="${ptsToPoly([t0, t1, t2, t3])}" fill="${topFill}" stroke="${stroke}" stroke-width="${strokeW}" stroke-linejoin="round" />`;

      return { svg, t0, t1, t2, t3, b0, b1, b2, b3 };
    }

    /********************************************************************
     * 4. ANIMATED 3D CUBIC ROOM MODULE RENDERERS (ALL 8 ANIMATIONS)
     * Each component is drawn around its local origin `(0, 0, 0)` and
     * projected with its animated offset `(offX, offY)` and `scale`.
     ********************************************************************/
    function renderRoomComponent(idx, yaw, pitch, offX, offY, scale, t, press) {
      let out = '';

      if (idx === 0) {
        // 01: Observations.
        const beamBackL = buildIsoBox(-78, 0, 0, 12, 168, 9, yaw, pitch, offX, offY, scale);
        const beamBackR = buildIsoBox(6, -78, 0, 156, 12, 9, yaw, pitch, offX, offY, scale);
        const beamFrontL = buildIsoBox(0, 78, 0, 168, 9, 6, yaw, pitch, offX, offY, scale, { topFill: 'var(--surface-left)' });
        const beamFrontR = buildIsoBox(78, 0, 0, 9, 156, 6, yaw, pitch, offX, offY, scale, { topFill: 'var(--surface-left)' });

        const scanSlide = Math.sin(t * 2.2) * 34;
        const domeSlideX = Math.cos(t * 1.7) * 24;
        const gantryX = buildIsoBox(0, scanSlide, 2, 154, 12, 6, yaw, pitch, offX, offY, scale);
        const gantryY = buildIsoBox(domeSlideX, 0, 2, 12, 154, 6, yaw, pitch, offX, offY, scale);

        const domeBase = buildIsoBox(domeSlideX, scanSlide, 8, 38, 38, 9, yaw, pitch, offX, offY, scale, {
          topFill: 'var(--surface-accent)',
          leftFill: 'var(--surface-accent)',
          rightFill: 'var(--surface-accent)',
          stroke: 'var(--surface-top)',
          strokeWidth: 1.0
        });
        const domeCap = buildIsoBox(domeSlideX, scanSlide, 15, 22, 22, 7, yaw, pitch, offX, offY, scale);

        out += beamBackL.svg + beamBackR.svg + gantryX.svg + gantryY.svg + beamFrontL.svg + beamFrontR.svg + domeBase.svg + domeCap.svg;

        // Sweeping laser scan cone
        const lensOrigin = projectPoint(domeSlideX, scanSlide, -4, yaw, pitch, offX, offY, scale);
        const raySpread = 34 + Math.sin(t * 4) * 5;
        const rayCorners = [
          projectPoint(domeSlideX - raySpread, scanSlide - raySpread, -52, yaw, pitch, offX, offY, scale),
          projectPoint(domeSlideX + raySpread, scanSlide - raySpread, -52, yaw, pitch, offX, offY, scale),
          projectPoint(domeSlideX + raySpread, scanSlide + raySpread, -52, yaw, pitch, offX, offY, scale),
          projectPoint(domeSlideX - raySpread, scanSlide + raySpread, -52, yaw, pitch, offX, offY, scale)
        ];
        rayCorners.forEach(rc => {
          out += `<line x1="${lensOrigin.x.toFixed(1)}" y1="${lensOrigin.y.toFixed(1)}" x2="${rc.x.toFixed(1)}" y2="${rc.y.toFixed(1)}" stroke="var(--stroke-subtle)" stroke-width="0.9" stroke-dasharray="3 3" opacity="0.7" />`;
        });
        out += `<polygon points="${ptsToPoly(rayCorners)}" fill="url(#cubeHatch)" stroke="var(--stroke-main)" stroke-width="0.85" stroke-dasharray="3 2" opacity="0.5" />`;
      }

      else if (idx === 1) {
        // 02: Agent.
        const bobZ = Math.sin(t * 3.8) * 4.5;
        const reach = press * 14 + Math.max(0, Math.sin(t * 3.8)) * 8;

        const pad = buildIsoBox(0, 0, 3, 46, 46, 6, yaw, pitch, offX, offY, scale, { topFill: 'var(--surface-left)' });
        const base = buildIsoBox(0, 0, 9, 32, 32, 9, yaw, pitch, offX, offY, scale);

        const tx = reach * 0.22;
        const ty = -reach * 0.22;
        const torso = buildIsoBox(tx, ty, 24 + bobZ * 0.5, 24, 24, 22, yaw, pitch, offX, offY, scale, {
          topFill: 'var(--surface-accent)',
          leftFill: 'var(--surface-accent)',
          rightFill: 'var(--surface-accent)',
          stroke: 'var(--surface-top)',
          strokeWidth: 1.0
        });

        const armShoulder = buildIsoBox(tx + 12 + reach * 0.35, ty - 12 - reach * 0.35, 27 + bobZ * 0.6, 24, 7, 7, yaw, pitch, offX, offY, scale);
        const armClaw = buildIsoBox(tx + 22 + reach * 0.75, ty - 20 - reach * 0.75, 25 + bobZ * 0.6, 9, 18, 7, yaw, pitch, offX, offY, scale, {
          topFill: press > 0.2 ? 'var(--surface-accent)' : 'var(--surface-top)'
        });

        const head = buildIsoBox(tx, ty, 43 + bobZ, 26, 26, 15, yaw, pitch, offX, offY, scale);
        const antenna = buildIsoBox(tx, ty, 54 + bobZ * 1.2, 4, 4, 9, yaw, pitch, offX, offY, scale);

        out += pad.svg + base.svg + torso.svg + armShoulder.svg + armClaw.svg + head.svg + antenna.svg;

        const headPt = projectPoint(tx, ty, 51 + bobZ, yaw, pitch, offX, offY, scale);
        out += `<text x="${headPt.x.toFixed(1)}" y="${(headPt.y + 3).toFixed(1)}" text-anchor="middle" fill="var(--stroke-main)" class="font-mono-tech" font-size="${(10.5 * scale).toFixed(1)}" font-weight="700">AI</text>`;
      }

      else if (idx === 2) {
        // 03: Task.
        const legOffsets = [[-20, -20], [20, -20], [20, 20], [-20, 20]];
        legOffsets.forEach(([lx, ly]) => {
          out += buildIsoBox(lx, ly, 7, 7, 7, 14, yaw, pitch, offX, offY, scale).svg;
        });

        const tableTop = buildIsoBox(0, 0, 17, 56, 56, 6, yaw, pitch, offX, offY, scale);
        out += tableTop.svg;

        const orbitAng = t * 2.3;
        const c1x = Math.cos(orbitAng) * 12 + press * 5;
        const c1y = Math.sin(orbitAng) * 12 - press * 5;
        const c1z = 31 + Math.sin(t * 4.5) * 4.5 + press * 6;

        const c2x = Math.cos(orbitAng + Math.PI) * 13;
        const c2y = Math.sin(orbitAng + Math.PI) * 13;
        const c2z = 27 + Math.cos(t * 4.5) * 3.5;

        const sh1 = projectPoint(c1x, c1y, 20.5, yaw, pitch, offX, offY, scale);
        const sh2 = projectPoint(c2x, c2y, 20.5, yaw, pitch, offX, offY, scale);
        out += `<ellipse cx="${sh1.x.toFixed(1)}" cy="${sh1.y.toFixed(1)}" rx="${(7 * scale).toFixed(1)}" ry="${(4 * scale).toFixed(1)}" fill="url(#cubeHatch)" stroke="var(--stroke-subtle)" stroke-width="0.8" />`;
        out += `<ellipse cx="${sh2.x.toFixed(1)}" cy="${sh2.y.toFixed(1)}" rx="${(6 * scale).toFixed(1)}" ry="${(3.5 * scale).toFixed(1)}" fill="url(#cubeHatch)" stroke="var(--stroke-subtle)" stroke-width="0.8" />`;

        const cube1 = buildIsoBox(c1x, c1y, c1z, 15, 15, 15, yaw, pitch, offX, offY, scale, {
          topFill: 'var(--surface-accent)',
          leftFill: 'var(--surface-accent)',
          rightFill: 'var(--surface-accent)',
          stroke: 'var(--surface-top)',
          strokeWidth: 1.0
        });
        const cube2 = buildIsoBox(c2x, c2y, c2z, 12, 12, 12, yaw, pitch, offX, offY, scale);
        out += cube1.svg + cube2.svg;
      }

      else if (idx === 3) {
        // 04: Judge.
        const plinth = buildIsoBox(0, 0, 4, 40, 40, 7, yaw, pitch, offX, offY, scale, { topFill: 'var(--surface-left)' });
        const verifierBox = buildIsoBox(0, 0, 14, 28, 28, 14, yaw, pitch, offX, offY, scale, {
          topFill: 'var(--surface-accent)',
          leftFill: 'var(--surface-accent)',
          rightFill: 'var(--surface-accent)',
          stroke: 'var(--surface-top)',
          strokeWidth: 1.0
        });
        out += plinth.svg + verifierBox.svg;

        const springCompress = Math.sin(t * 3.8) * 4 - press * 7;
        const coilH = Math.max(10, 21 + springCompress);
        const coils = 4;
        const totalPts = coils * 16;
        const zCoilStart = 22;
        let coilPath = '';
        for (let i = 0; i <= totalPts; i++) {
          const frac = i / totalPts;
          const ang = frac * coils * Math.PI * 2 + t * 2.2;
          const cx = Math.cos(ang) * 12;
          const cy = Math.sin(ang) * 12;
          const cz = zCoilStart + frac * coilH;
          const p = projectPoint(cx, cy, cz, yaw, pitch, offX, offY, scale);
          coilPath += (i === 0 ? `M ${p.x.toFixed(1)} ${p.y.toFixed(1)}` : ` L ${p.x.toFixed(1)} ${p.y.toFixed(1)}`);
        }
        out += `<path d="${coilPath}" fill="none" stroke="var(--stroke-main)" stroke-width="4.0" stroke-linecap="round" />`;
        out += `<path d="${coilPath}" fill="none" stroke="var(--surface-top)" stroke-width="1.6" stroke-linecap="round" />`;

        const zTopHead = 23 + coilH + 7;
        const scoreHead = buildIsoBox(0, 0, zTopHead, 30, 22, 14, yaw, pitch, offX, offY, scale);
        out += scoreHead.svg;

        const scorePt = projectPoint(0, 0, zTopHead + 8, yaw, pitch, offX, offY, scale);
        out += `<text x="${scorePt.x.toFixed(1)}" y="${(scorePt.y + 3).toFixed(1)}" text-anchor="middle" fill="var(--stroke-main)" class="font-mono-tech" font-size="${(8.8 * scale).toFixed(1)}" font-weight="700">SCORE</text>`;
      }

      else if (idx === 4) {
        // 05: Tools.
        const wallSlab = buildIsoBox(0, 0, 0, 12, 168, 98, yaw, pitch, offX, offY, scale);
        out += wallSlab.svg;

        const cliFrame = buildIsoBox(5, -36, 14, 5, 60, 36, yaw, pitch, offX, offY, scale, {
          topFill: 'var(--surface-accent)',
          leftFill: 'var(--surface-accent)',
          rightFill: 'var(--surface-accent)',
          stroke: 'var(--surface-top)',
          strokeWidth: 0.9
        });
        out += cliFrame.svg;

        for (let lineIdx = 0; lineIdx < 3; lineIdx++) {
          const zLine = 24 - lineIdx * 8;
          const len = 20 + ((Math.floor(t * 4) + lineIdx * 11) % 24);
          const pA = projectPoint(8.5, -60, zLine, yaw, pitch, offX, offY, scale);
          const pB = projectPoint(8.5, -60 + len, zLine, yaw, pitch, offX, offY, scale);
          out += `<line x1="${pA.x.toFixed(1)}" y1="${pA.y.toFixed(1)}" x2="${pB.x.toFixed(1)}" y2="${pB.y.toFixed(1)}" stroke="var(--surface-top)" stroke-width="1.7" />`;
        }

        const domFrame = buildIsoBox(5, 34, 16, 5, 56, 34, yaw, pitch, offX, offY, scale);
        const domInner = buildIsoBox(7, 34, 14, 3, 46, 22, yaw, pitch, offX, offY, scale, { topFill: 'url(#cubeHatch)' });
        out += domFrame.svg + domInner.svg;

        const activePortIdx = Math.floor(t * 2.6) % 5;
        [-50, -24, 8, 36, 60].forEach((py, pIdx) => {
          const isHot = pIdx === activePortIdx;
          const port = buildIsoBox(6 + (isHot ? 2.5 : 0), py, -24, 5, 14, 14, yaw, pitch, offX, offY, scale, {
            topFill: isHot ? 'var(--surface-top)' : 'var(--surface-accent)',
            leftFill: 'var(--surface-accent)',
            rightFill: 'var(--surface-accent)',
            stroke: isHot ? 'var(--stroke-main)' : 'var(--surface-top)',
            strokeWidth: isHot ? 1.3 : 0.8
          });
          out += port.svg;
        });
      }

      else if (idx === 5) {
        // 06: Data.
        const wallSlab = buildIsoBox(0, 0, 0, 156, 12, 98, yaw, pitch, offX, offY, scale);
        out += wallSlab.svg;

        const portalOuter = buildIsoBox(24, 5, -4, 50, 7, 72, yaw, pitch, offX, offY, scale, { topFill: 'var(--surface-left)' });
        const doorSlide = (Math.sin(t * 2.0) + 1) * 0.5 * 13;
        const doorLeafL = buildIsoBox(14 - doorSlide * 0.5, 8, -8, 15, 4, 60, yaw, pitch, offX, offY, scale, { topFill: 'url(#cubeHatch)' });
        const doorLeafR = buildIsoBox(34 + doorSlide * 0.5, 8, -8, 15, 4, 60, yaw, pitch, offX, offY, scale, { topFill: 'url(#cubeHatch)' });
        const headerSign = buildIsoBox(24, 7, 36, 42, 5, 10, yaw, pitch, offX, offY, scale, {
          topFill: 'var(--surface-accent)',
          leftFill: 'var(--surface-accent)',
          rightFill: 'var(--surface-accent)',
          stroke: 'var(--surface-top)',
          strokeWidth: 0.8
        });
        out += portalOuter.svg + doorLeafL.svg + doorLeafR.svg + headerSign.svg;

        [-15, 3, 21].forEach((sz, cIdx) => {
          const eject = (cIdx === 1) ? Math.max(0, Math.sin(t * 2.8)) * 7 : 0;
          const slot = buildIsoBox(-36, 6 + eject, sz, 42, 7, 11, yaw, pitch, offX, offY, scale, {
            topFill: cIdx === 1 ? 'var(--surface-accent)' : 'var(--surface-top)',
            leftFill: cIdx === 1 ? 'var(--surface-accent)' : 'var(--surface-left)',
            rightFill: cIdx === 1 ? 'var(--surface-accent)' : 'var(--surface-right)',
            stroke: cIdx === 1 ? 'var(--surface-top)' : 'var(--stroke-main)',
            strokeWidth: 1.0
          });
          out += slot.svg;
        });
      }

      else if (idx === 6) {
        // 07: Workspace.
        const slab = buildIsoBox(0, 0, 0, 168, 168, 12, yaw, pitch, offX, offY, scale, {
          topFill: 'var(--surface-floor)',
          leftFill: 'var(--surface-left)',
          rightFill: 'var(--surface-right)'
        });
        out += slab.svg;

        const zSurf = 6.2;
        const gridMin = -76, gridMax = 76;
        const steps = 6;
        for (let i = 0; i <= steps; i++) {
          const offset = gridMin + (i / steps) * (gridMax - gridMin);
          const pX0 = projectPoint(gridMin, offset, zSurf, yaw, pitch, offX, offY, scale);
          const pX1 = projectPoint(gridMax, offset, zSurf, yaw, pitch, offX, offY, scale);
          const pY0 = projectPoint(offset, gridMin, zSurf, yaw, pitch, offX, offY, scale);
          const pY1 = projectPoint(offset, gridMax, zSurf, yaw, pitch, offX, offY, scale);

          out += `<line x1="${pX0.x.toFixed(1)}" y1="${pX0.y.toFixed(1)}" x2="${pX1.x.toFixed(1)}" y2="${pX1.y.toFixed(1)}" stroke="var(--stroke-subtle)" stroke-width="0.7" opacity="0.55" />`;
          out += `<line x1="${pY0.x.toFixed(1)}" y1="${pY0.y.toFixed(1)}" x2="${pY1.x.toFixed(1)}" y2="${pY1.y.toFixed(1)}" stroke="var(--stroke-subtle)" stroke-width="0.7" opacity="0.55" />`;
        }

        const dashOffset = -(t * 48) % 240;
        const conduit1 = [
          projectPoint(-32, 34, zSurf + 0.4, yaw, pitch, offX, offY, scale),
          projectPoint(6, 34, zSurf + 0.4, yaw, pitch, offX, offY, scale),
          projectPoint(6, 6, zSurf + 0.4, yaw, pitch, offX, offY, scale),
          projectPoint(48, 6, zSurf + 0.4, yaw, pitch, offX, offY, scale),
          projectPoint(48, -14, zSurf + 0.4, yaw, pitch, offX, offY, scale)
        ];
        const conduit2 = [
          projectPoint(-32, 34, zSurf + 0.4, yaw, pitch, offX, offY, scale),
          projectPoint(-70, 34, zSurf + 0.4, yaw, pitch, offX, offY, scale)
        ];
        [conduit1, conduit2].forEach(cPts => {
          const d = cPts.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ');
          out += `<path d="${d}" fill="none" stroke="var(--stroke-main)" stroke-width="2.0" stroke-dasharray="7 5" stroke-dashoffset="${dashOffset.toFixed(1)}" />`;
        });
      }

      else if (idx === 7) {
        // 08: Runtime.
        const plenum = buildIsoBox(0, 0, 0, 178, 178, 14, yaw, pitch, offX, offY, scale);
        out += plenum.svg;

        const zSurf = 7.3;
        [-48, -16, 16].forEach((bx, bIdx) => {
          const pulseZ = (Math.floor(t * 3) % 3 === bIdx) ? 2 : 0;
          const blade = buildIsoBox(bx, -22, zSurf + 3.5 + pulseZ, 20, 78, 7, yaw, pitch, offX, offY, scale, {
            topFill: 'url(#cubeHatch)'
          });
          out += blade.svg;
        });

        const diodeBody = buildIsoBox(-54, 44, zSurf + 4.5, 20, 32, 9, yaw, pitch, offX, offY, scale, {
          topFill: 'var(--surface-accent)',
          leftFill: 'var(--surface-accent)',
          rightFill: 'var(--surface-accent)',
          stroke: 'var(--surface-top)',
          strokeWidth: 0.9
        });
        const diodeTerm1 = buildIsoBox(-54, 25, zSurf + 2, 14, 7, 4, yaw, pitch, offX, offY, scale);
        const diodeTerm2 = buildIsoBox(-54, 63, zSurf + 2, 14, 7, 4, yaw, pitch, offX, offY, scale);
        out += diodeTerm1.svg + diodeTerm2.svg + diodeBody.svg;

        const dashOffset = -(t * 55) % 200;
        const busPts = [
          projectPoint(48, -14, zSurf + 0.5, yaw, pitch, offX, offY, scale),
          projectPoint(48, 44, zSurf + 0.5, yaw, pitch, offX, offY, scale),
          projectPoint(-42, 44, zSurf + 0.5, yaw, pitch, offX, offY, scale)
        ];
        const busD = busPts.map((p, i) => `${i === 0 ? 'M' : 'L'} ${p.x.toFixed(1)} ${p.y.toFixed(1)}`).join(' ');
        out += `<path d="${busD}" fill="none" stroke="var(--stroke-main)" stroke-width="2.0" stroke-dasharray="6 4" stroke-dashoffset="${dashOffset.toFixed(1)}" />`;
      }

      return out;
    }


    function renderDissectedCallout(comp, anchorPt, dissectVal) {
      if (dissectVal < 0.18) return '';

      const opacity = Math.min(1, (dissectVal - 0.18) / 0.55);
      const side = comp.labelOffset.side;
      const elbowX = anchorPt.x + comp.labelOffset.lx * 0.55;
      const elbowY = anchorPt.y + comp.labelOffset.ly;
      const endX = anchorPt.x + comp.labelOffset.lx;
      const endY = elbowY;

      const titleText = `${comp.index} · ${comp.shortName}`;
      const charW = 7.2;
      const boxW = Math.max(titleText.length * charW + 14, 168);
      const boxH = 22;
      const boxX = side === 'left' ? endX - boxW - 4 : endX + 4;
      const boxY = endY - boxH / 2;
      const textX = side === 'left' ? endX - 10 : endX + 10;
      const textAnchor = side === 'left' ? 'end' : 'start';

      let badgeSvg = '';
      if (comp.badge) {
        badgeSvg = `
          <rect x="${boxX.toFixed(1)}" y="${boxY.toFixed(1)}" width="${boxW.toFixed(1)}" height="${boxH}" rx="1.5" fill="var(--surface-accent)" />
          <text x="${(boxX + boxW / 2).toFixed(1)}" y="${(endY + 4).toFixed(1)}" text-anchor="middle" fill="var(--surface-accent-text)" class="font-mono-tech" font-size="11" font-weight="700" letter-spacing="0.05em">${titleText}</text>
        `;
      } else {
        badgeSvg = `
          <rect x="${boxX.toFixed(1)}" y="${boxY.toFixed(1)}" width="${boxW.toFixed(1)}" height="${boxH}" rx="1.5" fill="var(--bg-card)" stroke="var(--stroke-main)" stroke-width="1.0" />
          <text x="${(boxX + boxW / 2).toFixed(1)}" y="${(endY + 4).toFixed(1)}" text-anchor="middle" fill="var(--text-primary)" class="font-mono-tech" font-size="11" font-weight="700" letter-spacing="0.04em">${titleText}</text>
        `;
      }

      const spec1Y = boxY + boxH + 12;
      const spec2Y = spec1Y + 12;

      return `
        <g opacity="${opacity.toFixed(2)}">
          <polyline points="${anchorPt.x.toFixed(1)},${anchorPt.y.toFixed(1)} ${elbowX.toFixed(1)},${elbowY.toFixed(1)} ${endX.toFixed(1)},${endY.toFixed(1)}"
                    fill="none" stroke="var(--stroke-main)" stroke-width="1.0" marker-start="url(#cubeCalloutDot)" />
          ${badgeSvg}
          <text x="${textX.toFixed(1)}" y="${spec1Y.toFixed(1)}" text-anchor="${textAnchor}" fill="var(--text-secondary)" class="font-mono-tech" font-size="10" font-weight="600">${comp.subSpecs[0]}</text>
          <text x="${textX.toFixed(1)}" y="${spec2Y.toFixed(1)}" text-anchor="${textAnchor}" fill="var(--text-muted)" class="font-mono-tech" font-size="9.5">${comp.subSpecs[1]}</text>
        </g>
      `;
    }



    const svgAxisUnderlay = document.getElementById('cubeAxisUnderlay');
    const svgLayersGroup = document.getElementById('cubeLayers');
    const svgAxisOverlay = document.getElementById('cubeAxisOverlay');
    const svgCalloutsGroup = document.getElementById('cubeCallouts');
    if (!svgAxisUnderlay || !svgLayersGroup || !svgAxisOverlay || !svgCalloutsGroup) return;

    let frameRequest = null;
    let lastTime = performance.now();
    let lastPulseTick = 0;
    let isVisible = !('IntersectionObserver' in window);

    function stopLoop() {
      if (frameRequest !== null) cancelAnimationFrame(frameRequest);
      frameRequest = null;
    }
    function startLoop() {
      if (frameRequest !== null || !isVisible || document.hidden || reducedMotion.matches) return;
      lastTime = performance.now();
      frameRequest = requestAnimationFrame(animateLoop);
    }
    function animateLoop(now) {
      frameRequest = null;
      if (!isVisible || document.hidden || reducedMotion.matches) return;
      const dt = Math.min(Math.max(0, (now - lastTime) / 1000), 0.05);
      lastTime = now;
      state.simTime += dt;

      if (!state.isDragging) {
        springs.yaw.target = state.orbitYaw + Math.sin(state.simTime * 0.65) * 6;
        springs.pitch.target = state.orbitPitch + Math.cos(state.simTime * 0.5) * 2;
      }
      if (state.simTime - lastPulseTick > 1.6) {
        lastPulseTick = state.simTime;
        springs.press.target = 1.0;
        setTimeout(() => { springs.press.target = 0.0; }, 240);
      }

      stepSpring(springs.dissect, dt);
      stepSpring(springs.yaw, dt);
      stepSpring(springs.pitch, dt);
      stepSpring(springs.press, dt);
      renderScene();
      frameRequest = requestAnimationFrame(animateLoop);
    }

    function syncInstantMotion() {
      if (!reducedMotion.matches) return;
      for (const spring of Object.values(springs)) {
        spring.val = spring.target;
        spring.vel = 0;
      }
      renderScene();
    }
    function toggleDissect() {
      state.isDissected = !state.isDissected;
      springs.dissect.target = state.isDissected ? 1 : 0;
      label.textContent = state.isDissected ? 'Assemble' : 'Separate';
      symbol.textContent = state.isDissected ? '[−]' : '[+]';
      const action = state.isDissected ? 'Assemble the cube' : 'Separate the cube';
      toggle.setAttribute('aria-label', action);
      toggle.setAttribute('aria-expanded', String(state.isDissected));
      viewport.setAttribute('aria-label', action);
      viewport.setAttribute('aria-expanded', String(state.isDissected));
      figure.setAttribute('data-expanded', String(state.isDissected));
      status.textContent = state.isDissected ? 'Parts separated' : 'Cube assembled';
      syncInstantMotion();
      startLoop();
    }

    viewport.setAttribute('role', 'button');
    viewport.setAttribute('tabindex', '0');
    viewport.setAttribute('aria-label', 'Separate the cube');
    viewport.setAttribute('aria-expanded', 'false');
    toggle.setAttribute('aria-expanded', 'false');
    toggle.hidden = false;
    toggle.addEventListener('click', toggleDissect);

    viewport.addEventListener('pointerdown', (event) => {
      if (state.isDragging || event.isPrimary === false || (event.pointerType === 'mouse' && event.button !== 0)) return;
      state.isDragging = true;
      state.activePointerId = event.pointerId;
      state.dragStartX = event.clientX;
      state.dragStartY = event.clientY;
      state.dragStartYaw = springs.yaw.val;
      state.dragStartPitch = springs.pitch.val;
      viewport.setPointerCapture(event.pointerId);
    });
    viewport.addEventListener('pointermove', (event) => {
      if (!state.isDragging || state.activePointerId !== event.pointerId) return;
      const dx = event.clientX - state.dragStartX;
      const dy = event.clientY - state.dragStartY;
      springs.yaw.target = Math.max(-75, Math.min(45, state.dragStartYaw + dx * 0.35));
      springs.pitch.target = Math.max(15, Math.min(48, state.dragStartPitch + dy * 0.25));
      syncInstantMotion();
    });
    viewport.addEventListener('pointerup', (event) => {
      if (!state.isDragging || state.activePointerId !== event.pointerId) return;
      const moved = Math.hypot(event.clientX - state.dragStartX, event.clientY - state.dragStartY);
      state.isDragging = false;
      state.activePointerId = null;
      if (moved < 6) {
        toggleDissect();
      } else {
        state.orbitYaw = springs.yaw.target;
        state.orbitPitch = springs.pitch.target;
      }
    });
    viewport.addEventListener('pointercancel', (event) => {
      if (state.activePointerId !== event.pointerId) return;
      state.isDragging = false;
      state.activePointerId = null;
    });
    viewport.addEventListener('click', (event) => {
      if (event.detail === 0) toggleDissect();
    });
    viewport.addEventListener('keydown', (event) => {
      if (event.key === ' ' || event.key === 'Enter') {
        event.preventDefault();
        toggleDissect();
        return;
      }
      const step = 8;
      if (event.key === 'ArrowLeft') state.orbitYaw = Math.max(-75, state.orbitYaw - step);
      else if (event.key === 'ArrowRight') state.orbitYaw = Math.min(45, state.orbitYaw + step);
      else if (event.key === 'ArrowUp') state.orbitPitch = Math.max(15, state.orbitPitch - step);
      else if (event.key === 'ArrowDown') state.orbitPitch = Math.min(48, state.orbitPitch + step);
      else if (event.key === 'Escape') { state.orbitYaw = -32; state.orbitPitch = 28; }
      else return;
      event.preventDefault();
      springs.yaw.target = state.orbitYaw;
      springs.pitch.target = state.orbitPitch;
      syncInstantMotion();
      startLoop();
    });

    const onMotionChange = () => {
      if (reducedMotion.matches) {
        stopLoop();
        springs.press.target = 0;
        syncInstantMotion();
      } else {
        startLoop();
      }
    };
    reducedMotion.addEventListener('change', onMotionChange);
    document.addEventListener('visibilitychange', () => document.hidden ? stopLoop() : startLoop());
    window.addEventListener('resize', () => { if (reducedMotion.matches) renderScene(); });
    renderScene();
    if ('IntersectionObserver' in window) {
      const observer = new IntersectionObserver((entries) => {
        isVisible = entries.some((entry) => entry.isIntersecting);
        if (isVisible) startLoop();
        else stopLoop();
      }, { threshold: 0.01 });
      observer.observe(viewport);
    } else {
      startLoop();
    }

    function renderScene() {
      const yaw = springs.yaw.val;
      const pitch = springs.pitch.val;
      const d = springs.dissect.val;
      const press = springs.press.val;
      const t = state.simTime;

      // On small screens, start close to the assembled cube and zoom out as it separates.
      const dView = Math.max(0, Math.min(1, d));
      if (viewport.clientWidth < 600) {
        const compact = [340, 100, 600, 610];
        const full = [0, 0, 1280, 820];
        cubeSvg.setAttribute('viewBox', compact.map((value, i) => value + (full[i] - value) * dView).join(' '));
      } else {
        cubeSvg.setAttribute('viewBox', '0 0 1280 820');
      }

      // 1. Central Cubic Room Wireframe & Dissection Trajectory Lines
      const c = 84;
      const botCorners = [
        projectPoint(-c, -c, -26, yaw, pitch),
        projectPoint(c, -c, -26, yaw, pitch),
        projectPoint(c, c, -26, yaw, pitch),
        projectPoint(-c, c, -26, yaw, pitch)
      ];
      const topCorners = [
        projectPoint(-c, -c, 78, yaw, pitch),
        projectPoint(c, -c, 78, yaw, pitch),
        projectPoint(c, c, 78, yaw, pitch),
        projectPoint(-c, c, 78, yaw, pitch)
      ];

      let underlayHtml = '';
      // Ghost wireframe of the central Cubic Room
      underlayHtml += `<polygon points="${ptsToPoly(botCorners)}" fill="none" stroke="var(--stroke-subtle)" stroke-width="0.9" stroke-dasharray="4 4" opacity="0.5" />`;
      underlayHtml += `<polygon points="${ptsToPoly(topCorners)}" fill="none" stroke="var(--stroke-subtle)" stroke-width="0.9" stroke-dasharray="4 4" opacity="0.5" />`;
      for (let i = 0; i < 4; i++) {
        underlayHtml += `<line x1="${botCorners[i].x.toFixed(1)}" y1="${botCorners[i].y.toFixed(1)}" x2="${topCorners[i].x.toFixed(1)}" y2="${topCorners[i].y.toFixed(1)}" stroke="var(--stroke-subtle)" stroke-width="0.9" stroke-dasharray="4 4" opacity="0.5" />`;
      }

      // Compute each component's current interpolated screen offset & scale
      const compScreenStates = ROOM_COMPONENTS.map((comp) => {
        // Base screen projection of its compact home socket inside the cubic room
        const homeScreen = projectPoint(comp.homePos.x, comp.homePos.y, comp.homePos.z, yaw, pitch, 0, 0, 1.0);
        const homeDeltaX = homeScreen.x - SVG_CENTER_X;
        const homeDeltaY = homeScreen.y - SVG_CENTER_Y;

        // Interpolate from compact room socket to dedicated non-overlapping dissected position
        const currOffX = homeDeltaX * (1 - d) + comp.dissectScreenOffset.sx * d;
        const currOffY = homeDeltaY * (1 - d) + comp.dissectScreenOffset.sy * d;
        const currScale = 1.0 * (1 - d) + comp.dissectScale * d;

        const currCenter = projectPoint(0, 0, 0, yaw, pitch, currOffX, currOffY, currScale);

        if (d > 0.03) {
          underlayHtml += `<line x1="${homeScreen.x.toFixed(1)}" y1="${homeScreen.y.toFixed(1)}" x2="${currCenter.x.toFixed(1)}" y2="${currCenter.y.toFixed(1)}"
                                 stroke="var(--stroke-subtle)" stroke-width="1.0" stroke-dasharray="3 3" opacity="0.65" />`;
          underlayHtml += `<circle cx="${homeScreen.x.toFixed(1)}" cy="${homeScreen.y.toFixed(1)}" r="2.2" fill="var(--stroke-subtle)" opacity="0.65" />`;
        }

        return { homeScreen, currOffX, currOffY, currScale, currCenter };
      });
      svgAxisUnderlay.innerHTML = underlayHtml;

      // 2. Render all 8 Cubic Room Components in back-to-front order
      // Order: Sub-Floor (7) -> Floor Slab (6) -> Back Walls (4, 5) -> Interior Stations (2, 1, 3) -> Ceiling Rig (0)
      const paintOrder = [7, 6, 4, 5, 2, 1, 3, 0];
      let layersHtml = '';
      paintOrder.forEach(idx => {
        const st = compScreenStates[idx];
        layersHtml += `
          <g class="room-part" data-layer-index="${idx}">
            ${renderRoomComponent(idx, yaw, pitch, st.currOffX, st.currOffY, st.currScale, t, press)}
          </g>
        `;
      });
      svgLayersGroup.innerHTML = layersHtml;

      // 3. Front Transparent Cubic Room Glass Walls when Compact (`1 - d`) + Live Signal Packet
      let overlayHtml = '';
      const compactOpacity = Math.max(0, 1 - d * 1.4);
      if (compactOpacity > 0.02) {
        // Draw the front-left and front-right transparent glass walls of the Compact Cubic Room
        // so when collapsed, it looks unmistakably like a closed 3D Cubic Room Box!
        const glassFL = [topCorners[3], topCorners[2], botCorners[2], botCorners[3]];
        const glassFR = [topCorners[1], topCorners[2], botCorners[2], botCorners[1]];
        overlayHtml += `
          <g opacity="${compactOpacity.toFixed(2)}">
            <polygon points="${ptsToPoly(glassFL)}" fill="var(--surface-top)" fill-opacity="0.16" stroke="var(--stroke-main)" stroke-width="1.5" stroke-linejoin="round" />
            <polygon points="${ptsToPoly(glassFR)}" fill="var(--surface-right)" fill-opacity="0.18" stroke="var(--stroke-main)" stroke-width="1.5" stroke-linejoin="round" />
            <line x1="${topCorners[2].x.toFixed(1)}" y1="${topCorners[2].y.toFixed(1)}" x2="${botCorners[2].x.toFixed(1)}" y2="${botCorners[2].y.toFixed(1)}" stroke="var(--stroke-main)" stroke-width="2.0" />
            <rect x="${(SVG_CENTER_X - 135).toFixed(1)}" y="${(botCorners[2].y + 38).toFixed(1)}" width="270" height="22" rx="2" fill="var(--surface-accent)" />
            <text x="${SVG_CENTER_X}" y="${(botCorners[2].y + 52.5).toFixed(1)}" text-anchor="middle" fill="var(--surface-accent-text)" class="font-mono-tech" font-size="9.5" font-weight="700" letter-spacing="0.06em">
              ENVIRONMENT CUBE · CLICK TO EXPLORE
            </text>
          </g>
        `;
      }

      // Traveling signal pulse between Agent (1) -> Workbench (2) -> Reward Tower (3)
      const pAgent = compScreenStates[1].currCenter;
      const pBench = compScreenStates[2].currCenter;
      const pReward = compScreenStates[3].currCenter;
      const prog = (t * 1.35) % 1.0;
      const pktX = prog < 0.5
        ? pAgent.x + (pBench.x - pAgent.x) * (prog * 2)
        : pBench.x + (pReward.x - pBench.x) * ((prog - 0.5) * 2);
      const pktY = prog < 0.5
        ? pAgent.y + (pBench.y - pAgent.y) * (prog * 2)
        : pBench.y + (pReward.y - pBench.y) * ((prog - 0.5) * 2);

      overlayHtml += `
        <polyline points="${pAgent.x.toFixed(1)},${pAgent.y.toFixed(1)} ${pBench.x.toFixed(1)},${pBench.y.toFixed(1)} ${pReward.x.toFixed(1)},${pReward.y.toFixed(1)}"
                  fill="none" stroke="var(--stroke-main)" stroke-width="1.2" stroke-dasharray="4 4" opacity="0.55" />
        <circle cx="${pktX.toFixed(1)}" cy="${pktY.toFixed(1)}" r="4.5" fill="var(--surface-accent)" stroke="var(--surface-top)" stroke-width="1.5" />
      `;
      svgAxisOverlay.innerHTML = overlayHtml;

      // 4. Render All 8 Dissected Component Callouts & Specs Simultaneously
      let calloutsHtml = '';
      ROOM_COMPONENTS.forEach((comp, idx) => {
        calloutsHtml += renderDissectedCallout(comp, compScreenStates[idx].currCenter, d);
      });
      svgCalloutsGroup.innerHTML = calloutsHtml;
    }



  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', setupCube, { once: true });
  else setupCube();
})();
