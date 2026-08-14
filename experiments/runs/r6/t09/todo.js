'use strict';

// Minimal in-memory todo store. Backing store is a plain array of items:
//   { id: number, title: string, done: boolean, tags: string[] }

function createStore() {
  return { items: [], nextId: 1 };
}

function add(store, title, tags = []) {
  if (typeof title !== 'string' || title.trim() === '') {
    throw new Error('title is required');
  }
  const item = { id: store.nextId, title: title.trim(), done: false, tags };
  store.items.push(item);
  store.nextId += 1;
  return item;
}

function get(store, id) {
  return store.items.find((it) => it.id === id) || null;
}

function complete(store, id) {
  const item = get(store, id);
  if (!item) return null;
  item.done = true;
  return item;
}

const STATUSES = ['all', 'done', 'pending'];

function list(store, options = {}) {
  const status = options.status === undefined ? 'all' : options.status;
  if (!STATUSES.includes(status)) {
    throw new Error(`unknown status: ${status}`);
  }
  if (status === 'all') return store.items.slice();
  const wantDone = status === 'done';
  return store.items.filter((it) => it.done === wantDone);
}

function remove(store, id) {
  const idx = store.items.findIndex((it) => it.id === id);
  if (idx === -1) return false;
  store.items.splice(idx, 1);
  return true;
}

function render(item) {
  const box = item.done ? '[x]' : '[ ]';
  const tags = item.tags.length ? ' ' + item.tags.map((t) => '#' + t).join(' ') : '';
  return `${box} ${item.id}. ${item.title}${tags}`;
}

module.exports = { createStore, add, get, list, complete, remove, render };
