/* BAM Battle Lab — original experimental game logic.
   No assets or executable code from the 1996 game are reproduced here.
   Browser: window.BAMSim; Node tests: require('./sim.js'). */
(function (root, create) {
  const api = create();
  if (typeof module !== "undefined" && module.exports) module.exports = api;
  root.BAMSim = api;
})(typeof globalThis !== "undefined" ? globalThis : this, function () {
  "use strict";
  const C = Object.freeze({
    width: 960, height: 560, waves: 5, manaCap: 300,
    golemCost: 34, warriorCost: 48, hunterCost: 56, channelerCost: 65,
    runeCost: 24, pulseCost: 38, barrierCost: 52, recallCost: 18,
    forgeHP: 240, golemMana: 1.05, forgeMana: 0.65,
    warriorHP: 170, warriorDamage: 27, warriorSpeed: 92,
    buildSeconds: 9, golemSpeed: 75, transformSeconds: 3, reverseSeconds: 2.5,
    unitCap: 20, pulseRadius: 245, barrierDuration: 7, barrierCooldown: 21, recallCooldown: 15
  });
  const ROLES = Object.freeze({
    guardian: { label: "Страж", hp: 170, damage: 19, speed: 64, range: 37, cost: C.warriorCost },
    hunter: { label: "Охотник", hp: 80, damage: 33, speed: 150, range: 31, cost: C.hunterCost },
    channeler: { label: "Заклинатель", hp: 65, damage: 15, speed: 72, range: 150, cost: C.channelerCost }
  });
  const UPGRADE_OPTIONS = Object.freeze([
    ["mana", "ritual"], ["damage", "forge"], ["mana", "damage"], ["ritual", "forge"]
  ]);
  const UPGRADE_LABELS = Object.freeze({
    mana: "Мудрость обелисков — +0,4 маны/сек. каждому голему",
    ritual: "Быстрые ритуалы — время −25%",
    damage: "Искусство боя — +20% урона всем защитникам",
    forge: "Рунная броня — +45 к максимальному здоровью Кузницы"
  });
  const SITES = Object.freeze({
    forge: { x: 153, y: 275 },
    barracks: { x: 312, y: 145 },
    foundation: { x: 400, y: 405 },
    pulse: { x: 470, y: 275 }
  });

  function random(s) {
    s.seed = ((1664525 * s.seed + 1013904223) >>> 0);
    return s.seed / 4294967296;
  }
  function dist(a, b) { return Math.hypot(a.x - b.x, a.y - b.y); }
  function message(s, value, type = "info") {
    s.messages.unshift({ value, type, at: s.time });
    if (s.messages.length > 6) s.messages.length = 6;
  }
  function makeUnit(s, type, x, y) {
    const isGolem = type === "golem";
    const hp = isGolem ? 46 : C.warriorHP;
    return { id: ++s.nextId, type, role: isGolem ? null : "guardian", x, y, hp, maxHp: hp, job: null };
  }
  function createGolem(s) {
    const angle = (s.nextId * 2.3999632297);
    const radius = 71 + (s.nextId % 3) * 22;
    const x = SITES.forge.x + 22 + Math.cos(angle) * radius;
    const y = SITES.forge.y + Math.sin(angle) * radius;
    const unit = makeUnit(s, "golem", x, y);
    s.units.push(unit);
    return unit;
  }
  function create(seed = 2026) {
    const s = {
      seed: seed >>> 0, nextId: 0, time: 0, mana: 116,
      forgeHP: C.forgeHP, units: [], enemies: [], effects: [],
      messages: [], selectedId: null, stance: "intercept", wave: 0, phase: "prep",
      countdown: 12, pendingSpawns: 0, spawnWait: 0,
      construction: null, rune: false, kills: 0, lostGolems: 0, lostWarriors: 0,
      enemySpawnIndex: 0, barrier: 0, cooldowns: { barrier: 0, recall: 0 },
      upgradeOptions: [], upgrades: { mana: 0, ritual: 0, damage: 0, forge: 0 },
      forgeMaxHP: C.forgeHP, resultReason: ""
    };
    for (let i = 0; i < 5; i++) createGolem(s);
    s.units.push(makeUnit(s, "warrior", 340, 268));
    message(s, "Оставь големов копить ману или преврати их в бойцов.");
    message(s, "Защити Кузницу на протяжении пяти волн.", "goal");
    return s;
  }
  function count(s, type) {
    return s.units.filter(u => u.type === type && u.hp > 0).length;
  }
  function getUnit(s, id) { return s.units.find(u => u.id === id && u.hp > 0); }
  function idleGolems(s) {
    return s.units.filter(u => u.type === "golem" && u.hp > 0 && !u.job);
  }
  function manaRate(s) {
    return C.forgeMana + idleGolems(s).length * (C.golemMana + s.upgrades.mana * .4);
  }
  function idleWarriors(s) {
    return s.units.filter(u => u.type === "warrior" && u.hp > 0 && !u.job);
  }
  function assignTravel(unit, kind, dest, duration) {
    unit.job = { kind, stage: "travel", dest, time: 0, duration };
  }
  function available(s, action) {
    if (action.startsWith("upgrade-")) {
      return s.phase === "upgrade" && s.upgradeOptions.includes(action.slice(8));
    }
    if (s.phase === "win" || s.phase === "lose" || s.phase === "upgrade") return false;
    switch (action) {
      case "stance": return true;
      case "summon": return s.mana >= C.golemCost && s.units.length < C.unitCap;
      case "promote": return s.mana >= C.warriorCost && idleGolems(s).length > 0;
      case "hunter": return s.mana >= C.hunterCost && idleGolems(s).length > 0;
      case "channeler": return s.mana >= C.channelerCost && idleGolems(s).length > 0;
      case "barrier": return s.mana >= C.barrierCost && s.cooldowns.barrier <= 0 && s.barrier <= 0 && count(s,"golem") > 0;
      case "recall": return s.mana >= C.recallCost && s.cooldowns.recall <= 0 &&
        (s.units.some(u => u.job) || s.units.some(u => u.type === "warrior"));
      case "revert": return idleWarriors(s).length > 0;
      case "build": return !s.rune && !s.construction && idleGolems(s).length >= 4 && s.mana >= C.runeCost;
      case "pulse": return s.rune && s.mana >= C.pulseCost &&
        s.enemies.some(e => e.hp > 0 && dist(e, SITES.pulse) < C.pulseRadius);
      default: return false;
    }
  }
  function fail(s, msg) { message(s, msg, "warn"); return { ok: false, message: msg }; }
  function dispatch(s, action) {
    if (!available(s, action)) return fail(s, "Сейчас это действие недоступно.");
    if (action.startsWith("upgrade-")) {
      const key = action.slice(8);
      s.upgrades[key]++;
      if (key === "forge") {
        s.forgeMaxHP += 45;
        s.forgeHP = Math.min(s.forgeMaxHP, s.forgeHP + 45);
      }
      s.upgradeOptions = [];
      s.phase = "prep"; s.countdown = 11;
      message(s, "Изучено улучшение: " + UPGRADE_LABELS[key], "good");
      return { ok: true, upgrade: key };
    }
    if (action === "barrier") {
      s.mana -= C.barrierCost;
      s.barrier = C.barrierDuration;
      s.cooldowns.barrier = C.barrierCooldown;
      s.effects.push({ type: "barrier", x: SITES.forge.x, y: SITES.forge.y, life: 1, max: 1 });
      message(s, "Барьер защитил всех големов на 7 секунд (снижает урон на 70%).", "good");
      return { ok: true };
    }
    if (action === "recall") {
      s.mana -= C.recallCost;
      s.cooldowns.recall = C.recallCooldown;
      if (s.construction) {
        s.mana = Math.min(C.manaCap, s.mana + Math.floor(C.runeCost / 2));
        s.construction = null;
      }
      let recalled = 0;
      for (const u of s.units) {
        if (!u.job && u.type !== "warrior") continue;
        const a = (u.id * 2.39996323);
        const dest = {
          x: SITES.forge.x + 70 + Math.cos(a) * 27,
          y: SITES.forge.y + Math.sin(a) * 70
        };
        assignTravel(u, "recall", dest, 0);
        recalled++;
      }
      message(s, "Отход! " + recalled + " существ возвращаются к Кузнице. Незавершённые ритуалы отменены.", "warn");
      return { ok: true, recalled };
    }
    if (action === "stance") {
      s.stance = s.stance === "intercept" ? "guard" : "intercept";
      message(s, s.stance === "guard" ?
        "Приказ: охранять Кузницу и работников, не преследовать далёких врагов." :
        "Приказ: перехватывать врагов по всему полю.", "good");
      return { ok: true, stance: s.stance };
    }
    if (action === "summon") {
      s.mana -= C.golemCost;
      const u = createGolem(s);
      message(s, "Новый голем ожил. Пока он неподвижен, он приносит ману.", "good");
      return { ok: true, unitId: u.id };
    }
    if (action === "promote" || action === "hunter" || action === "channeler") {
      const role = action === "promote" ? "guardian" : action;
      let u = getUnit(s, s.selectedId);
      if (u && u.job) return fail(s, "Выбранный голем уже выполняет приказ.");
      if (!u || u.type !== "golem") u = idleGolems(s)[0];
      s.mana -= ROLES[role].cost;
      assignTravel(u, "promote", {
        x: SITES.barracks.x + (random(s) - .5) * 60,
        y: SITES.barracks.y + 59 + random(s) * 19
      }, C.transformSeconds * Math.pow(.75, s.upgrades.ritual));
      u.job.role = role;
      message(s, "Голем #" + u.id + " идёт в Казармы, чтобы стать " + ROLES[role].label.toLowerCase() + "ом.", "good");
      return { ok: true, unitId: u.id };
    }
    if (action === "revert") {
      let u = getUnit(s, s.selectedId);
      if (u && u.job) return fail(s, "Выбранное существо уже выполняет приказ.");
      if (!u || u.type !== "warrior") u = idleWarriors(s)[0];
      assignTravel(u, "revert", {
        x: SITES.forge.x + 66 + (random(s) - .5) * 36,
        y: SITES.forge.y + (random(s) - .5) * 110
      }, C.reverseSeconds * Math.pow(.75, s.upgrades.ritual));
      message(s, "Воин #" + u.id + " возвращается к Кузнице. Во время ритуала он не сражается.");
      return { ok: true, unitId: u.id };
    }
    if (action === "build") {
      s.mana -= C.runeCost;
      const chosen = idleGolems(s).slice(0, 4);
      const ids = chosen.map(u => u.id);
      chosen.forEach((u, i) => {
        const angle = -Math.PI / 4 + i * Math.PI / 2;
        assignTravel(u, "build", {
          x: SITES.foundation.x + Math.cos(angle) * 33,
          y: SITES.foundation.y + Math.sin(angle) * 33
        }, C.buildSeconds);
      });
      s.construction = { time: 0, total: C.buildSeconds * Math.pow(.75, s.upgrades.ritual), ids, stage: "gather" };
      message(s, "Четыре голема идут к фундаменту. Охраняй их: если погибнет один, ритуал сорвётся!", "warn");
      return { ok: true, unitIds: ids };
    }
    if (action === "pulse") {
      const targets = s.enemies.filter(e => e.hp > 0 && dist(e, SITES.pulse) < C.pulseRadius);
      if (!targets.length) return fail(s, "В радиусе заклинания нет врагов.");
      s.mana -= C.pulseCost;
      for (const e of targets) { e.hp -= 53; e.slow = Math.max(e.slow, 3.4); }
      s.effects.push({ type: "pulse", x: SITES.pulse.x, y: SITES.pulse.y, life: .75, max: .75 });
      message(s, "Рунный импульс поразил " + targets.length + " противников!", "good");
      return { ok: true, targets: targets.length };
    }
    return fail(s, "Неизвестная команда.");
  }
  function spawnEnemy(s) {
    const wave = s.wave;
    const index = s.enemySpawnIndex++;
    // Original experimental scenario, not the 1996 game's enemies.
    const kind = wave === C.waves && index === (2 + wave * 2) - 1 ? "boss" :
      wave >= 3 && index % 4 === 3 ? "brute" :
      wave >= 2 && index % 3 === 1 ? "raider" : "soldier";
    const baseHp = 33 + 13 * wave;
    const hp = Math.round(baseHp * (kind === "boss" ? 6.5 : kind === "brute" ? 2.7 : kind === "raider" ? .78 : 1));
    const y = 115 + random(s) * 315;
    const enemy = {
      id: ++s.nextId, kind, x: 935 + random(s) * 16, y,
      hp, maxHp: hp,
      speed: (47 + wave * 2.5) * (kind === "boss" ? .5 : kind === "raider" ? 1.55 : kind === "brute" ? .66 : 1),
      damage: (7 + wave * 1.4) * (kind === "boss" ? 2.8 : kind === "brute" ? 1.8 : kind === "raider" ? .9 : 1),
      attackClock: .25, slow: 0
    };
    s.enemies.push(enemy);
    if (kind === "boss") message(s, "На поле появился ДРЕВНИЙ РАЗРУШИТЕЛЬ! Защити Кузницу!", "warn");
  }
  function beginWave(s) {
    s.wave++;
    s.phase = "battle";
    s.pendingSpawns = 2 + s.wave * 2;
    s.enemySpawnIndex = 0;
    s.spawnWait = 0;
    const threat = s.wave === C.waves ? " Последняя атака: приходит Древний разрушитель!" :
      s.wave >= 3 ? " Налётчики и бронированные громилы!" :
      s.wave >= 2 ? " Осторожно: налётчики охотятся на големов!" : "";
    message(s, "Волна " + s.wave + " / " + C.waves + ": враги приближаются!" + threat, "warn");
  }
  function moveToward(e, dest, speed, dt) {
    const d = dist(e, dest);
    if (d < .001) return d;
    const step = Math.min(d, speed * dt);
    e.x += (dest.x - e.x) / d * step;
    e.y += (dest.y - e.y) / d * step;
    return d - step;
  }
  function tickJobs(s, dt) {
    for (const u of s.units) {
      if (!u.job || u.hp <= 0) continue;
      const job = u.job;
      if (job.stage === "travel") {
        const remaining = moveToward(u, job.dest, C.golemSpeed, dt);
        if (remaining <= 0.01) {
          job.stage = "ritual";
          job.time = 0;
          if (job.kind === "recall") {
            u.job = null;
            message(s, "Существо #" + u.id + " вернулось к Кузнице.");
          } else if (job.kind !== "build") {
            message(s, "У алтаря вспыхнула магия: ритуал #" + u.id + " начался.", "good");
          }
        }
      } else if (job.stage === "ritual" && job.kind !== "build") {
        job.time += dt;
        if (job.time >= job.duration) {
          if (job.kind === "promote") {
            const role = ROLES[job.role] ? job.role : "guardian";
            u.type = "warrior"; u.role = role;
            u.hp = ROLES[role].hp; u.maxHp = ROLES[role].hp;
            message(s, "Голем #" + u.id + " превратился в воина!", "good");
          } else {
            u.type = "golem"; u.role = null; u.hp = 46; u.maxHp = 46;
            message(s, "Воин #" + u.id + " стал големом и снова копит ману.", "good");
          }
          s.effects.push({ type: "build", x: u.x, y: u.y, life: 1.2, max: 1.2 });
          u.job = null;
        }
      }
    }
    if (!s.construction) return;
    const ritual = s.construction;
    const assigned = ritual.ids.map(id => getUnit(s, id));
    if (assigned.some(u => !u)) {
      // A lost worker aborts the ritual; surviving workers become free again.
      for (const id of ritual.ids) {
        const worker = s.units.find(u => u.id === id);
        if (worker) worker.job = null;
      }
      s.construction = null;
      s.mana = Math.min(C.manaCap, s.mana + Math.floor(C.runeCost / 2));
      message(s, "Ритуал алтаря сорван! Выжившие големы освобождены, часть маны возвращена.", "warn");
      return;
    }
    if (ritual.stage === "gather") {
      if (assigned.every(u => u.job && u.job.stage === "ritual")) {
        ritual.stage = "ritual";
        message(s, "Четыре голема заняли места. Рунический алтарь пробуждается!", "good");
      }
    } else {
      ritual.time += dt;
      if (ritual.time >= ritual.total) {
        const spent = new Set(ritual.ids);
        s.units = s.units.filter(u => !spent.has(u.id));
        if (spent.has(s.selectedId)) s.selectedId = null;
        s.construction = null; s.rune = true;
        s.effects.push({ type: "build", x: SITES.foundation.x, y: SITES.foundation.y, life: 1.2, max: 1.2 });
        message(s, "Четыре голема слились с алтарём. Теперь доступен рунический импульс!", "good");
      }
    }
  }
  function step(s, dt) {
    if (s.phase === "win" || s.phase === "lose") return;
    s.time += dt;
    if (s.phase === "upgrade") return;
    s.barrier = Math.max(0, s.barrier - dt);
    s.cooldowns.barrier = Math.max(0, s.cooldowns.barrier - dt);
    s.cooldowns.recall = Math.max(0, s.cooldowns.recall - dt);
    s.mana = Math.min(C.manaCap, s.mana + manaRate(s) * dt);
    tickJobs(s, dt);
    for (const fx of s.effects) fx.life -= dt;
    s.effects = s.effects.filter(fx => fx.life > 0);
    if (s.phase === "prep") {
      s.countdown -= dt;
      if (s.countdown <= 0) beginWave(s);
    }
    if (s.phase !== "battle") return;
    s.spawnWait -= dt;
    while (s.pendingSpawns > 0 && s.spawnWait <= 0) {
      spawnEnemy(s);
      s.pendingSpawns--;
      s.spawnWait += 1.4;
    }

    const warriors = idleWarriors(s);
    for (const u of warriors) {
      let target = null, best = Infinity;
      for (const e of s.enemies) {
        if (e.hp <= 0) continue;
        if (s.stance === "guard" && dist(e, SITES.forge) > 260) continue;
        const d = dist(u, e);
        if (d < best) { best = d; target = e; }
      }
      const role = ROLES[u.role] || ROLES.guardian;
      if (target) {
        if (best <= role.range) {
          const bonus = u.role === "hunter" ? (target.kind === "raider" ? 1.65 : target.kind === "brute" ? .6 : 1) : 1;
          target.hp -= role.damage * bonus * (1 + s.upgrades.damage * .2) * dt;
          if (u.role === "channeler") target.slow = Math.max(target.slow, .35);
          if (!u.attackTimer || u.attackTimer <= 0) {
            u.attackTimer = u.role === "channeler" ? .6 : .4;
            s.effects.push({ type: "hit", x: target.x, y: target.y, life: .2, max: .2 });
          }
        } else moveToward(u, target, role.speed, dt);
      } else {
        moveToward(u, s.stance === "guard" ? { x: 265, y: 275 } : { x: 335, y: 275 },
          role.speed * .6, dt);
      }
      u.attackTimer = Math.max(0, (u.attackTimer || 0) - dt);
    }
    for (const e of s.enemies) {
      if (e.hp <= 0) continue;
      let target = null, best = Infinity;
      for (const u of warriors) {
        if (u.hp <= 0) continue;
        const d = dist(e, u);
        const reach = u.role === "guardian" ? 78 : 40;
        if (d < reach && d < best) { best = d; target = u; }
      }
      if (!target && e.kind === "raider") {
        let nearest = Infinity;
        for (const u of s.units) {
          if (u.hp <= 0 || u.type !== "golem") continue;
          const d = dist(e, u);
          if (d < nearest) { nearest = d; target = u; }
        }
      }
      if (!target) target = SITES.forge;
      const d = dist(e, target);
      const slowed = e.slow > 0 || (s.rune && dist(e, SITES.foundation) < 175);
      if (d > (target === SITES.forge ? 41 : 30)) {
        moveToward(e, target, e.speed * (slowed ? .65 : 1), dt);
      } else {
        e.attackClock -= dt;
        if (e.attackClock <= 0) {
          if (target === SITES.forge) s.forgeHP -= e.damage;
          else {
            const protectedWorker = target.type === "golem" && s.barrier > 0;
            target.hp -= e.damage * (protectedWorker ? .3 : 1);
          }
          e.attackClock += 1.15;
        }
      }
      if (s.rune && dist(e, SITES.foundation) < 175) e.hp -= 1.5 * dt;
      e.slow = Math.max(0, e.slow - dt);
    }
    s.units = s.units.filter(u => {
      if (u.hp > 0) return true;
      s.effects.push({ type: "death", x: u.x, y: u.y, life: .55, max: .55 });
      if (u.type === "golem") {
        s.lostGolems++;
        message(s, "Налётчик уничтожил голема! Производство маны снизилось.", "warn");
      } else {
        s.lostWarriors++;
        message(s, "Один из воинов погиб.", "warn");
      }
      return false;
    });
    if (s.selectedId && !getUnit(s, s.selectedId)) s.selectedId = null;
    s.enemies = s.enemies.filter(e => {
      if (e.hp > 0) return true;
      s.kills++;
      s.effects.push({ type: "death", x: e.x, y: e.y, life: .55, max: .55 });
      s.mana = Math.min(C.manaCap, s.mana + 3);
      return false;
    });
    if (s.forgeHP <= 0) {
      s.forgeHP = 0; s.phase = "lose";
      s.resultReason = "Кузница разрушена. Попробуй оставить больше големов для экономики или раньше собрать армию.";
      message(s, "Кузница пала.", "warn");
    } else if (s.pendingSpawns === 0 && s.enemies.length === 0) {
      if (s.wave === C.waves) {
        s.phase = "win"; s.resultReason = "Все пять волн отражены. Кузница выстояла!";
        message(s, "Победа! Кузница сохранена.", "good");
      } else {
        s.phase = "upgrade"; s.upgradeOptions = UPGRADE_OPTIONS[s.wave - 1].slice();
        s.forgeHP = Math.min(s.forgeMaxHP, s.forgeHP + 12);
        message(s, "Волна отбита. Выбери ОДНО улучшение, чтобы продолжить.", "good");
      }
    }
  }
  function advance(s, seconds) {
    if (!Number.isFinite(seconds) || seconds < 0) throw new Error("seconds must be non-negative");
    let left = Math.min(seconds, 5);
    while (left > .0000001) {
      const dt = Math.min(left, .05);
      step(s, dt); left -= dt;
    }
    return s;
  }
  return { C, SITES, ROLES, UPGRADE_LABELS, create, count, getUnit, manaRate, idleGolems, available, dispatch, advance, dist };
});
