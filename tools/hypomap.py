#!/usr/bin/env python3
"""가설 지도 생성기 — 37건 전수 현황을 한 페이지로.

    python tools/hypomap.py     ->  dashboard/hypotheses.html

두 TSV 를 읽어 만든다. HTML 을 손으로 고치지 않는다.

    experiments/raw/hypothesis-index.tsv    가설 인벤토리 (불변)
    experiments/hypothesis-status.tsv       검증된 것만. id -> 판정·라운드·결과·해설

인벤토리에 없는 id 가 상태 파일에 있으면 오류로 막는다 — 실험이 끝났는데
인벤토리에 없는 가설을 판정했다는 뜻이라, 조용히 넘기면 안 된다.
"""

from __future__ import annotations

import html
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import theme  # noqa: E402

REPO = Path(__file__).resolve().parents[1]
INDEX = REPO / "experiments/raw/hypothesis-index.tsv"
STATUS = REPO / "experiments/hypothesis-status.tsv"
DEST = REPO / "dashboard/hypotheses.html"

AXES = {
    "1": ("프롬프트 지시문", "무엇을 어떻게 시키는가"),
    "2": ("출력 스키마", "어떤 모양으로 내놓게 하는가"),
    "3": ("API 파라미터", "요청 설정으로 조절할 수 있는가"),
    "4": ("아키텍처", "일을 어떻게 쪼개고 넘기는가"),
    "5": ("코딩 에이전트", "코드 작업에 특화된 절감"),
    # 축 6 은 레버의 위치가 아니라 '왜 그 레버가 듣는가'를 다룬다 → 축 1-5 를 가로지른다.
    "6": ("정보이론", "무엇이 줄어들 수 있는 것인가"),
}
# 판정된 것 / 아직 안 한 것 / API 없이는 못 하는 것
PILL = {"채택": "win", "조건부 채택": "win", "부분 채택": "win", "기각": "lose",
        "판정 불가": "halt", "미검증": "open", "API 대기": "api"}

CSS = theme.TOKENS + theme.BASE + """
.prog{margin-top:34px;background:var(--surface);border:1px solid var(--line);
  border-radius:11px;padding:22px 24px 18px;box-shadow:var(--shadow)}
.prog h4{font-family:var(--mono);font-size:11px;letter-spacing:.12em;text-transform:uppercase;
  color:var(--faint);font-weight:500;margin-bottom:14px}
.bar{display:flex;height:30px;border-radius:4px;overflow:hidden;border:1px solid var(--line)}
.bar div{display:flex;align-items:center;justify-content:center;font-family:var(--mono);
  font-size:11px;font-weight:600;min-width:2px}
.bar .s-win{background:var(--cut-soft);color:var(--cut);box-shadow:inset 0 0 0 1px var(--cut)}
.bar .s-halt{background:var(--halt-soft);color:var(--halt);box-shadow:inset 0 0 0 1px var(--halt)}
.bar .s-api{background:var(--accent-soft);color:var(--accent)}
.bar .s-open{background:var(--sunk);color:var(--faint)}
.plegend{display:flex;gap:18px;flex-wrap:wrap;margin-top:14px;font-size:12.5px;color:var(--muted)}
.plegend span{display:flex;align-items:center;gap:7px}
.plegend i{width:12px;height:12px;border-radius:3px;display:inline-block;border:1px solid}
.plegend i.win{background:var(--cut-soft);border-color:var(--cut)}
.plegend i.halt{background:var(--halt-soft);border-color:var(--halt)}
.plegend i.api{background:var(--accent-soft);border-color:var(--accent)}
.plegend i.open{background:var(--sunk);border-color:var(--line)}

.filters{display:flex;gap:8px;flex-wrap:wrap;margin:44px 0 6px;align-items:center}
.filters .glabel{font-family:var(--mono);font-size:10.5px;letter-spacing:.11em;
  text-transform:uppercase;color:var(--faint);margin-right:2px}
.chip{font-family:var(--mono);font-size:11.5px;padding:5px 11px;border-radius:20px;cursor:pointer;
  background:var(--surface);color:var(--muted);border:1px solid var(--line);
  transition:background .13s,color .13s,border-color .13s}
.chip:hover{border-color:var(--accent);color:var(--ink)}
/* 눌린 칩의 글자색은 surface 토큰이다 — 밝은 테마에선 흰색, 어두운 테마에선
   짙은 색으로 자동으로 뒤집혀 테마 분기 없이 대비가 유지된다. */
.chip[aria-pressed="true"]{background:var(--accent);border-color:var(--accent);color:var(--surface)}
.cnt{font-family:var(--mono);font-size:11.5px;color:var(--faint);margin-left:auto}

.axis{margin-top:40px}
.axis>.ah{display:flex;align-items:baseline;gap:12px;border-bottom:1px solid var(--line);
  padding-bottom:11px;margin-bottom:16px}
.axis>.ah .an{font-family:var(--mono);font-size:11px;letter-spacing:.14em;color:var(--accent)}
.axis>.ah h2{font-size:19px;letter-spacing:-.014em;font-weight:640}
.axis>.ah .sub2{font-size:13.5px;color:var(--faint)}
.axis>.ah .k{margin-left:auto;font-family:var(--mono);font-size:11.5px;color:var(--faint)}

.cards{display:grid;gap:12px;grid-template-columns:repeat(auto-fill,minmax(300px,1fr))}
.card{background:var(--surface);border:1px solid var(--line);border-radius:10px;
  padding:14px 16px;box-shadow:var(--shadow);display:flex;flex-direction:column;gap:7px}
.card.tested{border-left:3px solid var(--cut)}
.card.halted{border-left:3px solid var(--halt)}
.card .r1{display:flex;align-items:center;gap:9px}
.card .hid{font-family:var(--mono);font-size:11px;color:var(--faint)}
.card .ttl{font-size:14.5px;font-weight:620;line-height:1.3}
.card .clm{font-size:13px;color:var(--muted);line-height:1.5}
.card .res{font-family:var(--mono);font-size:12px;color:var(--cut);
  background:var(--cut-soft);border:1px solid var(--cut-line);border-radius:6px;padding:6px 9px}
.card.halted .res{color:var(--halt);background:var(--halt-soft);border-color:var(--halt-line)}
.card .meta{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin-top:1px}
.card .ev{font-family:var(--mono);font-size:10.5px;color:var(--faint)}
.card a{font-family:var(--mono);font-size:11px;text-decoration:none;border-bottom:1px solid currentColor}

.note{margin-top:44px;padding:20px 22px;border-radius:11px;background:var(--surface);
  border:1px solid var(--line);border-left:3px solid var(--accent)}
.note h4{font-size:15px;margin-bottom:9px;font-weight:645}
.note p{margin:0;color:var(--muted);font-size:14.5px}
.note p+p{margin-top:10px}
.note b{color:var(--ink)}
"""


