#!/usr/bin/env python3
"""
Builds the course website from this repository into docs/, which GitHub Pages serves.

    python website/build.py

What ends up on the site:
    website/pages/*.html    the hand-written pages
    hpc_lab/**              every script, shown with syntax highlighting
    notebooks/*.ipynb       every notebook, rendered to its own page
    slides/*.pdf            every PDF you put there is listed on a Slides page

So after you change a script or a notebook, run this again and commit docs/.
It needs two packages:  pip install markdown pygments

The pages may use a few helper tags:
    <x-code lang="bash" title="...">raw text</x-code>      a highlighted snippet with a copy button
    <x-file path="hpc_lab/01_hello/hello.sbatch" open>     a whole file from the repository
    <x-math>x_t</x-math>   <x-math block>...</x-math>      LaTeX, turned into MathML (see texmath.py)
    <x-notebooks/>  <x-slides/>                            the notebook cards and the list of slides
    {{root}} {{repo}} {{clone}} {{zip}}                    paths and links
"""
import base64
import hashlib
import html
import json
import re
import shutil
import sys
from pathlib import Path
from urllib.parse import quote

import markdown
from pygments import highlight
from pygments.formatters import HtmlFormatter
from pygments.lexers import BashLexer, PythonLexer, TextLexer

sys.path.insert(0, str(Path(__file__).resolve().parent))
from texmath import tex_to_mathml  # noqa: E402

# ---- settings you may change ------------------------------------------------
REPO = "himanshubeniwal/behind-llms-lab"      # GitHub user/repository
BRANCH = "main"
SITE_NAME = "Behind the Secrets of LLMs"
NAV = [                                       # page file (without .html) and its label in the menu
    ("index", "Overview"),
    ("clusters", "Clusters"),
    ("setup", "Setup"),
    ("lab", "HPC lab"),
    ("crash-course", "Crash course"),
    ("notebooks", "Notebooks"),
    ("black-box", "Black box"),
    ("cheatsheet", "Cheat sheet"),
]
# -----------------------------------------------------------------------------

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "website"
OUT = ROOT / "docs"
REPO_URL = f"https://github.com/{REPO}"
LINKS = {
    "repo": REPO_URL,
    "clone": f"{REPO_URL}.git",
    "zip": f"{REPO_URL}/archive/refs/heads/{BRANCH}.zip",
    "blob": f"{REPO_URL}/blob/{BRANCH}",
    "raw": f"https://raw.githubusercontent.com/{REPO}/{BRANCH}",
    "colab": f"https://colab.research.google.com/github/{REPO}/blob/{BRANCH}",
}
LEXERS = {".py": PythonLexer, ".sh": BashLexer, ".sbatch": BashLexer, "bash": BashLexer,
          "python": PythonLexer, "text": TextLexer, ".txt": TextLexer}
FORMATTER = HtmlFormatter(nowrap=True)
esc = html.escape


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


# ----------------------------------------------------------------------------- code
def _sbatch_line(m):
    """Colour '#SBATCH --key=value  # comment' as a directive, not as one grey comment."""
    mm = re.match(r"(#SBATCH)(\s+)(--?[\w-]+)(=?)(\S*)(\s*)(#.*)?$", html.unescape(m.group(1)))
    if not mm:
        return m.group(0)
    d, s1, key, eq, val, s2, com = mm.groups()
    out = f'<span class="sbd">{d}</span>{s1}<span class="sbk">{esc(key)}</span>{eq}'
    if val:
        out += f'<span class="sbv">{esc(val)}</span>'
    out += s2
    if com:
        out += f'<span class="c1">{esc(com)}</span>'
    return out


def highlight_code(text, lang):
    lexer = LEXERS.get(lang, TextLexer)()
    text = text.replace("<zih-login>", "ZIHLOGINzz")              # keep it in one token
    out = highlight(text.rstrip("\n") + "\n", lexer, FORMATTER).rstrip("\n")
    out = out.replace("ZIHLOGINzz", '<span class="zih">&lt;zih-login&gt;</span>')
    if isinstance(lexer, BashLexer):
        out = re.sub(r'<span class="c1">(#SBATCH[^<]*)</span>', _sbatch_line, out)
    return out


