#!/usr/bin/env python3
"""Integre le contenu Family Day dans Elementor via l'API REST de WordPress.

Le site expose les routes en ecriture d'Elementor 4.x :
  POST /wp-json/elementor/v1/template-library/templates
       -> cree un document Elementor (title, type, content)
  POST /wp-json/elementor/v1/site-editor/templates-conditions/<id>
       -> definit les conditions d'affichage d'un modele Theme Builder

Authentification par mot de passe d'application (Basic auth).
Variables attendues : WP_URL, WP_USER, WP_APP_PASSWORD.

Modes :
  probe          diagnostic en lecture seule, n'ecrit rien
  push-blocks    envoie les 3 blocs de contenu dans la bibliotheque de modeles
  create-archive cree le modele d'archive produit dedie a la categorie
                 Family day, en repartant du template #3948 existant
"""
import base64
import json
import os
import ssl
import sys
import urllib.error
import urllib.request
import pathlib

BASE = os.environ.get("WP_URL", "https://alphababy.fr").rstrip("/")
USER = os.environ.get("WP_USER", "")
APP_PASSWORD = os.environ.get("WP_APP_PASSWORD", "")

ARCHIVE_TEMPLATE_ID = 3948   # Product Archive partage par toutes les categories
LOOP_ITEM_ID = 1641          # template loop item des fiches formules
TERM_ID = 133                # categorie produit family-day

ROOT = pathlib.Path(__file__).resolve().parent.parent
ELEMENTOR_DIR = ROOT / "elementor"

CA_BUNDLE = "/root/.ccr/ca-bundle.crt"


def _ctx():
    if os.path.exists(CA_BUNDLE):
        return ssl.create_default_context(cafile=CA_BUNDLE)
    return ssl.create_default_context()


def call(method, path, payload=None, *, quiet=False):
    """Appel REST authentifie. Renvoie (code, corps decode)."""
    url = path if path.startswith("http") else f"{BASE}/wp-json{path}"
    data = None
    headers = {"Accept": "application/json"}
    if payload is not None:
        data = json.dumps(payload).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if USER and APP_PASSWORD:
        token = base64.b64encode(
            f"{USER}:{APP_PASSWORD}".encode("utf-8")).decode("ascii")
        headers["Authorization"] = f"Basic {token}"
    req = urllib.request.Request(url, data=data, headers=headers,
                                 method=method)
    try:
        with urllib.request.urlopen(req, timeout=60, context=_ctx()) as r:
            body = r.read().decode("utf-8", "replace")
            code = r.status
    except urllib.error.HTTPError as e:
        body = e.read().decode("utf-8", "replace")
        code = e.code
    except urllib.error.URLError as e:
        print(f"  RESEAU {method} {url} -> {e.reason}")
        return 0, None
    try:
        parsed = json.loads(body)
    except ValueError:
        parsed = body
    if not quiet:
        print(f"  {method} {url} -> HTTP {code}")
    return code, parsed


def require_credentials():
    if not USER or not APP_PASSWORD:
        sys.exit(
            "WP_USER et WP_APP_PASSWORD sont requis.\n"
            "  cp .env.example .env && $EDITOR .env\n"
            "  set -a && . ./.env && set +a"
        )


def load_blocks():
    """Charge les 3 fichiers JSON generes, dans l'ordre d'insertion."""
    blocks = []
    for name in sorted(ELEMENTOR_DIR.glob("family-day-*.json")):
        d = json.loads(name.read_text(encoding="utf-8"))
        blocks.append((name.name, d))
    return blocks


def extract_data(document):
    """Retrouve le tableau d'elements Elementor dans une reponse REST."""
    if not isinstance(document, dict):
        return None
    for key in ("elements", "content"):
        val = document.get(key)
        if isinstance(val, list):
            return val
    meta = document.get("meta")
    if isinstance(meta, dict):
        raw = meta.get("_elementor_data")
        if isinstance(raw, str) and raw.strip().startswith("["):
            return json.loads(raw)
        if isinstance(raw, list):
            return raw
    return None