def read_tsv(p: Path) -> list[dict[str, str]]:
    lines = p.read_text(encoding="utf-8").strip().split("\n")
    head = lines[0].split("\t")
    return [dict(zip(head, ln.split("\t"))) for ln in lines[1:] if ln.strip()]


def inline(s: str) -> str:
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    return s


def build() -> str:
    inv = read_tsv(INDEX)
    st = {r["id"]: r for r in read_tsv(STATUS)}

    ids = {r["id"] for r in inv}
    ghost = sorted(set(st) - ids)
    if ghost:
        raise SystemExit(f"인벤토리에 없는 가설이 상태 파일에 있다: {ghost}")

    for r in inv:
        s = st.get(r["id"])
        r["status"] = s["status"] if s else ("API 대기" if r["testable"] == "API필요" else "미검증")
        r["result"] = s["result"] if s else ""
        r["explainer"] = s["explainer"] if s else ""
        r["round"] = s["round"] if s else ""

    c = Counter(r["status"] for r in inv)
    tested = sum(v for k, v in c.items() if k not in ("미검증", "API 대기"))
    seg = [("win", c["채택"] + c["조건부 채택"], "채택"),
           ("halt", c["기각"] + c["판정 불가"], "기각·판정 불가"),
           ("api", c["API 대기"], "API 대기"),
           ("open", c["미검증"], "미검증")]
    total = len(inv)

    p: list[str] = ["<title>가설 지도</title>", f"<style>{CSS}</style>", '<div class="wrap">']
    p.append(
        '<header><p class="kicker">출력 토큰 절감 연구 · 가설 전수</p>'
        "<h1>가설 지도</h1>"
        f'<p class="sub">축 5개에서 세운 가설 <b>{total}건</b>. 그중 <b>{tested}건</b>을 실측했고 '
        f'나머지는 아직 재보지 않았습니다. <b>기각과 판정 불가도 지우지 않고 남깁니다</b> — '
        "채택된 것만 세면 성공률이 부풀어 보입니다.</p></header>"
    )

    bars = "".join(
        f'<div class="s-{k}" style="width:{n/total*100:.1f}%">{n if n/total > .06 else ""}</div>'
        for k, n, _ in seg if n
    )
    legend = "".join(f'<span><i class="{k}"></i> {lab} {n}</span>' for k, n, lab in seg if n)
    p.append(f'<div class="prog"><h4>검증 진도 · {tested} / {total}</h4>'
             f'<div class="bar">{bars}</div><div class="plegend">{legend}</div></div>')

    p.append('<div class="filters" role="group" aria-label="상태 필터">'
             '<span class="glabel">상태</span>'
             '<button class="chip" data-v="*" aria-pressed="true">전체</button>'
             '<button class="chip" data-v="tested" aria-pressed="false">실측 완료</button>'
             '<button class="chip" data-v="미검증" aria-pressed="false">미검증</button>'
             '<button class="chip" data-v="API 대기" aria-pressed="false">API 대기</button>'
             '<span class="cnt" id="cnt"></span></div>')

    for ax, (name, blurb) in AXES.items():
        rows = [r for r in inv if r["axis"] == ax]
        cards = []
        for r in rows:
            done = r["status"] not in ("미검증", "API 대기")
            cls = "card" + (" tested" if done and r["status"] != "판정 불가" else "")
            if r["status"] == "판정 불가":
                cls = "card halted"
            res = f'<div class="res">{inline(r["result"])}</div>' if r["result"] else ""
            link = (f'<a href="../explainers/{r["explainer"]}.html">해설 &rarr;</a>'
                    if r["explainer"] else "")
            rnd = f'<span class="ev">라운드 {html.escape(r["round"])}</span>' if r["round"] else ""
            cards.append(
                f'<div class="{cls}" data-st="{html.escape(r["status"])}" '
                f'data-done="{"1" if done else "0"}">'
                f'<div class="r1"><span class="hid">{html.escape(r["id"])}</span>'
                f'<span class="pill {PILL[r["status"]]}">{html.escape(r["status"])}</span></div>'
                f'<div class="ttl">{html.escape(r["title"])}</div>'
                f'<div class="clm">{html.escape(r["claim"])}</div>'
                f'{res}<div class="meta"><span class="ev">근거 {html.escape(r["evidence"])}</span>'
                f'{rnd}{link}</div></div>'
            )
        p.append(
            f'<div class="axis" data-axis="{ax}"><div class="ah"><span class="an">축 {ax}</span>'
            f"<h2>{html.escape(name)}</h2><span class=\"sub2\">{html.escape(blurb)}</span>"
            f'<span class="k">{len(rows)}건</span></div>'
            f'<div class="cards">{"".join(cards)}</div></div>'
        )

    p.append(
        '<div class="note"><h4>이 표를 읽는 법</h4>'
        f"<p><b>미검증이 여전히 대부분입니다.</b> 실측 {tested}건 가운데 출력 형식 레버(축 2·4)가 "
        "먼저 끝났고, 프롬프트 레버(축 1·5)는 라운드 3에서 넷을 재면서 열렸습니다. "
        "코딩 에이전트 축(5)은 아직 대부분 비어 있습니다.</p>"
        f"<p><b>API 대기 {c['API 대기']}건</b>은 이 환경에 <code>ANTHROPIC_API_KEY</code>가 없어 "
        "원리적으로 검증할 수 없는 것들입니다. <code>usage.output_tokens</code> 없이는 "
        "thinking 토큰과 응답문을 분리할 수 없습니다.</p>"
        "<p><b>근거</b> 칸의 <code>추정</code>은 문서 근거 없이 세운 가설, "
        "<code>문서확인</code>은 공식 문서에 뒷받침이 있는 것, "
        "<code>측정필요</code>는 문서가 수치를 주지 않아 재봐야 하는 것, "
        "<code>이론유도</code>는 벤더 문서가 아니라 정보이론에서 예측을 뽑아낸 것입니다 "
        "— 축 6 전체가 여기 해당하며 문서 근거가 있는 가설과 같은 무게로 읽지 않습니다.</p></div>"
    )

    p.append(
        "<footer>"
        "<b>생성</b> — <code>python tools/hypomap.py</code>. "
        "출처는 experiments/raw/hypothesis-index.tsv(인벤토리)와 "
        "experiments/hypothesis-status.tsv(판정). HTML을 손으로 고치지 않습니다.<br>"
        "<b>수치</b> — 전부 문자 수 (proxy)이며 토큰이 아닙니다. 조건 간 상대 비율로만 읽으십시오.<br>"
        "<b>해설</b> — 실측된 가설은 explainers/ 에 입력·출력·절감률을 따라가는 문서가 있습니다."
        "</footer></div>"
    )

    p.append("""<script>
const cards=[...document.querySelectorAll('.card')],cnt=document.getElementById('cnt');
function apply(v){
  let n=0;
  for(const c of cards){
    const ok = v==='*' || (v==='tested' ? c.dataset.done==='1' : c.dataset.st===v);
    c.style.display = ok?'':'none'; if(ok) n++;
  }
  for(const ax of document.querySelectorAll('.axis'))
    ax.style.display = [...ax.querySelectorAll('.card')].some(c=>c.style.display!=='none')?'':'none';
  cnt.textContent = n+' / '+cards.length;
}
document.querySelectorAll('.chip').forEach(b=>b.addEventListener('click',()=>{
  document.querySelectorAll('.chip').forEach(x=>x.setAttribute('aria-pressed',String(x===b)));
  apply(b.dataset.v);
}));
apply('*');
</script>""")
    return "\n".join(p)


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    DEST.parent.mkdir(parents=True, exist_ok=True)
    out = build()
    DEST.write_text(out, encoding="utf-8", newline="\n")
    print(f"{DEST.relative_to(REPO)}  {len(out):,} bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
