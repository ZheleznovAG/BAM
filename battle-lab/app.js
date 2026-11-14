/* BAM Battle Lab — Canvas presentation. All illustrations are procedural. */
(function () {
  "use strict";
  const Sim = window.BAMSim;
  const cv = document.getElementById("battle");
  const c = cv.getContext("2d");
  const W = cv.width, H = cv.height;
  const el = id => document.getElementById(id);
  let game = Sim.create(), paused = false, speed = 1;
  let lastTime = performance.now(), lastUi = 0, lastLog = "", shownEnding = "";
  const site = Sim.SITES;

  function line(x1, y1, x2, y2, color, width = 1) {
    c.beginPath(); c.moveTo(x1, y1); c.lineTo(x2, y2);
    c.strokeStyle = color; c.lineWidth = width; c.stroke();
  }
  function circle(x, y, r, fill, stroke, width = 1) {
    c.beginPath(); c.arc(x, y, Math.max(.1, r), 0, Math.PI * 2);
    if (fill) { c.fillStyle = fill; c.fill(); }
    if (stroke) { c.lineWidth = width; c.strokeStyle = stroke; c.stroke(); }
  }
  function polygon(points, fill, stroke, width = 1) {
    c.beginPath();
    points.forEach((p, i) => i ? c.lineTo(p[0], p[1]) : c.moveTo(p[0], p[1]));
    c.closePath();
    if (fill) { c.fillStyle = fill; c.fill(); }
    if (stroke) { c.strokeStyle = stroke; c.lineWidth = width; c.stroke(); }
  }
  function glow(x, y, r, color) {
    const g = c.createRadialGradient(x, y, 2, x, y, r);
    g.addColorStop(0, color); g.addColorStop(1, "transparent");
    c.fillStyle = g; c.fillRect(x - r, y - r, r * 2, r * 2);
  }
  function label(text, x, y, color = "#bbd0cf", size = 11) {
    c.save(); c.font = "600 " + size + "px Segoe UI, sans-serif";
    c.textAlign = "center"; c.fillStyle = "#041016";
    c.fillText(text, x + 1, y + 2);
    c.fillStyle = color; c.fillText(text, x, y); c.restore();
  }
  function hpBar(x, y, val, max, width, color) {
    const ratio = Math.max(0, Math.min(1, val / max));
    c.fillStyle = "#08131acc"; c.fillRect(x - width / 2 - 2, y - 2, width + 4, 7);
    c.fillStyle = "#35444d"; c.fillRect(x - width / 2, y, width, 3);
    c.fillStyle = color; c.fillRect(x - width / 2, y, width * ratio, 3);
  }
  function backdrop(t) {
    const bg = c.createLinearGradient(0, 0, W, H);
    bg.addColorStop(0, "#263c3c"); bg.addColorStop(.53, "#1b3332"); bg.addColorStop(1, "#14272b");
    c.fillStyle = bg; c.fillRect(0, 0, W, H);
    for (let i = 0; i < 70; i++) {
      const x = (i * 137 + 57) % W, y = (i * 271 + 41) % H;
      circle(x, y, 8 + (i % 7) * 3, i % 2 ? "#3d534326" : "#5763421e");
    }
    c.strokeStyle = "#88baa10b"; c.lineWidth = 1;
    for (let x = 0; x < W; x += 48) line(x, 0, x, H, "#b3dac10c");
    for (let y = 0; y < H; y += 48) line(0, y, W, y, "#b3dac10c");
    c.beginPath(); c.moveTo(170, 277); c.bezierCurveTo(325, 290, 555, 290, 960, 256);
    c.strokeStyle = "#a99c6540"; c.lineWidth = 77; c.stroke();
    c.beginPath(); c.moveTo(170, 277); c.bezierCurveTo(325, 290, 555, 290, 960, 256);
    c.strokeStyle = "#2c3f387d"; c.lineWidth = 63; c.stroke();
    for (let i = 0; i < 32; i++) {
      const x = (i * 293 + 115) % W, y = (i * 173 + 39) % H;
      const alpha = .12 + .18 * Math.sin(t * .8 + i * 3);
      c.fillStyle = "rgba(201,215,155," + Math.max(0, alpha) + ")";
      c.fillRect(x, y, 2, 2);
    }
    const fog = c.createLinearGradient(0, 0, 0, H);
    fog.addColorStop(0, "#0b1b2438"); fog.addColorStop(.55, "#00000000"); fog.addColorStop(1, "#060b1538");
    c.fillStyle = fog; c.fillRect(0, 0, W, H);
  }
  function drawForge(t) {
    const x = site.forge.x, y = site.forge.y;
    glow(x, y, 140, "#b15aff25");
    circle(x, y + 12, 74, "#0c1b22d9", "#506773", 3);
    circle(x, y + 12, 58, "#1b2836", "#a079bd", 2);
    circle(x, y + 12, 43, "#131c2c", "#ad83d8", 1);
    for (let i = 0; i < 8; i++) {
      const a = i * Math.PI / 4 + t * .18;
      circle(x + Math.cos(a) * 51, y + 12 + Math.sin(a) * 51, 3, "#b9a3e4");
    }
    const rx = x + Math.sin(t * 1.4) * 4, ry = y + Math.cos(t * 1.2) * 4;
    glow(rx, ry, 46, "#da91fe4d");
    polygon([[rx, ry - 45], [rx + 26, ry - 9], [rx + 18, ry + 31], [rx - 21, ry + 31], [rx - 27, ry - 9]],
      "#5b477d", "#dec0fb", 3);
    polygon([[rx, ry - 35], [rx + 10, ry], [rx, ry + 22], [rx - 12, ry]], "#c2a0e6", "#f6e7ff", 1);
    circle(x, y + 12, 76 + Math.sin(t * 2) * 2, null, "#c595d23d", 2);
    label("КУЗНИЦА", x, y + 108, "#e6d6f6", 12);
    hpBar(x, y + 118, game.forgeHP, Sim.C.forgeHP, 116, "#b8dccd");
  }
  function drawBarracks(t) {
    const x = site.barracks.x, y = site.barracks.y;
    glow(x, y, 92, "#f1a76322");
    circle(x, y + 19, 58, "#132025c0", "#536257", 3);
    c.fillStyle = "#2c323b"; c.fillRect(x - 32, y - 19, 64, 62);
    c.strokeStyle = "#7c7465"; c.lineWidth = 3; c.strokeRect(x - 32, y - 19, 64, 62);
    polygon([[x - 43, y - 16], [x, y - 61], [x + 43, y - 16]], "#785947", "#d6a17c", 3);
    c.fillStyle = "#0f2025"; c.fillRect(x - 10, y + 4, 20, 39);
    line(x, y - 51, x, y - 76, "#ddd1c0", 2);
    polygon([[x, y - 75], [x + 23, y - 67], [x, y - 55]], "#d18b74");
    label("КАЗАРМЫ", x, y + 74, "#dfbd9f", 11);
  }
  function drawFoundation(t) {
    const x = site.foundation.x, y = site.foundation.y;
    glow(x, y, game.rune ? 150 : 84, game.rune ? "#48a6db28" : "#c2b09316");
    circle(x, y, 56, "#101f26a9", game.rune ? "#81ddf4" : "#817e70", 3);
    for (let i = 0; i < 4; i++) {
      const a = Math.PI * .25 + i * Math.PI / 2;
      const xx = x + Math.cos(a) * 39, yy = y + Math.sin(a) * 39;
      polygon([[xx, yy - 10], [xx + 10, yy], [xx, yy + 10], [xx - 10, yy]],
        game.rune ? "#6bd9f4" : game.construction ? "#9ab4d6" : "#333f3f",
        game.rune ? "#dcfcff" : "#879c99", 1);
    }
    if (game.rune) {
      const p = Math.sin(t * 2) * 4;
      polygon([[x, y - 66 + p], [x + 24, y - 7 + p], [x + 15, y + 24 + p],
        [x - 22, y + 24 + p], [x - 31, y - 7 + p]],
        "#276b83", "#9be8ff", 3);
      polygon([[x, y - 51 + p], [x + 11, y - 7 + p], [x, y + 14 + p],
        [x - 13, y - 7 + p]], "#8de5f7", "#efffff", 1);
      circle(x, y, 88 + 3 * Math.sin(t), null, "#72baf123", 2);
      label("РУННЫЙ АЛТАРЬ", x, y + 81, "#9ee7fa", 11);
    } else if (game.construction) {
      const r = game.construction.time / game.construction.total;
      c.beginPath(); c.arc(x, y, 62, -Math.PI / 2, -Math.PI / 2 + r * Math.PI * 2);
      c.strokeStyle = "#89d7e7"; c.lineWidth = 6; c.stroke();
      const arrived = game.construction.ids.filter(id => {
        const u = Sim.getUnit(game, id);
        return u && u.job && u.job.stage === "ritual";
      }).length;
      label(game.construction.stage === "gather" ? "ГОЛЕМЫ У ФУНДАМЕНТА " + arrived + "/4" :
        "РИТУАЛ " + Math.round(r * 100) + "%", x, y + 81, "#e0d3bb", 11);
    } else {
      polygon([[x, y - 24], [x + 23, y], [x, y + 24], [x - 23, y]],
        "#263638", "#7c9a9a", 2);
      label("ФУНДАМЕНТ · 4 ГОЛЕМА", x, y + 81, "#c5bb9e", 11);
    }
  }
  function drawGolem(u, t) {
    const x = u.x, y = u.y + Math.sin(t * 2.2 + u.id) * 1.8;
    glow(x, y, 26, "#ecc67621");
    circle(x, y + 9, 16, "#101a20a5");
    polygon([[x - 15, y + 9], [x - 14, y - 9], [x - 4, y - 21],
      [x + 10, y - 17], [x + 18, y - 2], [x + 12, y + 13]],
      "#8d8572", "#e0bf88", 2);
    polygon([[x - 6, y - 12], [x + 3, y - 15], [x + 9, y - 5], [x - 4, y + 2]],
      "#efc983");
    circle(x - 7, y - 3, 2, "#2f3741"); circle(x + 8, y - 4, 2, "#2f3741");
    if (Math.floor(t * 1.6 + u.id) % 3 === 0) label("+", x, y - 30, "#e6c48e", 13);
  }
  function drawWarrior(u, t) {
    const x = u.x, y = u.y + Math.sin(t * 3 + u.id) * 2;
    glow(x, y, 29, "#69d8eb20");
    circle(x, y + 12, 18, "#081b2470");
    polygon([[x - 12, y + 13], [x - 15, y - 5], [x, y - 18],
      [x + 15, y - 5], [x + 12, y + 13]], "#346780", "#9ce4ef", 2);
    polygon([[x, y - 18], [x + 13, y - 3], [x, y + 8], [x - 13, y - 3]],
      "#73bdcc", "#c9f6ff");
    circle(x, y - 22, 10, "#d4b49a", "#f7e6cf", 1);
    line(x + 13, y - 3, x + 25, y - 26, "#e3f6f4", 3);
    circle(x - 16, y + 2, 9, "#3c586d", "#a6cdda", 2);
    if (u.hp < u.maxHp) hpBar(x, y - 40, u.hp, u.maxHp, 32, "#72d9e3");
  }
  function drawEnemy(e, t) {
    const x = e.x, y = e.y + Math.sin(t * 5 + e.id) * 1.7;
    const brute = e.kind === "brute", raider = e.kind === "raider";
    const ink = brute ? "#825c9f" : raider ? "#af673c" : "#7f3f47";
    const edge = brute ? "#dec4ff" : raider ? "#f4bc80" : "#e7857a";
    c.save();
    c.translate(x, y);
    c.scale(brute ? 1.38 : raider ? .88 : 1, brute ? 1.38 : raider ? .88 : 1);
    glow(0, 0, 28, brute ? "#c18ffb36" : raider ? "#f3a76634" : "#ec5a5a21");
    circle(0, 9, 17, "#0b111cad");
    polygon([[-16, 12], [-17, -8], [-9, -17], [10, -18], [17, -8], [17, 12]], ink, edge, 2);
    if (brute) {
      polygon([[-20,-10],[-25,-30],[-6,-19]], "#9c77b5","#d5bce4",1);
      polygon([[20,-10],[25,-30],[6,-19]], "#9c77b5","#d5bce4",1);
      polygon([[-11,0],[0,8],[11,0],[0,-13]], "#4b385b","#caadde",2);
    } else if (raider) {
      polygon([[-18, -11], [-22, -28], [-3, -17]], "#cd8656");
      polygon([[18, -11], [22, -28], [4, -17]], "#cd8656");
      line(16, 0, 29, -15, "#efd5b8", 2);
    } else {
      polygon([[-18, -11], [-23, -23], [-5, -15]], "#c36662");
      polygon([[18, -11], [23, -23], [5, -15]], "#c36662");
    }
    circle(-6, -6, 3, "#f5d18a"); circle(7, -6, 3, "#f5d18a");
    c.restore();
    if (e.slow > 0) circle(x, y, brute ? 38 : 26, null, "#87d7fd77", 2);
    hpBar(x, y - (brute ? 42 : 31), e.hp, e.maxHp, brute ? 44 : 32, edge);
  }
  function drawJob(u, t) {
    if (!u.job) return;
    const job = u.job;
    const color = job.kind === "build" ? "#c7a5fc" :
      job.kind === "promote" ? "#91e1f0" : "#e8c48a";
    if (job.stage === "travel") {
      c.save();
      c.setLineDash([6, 7]);
      line(u.x, u.y, job.dest.x, job.dest.y, color + "65", 1.5);
      c.restore();
      const dx = job.dest.x - u.x, dy = job.dest.y - u.y;
      const d = Math.hypot(dx, dy);
      if (d > 10) {
        const px = u.x + dx / d * 33, py = u.y + dy / d * 33;
        polygon([[px, py], [px - dy / d * 5 - dx / d * 8, py + dx / d * 5 - dy / d * 8],
          [px + dy / d * 5 - dx / d * 8, py - dx / d * 5 - dy / d * 8]], color);
      }
      circle(u.x, u.y, 24 + Math.sin(t * 5 + u.id) * 1.2, null, color + "aa", 1.5);
    } else {
      const progress = job.kind === "build" && game.construction ?
        game.construction.time / game.construction.total : job.time / job.duration;
      const p = Math.max(0, Math.min(1, progress));
      glow(u.x, u.y, 43, color + "35");
      circle(u.x, u.y, 24, "#14222b44", color + "65", 1.5);
      c.beginPath();
      c.arc(u.x, u.y, 26, -Math.PI / 2, -Math.PI / 2 + p * Math.PI * 2);
      c.strokeStyle = color; c.lineWidth = 4; c.stroke();
      for (let i = 0; i < 3; i++) {
        const a = t * 2.8 + u.id + i * Math.PI * 2 / 3;
        circle(u.x + Math.cos(a) * 33, u.y + Math.sin(a) * 33, 2.6, color);
      }
    }
    label(job.kind === "build" ? "СТРОИТ" : job.kind === "promote" ? "ПРЕВРАЩАЕТСЯ" : "ВОЗВРАЩАЕТСЯ",
      u.x, u.y - (job.stage === "ritual" ? 49 : 35), color, 10);
  }
  function drawEffects() {
    for (const e of game.effects) {
      const p = 1 - e.life / e.max;
      if (e.type === "pulse") {
        circle(e.x, e.y, p * Sim.C.pulseRadius, null,
          "rgba(119,215,255," + ((1 - p) * .8) + ")", 4 + 3 * (1 - p));
        glow(e.x, e.y, 125, "#8ccfff20");
      } else if (e.type === "death") {
        for (let i = 0; i < 9; i++) {
          const a = i * Math.PI * 2 / 9;
          circle(e.x + Math.cos(a) * p * 33, e.y + Math.sin(a) * p * 33,
            4 * (1 - p), "#efc99b");
        }
      } else if (e.type === "build") {
        circle(e.x, e.y, 42 + 60 * p, null,
          "rgba(180,218,248," + (1 - p) + ")", 4);
      }
    }
  }
  function paint() {
    const t = game.time;
    backdrop(t);
    if (game.rune) {
      circle(site.foundation.x, site.foundation.y, 175, "#74dcfa08", "#8be4ff24", 2);
    }
    drawBarracks(t);
    drawFoundation(t);
    drawForge(t);
    for (const u of game.units) {
      if (u.type === "golem") drawGolem(u, t);
      else drawWarrior(u, t);
      drawJob(u, t);
      if (game.selectedId === u.id) {
        circle(u.x, u.y + 2, 27 + Math.sin(t * 3) * 2, null, "#fff2a1", 2);
        circle(u.x, u.y + 2, 33, null, "#fff2a14a", 1);
      }
    }
    for (const e of game.enemies) drawEnemy(e, t);
    drawEffects();
    c.save();
    c.font = "11px Segoe UI, sans-serif";
    c.fillStyle = "#d9e6e7";
    c.fillText("КУЗНИЦА", 20, 25);
    c.fillStyle = "#c3d0c3";
    c.fillText("→ НАПРАВЛЕНИЕ НАПАДЕНИЯ", W - 230, 25);
    c.restore();
    if (game.phase === "prep") {
      label("НОВАЯ ВОЛНА ЧЕРЕЗ " + Math.ceil(game.countdown) + " СЕК.",
        W / 2 + 90, 48, "#e7c897", 16);
    }
  }
  function setText(id, text) { el(id).textContent = text; }
  function updateUI() {
    const num = n => Math.ceil(n).toString();
    setText("mana", num(game.mana) + " / " + Sim.C.manaCap);
    setText("income", "+" + (Sim.C.forgeMana + (Sim.manaRate(game) - Sim.C.forgeMana)).toFixed(1) + " / сек.");
    setText("forge-hp", num(game.forgeHP) + " / " + Sim.C.forgeHP);
    setText("golems", Sim.count(game, "golem") + " големов");
    setText("warriors", Sim.count(game, "warrior") + " защитников");
    setText("wave", Math.max(1, game.wave) + " / " + Sim.C.waves);
    let phase = game.phase === "prep" ? "До волны: " + Math.ceil(game.countdown) + " сек." :
      game.phase === "battle" ? "Врагов на поле: " + game.enemies.length :
      game.phase === "win" ? "ПОБЕДА" : "ПОРАЖЕНИЕ";
    setText("phase", phase);
    const workersInDanger = game.enemies.some(e => e.kind === "raider" &&
      game.units.some(u => u.type === "golem" && Sim.dist(e, u) < 185));
    setText("battle-caption", workersInDanger ? "⚠ НАЛЁТЧИКИ У ГОЛЕМОВ!" :
      game.construction ? "Алтарь строится" :
      game.rune ? "Рунная защита активна" :
      game.wave >= 2 ? "Остерегайся налётчиков на работников" : "Кузница против вторжения");
    setText("kill-counter", game.kills + " побеждено · " + game.lostGolems + " големов потеряно");
    setText("stance-label", game.stance === "guard" ? "Охранять Кузницу" : "Перехват врагов");
    for (const action of ["summon", "promote", "build", "pulse", "revert", "stance"]) {
      el(action).disabled = !Sim.available(game, action);
    }
    const selected = Sim.getUnit(game, game.selectedId);
    const info = el("selection");
    if (!selected) {
      info.innerHTML = "<p>Нажми на голема или защитника, чтобы выбрать его. Кнопки превращения учитывают выделение.</p>";
    } else if (selected.job) {
      const job = selected.job;
      const destination = job.kind === "build" ? "фундаменту" :
        job.kind === "promote" ? "Казармам" : "Кузнице";
      const p = job.stage === "ritual" ?
        (job.kind === "build" && game.construction ?
          game.construction.time / game.construction.total : job.time / job.duration) : 0;
      info.innerHTML = "<strong>СУЩЕСТВО · #" + selected.id + "</strong><em>" +
        (job.stage === "travel" ? "Идёт к " + destination :
          "Ритуал: " + Math.round(Math.max(0, Math.min(1, p)) * 100) + "%") +
        ". Не производит ману и не сражается. Защити его!</em>";
    } else if (selected.type === "golem") {
      info.innerHTML = "<strong>ГОЛЕМ · #" + selected.id + "</strong><em>Производство +" +
        Sim.C.golemMana.toFixed(2) + " маны / сек. · Жизни " +
        num(selected.hp) + "/" + selected.maxHp + "</em>";
    } else {
      info.innerHTML = "<strong>ВОИН · #" + selected.id + "</strong><em>Атака " +
        Sim.C.warriorDamage + " / сек. · Жизни " + num(selected.hp) + "/" + selected.maxHp +
        " · Не производит ману</em>";
    }
    const signature = game.messages.map(e => e.at + ":" + e.value).join("|");
    if (signature !== lastLog) {
      lastLog = signature;
      const list = el("messages");
      list.replaceChildren();
      for (const e of game.messages) {
        const li = document.createElement("li");
        li.className = e.type; li.textContent = e.value;
        list.appendChild(li);
      }
    }
    el("canvas-banner").hidden = !paused || game.phase === "win" || game.phase === "lose";
    setText("pause", paused ? "Продолжить P" : "Пауза P");
    setText("speed", "Скорость ×" + speed);
    if ((game.phase === "win" || game.phase === "lose") && shownEnding !== game.phase) {
      shownEnding = game.phase;
      el("end-screen").hidden = false;
      setText("end-label", game.phase === "win" ? "ПОБЕДА" : "ПОРАЖЕНИЕ");
      setText("end-title", game.phase === "win" ? "Кузница выстояла" : "Кузница пала");
      setText("end-description", game.resultReason + " Побеждено врагов: " + game.kills +
        ". Потеряно големов: " + game.lostGolems + ", воинов: " + game.lostWarriors +
        ". Осталось големов: " + Sim.count(game, "golem") + ".");
    }
  }
  function command(action) {
    const result = Sim.dispatch(game, action);
    if (result.ok && result.unitId) game.selectedId = result.unitId;
    updateUI();
  }
  for (const action of ["summon", "promote", "build", "pulse", "revert", "stance"]) {
    el(action).addEventListener("click", () => command(action));
  }
  function restart() {
    game = Sim.create(); paused = false; speed = 1;
    shownEnding = ""; lastLog = "";
    el("end-screen").hidden = true; updateUI();
  }
  function togglePause() { paused = !paused; updateUI(); }
  el("restart").addEventListener("click", restart);
  el("play-again").addEventListener("click", restart);
  el("pause").addEventListener("click", togglePause);
  el("speed").addEventListener("click", () => { speed = speed === 1 ? 2 : 1; updateUI(); });
  cv.addEventListener("pointerdown", event => {
    const r = cv.getBoundingClientRect();
    const x = (event.clientX - r.left) * W / r.width;
    const y = (event.clientY - r.top) * H / r.height;
    let selected = null, best = 30;
    for (const u of game.units) {
      const d = Math.hypot(u.x - x, u.y - y);
      if (d < best) { selected = u; best = d; }
    }
    game.selectedId = selected ? selected.id : null;
    updateUI();
  });
  window.addEventListener("keydown", event => {
    const tag = document.activeElement && document.activeElement.tagName;
    if (tag === "INPUT" || tag === "TEXTAREA") return;
    const actions = { "1": "summon", "2": "promote", "3": "build", "4": "pulse", "5": "revert", "6": "stance" };
    if (actions[event.key]) { event.preventDefault(); command(actions[event.key]); }
    else if (event.key.toLowerCase() === "p") togglePause();
    else if (event.key.toLowerCase() === "r") restart();
  });
  function frame(now) {
    const dt = Math.min(.07, Math.max(0, (now - lastTime) / 1000));
    lastTime = now;
    if (!paused) Sim.advance(game, dt * speed);
    paint();
    if (now - lastUi > 130) { updateUI(); lastUi = now; }
    requestAnimationFrame(frame);
  }
  updateUI();
  requestAnimationFrame(frame);
})();
