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

test("training a warrior trades mana and production for defense", () => {
  const s = sim.create(42), before = s.mana;
  const unit = s.units.find(u => u.type === "golem");
  s.selectedId = unit.id;
  assert.equal(sim.dispatch(s, "promote").ok, true);
  assert.equal(sim.count(s, "golem"), 4);
  assert.equal(sim.count(s, "warrior"), 2);
  assert.equal(sim.getUnit(s, unit.id).type, "warrior");
  assert.equal(s.mana, before - sim.C.warriorCost);
  assert.equal(sim.dispatch(s, "revert").ok, true);
  assert.equal(sim.count(s, "golem"), 5);
  assert.equal(sim.count(s, "warrior"), 1);
});

test("a rune site consumes four golems and takes time to construct", () => {
  const s = sim.create(42);
  assert.equal(sim.dispatch(s, "build").ok, true);
  assert.equal(sim.count(s, "golem"), 1);
  assert.equal(s.rune, false);
  assert.ok(s.construction);
  run(s, 9.5);
  assert.equal(s.rune, true);
  assert.equal(s.construction, null);
  assert.equal(sim.available(s, "build"), false);
});

test("rune pulse requires nearby enemies and never spends mana on failure", () => {
  const s = sim.create(42);
  sim.dispatch(s, "build");
  run(s, 9.5);
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
