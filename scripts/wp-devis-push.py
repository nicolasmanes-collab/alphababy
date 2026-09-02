#!/usr/bin/env python3
"""Met en ligne les boutons « appel » et « demande de devis » d'une fiche produit.

Etapes, dans l'ordre :

  probe [id]            diagnostic en lecture seule, sauvegarde la fiche
  create-popup          cree le popup « Demande de devis » (inerte tant qu'il
                        n'a pas de condition d'affichage)
  set-popup-condition N publie le popup sur tout le site
  insert-buttons N [id] insere le bloc de boutons en haut de la fiche produit,
                        avec le lien d'ouverture du popup N
  restore [id]          remet la fiche produit dans son etat sauvegarde
  verify [id]           relit la page publiee et controle le rendu

Authentification par mot de passe d'application (Basic auth).
Variables attendues : WP_URL, WP_USER, WP_APP_PASSWORD.
"""
import base64
import json
import os
import re
import ssl
import sys
import urllib.error
import urllib.request
import pathlib

BASE = os.environ.get("WP_URL", "https://alphababy.fr").rstrip("/")
USER = os.environ.get("WP_USER", "")
APP_PASSWORD = os.environ.get("WP_APP_PASSWORD", "")

PRODUIT_TEST = 6424          # DEMON HUNTERS KPOP
CLASSE_BLOC_PRODUIT = "page-produit"
CLASSE_BLOC_CTA = "bloc-cta-produit"
POPUP_PLACEHOLDER = "__POPUP_ID__"

ROOT = pathlib.Path(__file__).resolve().parent.parent
ELEMENTOR_DIR = ROOT / "elementor"
CA_BUNDLE = "/root/.ccr/ca-bundle.crt"


def _ctx():
    if os.path.exists(CA_BUNDLE):
        return ssl.create_default_context(cafile=CA_BUNDLE)
    return ssl.create_default_context()


def call(method, path, payload=None, *, quiet=False):
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
        with urllib.request.urlopen(req, timeout=90, context=_ctx()) as r:
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
        sys.exit("WP_USER et WP_APP_PASSWORD sont requis.\n"
                 "  cp .env.example .env, renseigner, puis\n"
                 "  set -a && . ./.env && set +a")


def produit_id(position=2):
    """ID de fiche produit passe en argument, sinon la fiche de test."""
    if len(sys.argv) > position and sys.argv[position].isdigit():
        return int(sys.argv[position])
    return PRODUIT_TEST


def charger(nom):
    return json.loads((ELEMENTOR_DIR / nom).read_text(encoding="utf-8"))


def sauvegarde_path(pid):
    return ELEMENTOR_DIR / f"_produit-{pid}-avant.json"


# ---------------------------------------------------------------------------
# lecture / ecriture du contenu Elementor d'une fiche produit
# ---------------------------------------------------------------------------
def lire_donnees(pid):
    """Renvoie (elements, source) ou (None, None)."""
    code, body = call("GET", f"/wp/v2/product/{pid}?context=edit")
    if code == 200 and isinstance(body, dict):
        brut = (body.get("meta") or {}).get("_elementor_data")
        if isinstance(brut, str) and brut.strip().startswith("["):
            return json.loads(brut), "wp/v2"
        if isinstance(brut, list):
            return brut, "wp/v2"
        print(f"   meta exposees : {sorted((body.get('meta') or {}).keys())}")

    code, body = call("GET", f"/wc/v3/products/{pid}")
    if code == 200 and isinstance(body, dict):
        for m in body.get("meta_data", []):
            if m.get("key") == "_elementor_data":
                val = m.get("value")
                if isinstance(val, str):
                    return json.loads(val), "wc/v3"
                if isinstance(val, list):
                    return val, "wc/v3"
        cles = [m.get("key") for m in body.get("meta_data", [])]
        print(f"   meta_data WooCommerce : {cles}")
    return None, None


def ecrire_donnees(pid, elements, source):
    """Ecrit _elementor_data et vide le CSS genere pour forcer sa regeneration."""
    brut = json.dumps(elements, ensure_ascii=False, separators=(",", ":"))
    if source == "wp/v2":
        code, body = call("POST", f"/wp/v2/product/{pid}",
                          {"meta": {"_elementor_data": brut,
                                    "_elementor_css": ""}})
    else:
        code, body = call("PUT", f"/wc/v3/products/{pid}", {"meta_data": [
            {"key": "_elementor_data", "value": brut},
            {"key": "_elementor_css", "value": ""},
        ]})
    if code not in (200, 201):
        print("  ", json.dumps(body, ensure_ascii=False)[:600])
        return False
    return True


