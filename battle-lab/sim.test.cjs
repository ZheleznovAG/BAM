"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const sim = require("./sim.js");

function run(game, seconds) {
  while (seconds > 0) {
    const dt = Math.min(seconds, 5);
    sim.advance(game, dt);
    seconds -= dt;
  }
}

test("starts with working golem economy and one defender", () => {
  const s = sim.create(42);
  assert.equal(sim.count(s, "golem"), 5);
  assert.equal(sim.count(s, "warrior"), 1);
  assert.equal(s.wave, 0);
  run(s, 3);
  assert.ok(s.mana > 116);
  assert.equal(s.phase, "prep");
});

test("summoning costs mana and adds a mana-producing golem", () => {
  const s = sim.create(42), before = s.mana;
  assert.equal(sim.dispatch(s, "summon").ok, true);
  assert.equal(s.mana, before - sim.C.golemCost);
  assert.equal(sim.count(s, "golem"), 6);
});

test("promoting and reverting require travel and a vulnerable ritual", () => {
  const s = sim.create(42), mana = s.mana, income = sim.manaRate(s);
  const unit = s.units.find(u => u.type === "golem");
  s.selectedId = unit.id;
  assert.equal(sim.dispatch(s, "promote").ok, true);
  assert.equal(unit.type, "golem");
  assert.equal(unit.job.stage, "travel");
  assert.equal(sim.manaRate(s), income - sim.C.golemMana);
  assert.equal(s.mana, mana - sim.C.warriorCost);
  run(s, 7);
  assert.equal(unit.type, "warrior");
  assert.equal(unit.job, null);
  assert.equal(sim.dispatch(s, "revert").ok, true);
  assert.equal(unit.job.kind, "revert");
  run(s, 7);
  assert.equal(unit.type, "golem");
  assert.equal(unit.job, null);
  assert.equal(sim.count(s, "golem"), 5);
});

test("four golems walk to the foundation, channel, then become the altar", () => {
  const s = sim.create(42);
  const beforeRate = sim.manaRate(s);
  const result = sim.dispatch(s, "build");
  assert.equal(result.ok, true);
  assert.equal(result.unitIds.length, 4);
  assert.equal(sim.count(s, "golem"), 5);
  assert.equal(sim.manaRate(s), beforeRate - 4 * sim.C.golemMana);
  assert.equal(s.construction.stage, "gather");
  run(s, 6);
  assert.equal(s.rune, false);
  assert.equal(s.construction.stage, "ritual");
  run(s, 10);
  assert.equal(s.rune, true);
  assert.equal(s.construction, null);
  assert.equal(sim.count(s, "golem"), 1);
});

test("rune pulse requires nearby enemies and never spends mana on failure", () => {
  const s = sim.create(42);
  sim.dispatch(s, "build");
  run(s, 16);
  const before = s.mana;
  assert.equal(sim.dispatch(s, "pulse").ok, false);
  assert.equal(s.mana, before);
  const enemy = {
    id: 999, x: 470, y: 275, hp: 90, maxHp: 90,
    speed: 30, damage: 7, attackClock: 0, slow: 0
  };
  s.enemies.push(enemy);
  assert.equal(sim.dispatch(s, "pulse").ok, true);
  assert.equal(enemy.hp, 37);
  assert.equal(s.mana, before - sim.C.pulseCost);
  assert.ok(enemy.slow > 0);
});

test("enemy waves begin after a preparation window", () => {
  const s = sim.create(42);
  run(s, 12.2);
  assert.equal(s.wave, 1);
  assert.equal(s.phase, "battle");
  assert.ok(s.enemies.length > 0);
});

test("can lose when the enemy destroys the forge", () => {
  const s = sim.create(42);
  s.phase = "battle"; s.wave = 1; s.pendingSpawns = 0;
  s.forgeHP = 1;
  s.enemies.push({
    id: 999, x: sim.SITES.forge.x, y: sim.SITES.forge.y,
    hp: 999, maxHp: 999, speed: 0, damage: 10, attackClock: 0, slow: 0
  });
  run(s, .1);
  assert.equal(s.forgeHP, 0);
  assert.equal(s.phase, "lose");
  assert.equal(sim.available(s, "summon"), false);
});

test("mana supply respects a 300 mana cap", () => {
  const s = sim.create(42);
  s.countdown = 10_000;
  run(s, 100);
  assert.equal(s.mana, sim.C.manaCap);
});

test("summoning is blocked by the unit cap and insufficient mana", () => {
  const s = sim.create(42);
  s.mana = 0;
  assert.equal(sim.dispatch(s, "summon").ok, false);
  s.mana = 300;
  while (s.units.length < sim.C.unitCap) {
    assert.equal(sim.dispatch(s, "summon").ok, true);
    s.mana = 300;
  }
  assert.equal(sim.available(s, "summon"), false);
  assert.equal(sim.dispatch(s, "summon").ok, false);
});


