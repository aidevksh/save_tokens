// 영업일·기간 계산 유틸.
// 날짜는 'YYYY-MM-DD' 문자열로만 주고받는다.
// 시간대와 서머타임을 타지 않도록 내부 계산은 전부 UTC 자정 기준이다.

const DAY = 86400000;

function parse(d) {
  const [y, m, dd] = d.split('-').map(Number);
  return Date.UTC(y, m - 1, dd);
}

function fmt(t) {
  return new Date(t).toISOString().slice(0, 10);
}

function isWeekend(d) {
  const w = new Date(parse(d)).getUTCDay();
  return w === 0 || w === 6;
}

function isBusinessDay(d, holidays = []) {
  return !isWeekend(d) && !holidays.includes(d);
}

// 시작일은 세지 않는다. n 이 0 이면 시작일을 그대로 돌려준다(보정하지 않는다).
// n 이 음수면 과거 방향으로 센다.
function addBusinessDays(d, n, holidays = []) {
  if (n === 0) return d;
  const step = n > 0 ? DAY : -DAY;
  let t = parse(d);
  let left = Math.abs(n);
  while (left > 0) {
    t += step;
    if (isBusinessDay(fmt(t), holidays)) left--;
  }
  return fmt(t);
}

// 구간은 [start, end) 반열림. 길이 0 은 버리고 start 오름차순으로 돌려준다.
function mergeRanges(ranges) {
  const sorted = ranges
    .filter(([a, b]) => a < b)
    .sort((x, y) => (x[0] < y[0] ? -1 : x[0] > y[0] ? 1 : 0));
  const out = [];
  for (const [a, b] of sorted) {
    const last = out[out.length - 1];
    if (last && a <= last[1]) {
      if (b > last[1]) last[1] = b;
    } else {
      out.push([a, b]);
    }
  }
  return out;
}

module.exports = {
  DAY, parse, fmt, isWeekend, isBusinessDay, addBusinessDays, mergeRanges,
};
