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

function addBusinessDays(d, n, holidays = []) {
  if (n === 0) return d;
  const step = n < 0 ? -DAY : DAY;
  let remaining = Math.abs(n);
  let t = parse(d);
  while (remaining > 0) {
    t += step;
    if (isBusinessDay(fmt(t), holidays)) remaining -= 1;
  }
  return fmt(t);
}

function mergeRanges(ranges) {
  const sorted = ranges
    .filter(([start, end]) => parse(start) < parse(end))
    .sort((a, b) => parse(a[0]) - parse(b[0]));
  const merged = [];
  for (const [start, end] of sorted) {
    const last = merged[merged.length - 1];
    if (last && parse(start) <= parse(last[1])) {
      if (parse(end) > parse(last[1])) last[1] = end;
    } else {
      merged.push([start, end]);
    }
  }
  return merged;
}

module.exports = {
  DAY,
  parse,
  fmt,
  isWeekend,
  isBusinessDay,
  addBusinessDays,
  mergeRanges,
};