def aplatir(elements, sortie=None):
    sortie = [] if sortie is None else sortie
    for el in elements:
        sortie.append(el)
        aplatir(el.get("elements", []), sortie)
    return sortie


def position_insertion(elements):
    """Index du bloc produit principal, ou 1 par defaut."""
    for i, el in enumerate(elements):
        classes = (el.get("settings") or {}).get("_css_classes", "")
        if CLASSE_BLOC_PRODUIT in classes:
            return i
    return min(1, len(elements))


def deja_present(elements):
    return any(CLASSE_BLOC_CTA in ((el.get("settings") or {})
               .get("_css_classes", "")) for el in aplatir(elements))


def injecter_popup_id(bloc, popup_id):
    """Remplace le marqueur du lien popup par l'ID reel."""
    lien = base64.b64encode(
        json.dumps({"id": str(popup_id), "toggle": False},
                   separators=(",", ":")).encode("utf-8")).decode("ascii")
    brut = json.dumps(bloc, ensure_ascii=False)
    ancien = base64.b64encode(
        json.dumps({"id": POPUP_PLACEHOLDER, "toggle": False},
                   separators=(",", ":")).encode("utf-8")).decode("ascii")
    brut = brut.replace(ancien, lien)
    if lien not in brut:
        sys.exit("marqueur __POPUP_ID__ introuvable dans le bloc de boutons")
    return json.loads(brut)


# ---------------------------------------------------------------------------
# commandes
# ---------------------------------------------------------------------------
def cmd_probe():
    require_credentials()
    pid = produit_id()
    print("== 1. Identite du compte ==")
    code, me = call("GET", "/wp/v2/users/me?context=edit")
    if code != 200:
        print("  ", json.dumps(me, ensure_ascii=False)[:400])
        sys.exit("Authentification refusee, voir scripts/wp-check.sh")
    print(f"   {me.get('slug')} / roles={me.get('roles')}")

    print(f"\n== 2. Lecture de la fiche produit #{pid} ==")
    elements, source = lire_donnees(pid)
    if not elements:
        sys.exit("   contenu Elementor illisible par l'API : passer par la"
                 " procedure manuelle (elementor/README-devis.md)")
    print(f"   source : {source}, {len(elements)} conteneurs racine")
    for i, el in enumerate(elements):
        classes = (el.get("settings") or {}).get("_css_classes", "")
        print(f"     [{i}] #{el.get('id')} {el.get('elType')} {classes}")
    print(f"   bloc CTA deja present : {deja_present(elements)}")
    print(f"   insertion prevue en position {position_insertion(elements)}")
    chemin = sauvegarde_path(pid)
    chemin.write_text(json.dumps(elements, ensure_ascii=False, indent=2),
                      encoding="utf-8")
    print(f"   sauvegarde : {chemin.relative_to(ROOT)}")

    print("\n== 3. Popups existants ==")
    code, body = call("GET", "/wp/v2/elementor_library?elementor_library_type"
                             "=popup&per_page=50&context=edit")
    if code == 200 and isinstance(body, list):
        for t in body:
            titre = (t.get("title") or {}).get("rendered", "")
            print(f"     #{t.get('id')} {titre}")


def cmd_create_popup():
    require_credentials()
    popup = charger("devis-02-popup.json")
    if "--dry-run" in sys.argv:
        print(json.dumps(popup, ensure_ascii=False, indent=2)[:1500])
        return
    code, body = call("POST", "/elementor/v1/template-library/templates", {
        "title": popup["title"],
        "type": "popup",
        "content": popup["content"],
        "page_settings": popup["page_settings"],
    })
    if code not in (200, 201):
        sys.exit("ECHEC : " + json.dumps(body, ensure_ascii=False)[:600])
    tid = body.get("template_id") or body.get("id")
    print(f"\n  popup cree : #{tid}")
    print("  il reste inerte tant que la condition d'affichage n'est pas"
          " posee :")
    print(f"    python3 scripts/wp-devis-push.py set-popup-condition {tid}")


