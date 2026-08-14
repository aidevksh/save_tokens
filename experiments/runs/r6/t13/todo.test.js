'use strict';

const test = require('node:test');
const assert = require('node:assert');
const todo = require('./todo.js');

test('add assigns incrementing ids', () => {
  const s = todo.createStore();
  assert.strictEqual(todo.add(s, 'one').id, 1);
  assert.strictEqual(todo.add(s, 'two').id, 2);
});

test('add rejects empty titles', () => {
  const s = todo.createStore();
  assert.throws(() => todo.add(s, '   '));
});

test('remove returns false for unknown id', () => {
  const s = todo.createStore();
  assert.strictEqual(todo.remove(s, 99), false);
});

test('render marks done items', () => {
  const s = todo.createStore();
  const it = todo.add(s, 'ship', ['work']);
  assert.strictEqual(todo.render(it), '[ ] 1. ship #work');
  it.done = true;
  assert.strictEqual(todo.render(it), '[x] 1. ship #work');
});

// --- feature under test: complete() and list() filtering ---

test('complete marks an item done and returns it', () => {
  const s = todo.createStore();
  todo.add(s, 'a');
  const it = todo.complete(s, 1);
  assert.strictEqual(it.done, true);
  assert.strictEqual(it.id, 1);
});

test('complete returns null for unknown id', () => {
  const s = todo.createStore();
  assert.strictEqual(todo.complete(s, 42), null);
});

test('complete is idempotent', () => {
  const s = todo.createStore();
  todo.add(s, 'a');
  todo.complete(s, 1);
  assert.strictEqual(todo.complete(s, 1).done, true);
  assert.strictEqual(todo.list(s).length, 1);
});

test('list filters by status', () => {
  const s = todo.createStore();
  todo.add(s, 'a');
  todo.add(s, 'b');
  todo.complete(s, 1);
  assert.deepStrictEqual(
    todo.list(s, { status: 'done' }).map((i) => i.id),
    [1]
  );
  assert.deepStrictEqual(
    todo.list(s, { status: 'pending' }).map((i) => i.id),
    [2]
  );
  assert.strictEqual(todo.list(s, { status: 'all' }).length, 2);
  assert.strictEqual(todo.list(s).length, 2);
});

test('list rejects an unknown status', () => {
  const s = todo.createStore();
  assert.throws(() => todo.list(s, { status: 'bogus' }));
});