def code_block(text, lang="text", title="", link="", extra_class=""):
    """A <figure> with a title bar, a copy button and the highlighted code."""
    label = {"bash": "shell", "python": "python", "text": ""}.get(lang, lang.lstrip("."))
    if lang in (".sbatch", ".sh"):
        label = "slurm job script" if lang == ".sbatch" else "shell"
    if lang == ".py":
        label = "python"
    bar = f'<span class="code-title">{esc(title)}</span>' if title else ""
    bar += f'<span class="code-lang">{esc(label)}</span>' if label else ""
    if link:
        bar += f'<a class="code-link" href="{esc(link)}">GitHub</a>'
    bar += '<button class="copy" type="button" aria-label="Copy the code">Copy</button>'
    return (f'<figure class="code {extra_class}"><figcaption>{bar}</figcaption>'
            f'<pre tabindex="0"><code class="hl">{highlight_code(text, lang)}</code></pre></figure>')


def file_block(path, is_open=False):
    """A whole file from the repository inside a <details>, so long files stay folded."""
    f = ROOT / path
    text = f.read_text(encoding="utf-8")
    n_lines = text.count("\n") + (0 if text.endswith("\n") else 1)
    fig = code_block(text, f.suffix, title=path, link=f"{LINKS['blob']}/{quote(path)}")
    return (f'<details class="file"{" open" if is_open else ""}><summary><span class="file-name">{esc(f.name)}</span>'
            f'<span class="file-meta">{n_lines} lines</span></summary>{fig}</details>')


# ----------------------------------------------------------------------------- markdown
MD = markdown.Markdown(extensions=["tables", "sane_lists", "toc"], output_format="html5")


def md_to_html(src, heading_shift=0):
    """Markdown with $math$ and ```code``` to HTML."""
    keep = []

    def stash(value):
        keep.append(value)
        return f"zzKEEP{len(keep) - 1}zz"

    def fence(m):
        lang = {"bash": "bash", "sh": "bash", "python": "python", "py": "python"}.get(m.group(1).strip(), "text")
        return "\n\n" + stash(code_block(m.group(2), lang)) + "\n\n"

    src = re.sub(r"```([^\n]*)\n(.*?)```", fence, src, flags=re.S)
    spans = []

    def hide_span(m):
        spans.append(m.group(0))
        return f"zzSPAN{len(spans) - 1}zz"

    src = re.sub(r"`[^`\n]+`", hide_span, src)                       # no math inside `code`
    src = re.sub(r"\$\$(.+?)\$\$", lambda m: stash(tex_to_mathml(m.group(1), display=True)), src, flags=re.S)
    def inline(m):
        out = tex_to_mathml(m.group(1))
        # a long formula cannot wrap, so on a phone it gets its own line that scrolls sideways
        return stash(f'<span class="math-block">{out}</span>' if len(m.group(1)) > 60 else out)

    src = re.sub(r"\$([^$\n]+?)\$", inline, src)
    src = re.sub(r"zzSPAN(\d+)zz", lambda m: spans[int(m.group(1))], src)

    MD.reset()
    out = MD.convert(src)
    if heading_shift:
        out = re.sub(r"<(/?)h([1-5])", lambda m: f"<{m.group(1)}h{int(m.group(2)) + heading_shift}", out)
    out = re.sub(r"<p>(zzKEEP\d+zz)</p>", r"\1", out)
    out = re.sub(r"zzKEEP(\d+)zz", lambda m: keep[int(m.group(1))], out)
    return out.replace("<table>", '<div class="table-wrap"><table>').replace("</table>", "</table></div>")


# ----------------------------------------------------------------------------- notebooks
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")


def readme_table():
    """'what it covers' and 'runtime' for each notebook, from the table in README.md."""
    info = {}
    for line in (ROOT / "README.md").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\|\s*\[([^\]]+)\]\([^)]*\)\s*\|\s*(.*?)\s*\|\s*(.*?)\s*\|", line)
        if m:
            info[m.group(1).strip()] = {"covers": m.group(2), "runtime": m.group(3)}
    return info