# ---------------------------------------------------------------------------
# probe : diagnostic
# ---------------------------------------------------------------------------
def cmd_probe():
    require_credentials()
    print("== 1. Identite du compte ==")
    code, me = call("GET", "/wp/v2/users/me?context=edit")
    if code != 200:
        print("  ", json.dumps(me, ensure_ascii=False)[:400])
        sys.exit("Authentification refusee, voir scripts/wp-check.sh")
    print(f"   {me.get('slug')} / roles={me.get('roles')}")

    print("\n== 2. Lecture du template d'archive #%d ==" % ARCHIVE_TEMPLATE_ID)
    found = False
    for path in (
        f"/wp/v2/elementor_library/{ARCHIVE_TEMPLATE_ID}?context=edit",
        f"/elementor/v1/documents/{ARCHIVE_TEMPLATE_ID}",
        f"/elementor/v1/documents?ids={ARCHIVE_TEMPLATE_ID}",
    ):
        code, body = call("GET", path)
        if code != 200:
            print("  ", json.dumps(body, ensure_ascii=False)[:200])
            continue
        data = extract_data(body if not isinstance(body, list) else
                            (body[0] if body else {}))
        if data:
            print(f"   DONNEES TROUVEES : {len(data)} conteneurs racine")
            (ROOT / "elementor" / "_archive-3948-actuel.json").write_text(
                json.dumps(data, ensure_ascii=False, indent=2),
                encoding="utf-8")
            print("   sauvegarde dans elementor/_archive-3948-actuel.json")
            found = True
            break
        keys = sorted(body.keys()) if isinstance(body, dict) else type(body)
        print(f"   pas de donnees Elementor. Cles : {keys}")
    if not found:
        print("   -> repli : mode push-blocks (insertion manuelle dans"
              " l'editeur)")

    print("\n== 3. Modeles Theme Builder et conditions ==")
    call("GET", "/elementor/v1/site-editor/templates")
    code, cfg = call("GET", "/elementor/v1/site-editor/conditions-config")
    if code == 200:
        (ROOT / "elementor" / "_conditions-config.json").write_text(
            json.dumps(cfg, ensure_ascii=False, indent=2), encoding="utf-8")
        print("   format des conditions sauvegarde dans"
              " elementor/_conditions-config.json")

    print("\n== 4. Blocs a integrer ==")
    for name, d in load_blocks():
        print(f"   {name} : type={d['type']}, "
              f"{len(d['content'])} conteneur(s) racine")


# ---------------------------------------------------------------------------
# push-blocks : envoie les blocs dans la bibliotheque de modeles
# ---------------------------------------------------------------------------
def cmd_push_blocks():
    require_credentials()
    created = []
    for name, d in load_blocks():
        print(f"== {name} ==")
        payload = {
            "title": d["title"],
            "type": d.get("type", "container"),
            "content": d["content"],
        }
        code, body = call(
            "POST", "/elementor/v1/template-library/templates", payload)
        if code not in (200, 201):
            print("  ECHEC :", json.dumps(body, ensure_ascii=False)[:500])
            continue
        tid = body.get("template_id") or body.get("id") if isinstance(
            body, dict) else None
        print(f"  cree : template_id={tid}")
        created.append((d["title"], tid))
    print("\nModeles disponibles dans Elementor > Modeles > Modeles"
          " enregistres :")
    for title, tid in created:
        print(f"  #{tid}  {title}")


# ---------------------------------------------------------------------------
# create-archive : modele d'archive dedie a la categorie Family day
# ---------------------------------------------------------------------------
NEW_H1 = "Family Day en entreprise : une organisation clé en main"


