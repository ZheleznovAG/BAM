"use strict";
const test = require("node:test");
const assert = require("node:assert/strict");
const fs = require("node:fs");
const vm = require("node:vm");
const path = require("node:path");
const Sim = require("./sim.js");

const here = __dirname;
const html = fs.readFileSync(path.join(here, "index.html"), "utf8");
const source = fs.readFileSync(path.join(here, "app.js"), "utf8");
const ids = Array.from(html.matchAll(/\bid="([^"]+)"/g), x => x[1]);

function mount() {
  const frames = [];
  const scripts = [];
  let drawnImages = 0;
  const context = new Proxy({
    createLinearGradient() { return { addColorStop() {} }; },
    createRadialGradient() { return { addColorStop() {} }; },
    drawImage() { drawnImages++; },
    measureText(s) { return { width: s.length * 6 }; },
  }, { get(target, key) { return key in target ? target[key] : () => {}; } });
  const nodes = Object.fromEntries(ids.map(id => [id, {
    id, disabled: false, hidden: false, innerHTML: "", textContent: "",
    children: [], events: {},
    addEventListener(name, handler) { this.events[name] = handler; },
    replaceChildren() { this.children = []; },
    appendChild(child) { this.children.push(child); },
    getContext() { return context; },
    getBoundingClientRect() { return {left:0,top:0,width:960,height:560}; }
  }]));
  const document = {
    activeElement: {tagName: "BODY"},
    getElementById(id) { return nodes[id] || null; },
    createElement(name) { return {tagName: name, className: "", textContent: ""}; },
    head: { appendChild(script) { scripts.push(script); } }
  };
  const winEvents = {};
  const window = {
    BAMSim: Sim,
    addEventListener(name, cb) { winEvents[name] = cb; }
  };
  class FakeImage {
    constructor() { this.complete = false; this.naturalWidth = 0; this.naturalHeight = 0; }
    set src(value) {
      this._src = value;
      this.complete = true; this.naturalWidth = 17; this.naturalHeight = 25;
      if (this.onload) this.onload();
    }
    get src() { return this._src; }
  }
  vm.runInNewContext(source, {
    window, document, Image: FakeImage,
    performance: { now: () => 0 },
    requestAnimationFrame: fn => frames.push(fn)
  }, { timeout: 1000, filename: "app.js" });
  return {
    nodes, scripts, window, winEvents, frames,
    nextFrame(now = 120) {
      const next = frames.shift();
      assert.equal(typeof next, "function");
      next(now);
    },
    drawnImages() { return drawnImages; }
  };
}

const demoPack = {
  version: 1, localOnly: true,
  roles: {
    golem: {
      fps: 6, resourceId: "1000",
      frames: [
        {src:"../.local/bam-assets/1000/frame-000.png",
         width:17,height:16,originX:9,originY:11},
        {src:"../.local/bam-assets/1000/frame-001.png",
         width:13,height:23,originX:7,originY:28}
      ]
    }
  }
};

test("UI has all required sprite controls and starts without needing local files", () => {
  const x = mount();
  assert.equal(x.scripts.length, 0);
  assert.match(x.nodes["asset-status"].textContent, /Процедурная графика/);
  x.nextFrame();
  assert.equal(x.drawnImages(), 0);
});

test("button loads opt-in local pack and draws original sprite frames", () => {
  const x = mount();
  x.nodes["asset-toggle"].events.click();
  assert.equal(x.scripts.length, 1);
  assert.equal(x.scripts[0].src, "../.local/bam-assets/asset-pack.js");
  x.window.BAM_LOCAL_ASSETS = demoPack;
  x.scripts[0].onload();
  x.nextFrame();
  assert.ok(x.drawnImages() >= 5);
  assert.match(x.nodes["asset-status"].textContent, /Локальные спрайты/);
  const previous = x.drawnImages();
  x.nodes["asset-toggle"].events.click();
  x.nextFrame(230);
  assert.equal(x.drawnImages(), previous);
});

test("missing local pack is a recoverable condition, not a game crash", () => {
  const x = mount();
  x.nodes["asset-toggle"].events.click();
  x.scripts[0].onerror();
  assert.match(x.nodes["asset-status"].textContent, /не найден/);
  assert.equal(x.nodes["asset-toggle"].disabled, false);
  x.nextFrame();
  assert.equal(x.drawnImages(), 0);
});

test("malformed pack is rejected and the game keeps procedural art", () => {
  const x = mount();
  x.nodes["asset-toggle"].events.click();
  x.window.BAM_LOCAL_ASSETS = {
    version: 1, localOnly: true,
    roles: {
      golem: {fps:6,frames:[{src:"https://example.org/img.png",
        width:17,height:16,originX:0,originY:0}]}
    }
  };
  x.scripts[0].onload();
  assert.match(x.nodes["asset-status"].textContent, /некорректный/);
  x.nextFrame();
  assert.equal(x.drawnImages(), 0);
});

test("the sprite toggle does not change battle simulation state", () => {
  const x = mount();
  x.nodes["asset-toggle"].events.click();
  x.window.BAM_LOCAL_ASSETS = demoPack;
  x.scripts[0].onload();
  const before = x.nodes.mana.textContent;
  x.nodes["asset-toggle"].events.click();
  assert.equal(x.nodes.mana.textContent, before);
  x.nodes.summon.events.click();
  assert.notEqual(x.nodes.mana.textContent, before);
});