def load_notebooks():
    table = readme_table()
    books = []
    for path in sorted((ROOT / "notebooks").glob("*.ipynb")):
        nb = json.loads(path.read_text(encoding="utf-8"))
        cells = [c for c in nb["cells"] if "".join(c["source"]).strip()]
        md_text = "\n".join("".join(c["source"]) for c in cells if c["cell_type"] == "markdown")
        title = re.search(r"^#\s+(.+)$", md_text, flags=re.M)
        time_line = re.search(r"^Time:\s*(.+?)(?:\.|$)", md_text, flags=re.M)
        code_cells = [c for c in cells if c["cell_type"] == "code"]
        books.append({
            "path": path, "name": path.stem, "slug": slugify(path.stem), "cells": cells,
            "title": re.sub(r"^\d+\w*\.\s*", "", title.group(1)).strip() if title else path.stem,
            "number": re.match(r"\s*(\w+)", path.stem).group(1),
            "time": time_line.group(1).strip() if time_line else "",
            "sections": [re.sub(r"^\d+\.\s*", "", s) for s in re.findall(r"^##\s+(.+)$", md_text, flags=re.M)],
            "exercises": len(re.findall(r"^\d+\.\s+\*\*", md_text.split("### Exercises")[-1], flags=re.M))
                         if "### Exercises" in md_text else 0,
            "n_code": len(code_cells),
            "has_outputs": any(c.get("outputs") for c in code_cells),
            "covers": table.get(path.stem, {}).get("covers", ""),
            "runtime": table.get(path.stem, {}).get("runtime", ""),
            "file": f"notebooks/{quote(path.name)}",
        })
    return books


def notebook_links(nb, root):
    return (f'<a class="btn btn-primary" href="{LINKS["colab"]}/{nb["file"]}">Open in Colab</a>'
            f'<a class="btn" href="{LINKS["blob"]}/{nb["file"]}">View on GitHub</a>'
            f'<a class="btn" href="{LINKS["raw"]}/{nb["file"]}" download>Download .ipynb</a>')


def render_output(out, nb, counter):
    kind = out["output_type"]
    if kind == "stream":
        text = ANSI.sub("", "".join(out["text"])).rstrip()
        return f'<pre class="nb-stream" tabindex="0">{esc(text)}</pre>' if text else ""
    if kind in ("display_data", "execute_result"):
        data = out.get("data", {})
        if "image/png" in data:
            counter[0] += 1
            raw = base64.b64decode("".join(data["image/png"]))
            name = f"{nb['slug']}-fig{counter[0]}.png"
            (OUT / "assets" / "nb").mkdir(parents=True, exist_ok=True)
            (OUT / "assets" / "nb" / name).write_bytes(raw)
            w, h = int.from_bytes(raw[16:20], "big"), int.from_bytes(raw[20:24], "big")
            return (f'<div class="nb-fig"><img src="../assets/nb/{name}" width="{w}" height="{h}" loading="lazy" '
                    f'alt="Figure {counter[0]}: plot produced by the code cell above"></div>')
        if "text/plain" in data:
            return f'<pre class="nb-stream" tabindex="0">{esc("".join(data["text/plain"]).rstrip())}</pre>'
    if kind == "error":
        text = ANSI.sub("", "\n".join(out.get("traceback", [])))
        return f'<pre class="nb-stream nb-error" tabindex="0">{esc(text)}</pre>'
    return ""


