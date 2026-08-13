#!/usr/bin/env python3
"""실험 해설 HTML 생성기 (CLAUDE.md 문서 규칙 §해설 문서).

실험 하나 = 명세 JSON 하나 = 해설 HTML 하나.
구조와 스타일은 여기에 고정하고, 명세에는 내용만 넣는다.
CSS 를 문서마다 복사하지 않기 위한 것이므로 HTML 을 손으로 고치지 않는다.

    python tools/explainer.py              # explainers/*.json 전부 생성
    python tools/explainer.py r1-h1        # 하나만

## 명세 스키마 (explainers/<slug>.json)

    slug      파일명. 출력은 explainers/<slug>.html
    title     페이지 이름. 짧은 명사구. 설명을 붙이지 않는다
    kicker    상단 라벨. 예: "라운드 1 · 실험 H1"
    verdict   채택 | 기각 | 판정 불가
    headline  큰 제목
    sub       한 문단 요약. **굵게** 지원
    task      무슨 일을 시킨 실험인지 한 줄
    common    {cap, code, lang, note} 조건 공통 입력
    fork      갈림길 라벨 (생략 시 기본값)
    branches  [{who, what, prompt, size, code, lang, note, kind}]
              kind: base(기준) | win(짧아짐) | lose(길어짐)
    result    {unit, rows:[{label, chars, delta, kind}], foot} 또는 null
              막대 길이는 rows 의 chars 최댓값 기준으로 자동 계산된다
    blocks    [{type: why|trap|halt, title, paras:[...], result:{...}?}]
    summary   {cols:[...], rows:[[...]]} 또는 null
    footer    [...]  문서 하단 각주 줄

`paras` 와 `sub` 는 **굵게**, `코드` 를 지원한다. 그 외 HTML 은 이스케이프된다.

## 강조 표시

코드 블록은 `lang` 에 따라 자동으로 칠한다 — 손으로 span 을 넣지 않는다.
    diff  @@ 머리글 / -줄 / +줄 / 문맥줄
    json  "키": 이름
    tsv   첫 줄(헤더), 탭 문자를 눈에 보이게 표시
    그 외  칠하지 않음
"""

from __future__ import annotations

import html
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import theme  # noqa: E402  (경로 삽입 뒤에 와야 한다)

REPO = Path(__file__).resolve().parents[1]
SRC = REPO / "explainers"

VERDICT_KIND = {"채택": "win", "기각": "lose", "판정 불가": "halt"}

