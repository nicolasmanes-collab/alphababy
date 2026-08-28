#!/usr/bin/env python3
"""Rend un apercu HTML local d'un contenu Elementor.

Elementor ne permet pas de previsualiser publiquement un modele de
bibliotheque. Ce script reconstitue le rendu a partir du JSON, avec les
polices et la palette du kit global du site, pour valider le contenu avant
de poser la condition d'affichage.

Usage : preview-elementor.py <fichier.json> [sortie.html]
"""
import html
import json
import pathlib
import sys

GLOBALS = {
    "primary": "#EE743A",
    "secondary": "#80A681",
    "text": "#222222",
    "accent": "#EE743A",
    "7f6e0fa": "#F6F1E5",
    "65cf053": "#FFFFFF",
    "538bd57": "#A2C8C8",
    "903b93c": "#FDCD69",
}

UP = "https://alphababy.fr/wp-content/uploads/2023/10"

FORMULES = [
    ("Family Day sur mesure", "POPULAIRE", "3500.00€"),
    ("Family Day une journée à la fête foraine", "POPULAIRE", "3500.00€"),
    ("Family Day une journée aux jeux olympiques", "CREATION ALPHABABY",
     "2500.00€"),
]


def st(el):
    s = el.get("settings")
    return s if isinstance(s, dict) else {}


def color(el, key, default=None):
    """Resout une couleur, globale du kit ou valeur littérale."""
    s = st(el)
    g = s.get("__globals__") or {}
    ref = g.get(key)
    if ref and "colors?id=" in ref:
        return GLOBALS.get(ref.split("colors?id=")[1], default)
    return s.get(key, default)


def px(val, default=""):
    if isinstance(val, dict):
        size = val.get("size", "")
        if size == "" or size is None:
            return default
        return f"{size}{val.get('unit', 'px')}"
    return default


def box(val):
    if not isinstance(val, dict):
        return ""
    u = val.get("unit", "px")
    parts = [val.get(k) or "0" for k in ("top", "right", "bottom", "left")]
    return " ".join(f"{p}{u}" for p in parts)


def typo(el, prefix=""):
    s = st(el)
    css = []
    fam = s.get(f"{prefix}font_family")
    if fam:
        # guillemets simples : la regle part dans un attribut style="..."
        css.append(f"font-family:'{fam}',sans-serif")
    fs = px(s.get(f"{prefix}font_size"))
    if fs:
        css.append(f"font-size:{fs}")
    fw = s.get(f"{prefix}font_weight")
    if fw:
        css.append(f"font-weight:{fw}")
    lh = s.get(f"{prefix}line_height")
    if isinstance(lh, dict) and lh.get("size"):
        css.append(f"line-height:{lh['size']}")
    return ";".join(css)


def render(el):
    t = el.get("widgetType") or el.get("elType")
    s = st(el)

    if t == "container":
        css = ["display:flex", "flex-direction:column"]
        gap = s.get("flex_gap")
        if isinstance(gap, dict):
            css.append(f"gap:{gap.get('row', 20)}px")
        if s.get("background_color"):
            css.append(f"background:{s['background_color']}")
        if s.get("border_radius"):
            css.append(f"border-radius:{box(s['border_radius'])}")
        if s.get("padding"):
            css.append(f"padding:{box(s['padding'])}")
        if s.get("margin"):
            css.append(f"margin:{box(s['margin'])}")
        if s.get("content_width", "boxed") == "boxed":
            css += ["max-width:1350px", "margin-left:auto",
                    "margin-right:auto", "width:100%"]
        if s.get("flex_align_items"):
            css.append(f"align-items:{s['flex_align_items']}")
        inner = "".join(render(c) for c in el.get("elements", []))
        return f'<div style="{";".join(css)}">{inner}</div>'

    if t == "heading":
        tag = s.get("header_size", "h2")
        css = [f"color:{color(el, 'title_color', '#222')}", "margin:0"]
        tp = typo(el, "typography_")
        if tp:
            css.append(tp)
        if s.get("align"):
            css.append(f"text-align:{s['align']}")
        return (f'<{tag} style="{";".join(css)}">'
                f'{html.escape(s.get("title", ""))}</{tag}>')

    if t == "text-editor":
        css = [f"color:{color(el, 'text_color', '#222')}"]
        tp = typo(el, "typography_")
        if tp:
            css.append(tp)
        if s.get("align"):
            css.append(f"text-align:{s['align']}")
        return f'<div class="txt" style="{";".join(css)}">{s.get("editor", "")}</div>'

    if t == "icon-list":
        ic = color(el, "icon_color", "#EE743A")
        tc = color(el, "text_color", "#222")
        gap = px(s.get("space_between"), "12px")
        rows = []
        for it in s.get("icon_list", []):
            label = html.escape(it.get("text", ""))
            link = it.get("link") or {}
            if link.get("url"):
                label = (f'<a href="{html.escape(link["url"])}"'
                         f' style="color:{tc}">{label}</a>')
            rows.append(
                f'<li style="display:flex;gap:10px;margin-bottom:{gap}">'
                f'<span style="color:{ic};flex:0 0 auto">&#10003;</span>'
                f'<span style="color:{tc}">{label}</span></li>')
        return (f'<ul style="list-style:none;padding:0;margin:0;'
                f'font-family:Raleway,sans-serif;font-size:17px">'
                f'{"".join(rows)}</ul>')

    if t == "button":
        bg = color(el, "background_color", "#EE743A")
        fg = color(el, "button_text_color", "#FFFFFF")
        wrap = ("text-align:center" if s.get("align") == "center"
                else "text-align:left")
        return (f'<div style="{wrap}"><a href="'
                f'{html.escape((s.get("link") or {}).get("url", "#"))}"'
                f' style="display:inline-block;background:{bg};color:{fg};'
                f'padding:{box(s.get("text_padding")) or "16px 32px"};'
                f'border-radius:{box(s.get("border_radius")) or "15px"};'
                f'text-decoration:none;font-family:Raleway,sans-serif;'
                f'font-size:18px;font-weight:600">'
                f'{html.escape(s.get("text", ""))}</a></div>')

    if t == "nested-accordion":
        kids = el.get("elements", [])
        out = []
        for i, item in enumerate(s.get("items", [])):
            body = render(kids[i]) if i < len(kids) else ""
            out.append(
                '<details style="background:#fff;border-radius:10px;'
                'margin-bottom:10px;padding:0 18px">'
                '<summary style="cursor:pointer;padding:18px 0;'
                'font-family:Raleway,sans-serif;font-size:19px;'
                'font-weight:600;color:#222">'
                f'{html.escape(item.get("item_title", ""))}</summary>'
                f'<div style="padding-bottom:18px">{body}</div></details>')
        return "".join(out)

    if t == "shortcode":
        return ('<div class="exist"><b>Bloc existant, inchangé</b><br>'
                'Formulaire de filtres : Formule, Lieu, '
                'Type d’événement, Thème<br>'
                f'<code>{html.escape(s.get("shortcode", ""))}</code></div>')

    if t == "loop-grid":
        cards = "".join(
            f'<div class="card"><div class="badge">{b}</div>'
            f'<div class="ttl">{html.escape(n)}</div>'
            f'<div class="prix">À partir de<br><b>{p}</b></div>'
            '<div class="lien">En savoir +</div></div>'
            for n, b, p in FORMULES)
        return ('<div class="exist"><b>Bloc existant, inchangé</b><br>'
                f'Loop grid, modèle de vignette #{s.get("template_id")}, '
                f'ID de requête <code>{s.get("post_query_query_id")}</code>'
                f'</div><div class="grid">{cards}</div>')

    if t == "woocommerce-archive-description":
        return ('<div class="exist">Description de catégorie '
                '(retirée dans le nouveau modèle)</div>')

    return f'<div class="exist">widget {t} non rendu dans l’aperçu</div>'


