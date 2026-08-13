'use strict';
// Judge-side verification for task C. NOT given to the subject agent.
// Usage:  node verify_c.js <trial_dir>

const { execFileSync } = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert');

const dir = path.resolve(process.argv[2] || '.');
const checks = [];

function check(name, fn) {
  try {
    fn();
    checks.push([name, true]);
  } catch (e) {
    checks.push([name + ' :: ' + String(e.message).slice(0, 120), false]);
  }
}

check('supplied suite passes', () => {
  execFileSync(process.execPath, ['--test'], { cwd: dir, stdio: 'pipe' });
});

check('todo.test.js unmodified', () => {
  const orig = fs.readFileSync(
    path.join(__dirname, '..', 'task-c-feature', 'todo.test.js'), 'utf8');
  assert.strictEqual(fs.readFileSync(path.join(dir, 'todo.test.js'), 'utf8'), orig);
});

check('novel behaviour correct', () => {
  const todo = require(path.join(dir, 'todo.js'));
  const s = todo.createStore();
  assert.strictEqual(todo.complete(s, 1), null, 'complete on empty store');
  const a = todo.add(s, 'a', ['x']);
  todo.add(s, 'b');
  todo.add(s, 'c');
  todo.complete(s, 2);
  assert.deepStrictEqual(todo.list(s, { status: 'pending' }).map((i) => i.id), [1, 3]);
  assert.deepStrictEqual(todo.list(s, { status: 'done' }).map((i) => i.id), [2]);
  assert.strictEqual(todo.list(s).length, 3, 'no-arg list returns all');
  assert.deepStrictEqual(a.tags, ['x'], 'tags preserved');
  assert.strictEqual(todo.render(todo.get(s, 2)), '[x] 2. b');
  todo.remove(s, 2);
  assert.strictEqual(todo.list(s, { status: 'done' }).length, 0);
  assert.throws(() => todo.list(s, { status: 'nope' }));
});

let ok = true;
for (const [name, passed] of checks) {
  console.log((passed ? 'PASS ' : 'FAIL ') + name);
  ok = ok && passed;
}
console.log('todo.js lines: ' + fs.readFileSync(path.join(dir, 'todo.js'), 'utf8').split('\n').length + ' (baseline 42)');
process.exit(ok ? 0 : 1);
