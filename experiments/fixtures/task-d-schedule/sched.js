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

module.exports = { DAY, parse, fmt, isWeekend, isBusinessDay };