PAGE = """<title>Aperçu Family Day entreprise</title>
<style>
@font-face{{font-family:LilitaOne;src:url("{up}/LilitaOne-Regular.woff2")
 format("woff2");font-display:swap}}
@font-face{{font-family:Raleway;src:url("{up}/raleway.regular.ttf");
 font-weight:400;font-display:swap}}
@font-face{{font-family:Raleway;src:url("{up}/raleway.heavy_.ttf");
 font-weight:600;font-display:swap}}
body{{margin:0;background:#fff;color:#222;font-family:Raleway,sans-serif}}
.wrap{{padding:0 20px 60px}}
.note{{max-width:1350px;margin:0 auto 10px;padding:14px 18px;
 background:#A2C8C8;border-radius:10px;font-size:14px}}
.h1band{{max-width:1350px;margin:30px auto 0;background:#EE743A;
 border-radius:15px;padding:10px 20px}}
.h1band h1{{color:#fff;font-family:LilitaOne,sans-serif;margin:0;
 font-size:40px;font-weight:400}}
.txt p{{margin:0 0 14px}}
.txt a{{color:#EE743A}}
.exist{{border:2px dashed #80A681;background:#f4f8f4;border-radius:10px;
 padding:14px 18px;font-size:14px;color:#3c5c3d}}
.exist code{{background:#fff;padding:1px 5px;border-radius:4px}}
.grid{{display:grid;grid-template-columns:repeat(3,1fr);gap:20px}}
.card{{background:#F6F1E5;border-radius:15px;padding:18px;font-size:14px}}
.badge{{color:#EE743A;font-weight:600;font-size:12px}}
.ttl{{font-family:LilitaOne,sans-serif;font-size:20px;margin:8px 0}}
.prix{{margin:10px 0}}
.lien{{color:#EE743A;font-weight:600}}
details summary::-webkit-details-marker{{color:#EE743A}}
@media(max-width:700px){{.grid{{grid-template-columns:1fr}}
 .h1band h1{{font-size:28px}}}}
</style>
<div class="wrap">
<div class="note"><b>Aperçu local</b> du modèle Elementor
<b>#8977 « Modèle catégorie Family Day »</b>, reconstitué à partir du JSON
réellement enregistré sur le site. Les blocs encadrés en vert sont les
éléments existants, réinsérés sans modification. Le rendu final sur
alphababy.fr reprendra les styles du thème, l’en-tête et le pied de page.
</div>
{body}
</div>
"""


def main():
    src = pathlib.Path(sys.argv[1])
    out = pathlib.Path(sys.argv[2] if len(sys.argv) > 2
                       else src.with_suffix(".preview.html"))
    data = json.loads(src.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("content", [])

    parts = []
    for el in data:
        # le premier conteneur porte le bandeau H1 orange
        flat = json.dumps(el)
        if '"header_size": "h1"' in flat or '"header_size":"h1"' in flat:
            title = ""
            def find(e):
                nonlocal title
                if st(e).get("header_size") == "h1":
                    title = st(e).get("title", "")
                for c in e.get("elements", []):
                    find(c)
            find(el)
            parts.append(f'<div class="h1band"><h1>{html.escape(title)}</h1>'
                         '</div>')
            continue
        parts.append(render(el))

    out.write_text(PAGE.format(up=UP, body="".join(parts)), encoding="utf-8")
    print(f"{out}  ({out.stat().st_size} octets)")


if __name__ == "__main__":
    main()
