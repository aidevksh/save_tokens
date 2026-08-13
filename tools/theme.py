"""저장소 HTML 산출물의 공통 시각 토큰.

해설 문서(tools/explainer.py)와 대시보드(tools/hypomap.py)가 함께 쓴다.
색·활자를 문서마다 복사하면 라운드가 쌓일수록 어긋나므로 여기 한 곳에만 둔다.

세 가지 테마 상태를 모두 정의한다:
  :root                                        밝은 테마 (기본)
  @media (prefers-color-scheme:dark) + guard   OS 다크, 단 명시적 light 선택이 이김
  :root[data-theme="dark"]                     명시적 다크 선택
색을 media 블록 안에서만 정의하면 표시 상태에 따라 글자와 배경이 어긋난다.
"""

TOKENS = """
:root{
  --paper:#F1F2F5; --surface:#FFFFFF; --raise:#F7F8FB; --sunk:#EDEFF4;
  --ink:#14171F; --muted:#5F6779; --faint:#8A92A2;
  --line:#DCE0E8; --hair:#E9ECF2;
  --accent:#2E5E86; --accent-soft:#E3EDF6;
  --cut:#0F6B54; --cut-soft:#DCEFE8; --cut-line:#8FCBB8;
  --bloat:#A34E26; --bloat-soft:#F8E6DA; --bloat-line:#E0A882;
  --halt:#5D5F6B; --halt-soft:#E8E9ED; --halt-line:#B3B6BF;
  --shadow:0 1px 2px rgba(20,23,31,.05),0 10px 30px -16px rgba(20,23,31,.18);
  --mono:"Cascadia Mono","SF Mono",ui-monospace,Consolas,"Liberation Mono",monospace;
  --sans:system-ui,-apple-system,"Segoe UI","Malgun Gothic","Apple SD Gothic Neo","Noto Sans KR",sans-serif;
}
@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --paper:#0E1118; --surface:#171B24; --raise:#1C212B; --sunk:#12161E;
    --ink:#E5E8EF; --muted:#9AA2B2; --faint:#767E8D;
    --line:#282E3A; --hair:#222833;
    --accent:#79ADD9; --accent-soft:#1A2938;
    --cut:#48C99A; --cut-soft:#112A22; --cut-line:#245F4B;
    --bloat:#E2905C; --bloat-soft:#2C1F17; --bloat-line:#6B4530;
    --halt:#9DA3B0; --halt-soft:#1E2129; --halt-line:#3A3F4A;
    --shadow:0 1px 2px rgba(0,0,0,.4),0 10px 30px -16px rgba(0,0,0,.7);
  }
}
:root[data-theme="dark"]{
  --paper:#0E1118; --surface:#171B24; --raise:#1C212B; --sunk:#12161E;
  --ink:#E5E8EF; --muted:#9AA2B2; --faint:#767E8D;
  --line:#282E3A; --hair:#222833;
  --accent:#79ADD9; --accent-soft:#1A2938;
  --cut:#48C99A; --cut-soft:#112A22; --cut-line:#245F4B;
  --bloat:#E2905C; --bloat-soft:#2C1F17; --bloat-line:#6B4530;
  --halt:#9DA3B0; --halt-soft:#1E2129; --halt-line:#3A3F4A;
  --shadow:0 1px 2px rgba(0,0,0,.4),0 10px 30px -16px rgba(0,0,0,.7);
}
"""

BASE = """
*{box-sizing:border-box}
body{margin:0;background:var(--paper);color:var(--ink);font-family:var(--sans);
  font-size:15.5px;line-height:1.68;-webkit-font-smoothing:antialiased}
.wrap{max-width:960px;margin:0 auto;padding:0 22px 100px}
h1,h2,h3,h4{margin:0;text-wrap:balance}
code{font-family:var(--mono);font-size:.9em;background:var(--sunk);padding:1px 5px;
  border-radius:3px;border:1px solid var(--hair)}
.mono{font-family:var(--mono);font-variant-numeric:tabular-nums}
:focus-visible{outline:2px solid var(--accent);outline-offset:3px;border-radius:3px}
a{color:var(--accent)}

header{padding:70px 0 0}
.kicker{font-family:var(--mono);font-size:11px;letter-spacing:.16em;text-transform:uppercase;
  color:var(--faint);margin:0 0 16px;display:flex;align-items:center;gap:12px;flex-wrap:wrap}
h1{font-size:clamp(30px,5.4vw,48px);line-height:1.08;letter-spacing:-.024em;font-weight:680}
.sub{margin:20px 0 0;font-size:18px;color:var(--muted);max-width:56ch}
.sub b{color:var(--ink);font-weight:620}

.scroll{overflow-x:auto;border:1px solid var(--line);border-radius:11px;background:var(--surface);
  box-shadow:var(--shadow);margin-top:16px}
table{border-collapse:collapse;width:100%;font-size:14px;min-width:560px}
th,td{padding:12px 15px;text-align:left;border-bottom:1px solid var(--hair);vertical-align:top}
thead th{font-family:var(--mono);font-size:10.5px;letter-spacing:.11em;text-transform:uppercase;
  color:var(--faint);font-weight:500;background:var(--raise);border-bottom:1px solid var(--line)}
tbody tr:last-child td{border-bottom:none}

.pill{display:inline-block;font-family:var(--mono);font-size:10.5px;letter-spacing:.05em;
  padding:2.5px 9px;border-radius:20px;white-space:nowrap;border:1px solid}
.pill.win{background:var(--cut-soft);color:var(--cut);border-color:var(--cut)}
.pill.lose{background:var(--bloat-soft);color:var(--bloat);border-color:var(--bloat)}
.pill.halt{background:var(--halt-soft);color:var(--halt);border-color:var(--halt)}
.pill.open{background:transparent;color:var(--faint);border-color:var(--line)}
.pill.api{background:transparent;color:var(--accent);border-color:var(--accent)}

footer{margin-top:80px;padding-top:22px;border-top:1px solid var(--line);
  font-size:12.5px;color:var(--faint);line-height:1.85}
footer b{color:var(--muted)}
"""
