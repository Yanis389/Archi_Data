"""Boîte à outils de génération des livrables PDF (HTML -> PDF via Chrome headless).

- `Doc` : construit un document (titres, paragraphes Markdown, tableaux, encadrés, schémas SVG).
- `flow_diagram` : schéma en colonnes (utilisateurs -> questions -> KPI -> domaines -> fichiers).
- `layer_diagram` : schéma d'architecture en couches (sources -> ingestion -> zones -> usages).
- Statuts du TP : Vérifié / Déduit / Hypothèse / Non disponible / À valider (badges colorés).
"""
from __future__ import annotations

import html
import re
import shutil
import subprocess
import tempfile
from datetime import datetime
from pathlib import Path

import markdown

AUTEUR = "Yanis"          # à compléter avec ton nom complet si besoin
FORMATION = "IPSSI - Mastère Développement, Data & IA - 5e année"
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

MOIS = ["janvier", "février", "mars", "avril", "mai", "juin", "juillet", "août", "septembre",
        "octobre", "novembre", "décembre"]


def date_fr(d: datetime | None = None) -> str:
    d = d or datetime.now()
    return f"{d.day} {MOIS[d.month - 1]} {d.year}"


# ----------------------------------------------------------------------------- statuts
STATUTS = {
    "V": ("Vérifié", "v"), "D": ("Déduit", "d"), "H": ("Hypothèse", "h"),
    "N": ("Non disponible", "n"), "A": ("À valider", "a"),
}


def S(code: str) -> str:
    """Badge de statut (V, D, H, N, A)."""
    label, cls = STATUTS[code]
    return f'<span class="st {cls}">{label}</span>'


FAISABILITE = {"C": ("Couverte", "v"), "P": ("Partielle", "h"), "N": ("Non fiable", "n"), "X": ("Non couverte", "n")}


def F(code: str) -> str:
    """Badge de faisabilité d'un besoin (vocabulaire distinct des statuts de certitude du TP)."""
    label, cls = FAISABILITE[code]
    return f'<span class="st {cls}">{label}</span>'


def B(label: str, cls: str = "v") -> str:
    """Badge libre (verdict d'exploitabilité, par exemple) : cls v=vert, h=ambre, n=rouge, d=bleu."""
    return f'<span class="st {cls}">{label}</span>'


def inline(txt: str) -> str:
    """Markdown en ligne -> HTML (sans <p>)."""
    out = markdown.markdown(str(txt), extensions=["sane_lists"])
    out = re.sub(r"^<p>(.*)</p>$", r"\1", out.strip(), flags=re.S)
    return out


