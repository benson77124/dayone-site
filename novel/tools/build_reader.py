#!/usr/bin/env python3
"""把一章小說 markdown 轉成可直接閱讀的 HTML 頁面。

用法:
    python3 novel/tools/build_reader.py novel/03-章節/102_第一百零二章_下一個.md [輸出.html]

小說自己的記號會被轉成版面元素：
    # 第X章　標題   章名
    〔...〕         場景標記
    【...】         系統面板（連續行合併成一塊）
    （...）         內心獨白（連續行合併成一塊）
    ---            段落分隔
    其餘            正文段落
"""

import html
import re
import sys
from pathlib import Path

SCENE = re.compile(r"^〔(.+)〕$")
SYSTEM = re.compile(r"^【(.+)】$")
INNER = re.compile(r"^（(.+)）$")
TITLE = re.compile(r"^#\s+(.+)$")


def classify(line):
    """回傳 (種類, 內容)。"""
    if m := TITLE.match(line):
        return "title", m.group(1).strip()
    if m := SCENE.match(line):
        return "scene", m.group(1).strip()
    if m := SYSTEM.match(line):
        return "system", m.group(1).strip()
    if m := INNER.match(line):
        return "inner", m.group(1).strip()
    if line.strip() == "---":
        return "rule", ""
    return "para", line.strip()


def parse(md):
    """把 markdown 拆成 (章名, 區塊列表)。區塊為 (種類, [文字...])。"""
    title = ""
    blocks = []
    for raw in md.splitlines():
        if not raw.strip():
            continue
        kind, text = classify(raw)
        if kind == "title":
            title = text
            continue
        # 連續的系統行 / 內心行合併成同一塊，其餘各自成塊
        if kind in ("system", "inner") and blocks and blocks[-1][0] == kind:
            blocks[-1][1].append(text)
        else:
            blocks.append((kind, [text]))
    return title, blocks


def render_blocks(blocks):
    out = []
    for kind, lines in blocks:
        if kind == "rule":
            out.append('<hr class="brk" />')
        elif kind == "scene":
            out.append(f'<p class="scene">{html.escape(lines[0])}</p>')
        elif kind == "system":
            rows = "".join(f"<span>{html.escape(t)}</span>" for t in lines)
            out.append(f'<div class="sys" role="note">{rows}</div>')
        elif kind == "inner":
            rows = "".join(f"<span>{html.escape(t)}</span>" for t in lines)
            out.append(f'<div class="inner">{rows}</div>')
        else:
            out.append(f"<p>{html.escape(lines[0])}</p>")
    return "\n".join(out)


def split_title(title):
    """「第一百零二章　下一個」→ ("第一百零二章", "下一個")。"""
    parts = re.split(r"[　\s]+", title, maxsplit=1)
    return (parts[0], parts[1]) if len(parts) == 2 else (title, "")


