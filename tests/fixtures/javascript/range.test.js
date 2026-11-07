const test = require('node:test');
const assert = require('node:assert/strict');
const { clamp } = require('./range');

test('keeps values inside the bounds', () => assert.equal(clamp(5, 0, 10), 5));
test('raises low values', () => assert.equal(clamp(-2, 0, 10), 0));
test('lowers high values', () => assert.equal(clamp(20, 0, 10), 10));
test('supports negative bounds', () => assert.equal(clamp(-5, -10, -1), -5));