CSS = """
:root { --bleu:#1b3a57; --teal:#1a8f8f; --gris:#5b6770; --fond:#f1f5f8; --ligne:#c9d3da; }
@page { size: A4; margin: 17mm 15mm 18mm 15mm;
  @bottom-left { content: string(doctitle); font: 8pt Helvetica, Arial, sans-serif; color:#7a858c; }
  @bottom-right { content: counter(page) " / " counter(pages); font: 8pt Helvetica, Arial, sans-serif; color:#7a858c; } }
@page :first { @bottom-left { content: ""; } @bottom-right { content: ""; } }
@page land { size: A4 landscape; margin: 15mm 14mm 16mm 14mm;
  @bottom-left { content: string(doctitle); font: 8pt Helvetica, Arial, sans-serif; color:#7a858c; }
  @bottom-right { content: counter(page) " / " counter(pages); font: 8pt Helvetica, Arial, sans-serif; color:#7a858c; } }
.land { page: land; }
* { box-sizing: border-box; }
body { font: 10pt/1.42 "Helvetica Neue", Helvetica, Arial, sans-serif; color:#1d2830; margin:0; }
.doctitle { string-set: doctitle content(); display:block; height:0; overflow:hidden; font-size:0; line-height:0; margin:0; }
.cover { padding-top: 40mm; page-break-after: always; }
.cover .kicker { color: var(--teal); letter-spacing:.12em; text-transform:uppercase; font-size:10pt; font-weight:600; }
.cover h1 { font-size: 26pt; line-height:1.15; color: var(--bleu); margin: 6mm 0 3mm; border:0; }
.cover .sub { font-size: 13pt; color: var(--gris); margin-bottom: 14mm; }
.cover table.meta { width:auto; font-size:10pt; border:0; }
.cover table.meta td { border:0; padding: 2px 14px 2px 0; }
.cover table.meta td:first-child { color: var(--gris); }
.cover .mission { margin-top: 16mm; background: var(--bleu); color:#fff; padding: 5mm 6mm; border-radius: 3mm; font-size: 10pt; }
h1 { font-size: 17pt; color: var(--bleu); border-bottom: 2px solid var(--teal); padding-bottom: 2mm; margin: 9mm 0 4mm; }
h2 { font-size: 12.5pt; color: var(--teal); margin: 6mm 0 2mm; }
h3 { font-size: 10.5pt; color: var(--bleu); margin: 4mm 0 1.5mm; }
h1, h2, h3 { page-break-after: avoid; }
p { margin: 0 0 2.4mm; text-align: justify; hyphens: auto; }
ul, ol { margin: 0 0 3mm 0; padding-left: 5.5mm; } li { margin-bottom: 1mm; }
table { border-collapse: collapse; width:100%; margin: 2mm 0 4mm; font-size: 8.4pt; }
table.fixed { table-layout: fixed; } table.fixed td, table.fixed th { overflow-wrap: anywhere; }
th { background: var(--bleu); color:#fff; text-align:left; padding: 1.6mm 2mm; font-weight:600; }
td { border: 1px solid var(--ligne); padding: 1.4mm 2mm; vertical-align: top; }
tr { page-break-inside: avoid; } table.keep { page-break-inside: avoid; } tbody tr:nth-child(even) td { background:#f7fafb; }
td.num, th.num { text-align:right; font-variant-numeric: tabular-nums; } td.num { white-space:nowrap; }
code { font: 8.6pt Menlo, monospace; background:#eef2f5; padding: 0 1mm; border-radius: 1mm; }
.st { display:inline-block; font-size:7.2pt; font-weight:700; padding: .2mm 1.6mm; border-radius: 1.2mm; white-space:nowrap; color:#fff; }
.st.v { background:#1e7b4b; } .st.d { background:#2c6fb0; } .st.h { background:#b8860b; }
.st.n { background:#a23b3b; } .st.a { background:#7a4fa3; }
.box { border-left: 1.2mm solid var(--teal); background: var(--fond); padding: 3mm 4mm; margin: 3mm 0 4mm; border-radius: 0 2mm 2mm 0; page-break-inside: avoid; }
.box .t { font-weight:700; color: var(--bleu); margin-bottom: 1mm; }
.box.warn { border-color:#b8630b; background:#fdf3e1; } .box.warn .t { color:#8a4a06; }
.box.ok { border-color:#1e7b4b; background:#eaf6ef; } .box.bad { border-color:#a23b3b; background:#faeaea; }
.box p:last-child, .box ul:last-child { margin-bottom:0; }
figure { margin: 3mm 0 5mm; page-break-inside: avoid; text-align:center; }
figure svg { max-width:100%; height:auto; } figcaption { font-size:8.4pt; color: var(--gris); margin-top: 1.5mm; }
.pb { page-break-before: always; }
.small { font-size: 8.4pt; color: var(--gris); }
.kpi-row { display:flex; gap:3mm; margin: 2mm 0 4mm; } .kpi { flex:1; background: var(--fond); border-radius:2mm; padding:2.5mm 3mm; }
.kpi .n { font-size: 15pt; font-weight:700; color: var(--bleu); } .kpi .l { font-size:8pt; color: var(--gris); }
"""


