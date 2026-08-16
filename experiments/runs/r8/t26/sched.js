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

// 시작일은 세지 않고, n 영업일만큼 이동한 날짜를 돌려준다.
// n === 0 이면 시작일이 영업일이 아니어도 그대로 돌려준다.
function addBusinessDays(d, n, holidays = []) {
  if (n === 0) return d;
  const step = n > 0 ? DAY : -DAY;
  let left = Math.abs(n);
  let t = parse(d);
  while (left > 0) {
    t += step;
    if (isBusinessDay(fmt(t), holidays)) left--;
  }
  return fmt(t);
}

// [start, end) 반열림 구간을 병합한다.
// 길이 0 구간은 버리고, start 오름차순으로 돌려준다.
function mergeRanges(ranges) {
  const sorted = ranges
    .filter(([a, b]) => parse(a) < parse(b))
    .sort((x, y) => parse(x[0]) - parse(y[0]));
  const out = [];
  for (const [a, b] of sorted) {
    const last = out[out.length - 1];
    if (last && parse(a) <= parse(last[1])) {
      if (parse(b) > parse(last[1])) last[1] = b;
    } else {
      out.push([a, b]);
    }
  }
  return out;
}

module.exports = {
  DAY, parse, fmt, isWeekend, isBusinessDay, addBusinessDays, mergeRanges,
};