CSS = theme.TOKENS + theme.BASE + """
.vb{font-family:var(--mono);font-size:10.5px;letter-spacing:.1em;padding:3px 10px;border-radius:20px;
  border:1px solid;text-transform:none}
.vb.win{background:var(--cut-soft);color:var(--cut);border-color:var(--cut)}
.vb.lose{background:var(--bloat-soft);color:var(--bloat);border-color:var(--bloat)}
.vb.halt{background:var(--halt-soft);color:var(--halt);border-color:var(--halt)}
.task{margin:26px 0 0;padding:14px 18px;background:var(--surface);border:1px solid var(--line);
  border-radius:10px;font-size:14.5px;color:var(--muted)}
.task b{color:var(--ink)}
.legend{display:flex;gap:20px;flex-wrap:wrap;margin:16px 0 0;padding:14px 18px;
  background:var(--surface);border:1px solid var(--line);border-radius:10px;font-size:13.5px;color:var(--muted)}
.legend span{display:flex;align-items:center;gap:8px}
.sw{width:14px;height:14px;border-radius:3px;border:1px solid;display:inline-block}
.sw.c{background:var(--cut-soft);border-color:var(--cut)}
.sw.b{background:var(--bloat-soft);border-color:var(--bloat)}
.sw.n{background:var(--accent-soft);border-color:var(--accent)}

.step{margin-top:44px}
.step>.lab{display:flex;align-items:center;gap:10px;margin-bottom:13px}
.step>.lab .b{font-family:var(--mono);font-size:10.5px;letter-spacing:.1em;padding:3px 9px;
  border-radius:5px;background:var(--sunk);color:var(--muted);border:1px solid var(--line)}
.step>.lab h3{font-size:16px;font-weight:620}
.step>.note{margin:0 0 13px;color:var(--muted);font-size:14.5px}

.box{background:var(--surface);border:1px solid var(--line);border-radius:11px;
  box-shadow:var(--shadow);overflow:hidden}
.cap{padding:10px 15px;background:var(--raise);border-bottom:1px solid var(--line);
  font-family:var(--mono);font-size:11px;letter-spacing:.06em;color:var(--muted);
  display:flex;align-items:center;gap:10px;flex-wrap:wrap}
.cap .sz{margin-left:auto;color:var(--ink);font-weight:600}
pre{margin:0;padding:15px;font-family:var(--mono);font-size:12.3px;line-height:1.62;
  overflow-x:auto;white-space:pre;color:var(--ink)}
pre .g{color:var(--faint)}
pre .del{color:var(--bloat)}
pre .add{color:var(--cut)}
pre .hh{color:var(--accent)}
pre .tab{color:var(--faint);opacity:.55}
.trunc{padding:9px 15px;border-top:1px dashed var(--line);background:var(--sunk);
  font-size:12.5px;color:var(--faint)}
.trunc b{color:var(--muted)}

.fork{display:flex;flex-direction:column;align-items:center;margin:26px 0 6px}
.fork .stem{width:2px;height:26px;background:var(--line)}
.fork .txt{font-family:var(--mono);font-size:11px;letter-spacing:.09em;color:var(--faint);
  padding:5px 12px;border:1px dashed var(--line);border-radius:20px;background:var(--paper)}

.pair{display:grid;gap:16px;grid-template-columns:repeat(var(--cols),1fr)}
@media (max-width:820px){.pair{grid-template-columns:1fr}}
.branch{border-radius:11px;border:1px solid var(--line);background:var(--surface);
  box-shadow:var(--shadow);overflow:hidden;display:flex;flex-direction:column}
.branch.win{border-color:var(--cut-line)}
.branch.lose{border-color:var(--bloat-line)}
.branch.halt{border-color:var(--halt-line)}
.branch>.top{padding:12px 15px;border-bottom:1px solid var(--line)}
.branch.win>.top{background:var(--cut-soft)}
.branch.lose>.top{background:var(--bloat-soft)}
.branch.halt>.top{background:var(--halt-soft)}
.branch.base>.top{background:var(--accent-soft)}
.branch>.top .who{font-family:var(--mono);font-size:10.5px;letter-spacing:.11em;
  text-transform:uppercase;color:var(--muted)}
.branch>.top .what{font-size:14.5px;font-weight:620;margin-top:2px}
.branch .ptxt{padding:13px 15px;font-size:13.5px;color:var(--muted);
  border-bottom:1px dashed var(--hair);background:var(--raise)}
.branch pre{flex:1}

.result{margin-top:24px;background:var(--surface);border:1px solid var(--line);
  border-radius:11px;padding:22px 22px 16px;box-shadow:var(--shadow)}
.result>h4{font-size:13px;font-family:var(--mono);letter-spacing:.1em;text-transform:uppercase;
  color:var(--faint);font-weight:500;margin-bottom:18px}
.rrow{display:grid;grid-template-columns:168px 1fr;gap:14px;align-items:center;margin-bottom:12px}
.rrow .rl{font-size:13.5px;color:var(--muted);text-align:right}
.rtrack{display:flex;align-items:center;min-height:32px}
.rfill{height:28px;border-radius:3px;border:1px solid;min-width:3px;
  animation:grow .75s cubic-bezier(.2,.75,.3,1) both;transform-origin:left}
.rfill.n{background:var(--accent-soft);border-color:var(--accent)}
.rfill.c{background:var(--cut-soft);border-color:var(--cut)}
.rfill.b{background:var(--bloat-soft);border-color:var(--bloat)}
@keyframes grow{from{transform:scaleX(.02)}to{transform:scaleX(1)}}
@media (prefers-reduced-motion:reduce){.rfill{animation:none}}
.rv{font-family:var(--mono);font-size:13px;font-variant-numeric:tabular-nums;
  margin-left:11px;white-space:nowrap;color:var(--muted)}
.rv b{color:var(--ink)}
.rv .d{font-weight:700;margin-left:9px;font-size:14px}
.rv .d.c{color:var(--cut)} .rv .d.b{color:var(--bloat)}
.foot{margin-top:12px;font-size:12.5px;color:var(--faint)}
.foot b{color:var(--ink)}

.blk{margin-top:26px;padding:20px 22px;border-radius:11px;border:1px solid var(--line);
  border-left-width:3px;background:var(--surface)}
.blk.why{border-left-color:var(--accent)}
.blk.trap{background:var(--bloat-soft);border-color:var(--bloat);border-left-color:var(--bloat)}
.blk.halt{background:var(--halt-soft);border-color:var(--halt-line);border-left-color:var(--halt)}
.blk h4{font-size:15px;margin-bottom:9px;font-weight:650}
.blk.trap h4{color:var(--bloat)}
.blk.halt h4{color:var(--halt)}
.blk p{margin:0;color:var(--muted);font-size:14.5px}
.blk.trap p,.blk.halt p{color:var(--ink)}
.blk p+p{margin-top:10px}
.blk b{color:var(--ink)}

.shead{border-bottom:2px solid var(--ink);padding-bottom:14px;margin:80px 0 0}
.shead .n{font-family:var(--mono);font-size:11px;letter-spacing:.15em;
  text-transform:uppercase;color:var(--accent)}
.shead h2{font-size:26px;letter-spacing:-.018em;margin-top:6px;font-weight:660}
"""