class Doc:
    def __init__(self, titre: str, sous_titre: str, uc: str, mission: str = ""):
        self.titre, self.sous_titre, self.uc, self.mission = titre, sous_titre, uc, mission
        self.body: list[str] = []

    # -- contenu
    def md(self, txt: str) -> None:
        self.body.append(markdown.markdown(txt, extensions=["sane_lists", "md_in_html"]))

    def h1(self, t: str, saut: bool = False) -> None:
        self.body.append(f'<h1{" class=pb" if saut else ""}>{html.escape(t)}</h1>')

    def h2(self, t: str) -> None:
        self.body.append(f"<h2>{html.escape(t)}</h2>")

    def h3(self, t: str) -> None:
        self.body.append(f"<h3>{html.escape(t)}</h3>")

    def p(self, t: str) -> None:
        self.body.append(f"<p>{inline(t)}</p>")

    def ul(self, items: list[str]) -> None:
        self.body.append("<ul>" + "".join(f"<li>{inline(i)}</li>" for i in items) + "</ul>")

    def ol(self, items: list[str]) -> None:
        self.body.append("<ol>" + "".join(f"<li>{inline(i)}</li>" for i in items) + "</ol>")

    def box(self, titre: str, texte: str, kind: str = "") -> None:
        inner = markdown.markdown(texte, extensions=["sane_lists"])
        self.body.append(f'<div class="box {kind}"><div class="t">{inline(titre)}</div>{inner}</div>')

    def kpis(self, items: list[tuple[str, str]]) -> None:
        self.body.append('<div class="kpi-row">' + "".join(
            f'<div class="kpi"><div class="n">{html.escape(str(n))}</div><div class="l">{html.escape(l)}</div></div>'
            for n, l in items) + "</div>")

    def table(self, headers: list[str], rows: list[list], num_cols: tuple[int, ...] = (),
              widths: list[int] | None = None) -> None:
        cg = ""
        if widths:
            cg = "<colgroup>" + "".join(f'<col style="width:{w}%">' for w in widths) + "</colgroup>"
        th = "".join(f'<th class="{"num" if i in num_cols else ""}">{html.escape(h)}</th>'
                     for i, h in enumerate(headers))
        trs = []
        for r in rows:
            tds = "".join(f'<td class="{"num" if i in num_cols else ""}">{inline(c)}</td>'
                          for i, c in enumerate(r))
            trs.append(f"<tr>{tds}</tr>")
        klass = ' class="fixed"' if widths else ""
        if len(rows) <= 12:  # petit tableau : ne pas le couper entre deux pages
            klass = klass[:-1] + ' keep"' if klass else ' class="keep"'
        self.body.append(f"<table{klass}>{cg}<thead><tr>{th}</tr></thead><tbody>{''.join(trs)}</tbody></table>")

    def figure(self, svg: str, legende: str) -> None:
        self.body.append(f"<figure>{svg}<figcaption>{inline(legende)}</figcaption></figure>")

    def raw(self, h: str) -> None:
        self.body.append(h)

    def landscape(self, on: bool = True) -> None:
        """Ouvre (True) ou ferme (False) une section en paysage."""
        self.body.append('<div class="land">' if on else "</div>")

    def pagebreak(self) -> None:
        self.body.append('<div class="pb"></div>')

    # -- rendu
    def html(self) -> str:
        meta = [("Auteur", AUTEUR), ("Formation", FORMATION), ("Date", date_fr()),
                ("Périmètre", self.uc),
                ("Source des données", "TPCx-BB (jeu synthétique), dossiers data/ et data_refresh/")]
        meta_html = "".join(f"<tr><td>{k}</td><td>{html.escape(v)}</td></tr>" for k, v in meta)
        mission = f'<div class="mission">{inline(self.mission)}</div>' if self.mission else ""
        cover = (f'<div class="cover"><div class="kicker">Retail Intelligence Platform - TP Jour 1</div>'
                 f'<h1>{html.escape(self.titre)}</h1><div class="sub">{html.escape(self.sous_titre)}</div>'
                 f'<table class="meta">{meta_html}</table>{mission}</div>')
        return (f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><title>{html.escape(self.titre)}</title>'
                f"<style>{CSS}</style></head><body><span class=\"doctitle\">{html.escape(self.titre)}</span>"
                f"{cover}{''.join(self.body)}</body></html>")

    def save_pdf(self, pdf_path: Path) -> None:
        pdf_path = Path(pdf_path)
        pdf_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.TemporaryDirectory() as td:
            hp = Path(td) / "doc.html"
            hp.write_text(self.html(), encoding="utf-8")
            cmd = [CHROME, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                   f"--print-to-pdf={pdf_path.resolve()}", "--virtual-time-budget=4000", hp.as_uri()]
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
        if not pdf_path.exists() or pdf_path.stat().st_size < 2000:
            raise RuntimeError(f"échec du rendu PDF {pdf_path.name}: {r.stderr[-400:]}")