def cmd_set_popup_condition():
    require_credentials()
    if len(sys.argv) < 3:
        sys.exit("usage : wp-devis-push.py set-popup-condition <popup_id>")
    tid = sys.argv[2]
    code, body = call(
        "PUT", f"/elementor/v1/site-editor/templates-conditions/{tid}",
        {"conditions": [{"type": "include", "name": "general"}]})
    print("  ", json.dumps(body, ensure_ascii=False)[:400])
    if code not in (200, 201):
        sys.exit("ECHEC de la pose de condition")
    print("\n  popup affichable sur tout le site, ouvert uniquement par le"
          " bouton.")


def cmd_insert_buttons():
    require_credentials()
    if len(sys.argv) < 3 or not sys.argv[2].isdigit():
        sys.exit("usage : wp-devis-push.py insert-buttons <popup_id> "
                 "[produit_id]")
    popup_id = sys.argv[2]
    pid = produit_id(3)

    elements, source = lire_donnees(pid)
    if not elements:
        sys.exit("contenu Elementor illisible")
    chemin = sauvegarde_path(pid)
    if not chemin.exists():
        chemin.write_text(json.dumps(elements, ensure_ascii=False, indent=2),
                          encoding="utf-8")
        print(f"  sauvegarde : {chemin.relative_to(ROOT)}")
    if deja_present(elements):
        sys.exit("le bloc de boutons est deja present sur cette fiche")

    bloc = injecter_popup_id(charger("devis-01-boutons.json")["content"],
                             popup_id)
    pos = position_insertion(elements)
    fusion = elements[:pos] + bloc + elements[pos:]
    print(f"  insertion en position {pos}, "
          f"{len(elements)} -> {len(fusion)} conteneurs racine")
    if "--dry-run" in sys.argv:
        print("  --dry-run : rien n'a ete envoye.")
        return
    if not ecrire_donnees(pid, fusion, source):
        sys.exit("ECHEC de l'ecriture")
    print(f"\n  fiche #{pid} mise a jour.")
    print("  vider le cache WP Rocket, puis :")
    print(f"    python3 scripts/wp-devis-push.py verify {pid}")


def cmd_restore():
    require_credentials()
    pid = produit_id()
    chemin = sauvegarde_path(pid)
    if not chemin.exists():
        sys.exit(f"pas de sauvegarde : {chemin}")
    elements = json.loads(chemin.read_text(encoding="utf-8"))
    _, source = lire_donnees(pid)
    if not source:
        sys.exit("contenu Elementor illisible")
    if not ecrire_donnees(pid, elements, source):
        sys.exit("ECHEC de la restauration")
    print(f"  fiche #{pid} restauree depuis {chemin.relative_to(ROOT)}")


def cmd_verify():
    """Relit la page publiee. Accepte un ID de produit ou une URL."""
    url = None
    pid = produit_id()
    for arg in sys.argv[2:]:
        if arg.startswith("http"):
            url = arg
    if not url:
        code, body = call("GET", f"/wc/v3/products/{pid}", quiet=True)
        if code == 200 and isinstance(body, dict):
            url = body.get("permalink")
    if not url:
        sys.exit("URL introuvable : passer l'URL de la fiche en argument")
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=90, context=_ctx()) as r:
        html = r.read().decode("utf-8", "replace")
    print(f"  page : {url} ({len(html)} octets)")
    print(f"  bloc CTA           : {CLASSE_BLOC_CTA in html}")
    print(f"  lien telephone     : {'tel:+33130101910' in html}")
    print(f"  action popup       : "
          f"{'elementor-action%3Aaction%3Dpopup' in html or 'popup:open' in html}")
    print(f"  formulaire devis   : {'Demande de devis' in html}")
    ids = set(re.findall(r'data-id="([0-9a-z]+)"', html))
    print(f"  IDs de widgets     : {len(ids)} uniques")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "probe"
    {
        "probe": cmd_probe,
        "create-popup": cmd_create_popup,
        "set-popup-condition": cmd_set_popup_condition,
        "insert-buttons": cmd_insert_buttons,
        "restore": cmd_restore,
        "verify": cmd_verify,
    }.get(mode, lambda: sys.exit(f"mode inconnu : {mode}"))()