# ── 인라인 마크업 ────────────────────────────────────────────
def inline(s: str) -> str:
    s = html.escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"`(.+?)`", r"<code>\1</code>", s)
    return s


# ── 코드 강조 ────────────────────────────────────────────────
def paint(code: str, lang: str) -> str:
    out: list[str] = []
    for i, ln in enumerate(code.split("\n")):
        e = html.escape(ln)
        if lang == "diff":
            if ln.startswith("@@"):
                e = f'<span class="hh">{e}</span>'
            elif ln.startswith("-"):
                e = f'<span class="del">{e}</span>'
            elif ln.startswith("+"):
                e = f'<span class="add">{e}</span>'
            else:
                e = f'<span class="g">{e}</span>'
        elif lang == "json":
            e = re.sub(r"(&quot;[a-z_]+&quot;)(\s*:)", r'<span class="hh">\1</span>\2', e)
        elif lang == "tsv":
            e = e.replace("\t", '<span class="tab">→</span>')
            if i == 0:
                e = f'<span class="hh">{e}</span>'
        out.append(e)
    return "\n".join(out)


def codebox(spec: dict, cap: str = "", size: str = "") -> str:
    head = ""
    if cap or size:
        sz = f'<span class="sz">{html.escape(size)}</span>' if size else ""
        head = f'<div class="cap">{html.escape(cap)}{sz}</div>'
    body = paint(spec.get("code", ""), spec.get("lang", ""))
    note = spec.get("note", "")
    tail = f'<div class="trunc">{inline(note)}</div>' if note else ""
    return f"{head}<pre>{body}</pre>{tail}"


# ── 결과 막대 ────────────────────────────────────────────────
def result_block(r: dict) -> str:
    rows = r["rows"]
    top = max(x["chars"] for x in rows)
    bars = []
    for x in rows:
        w = x["chars"] / top * 100
        d = x.get("delta")
        dk = "c" if (d or "").startswith("−") else "b"
        dhtml = f'<span class="d {dk}">{html.escape(d)}</span>' if d else ""
        bars.append(
            f'<div class="rrow"><div class="rl">{inline(x["label"])}</div>'
            f'<div class="rtrack"><div class="rfill {x["kind"]}" style="width:{w:.1f}%"></div>'
            f'<span class="rv"><b>{x["chars"]:,}</b>자{dhtml}</span></div></div>'
        )
    foot = f'<p class="foot">{inline(r["foot"])}</p>' if r.get("foot") else ""
    return (
        f'<div class="result"><h4>{html.escape(r["unit"])}</h4>'
        + "".join(bars) + foot + "</div>"
    )