# ----------------------------------------------------------------------------- schémas SVG
PALETTE = {  # statut -> (remplissage, contour, texte, pointillé)
    "v": ("#e3f3ea", "#1e7b4b", "#14452a", ""), "d": ("#e4eef8", "#2c6fb0", "#173f66", ""),
    "p": ("#fdf0d5", "#b8860b", "#6b4e06", ""), "h": ("#f1f1f1", "#8a8f94", "#4a4f54", "5 3"),
    "n": ("#f8e3e3", "#a23b3b", "#6b1f1f", "5 3"), "x": ("#ffffff", "#1b3a57", "#1b3a57", ""),
    "b": ("#1b3a57", "#1b3a57", "#ffffff", ""), "t": ("#d9efef", "#1a8f8f", "#0e5656", ""),
}


def _wrap(text: str, width_chars: int) -> list[str]:
    words, lines, cur = text.split(), [], ""
    for w in words:
        if len(cur) + len(w) + 1 <= width_chars:
            cur = f"{cur} {w}".strip()
        else:
            lines.append(cur)
            cur = w
    if cur:
        lines.append(cur)
    return lines


def svg_box(x, y, w, h, text, st="x", size=9.5, bold=False, sub: str = "") -> str:
    fill, stroke, col, dash = PALETTE[st]
    chars = max(8, int(w / (size * 0.53)))
    lines = _wrap(text, chars)
    sublines = _wrap(sub, int(w / (size * 0.5))) if sub else []
    total = len(lines) + len(sublines)
    lh = size * 1.25
    y0 = y + h / 2 - (total - 1) * lh / 2 + size * 0.33
    out = [f'<rect x="{x:.1f}" y="{y:.1f}" width="{w:.1f}" height="{h:.1f}" rx="5" fill="{fill}" '
           f'stroke="{stroke}" stroke-width="1.3"' + (f' stroke-dasharray="{dash}"' if dash else "") + "/>"]
    for i, ln in enumerate(lines):
        out.append(f'<text x="{x + w / 2:.1f}" y="{y0 + i * lh:.1f}" text-anchor="middle" font-size="{size}" '
                   f'fill="{col}" font-weight="{700 if bold else 500}">{html.escape(ln)}</text>')
    for i, ln in enumerate(sublines):
        out.append(f'<text x="{x + w / 2:.1f}" y="{y0 + (len(lines) + i) * lh:.1f}" text-anchor="middle" '
                   f'font-size="{size - 1.5}" fill="{col}" opacity=".8">{html.escape(ln)}</text>')
    return "".join(out)