def render_notebook(nb):
    parts, counter, n_code = [], [0], 0
    for cell in nb["cells"]:
        src = "".join(cell["source"])
        if cell["cell_type"] == "markdown":
            src = re.sub(r"^#\s+.+\n", "", src, count=1) if not parts else src   # the page already has the title
            parts.append(f'<div class="nb-md">{md_to_html(src)}</div>')
        elif cell["cell_type"] == "code":
            n_code += 1
            outs = "".join(render_output(o, nb, counter) for o in cell.get("outputs", []))
            outs = f'<div class="nb-out"><span class="nb-out-label">output</span>{outs}</div>' if outs else ""
            parts.append(f'<div class="nb-cell" id="cell-{n_code}">'
                         f'{code_block(src, "python", title=f"In [{n_code}]", extra_class="nb-code")}{outs}</div>')
    note = "" if nb["has_outputs"] else (
        '<div class="callout note"><strong>No outputs here.</strong> This notebook is saved without its outputs, '
        'because the models are downloaded when you run it. Open it in Colab to see the results.</div>')
    actions = f'<div class="btn-row nb-actions">{notebook_links(nb, "../")}</div>'
    return f'{actions}{note}<div class="nb">{"".join(parts)}</div>{actions}'


def notebook_cards(books, root):
    cards = []
    for nb in books:
        chips = "".join(f"<li>{esc(s)}</li>" for s in nb["sections"][:9])
        meta = [f"<span>{esc(nb['time'])}</span>" if nb["time"] else "",
                f"<span>{esc(nb['runtime'])}</span>" if nb["runtime"] else "",
                f"<span>{nb['n_code']} code cells</span>",
                f"<span>{nb['exercises']} exercises</span>" if nb["exercises"] else ""]
        cards.append(
            f'<article class="nb-card"><div class="nb-card-num">{esc(nb["number"])}</div><div class="nb-card-body">'
            f'<h3 id="nb-{nb["slug"]}"><a href="{root}notebooks/{nb["slug"]}.html">{esc(nb["title"])}</a></h3>'
            f'<p>{esc(nb["covers"][:1].upper() + nb["covers"][1:])}{"." if nb["covers"] else ""}</p>'
            f'<div class="meta-row">{"".join(meta)}</div><ul class="chip-list">{chips}</ul>'
            f'<div class="btn-row"><a class="btn btn-primary" href="{root}notebooks/{nb["slug"]}.html">Read it here</a>'
            f'<a class="btn" href="{LINKS["colab"]}/{nb["file"]}">Open in Colab</a>'
            f'<a class="btn" href="{LINKS["blob"]}/{nb["file"]}">GitHub</a>'
            f'<a class="btn" href="{LINKS["raw"]}/{nb["file"]}" download>.ipynb</a></div></div></article>')
    return '<div class="nb-cards">' + "".join(cards) + "</div>"


# ----------------------------------------------------------------------------- slides
def load_slides():
    """PDFs in slides/. An optional slides/index.json adds a title, the author and a note per file."""
    folder = ROOT / "slides"
    if not folder.is_dir():
        return []
    info = json.loads((folder / "index.json").read_text(encoding="utf-8")) if (folder / "index.json").exists() else {}
    decks = []
    for pdf in sorted(folder.glob("*.pdf")):
        meta = info.get(pdf.name, {})
        decks.append({"file": pdf, "title": meta.get("title", pdf.stem.replace("_", " ")),
                      "by": meta.get("by", ""), "note": meta.get("note", ""),
                      "size": f"{pdf.stat().st_size / 2**20:.1f} MB"})
    return decks


def slides_html(decks, root):
    out = []
    for d in decks:
        href = f"{root}slides/{quote(d['file'].name)}"
        by = f'<span>{esc(d["by"])}</span>' if d["by"] else ""
        note = f"<p>{esc(d['note'])}</p>" if d["note"] else ""
        out.append(
            f'<article class="deck"><div class="deck-head"><h2 id="{slugify(d["title"])}">{esc(d["title"])}</h2>'
            f'<div class="meta-row">{by}<span>PDF, {d["size"]}</span></div>{note}'
            f'<div class="btn-row"><a class="btn btn-primary" href="{href}">Open the PDF</a>'
            f'<a class="btn" href="{href}" download>Download</a></div></div>'
            f'<object class="deck-view" data="{href}#view=FitH" type="application/pdf" aria-label="{esc(d["title"])}">'
            f'<p>Your browser cannot show PDFs here. <a href="{href}">Open the PDF</a> instead.</p></object></article>')
    return "".join(out)