# ── 문서 조립 ────────────────────────────────────────────────
def build(s: dict) -> str:
    vk = VERDICT_KIND[s["verdict"]]
    p: list[str] = [f'<title>{html.escape(s["title"])}</title>', f"<style>{CSS}</style>", '<div class="wrap">']

    p.append(
        f'<header><p class="kicker">{html.escape(s["kicker"])}'
        f'<span class="vb {vk}">판정 · {html.escape(s["verdict"])}</span></p>'
        f'<h1>{html.escape(s["headline"])}</h1>'
        f'<p class="sub">{inline(s["sub"])}</p>'
        f'<p class="task"><b>시킨 일</b> — {inline(s["task"])}</p>'
        '<div class="legend"><span><i class="sw n"></i> 기준 (비교 대상)</span>'
        '<span><i class="sw c"></i> 짧아짐 = 이득</span>'
        '<span><i class="sw b"></i> 길어짐 = 손해</span>'
        '<span class="mono" style="margin-left:auto">모든 수치는 문자 수 (토큰 아님)</span></div></header>'
    )

    c = s["common"]
    p.append(
        '<div class="step"><div class="lab"><span class="b">1</span>'
        '<h3>입력 — 모든 조건에 똑같이 준 것</h3></div>'
        + (f'<p class="note">{inline(c["note_before"])}</p>' if c.get("note_before") else "")
        + '<div class="box">' + codebox(c, c.get("cap", "프롬프트 (공통 부분)")) + "</div></div>"
    )

    fork = s.get("fork", "여기서만 갈린다 — 문단 하나")
    p.append(f'<div class="fork"><div class="stem"></div><div class="txt">{html.escape(fork)}</div>'
             '<div class="stem"></div></div>')

    br = s["branches"]
    cards = []
    for b in br:
        cards.append(
            f'<div class="branch {b["kind"]}"><div class="top">'
            f'<div class="who">{html.escape(b["who"])}</div>'
            f'<div class="what">{html.escape(b["what"])}</div></div>'
            f'<div class="ptxt">{inline(b["prompt"])}</div>'
            + codebox(b, "나온 답", b.get("size", "")) + "</div>"
        )
    p.append(
        '<div class="step"><div class="lab"><span class="b">2</span>'
        '<h3>갈라지는 문장, 그리고 나온 답</h3></div>'
        f'<div class="pair" style="--cols:{len(br)}">' + "".join(cards) + "</div></div>"
    )

    if s.get("result"):
        p.append(
            '<div class="step"><div class="lab"><span class="b">3</span>'
            '<h3>그래서 얼마나 아꼈나</h3></div>' + result_block(s["result"]) + "</div>"
        )

    for b in s.get("blocks", []):
        inner = "".join(f"<p>{inline(x)}</p>" for x in b["paras"])
        extra = result_block(b["result"]) if b.get("result") else ""
        p.append(f'<div class="blk {b["type"]}"><h4>{inline(b["title"])}</h4>{inner}{extra}</div>')

    if s.get("summary"):
        sm = s["summary"]
        th = "".join(f"<th>{inline(x)}</th>" for x in sm["cols"])
        tr = "".join("<tr>" + "".join(f"<td>{inline(x)}</td>" for x in r) + "</tr>" for r in sm["rows"])
        p.append('<div class="shead"><div class="n">정리</div><h2>그래서 언제 이렇게 시키나</h2></div>'
                 f'<div class="scroll"><table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody></table></div>')

    p.append("<footer>" + "<br>\n".join(inline(x) for x in s.get("footer", [])) + "</footer>")
    p.append("</div>")
    return "\n".join(p)


def main(argv: list[str]) -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    specs = sorted(SRC.glob("*.json"))
    if argv:
        specs = [x for x in specs if any(a in x.stem for a in argv)]
    if not specs:
        print("명세 없음", file=sys.stderr)
        return 1
    for f in specs:
        s = json.loads(f.read_text(encoding="utf-8"))
        assert s["slug"] == f.stem, f"{f.name}: slug 불일치 ({s['slug']})"
        assert s["verdict"] in VERDICT_KIND, f"{f.name}: 알 수 없는 판정 {s['verdict']}"
        dest = SRC / f"{s['slug']}.html"
        out = build(s)
        dest.write_text(out, encoding="utf-8", newline="\n")
        print(f"{dest.relative_to(REPO)}  {len(out):,} bytes  [{s['verdict']}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