def insert_content(existing):
    """Assemble le contenu du nouveau modele d'archive.

    `existing` est le tableau d'elements du template #3948. On y insere les
    blocs, on remplace le texte du H1 et on retire la description d'archive
    devenue redondante. Les widgets filtres et loop grid ne sont pas touches.
    """
    blocks = {name: d["content"] for name, d in load_blocks()}
    intro = blocks["family-day-01-introduction.json"]
    titre = blocks["family-day-02-titre-formules.json"]
    seo = blocks["family-day-03-contenu-seo.json"]

    out = json.loads(json.dumps(existing))  # copie profonde

    def walk(elements):
        for el in elements:
            yield el
            yield from walk(el.get("elements", []))

    # H1 statique a la place du titre d'archive dynamique
    for el in walk(out):
        if el.get("widgetType") == "heading" and \
                el.get("settings", {}).get("header_size") == "h1":
            el["settings"]["title"] = NEW_H1
            el["settings"].pop("__dynamic__", None)
            print(f"  H1 #{el['id']} remplace")
            break

    # Reperage du conteneur qui porte les filtres et la loop grid
    host = None
    for el in walk(out):
        kids = el.get("elements", [])
        types = [k.get("widgetType") for k in kids]
        if "loop-grid" in types:
            host = el
            break
    if host is None:
        raise SystemExit("loop grid introuvable dans le template #3948")

    kids = host["elements"]
    types = [k.get("widgetType") for k in kids]
    i_loop = types.index("loop-grid")

    # description d'archive retiree : remplacee par la nouvelle introduction
    if "woocommerce-archive-description" in types:
        j = types.index("woocommerce-archive-description")
        removed = kids.pop(j)
        print(f"  widget description d'archive #{removed['id']} retire")
        types.pop(j)
        i_loop -= 1

    i_filters = types.index("shortcode") if "shortcode" in types else -1
    at_intro = i_filters if i_filters >= 0 else i_loop
    host["elements"] = (
        kids[:at_intro] + intro
        + kids[at_intro:i_loop] + titre
        + [kids[i_loop]] + seo
        + kids[i_loop + 1:]
    )
    print(f"  introduction inseree en position {at_intro}")
    print(f"  titre formules insere avant la loop grid #{kids[i_loop]['id']}")
    print(f"  contenu SEO insere apres la loop grid")
    return out


def cmd_create_archive():
    require_credentials()
    src = ELEMENTOR_DIR / "_archive-3948-actuel.json"
    if not src.exists():
        sys.exit("Lancer d'abord : wp-elementor-push.py probe\n"
                 "Le contenu du template #3948 doit etre lisible.")
    existing = json.loads(src.read_text(encoding="utf-8"))

    print("== Assemblage du contenu ==")
    content = insert_content(existing)
    out = ELEMENTOR_DIR / "_archive-family-day-fusionne.json"
    out.write_text(json.dumps(content, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    print(f"  contenu fusionne : {out.relative_to(ROOT)}")

    if "--dry-run" in sys.argv:
        print("\n--dry-run : rien n'a ete envoye au site.")
        return

    print("\n== Creation du modele d'archive ==")
    code, body = call("POST", "/elementor/v1/template-library/templates", {
        "title": "Archive produit - Family Day",
        "type": "product-archive",
        "content": content,
    })
    if code not in (200, 201):
        sys.exit("ECHEC : " + json.dumps(body, ensure_ascii=False)[:600])
    tid = body.get("template_id") or body.get("id")
    print(f"  modele cree : #{tid}")
    print("\nProchaine etape : definir la condition d'affichage sur la"
          f" categorie produit #{TERM_ID}, puis publier le modele.")
    print("Elementor > Modeles > Theme Builder > Archive produit >"
          " 'Archive produit - Family Day' > Conditions d'affichage.")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "probe"
    {
        "probe": cmd_probe,
        "push-blocks": cmd_push_blocks,
        "create-archive": cmd_create_archive,
    }.get(mode, lambda: sys.exit(f"mode inconnu : {mode}"))()