CSS = """
*,*::before,*::after{box-sizing:border-box}

:root{
  /* 冷調紙面。故事是冰、海、影，所以中性色偏藍而不是偏暖 */
  --ground:#F1F3F6;
  --sheet:#FBFCFD;
  --ink:#161A20;
  --muted:#69737F;
  --hair:#D8DDE4;
  /* 系統藍——書裡指定的顏色 */
  --sys:#2C63AC;
  --sys-bg:#E7EEF8;
  --sys-edge:#9EBBE0;
  /* 金。全頁只用在章名的一條線上 */
  --gold:#9C7833;

  --serif:"Songti TC","Noto Serif TC","Source Han Serif TC","Noto Serif CJK TC",
          "Hiragino Mincho ProN","SimSun",serif;
  --sans:"PingFang TC","Noto Sans TC","Source Han Sans TC","Noto Sans CJK TC",
         "Hiragino Sans CNS","Microsoft JhengHei",sans-serif;
}

@media (prefers-color-scheme:dark){
  :root:not([data-theme="light"]){
    --ground:#0C1015;
    --sheet:#11171E;
    --ink:#DCE2E9;
    --muted:#7B8896;
    --hair:#232C36;
    --sys:#74AAE8;
    --sys-bg:#12202F;
    --sys-edge:#2C425C;
    --gold:#CFA75C;
  }
}
:root[data-theme="dark"]{
  --ground:#0C1015;
  --sheet:#11171E;
  --ink:#DCE2E9;
  --muted:#7B8896;
  --hair:#232C36;
  --sys:#74AAE8;
  --sys-bg:#12202F;
  --sys-edge:#2C425C;
  --gold:#CFA75C;
}

html{-webkit-text-size-adjust:100%}
body{
  margin:0;
  background:var(--ground);
  color:var(--ink);
  font-family:var(--serif);
  font-size:1.0625rem;
  line-height:1.95;
}

/* 捲動進度：兩萬字的一章，讀者需要知道自己在哪 */
.prog{position:fixed;inset:0 auto auto 0;height:2px;width:0;background:var(--gold);z-index:9}

.wrap{max-width:41rem;margin:0 auto;padding:clamp(2rem,6vw,4.5rem) clamp(1.15rem,5vw,2rem) 6rem}

header{margin-bottom:clamp(2.5rem,7vw,4rem)}
.eyebrow{
  font-family:var(--sans);font-size:.72rem;letter-spacing:.22em;
  color:var(--muted);margin:0 0 .9rem;text-transform:none;
}
h1{
  font-size:clamp(1.9rem,6vw,2.6rem);line-height:1.3;margin:0;
  font-weight:700;letter-spacing:.02em;text-wrap:balance;
}
.rule{width:3.5rem;height:2px;background:var(--gold);margin:1.4rem 0 0;border:0}

main{display:flex;flex-direction:column;gap:1.5rem}
main p{margin:0;text-align:justify;text-justify:inter-ideograph}

/* 場景標記 〔第７３１日　０７：４０〕 */
.scene{
  font-family:var(--sans);font-size:.82rem;letter-spacing:.12em;
  color:var(--muted);padding-top:1.4rem;border-top:1px solid var(--hair);
  margin-top:1.2rem!important;
}

/* 系統面板 【　】 */
.sys{
  display:flex;flex-direction:column;gap:.3rem;
  font-family:var(--sans);font-size:.9rem;line-height:1.75;letter-spacing:.04em;
  color:var(--sys);background:var(--sys-bg);
  border-left:2px solid var(--sys-edge);border-radius:0 3px 3px 0;
  padding:.85rem 1.1rem;font-variant-numeric:tabular-nums;
  overflow-x:auto;
}

/* 內心獨白 （　） */
.inner{
  display:flex;flex-direction:column;gap:.55rem;
  color:var(--muted);padding-left:1.35rem;
  border-left:1px solid var(--hair);
}

/* 段落分隔 --- */
.brk{border:0;height:1px;background:none;margin:1.1rem auto;width:100%;
     display:flex;align-items:center;justify-content:center}
.brk::after{
  content:"◆";color:var(--hair);font-size:.62rem;letter-spacing:.6em;
  display:block;text-align:center;line-height:1;
}

footer{
  margin-top:4.5rem;padding-top:1.6rem;border-top:1px solid var(--hair);
  font-family:var(--sans);font-size:.78rem;letter-spacing:.1em;color:var(--muted);
  display:flex;justify-content:space-between;gap:1rem;flex-wrap:wrap;
}
footer span{font-variant-numeric:tabular-nums}

@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important}}
"""

PAGE = """<title>{title}</title>
<meta name="viewport" content="width=device-width,initial-scale=1" />
<style>{css}</style>
<div class="prog" id="prog"></div>
<div class="wrap">
  <header>
    <p class="eyebrow">{eyebrow}</p>
    <h1>{heading}</h1>
    <hr class="rule" />
  </header>
  <main>
{body}
  </main>
  <footer>
    <span>{chapter}　完</span>
    <span>{count} 字</span>
  </footer>
</div>
<script>
  var prog = document.getElementById('prog');
  function tick(){{
    var h = document.documentElement.scrollHeight - window.innerHeight;
    prog.style.width = (h > 0 ? (window.scrollY / h) * 100 : 0) + '%';
  }}
  addEventListener('scroll', tick, {{passive:true}});
  addEventListener('resize', tick);
  tick();
</script>
"""


def build(md_path, out_path=None):
    md = Path(md_path).read_text(encoding="utf-8")
    title, blocks = parse(md)
    chapter, name = split_title(title)
    body = render_blocks(blocks)
    count = sum(len("".join(lines)) for _, lines in blocks)

    page = PAGE.format(
        title=html.escape(title),
        css=CSS,
        eyebrow=html.escape(chapter),
        heading=html.escape(name or chapter),
        chapter=html.escape(chapter),
        count=f"{count:,}",
        body=body,
    )
    out = Path(out_path) if out_path else Path(md_path).with_suffix(".html")
    out.write_text(page, encoding="utf-8")
    return out, count


if __name__ == "__main__":
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    dest, n = build(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    print(f"{dest}　{n:,} 字")