# ----------------------------------------------------------------------------- pages
def parse_page(path):
    """A page starts with an HTML comment of 'key: value' lines, the rest is the body."""
    text = path.read_text(encoding="utf-8")
    meta = {}
    m = re.match(r"\s*<!--(.*?)-->", text, flags=re.S)
    if m:
        for line in m.group(1).strip().splitlines():
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
        text = text[m.end():]
    return meta, text


def expand(body, ctx):
    """Replace the helper tags of a page."""
    root = ctx["root"]
    for key, value in LINKS.items():                     # first, so that they also work inside <x-code>
        body = body.replace("{{" + key + "}}", value)
    body = body.replace("{{root}}", root)

    def x_code(m):
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
        text = m.group(2).strip("\n")
        return code_block(text, attrs.get("lang", "bash"), attrs.get("title", ""),
                          extra_class="output" if attrs.get("lang") == "text" else "")

    def x_file(m):
        attrs = dict(re.findall(r'(\w+)="([^"]*)"', m.group(1)))
        return file_block(attrs["path"], is_open=bool(re.search(r"\bopen\b", m.group(1).split('"')[-1])))

    body = re.sub(r"<x-code([^>]*)>(.*?)</x-code>", x_code, body, flags=re.S)
    body = re.sub(r"<x-file([^>]*?)/?>", x_file, body)
    body = re.sub(r"<x-math block>(.*?)</x-math>", lambda m: tex_to_mathml(html.unescape(m.group(1)), True), body, flags=re.S)
    body = re.sub(r"<x-math>(.*?)</x-math>", lambda m: tex_to_mathml(html.unescape(m.group(1))), body, flags=re.S)
    body = re.sub(r'<x-repeat n="(\d+)"/>', lambda m: "<i></i>" * int(m.group(1)), body)
    body = body.replace("<x-notebooks/>", notebook_cards(ctx["notebooks"], root))
    body = body.replace("<x-slides/>", slides_html(ctx["slides"], root))
    return body


def add_heading_ids(body):
    """Give every <h2> an id and return the list for the table of contents."""
    toc, seen = [], set()

    def fix(m):
        attrs, inner = m.group(1), m.group(2)
        label = re.sub(r"<[^>]+>", "", inner).strip()
        found = re.search(r'id="([^"]+)"', attrs)
        hid = found.group(1) if found else slugify(html.unescape(label))
        while hid in seen:
            hid += "-2"
        seen.add(hid)
        toc.append((hid, label))
        attrs = attrs if found else f'{attrs} id="{hid}"'
        return f'<h2{attrs}>{inner}<a class="anchor" href="#{hid}" aria-label="Link to this section">#</a></h2>'

    return re.sub(r"<h2([^>]*)>(.*?)</h2>", fix, body, flags=re.S), toc


ICON_GITHUB = ('<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="currentColor" d="M12 2a10 10 0 0 0-3.16 '
               '19.49c.5.09.68-.22.68-.48v-1.7c-2.78.6-3.37-1.34-3.37-1.34-.46-1.16-1.11-1.47-1.11-1.47-.91-.62.07-.6.07-.6 1 .07 '
               '1.53 1.03 1.53 1.03.9 1.52 2.34 1.08 2.91.83.09-.65.35-1.09.63-1.34-2.22-.25-4.56-1.11-4.56-4.94 0-1.09.39-1.98 '
               '1.03-2.68-.1-.25-.45-1.27.1-2.64 0 0 .84-.27 2.75 1.02a9.5 9.5 0 0 1 5 0c1.91-1.3 2.75-1.02 2.75-1.02.55 1.37.2 '
               '2.39.1 2.64.64.7 1.03 1.59 1.03 2.68 0 3.84-2.34 4.68-4.57 4.93.36.31.68.92.68 1.85v2.74c0 .27.18.58.69.48A10 10 0 0 '
               '0 12 2Z"/></svg>')
ICON_THEME = ('<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true"><path fill="currentColor" d="M12 3a9 9 0 1 0 '
              '0 18V3Z"/><circle cx="12" cy="12" r="8.25" fill="none" stroke="currentColor" stroke-width="1.5"/></svg>')