def svg_arrow(x1, y1, x2, y2, color="#5b6770", dash="", label="", curve=True, label_dy=-4) -> str:
    if curve:
        mx = (x1 + x2) / 2
        d = f"M{x1:.1f},{y1:.1f} C{mx:.1f},{y1:.1f} {mx:.1f},{y2:.1f} {x2 - 5:.1f},{y2:.1f}"
    else:
        d = f"M{x1:.1f},{y1:.1f} L{x2 - 5:.1f},{y2:.1f}"
    out = (f'<path d="{d}" fill="none" stroke="{color}" stroke-width="1.2"'
           + (f' stroke-dasharray="{dash}"' if dash else "") + ' marker-end="url(#arr)"/>')
    if label:
        out += (f'<text x="{(x1 + x2) / 2:.1f}" y="{(y1 + y2) / 2 + label_dy:.1f}" text-anchor="middle" '
                f'font-size="8" fill="#5b6770">{html.escape(label)}</text>')
    return out


def svg_wrap(width, height, inner) -> str:
    defs = ('<defs><marker id="arr" viewBox="0 0 10 10" refX="9" refY="5" markerWidth="6" markerHeight="6" '
            'orient="auto-start-reverse"><path d="M0,0 L10,5 L0,10 z" fill="#5b6770"/></marker></defs>')
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" '
            f'height="{height}" font-family="Helvetica, Arial, sans-serif">{defs}{inner}</svg>')


def flow_diagram(columns: list[dict], edges: list[tuple], width=760, node_h=34, gap=10,
                 legend: list[tuple[str, str]] | None = None) -> str:
    """columns : [{"titre": str, "noeuds": [{"id","texte","st"}]}]  edges : [(id_a, id_b, dash?)]."""
    ncol = len(columns)
    colw = (width - 20) / ncol
    bw = colw - 26
    hmax = max(len(c["noeuds"]) for c in columns)
    top = 34
    height = top + hmax * (node_h + gap) + 14 + (24 if legend else 0)
    pos, parts = {}, []
    for ci, col in enumerate(columns):
        x = 10 + ci * colw + 3
        parts.append(f'<text x="{x + bw / 2:.1f}" y="18" text-anchor="middle" font-size="10" font-weight="700" '
                     f'fill="#1b3a57">{html.escape(col["titre"])}</text>')
        n = len(col["noeuds"])
        span = hmax * (node_h + gap) - gap
        y0 = top + (span - (n * (node_h + gap) - gap)) / 2
        for ni, nd in enumerate(col["noeuds"]):
            y = y0 + ni * (node_h + gap)
            pos[nd["id"]] = (x, y)
            parts.insert(0, "")  # garde l'ordre stable
    edge_svg = []
    for e in edges:
        a, b = e[0], e[1]
        dash = e[2] if len(e) > 2 else ""
        if a not in pos or b not in pos:
            continue
        (xa, ya), (xb, yb) = pos[a], pos[b]
        edge_svg.append(svg_arrow(xa + bw, ya + node_h / 2, xb, yb + node_h / 2, dash=dash))
    box_svg = []
    for col in columns:
        for nd in col["noeuds"]:
            x, y = pos[nd["id"]]
            box_svg.append(svg_box(x, y, bw, node_h, nd["texte"], nd.get("st", "x"), size=8.6))
    leg = ""
    if legend:
        lx = 10
        for st, lab in legend:
            fill, stroke, _, dash = PALETTE[st]
            leg += (f'<rect x="{lx}" y="{height - 18}" width="12" height="10" rx="2" fill="{fill}" stroke="{stroke}"'
                    + (f' stroke-dasharray="{dash}"' if dash else "") + "/>"
                    f'<text x="{lx + 16}" y="{height - 9.5}" font-size="8.5" fill="#444">{html.escape(lab)}</text>')
            lx += 24 + len(lab) * 5
    return svg_wrap(width, height, "".join(edge_svg) + "".join(box_svg) + "".join(parts) + leg)


def check_chrome() -> None:
    if not Path(CHROME).exists():
        raise SystemExit("Google Chrome introuvable : nécessaire pour générer les PDF (voir scripts/rapport.py)")
    if shutil.which("pdfinfo") is None:
        pass  # facultatif : sert seulement aux contrôles manuels