test("tactical order switches between intercept and guarding without spending mana", () => {
  const s = sim.create(42);
  const mana = s.mana;
  assert.equal(s.stance, "intercept");
  assert.equal(sim.dispatch(s, "stance").ok, true);
  assert.equal(s.stance, "guard");
  assert.equal(s.mana, mana);
  sim.dispatch(s, "stance");
  assert.equal(s.stance, "intercept");
});

test("a raider attacks a mana-producing golem and reduces future income", () => {
  const s = sim.create(42);
  s.units = s.units.filter(u => u.type === "golem");
  const victim = s.units[0];
  s.units = [victim];
  s.phase = "battle"; s.wave = 1; s.pendingSpawns = 0;
  s.enemies = [{
    id: 999, kind: "raider", x: victim.x, y: victim.y,
    hp: 999, maxHp: 999, speed: 0, damage: 100,
    attackClock: 0, slow: 0
  }];
  sim.advance(s, .1);
  assert.equal(sim.count(s, "golem"), 0);
  assert.equal(s.lostGolems, 1);
  const before = s.mana;
  sim.advance(s, .1);
  assert.ok(s.mana - before < sim.C.forgeMana * .2);
});

test("wave two includes raiders; wave three also includes brutes", () => {
  const s = sim.create(42);
  s.phase = "prep"; s.wave = 1; s.countdown = .01; s.enemies = [];
  run(s, 9);
  assert.equal(s.wave, 2);
  assert.ok(s.enemies.some(e => e.kind === "raider"));
  s.phase = "prep"; s.wave = 2; s.countdown = .01;
  s.enemies = []; s.pendingSpawns = 0;
  run(s, 11);
  assert.equal(s.wave, 3);
  assert.ok(s.enemies.some(e => e.kind === "brute"));
});

test("guarding protects home instead of chasing a distant enemy", () => {
  function setup(guard) {
    const s = sim.create(42);
    s.phase = "battle"; s.wave = 1; s.pendingSpawns = 0;
    s.enemies = [{
      id: 999, kind: "soldier", x: 880, y: 270,
      hp: 999, maxHp: 999, speed: 0, damage: 0, attackClock: 5, slow: 0
    }];
    if (guard) sim.dispatch(s, "stance");
    return s;
  }
  const hunting = setup(false), guarding = setup(true);
  run(hunting, .5); run(guarding, .5);
  const huntX = hunting.units.find(u => u.type === "warrior").x;
  const guardX = guarding.units.find(u => u.type === "warrior").x;
  assert.ok(huntX > 340);
  assert.ok(guardX < 340);
});

test("same seed and orders reproduce exactly the same simulation", () => {
  const a = sim.create(2026), b = sim.create(2026);
  for (const s of [a, b]) {
    sim.dispatch(s, "summon");
    sim.dispatch(s, "promote");
    run(s, 16);
  }
  assert.equal(JSON.stringify(a), JSON.stringify(b));
});

test("tactical changes are unavailable once the battle ends", () => {
  const s = sim.create(42);
  s.phase = "win";
  assert.equal(sim.available(s, "stance"), false);
  assert.equal(sim.dispatch(s, "stance").ok, false);
  assert.equal(s.stance, "intercept");
});

test("a selected busy worker is not reassigned to a different role", () => {
  const s = sim.create(42);
  const rate = sim.manaRate(s);
  sim.dispatch(s, "build");
  assert.equal(sim.idleGolems(s).length, 1);
  assert.equal(sim.manaRate(s), rate - 4 * sim.C.golemMana);
  const id = s.construction.ids[0];
  s.selectedId = id;
  assert.equal(sim.dispatch(s, "promote").ok, false);
  assert.equal(sim.getUnit(s, id).job.kind, "build");
});

test("killing a builder aborts construction and frees remaining workers", () => {
  const s = sim.create(42);
  const before = s.mana;
  sim.dispatch(s, "build");
  sim.getUnit(s, s.construction.ids[0]).hp = 0;
  sim.advance(s, .1);
  assert.equal(s.construction, null);
  assert.equal(s.rune, false);
  assert.equal(sim.idleGolems(s).length, 4);
  assert.ok(s.mana > before - sim.C.runeCost);
  assert.equal(s.units.filter(u => u.job).length, 0);
});

test("a killed golem cannot complete a pending promotion", () => {
  const s = sim.create(42);
  const u = s.units.find(x => x.type === "golem");
  s.selectedId = u.id;
  sim.dispatch(s, "promote");
  u.hp = 0;
  s.phase = "battle"; s.wave = 1; s.pendingSpawns = 0;
  s.enemies = [{ id: 999, kind: "soldier", x: 900, y: 400,
    hp: 999, maxHp: 999, speed: 0, damage: 0, attackClock: 10, slow: 0 }];
  sim.advance(s, .1);
  assert.equal(sim.getUnit(s, u.id), undefined);
  assert.equal(sim.count(s, "warrior"), 1);
});

test("jobs evolve deterministically when the seed and commands match", () => {
  const a = sim.create(104), b = sim.create(104);
  for (const s of [a, b]) {
    sim.dispatch(s, "build");
    run(s, 2.25);
  }
  assert.equal(JSON.stringify(a), JSON.stringify(b));
});