BRAND_MARK = ('<svg viewBox="0 0 32 32" width="28" height="28" aria-hidden="true"><rect x="5" y="12" width="22" height="15" rx="3" '
              'fill="none" stroke="currentColor" stroke-width="2"/><path d="M5 11 16 4l11 7" fill="none" stroke="var(--amber)" '
              'stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/><circle cx="16" cy="19.5" r="2.4" fill="var(--amber)"/></svg>')


def layout(meta, body, ctx, slug, toc=()):
    root = ctx["root"]
    title = meta.get("title", SITE_NAME)
    full_title = SITE_NAME + " · Lab" if slug == "index" else f"{title} · {SITE_NAME}"
    desc = meta.get("description", "Lab material for the course Behind the Secrets of Large Language Models.")
    current = ' aria-current="page"'
    nav = "".join(
        f'<a href="{root}{page}.html"{current if page == ctx["nav"] else ""}>{esc(label)}</a>'
        for page, label in ctx["menu"])

    if meta.get("layout") == "home":
        main = body
    else:
        hero = (f'<header class="page-hero"><div class="wrap"><p class="eyebrow">{esc(meta.get("eyebrow", ""))}</p>'
                f'<h1>{esc(title)}</h1><p class="lead">{meta.get("lead", "")}</p></div></header>')
        aside = ""
        if len(toc) >= 3 and meta.get("toc", "yes") != "no":
            items = "".join(f'<li><a href="#{hid}">{label}</a></li>' for hid, label in toc)
            aside = f'<aside class="toc" aria-label="On this page"><p>On this page</p><ol>{items}</ol></aside>'
        order = [p for p, _ in ctx["menu"]]
        pager = ""
        if ctx["nav"] in order and slug == ctx["nav"]:
            i = order.index(slug)
            prev_link = (f'<a class="pager-prev" href="{root}{order[i - 1]}.html"><span>Previous</span>'
                         f'{esc(dict(ctx["menu"])[order[i - 1]])}</a>') if i > 0 else "<span></span>"
            next_link = (f'<a class="pager-next" href="{root}{order[i + 1]}.html"><span>Next</span>'
                         f'{esc(dict(ctx["menu"])[order[i + 1]])}</a>') if i + 1 < len(order) else "<span></span>"
            pager = f'<nav class="pager wrap" aria-label="Previous and next page">{prev_link}{next_link}</nav>'
        main = (f'{hero}<div class="wrap layout{" has-toc" if aside else ""}"><article class="prose">{body}</article>'
                f'{aside}</div>{pager}')

    scripts = f'<script src="{root}assets/site.js?v={ctx["v"]}" defer></script>'
    if meta.get("widgets"):
        scripts += f'<script src="{root}assets/widgets.js?v={ctx["v"]}" defer></script>'
    return f"""<!doctype html>
<html lang="en" data-theme="dark">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{esc(full_title)}</title>
<meta name="description" content="{esc(desc)}">
<meta property="og:title" content="{esc(full_title)}">
<meta property="og:description" content="{esc(desc)}">
<meta property="og:type" content="website">
<meta name="color-scheme" content="dark light">
<link rel="icon" href="{root}assets/favicon.svg" type="image/svg+xml">
<link rel="stylesheet" href="{root}assets/site.css?v={ctx["v"]}">
<script>(function(){{try{{var t=localStorage.getItem("theme");if(t!=="light"&&t!=="dark")t=matchMedia("(prefers-color-scheme: light)").matches?"light":"dark";document.documentElement.dataset.theme=t}}catch(e){{}}}})()</script>
</head>
<body class="page-{slug.replace("/", "-")}">
<a class="skip" href="#main">Skip to the content</a>
<header class="top">
  <div class="top-in">
    <a class="brand" href="{root}index.html">{BRAND_MARK}<span class="brand-text"><b>Behind the Secrets of LLMs</b><i>lab</i></span></a>
    <button class="nav-toggle" type="button" aria-expanded="false" aria-controls="nav">Menu</button>
    <nav id="nav" class="nav" aria-label="Main">{nav}</nav>
    <div class="top-tools">
      <a class="icon-btn" href="{REPO_URL}" aria-label="The repository on GitHub" title="GitHub repository">{ICON_GITHUB}</a>
      <button class="icon-btn theme-toggle" type="button" aria-label="Switch between dark and light" title="Dark or light">{ICON_THEME}</button>
    </div>
  </div>
</header>
<main id="main">
{main}
</main>
<footer class="foot">
  <div class="wrap foot-in">
    <div>
      <p class="foot-title">{BRAND_MARK} Behind the Secrets of LLMs</p>
      <p>Lab material for the course <em>Behind the Secrets of Large Language Models</em> at TU Dresden (ScaDS.AI).</p>
      <p class="foot-small">This site loads no trackers, no web fonts and no scripts from other servers. It is built from the repository with <code>website/build.py</code>.</p>
    </div>
    <div>
      <p class="foot-head">The material</p>
      <a href="{REPO_URL}">GitHub repository</a>
      <a href="{LINKS["zip"]}">Download everything (.zip)</a>
      <a href="{root}notebooks.html">Notebooks</a>
      <a href="{root}lab.html">HPC lab</a>
    </div>
    <div>
      <p class="foot-head">Help with the cluster</p>
      <a href="https://compendium.hpc.tu-dresden.de">ZIH HPC Compendium</a>
      <a href="https://jupyterhub.hpc.tu-dresden.de">JupyterHub</a>
      <a href="mailto:hpc-support@tu-dresden.de">hpc-support@tu-dresden.de</a>
      <a href="{root}cheatsheet.html">Cheat sheet</a>
    </div>
  </div>
</footer>
{scripts}
</body>
</html>
"""


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "assets").mkdir(parents=True)
    (OUT / "notebooks").mkdir()
    (OUT / ".nojekyll").write_text("")

    version = hashlib.sha1()
    for f in sorted((SRC / "assets").iterdir()):
        shutil.copy(f, OUT / "assets" / f.name)
        version.update(f.read_bytes())

    notebooks, slides = load_notebooks(), load_slides()
    menu = NAV + ([("slides", "Slides")] if slides else [])
    ctx = {"notebooks": notebooks, "slides": slides, "menu": menu, "v": version.hexdigest()[:8], "root": "", "nav": ""}

    for path in sorted((SRC / "pages").glob("*.html")):
        slug = path.stem
        if slug == "slides" and not slides:
            continue
        meta, body = parse_page(path)
        # GitHub Pages shows 404.html for any missing path, so its links must not be relative
        ctx.update(root=f"/{REPO.split('/')[1]}/" if slug == "404" else "", nav=meta.get("nav", slug))
        body, toc = add_heading_ids(expand(body, ctx))
        (OUT / f"{slug}.html").write_text(layout(meta, body, ctx, slug, toc), encoding="utf-8")
        print(f"page      docs/{slug}.html")

    for nb in notebooks:
        ctx.update(root="../", nav="notebooks")
        meta = {"title": nb["title"], "eyebrow": f"Notebook {nb['number']}",
                "lead": esc(" · ".join(x for x in (nb["time"], nb["runtime"]) if x)),
                "description": f"Notebook {nb['number']}: {nb['title']}. {nb['covers']}"}
        body, toc = add_heading_ids(render_notebook(nb))
        body = '<p class="back"><a href="../notebooks.html">All notebooks</a></p>' + body
        (OUT / "notebooks" / f"{nb['slug']}.html").write_text(
            layout(meta, body, ctx, f"notebooks/{nb['slug']}", toc), encoding="utf-8")
        print(f"notebook  docs/notebooks/{nb['slug']}.html")

    if slides:
        (OUT / "slides").mkdir()
        for d in slides:
            shutil.copy(d["file"], OUT / "slides" / d["file"].name)
            print(f"slides    docs/slides/{d['file'].name}")

    size = sum(f.stat().st_size for f in OUT.rglob("*") if f.is_file())
    print(f"done: {sum(1 for _ in OUT.rglob('*.html'))} pages, {size / 2**20:.1f} MB in {OUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
