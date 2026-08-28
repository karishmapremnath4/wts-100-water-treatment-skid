#!/usr/bin/env python3
"""Render the WTS-100 markdown documents to PDF.

No pandoc or markdown library on this machine, so this converts the subset of
markdown these documents use: headings, tables, bold, inline code, fenced code
blocks, bullet and numbered lists, horizontal rules.

Usage:  python3 make_pdf.py
"""
import re, html, subprocess, pathlib

HERE = pathlib.Path(__file__).resolve().parent
DOCS = HERE.parent / "docs"
PDFS = HERE.parent / "pdf"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

BULLET = r"^\s*[-*]\s+"
NUMBER = r"^\s*\d+\.\s+"


def inline(s):
    s = html.escape(s)
    s = re.sub(r'`([^`]+)`', r'<code>\1</code>', s)
    s = re.sub(r'\*\*([^*]+)\*\*', r'<strong>\1</strong>', s)
    return s


def md2html(text):
    out, lines, i = [], text.split("\n"), 0
    while i < len(lines):
        ln = lines[i]

        if ln.startswith("```"):
            i += 1
            buf = []
            while i < len(lines) and not lines[i].startswith("```"):
                buf.append(html.escape(lines[i])); i += 1
            out.append("<pre>" + "\n".join(buf) + "</pre>"); i += 1; continue

        if ln.startswith("|") and i + 1 < len(lines) and re.match(r'^\|[\s:|-]+\|$', lines[i+1]):
            def cells(r): return [c.strip() for c in r.strip().strip("|").split("|")]
            hdr = cells(ln); i += 2
            rows = []
            while i < len(lines) and lines[i].startswith("|"):
                rows.append(cells(lines[i])); i += 1
            t = ["<table><thead><tr>"]
            t += [f"<th>{inline(c)}</th>" for c in hdr]
            t.append("</tr></thead><tbody>")
            for r in rows:
                t.append("<tr>" + "".join(f"<td>{inline(c)}</td>" for c in r) + "</tr>")
            t.append("</tbody></table>")
            out.append("".join(t)); continue

        m = re.match(r'^(#{1,4})\s+(.*)$', ln)
        if m:
            out.append(f"<h{len(m.group(1))}>{inline(m.group(2))}</h{len(m.group(1))}>")
            i += 1; continue

        if re.match(r'^---+$', ln):
            out.append("<hr>"); i += 1; continue

        if re.match(BULLET, ln):
            items = []
            while i < len(lines) and re.match(BULLET, lines[i]):
                items.append("<li>" + inline(re.sub(BULLET, "", lines[i])) + "</li>"); i += 1
            out.append("<ul>" + "".join(items) + "</ul>"); continue

        if re.match(NUMBER, ln):
            items = []
            while i < len(lines) and re.match(NUMBER, lines[i]):
                items.append("<li>" + inline(re.sub(NUMBER, "", lines[i])) + "</li>"); i += 1
            out.append("<ol>" + "".join(items) + "</ol>"); continue

        if ln.strip() == "":
            i += 1; continue

        buf = []
        while i < len(lines) and lines[i].strip() and not re.match(
                r'^(#{1,4}\s|\||```|---+$|\s*[-*]\s|\s*\d+\.\s)', lines[i]):
            buf.append(lines[i]); i += 1
        if buf:
            out.append("<p>" + inline(" ".join(buf)) + "</p>")
    return "\n".join(out)


CSS = """
@page { size: A4; margin: 16mm 14mm; }
body { font-family: -apple-system, Helvetica, Arial, sans-serif; font-size: 10pt;
       line-height: 1.45; color: #111; }
h1 { font-size: 18pt; border-bottom: 2px solid #111; padding-bottom: 4px; margin: 0 0 4px; }
h2 { font-size: 13pt; margin: 18px 0 6px; border-bottom: 1px solid #bbb; padding-bottom: 2px; }
h3 { font-size: 11pt; margin: 12px 0 4px; }
p  { margin: 6px 0; }
ul, ol { margin: 6px 0 6px 20px; }
li { margin: 2px 0; }
table { border-collapse: collapse; width: 100%; margin: 8px 0; font-size: 8.8pt;
        page-break-inside: avoid; }
th, td { border: 1px solid #999; padding: 3px 6px; text-align: left; vertical-align: top; }
th { background: #eceff3; font-weight: 700; }
pre { background: #f4f5f7; border-left: 3px solid #888; padding: 7px 9px;
      font-family: Menlo, monospace; font-size: 8.5pt; margin: 8px 0; }
code { background: #f4f5f7; padding: 1px 3px; font-family: Menlo, monospace; font-size: 9pt; }
hr { border: 0; border-top: 1px solid #ccc; margin: 14px 0; }
"""


def render(md_name, pdf_name):
    body = md2html((DOCS / md_name).read_text())
    tmp = HERE / "_build.html"
    tmp.write_text(f'<html><head><meta charset="utf-8"><style>{CSS}</style></head>'
                   f'<body>{body}</body></html>', encoding="utf-8")
    pdf = PDFS / pdf_name
    subprocess.run([CHROME, "--headless", "--disable-gpu", "--no-pdf-header-footer",
                    f"--print-to-pdf={pdf}", f"file://{tmp}"],
                   check=True, capture_output=True, timeout=120)
    tmp.unlink()
    print("wrote", pdf.name)


if __name__ == "__main__":
    render("01_control_narrative.md", "WTS-100_Control_Narrative.pdf")
    render("02_instrument_index.md",  "WTS-100_Instrument_Index.pdf")
    render("03_signal_scaling.md",    "WTS-100_Signal_Scaling.pdf")
