const test = require('node:test');
const assert = require('node:assert');
const s = require('./sched');

const HOL = ['2026-05-05', '2026-05-06'];

// ── 이미 통과하는 것 ───────────────────────────────────────────────
test('isWeekend', () => {
  assert.equal(s.isWeekend('2026-05-02'), true);   // 토
  assert.equal(s.isWeekend('2026-05-03'), true);   // 일
  assert.equal(s.isWeekend('2026-05-04'), false);  // 월
});

test('isBusinessDay 는 공휴일도 뺀다', () => {
  assert.equal(s.isBusinessDay('2026-05-04', HOL), true);
  assert.equal(s.isBusinessDay('2026-05-05', HOL), false);
  assert.equal(s.isBusinessDay('2026-05-02', HOL), false);
});

test('fmt/parse 왕복', () => {
  assert.equal(s.fmt(s.parse('2026-05-04')), '2026-05-04');
});

// ── addBusinessDays ───────────────────────────────────────────────
// 규약: 시작일은 세지 않는다. n 만큼의 영업일을 지난 날짜를 돌려준다.
test('addBusinessDays 는 주말을 건너뛴다', () => {
  assert.equal(s.addBusinessDays('2026-05-01', 1, []), '2026-05-04');
  assert.equal(s.addBusinessDays('2026-05-04', 3, []), '2026-05-07');
});

test('addBusinessDays 는 공휴일도 건너뛴다', () => {
  assert.equal(s.addBusinessDays('2026-05-04', 1, HOL), '2026-05-07');
  assert.equal(s.addBusinessDays('2026-05-01', 2, HOL), '2026-05-07');
});

test('addBusinessDays(n=0) 은 시작일을 그대로 돌려준다', () => {
  // 시작일이 영업일이 아니어도 당겨오거나 미루지 않는다.
  assert.equal(s.addBusinessDays('2026-05-04', 0, HOL), '2026-05-04');
  assert.equal(s.addBusinessDays('2026-05-05', 0, HOL), '2026-05-05');
  assert.equal(s.addBusinessDays('2026-05-02', 0, []), '2026-05-02');
});

test('addBusinessDays 는 음수면 거꾸로 센다', () => {
  assert.equal(s.addBusinessDays('2026-05-07', -1, HOL), '2026-05-04');
  assert.equal(s.addBusinessDays('2026-05-04', -1, []), '2026-05-01');
  assert.equal(s.addBusinessDays('2026-05-07', -2, HOL), '2026-05-01');
});

// ── mergeRanges ───────────────────────────────────────────────────
// 규약: 구간은 [start, end) 반열림이다. 결과는 start 오름차순으로 돌려준다.
test('mergeRanges 는 겹치는 구간을 합친다', () => {
  assert.deepEqual(
    s.mergeRanges([['2026-05-01', '2026-05-05'], ['2026-05-03', '2026-05-09']]),
    [['2026-05-01', '2026-05-09']]);
});

test('mergeRanges 는 맞닿은 구간도 합친다', () => {
  // 반열림이므로 앞 구간의 end 와 뒤 구간의 start 가 같으면 빈틈이 없다.
  assert.deepEqual(
    s.mergeRanges([['2026-05-01', '2026-05-05'], ['2026-05-05', '2026-05-09']]),
    [['2026-05-01', '2026-05-09']]);
  // 하루라도 벌어지면 합치지 않는다.
  assert.deepEqual(
    s.mergeRanges([['2026-05-01', '2026-05-05'], ['2026-05-06', '2026-05-09']]),
    [['2026-05-01', '2026-05-05'], ['2026-05-06', '2026-05-09']]);
});

test('mergeRanges 는 길이 0 구간을 버리고 정렬해서 돌려준다', () => {
  assert.deepEqual(
    s.mergeRanges([['2026-05-09', '2026-05-11'], ['2026-05-04', '2026-05-04'],
                   ['2026-05-01', '2026-05-03']]),
    [['2026-05-01', '2026-05-03'], ['2026-05-09', '2026-05-11']]);
  assert.deepEqual(s.mergeRanges([]), []);
});
