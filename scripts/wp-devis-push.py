#!/usr/bin/env python3
"""Met en ligne les boutons « appel » et « demande de devis » d'une fiche produit.

Etapes, dans l'ordre :

  probe [id]            diagnostic en lecture seule, sauvegarde la fiche
  create-popup          cree le popup « Demande de devis » (inerte tant qu'il
                        n'a pas de condition d'affichage)
  set-popup-condition N publie le popup sur tout le site
  update-popup N        remet a jour le contenu du popup N
  insert-buttons N [id] insere le bloc de boutons en haut de la fiche produit,
                        avec le lien d'ouverture du popup N
  insert-batch N f      insere le bloc sur toutes les fiches listees dans le
                        fichier f, un ID ou une URL par ligne
  restore [id]          remet la fiche produit dans son etat sauvegarde
  verify [id]           relit la page publiee et controle le rendu

Authentification par mot de passe d'application (Basic auth).
Variables attendues : WP_URL, WP_USER, WP_APP_PASSWORD.
"""
import base64
import importlib.util
import json
import os
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
import pathlib

BASE = os.environ.get("WP_URL", "https://alphababy.fr").rstrip("/")
USER = os.environ.get("WP_USER", "")
APP_PASSWORD = os.environ.get("WP_APP_PASSWORD", "")

PRODUIT_TEST = 6424          # DEMON HUNTERS KPOP
CLASSE_BLOC_PRODUIT = "page-produit"
CLASSE_BLOC_CTA = "bloc-cta-produit"

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
_spec = importlib.util.spec_from_file_location(
    "builder", pathlib.Path(__file__).resolve().parent
    / "build-elementor-devis.py")
builder = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(builder)

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
    vider_caches(pid)
    return True


def vider_caches(pid):
    """Supprime le HTML et le CSS pre-calcules par Elementor pour cette fiche.

    Sans cela, la page continue de servir l'ancien rendu : Elementor met en
    cache le HTML des elements dans _elementor_element_cache.
    """
    cibles = {"_elementor_element_cache", "_elementor_css",
              "_elementor_page_assets"}
    code, body = call("GET", f"/wc/v3/products/{pid}", quiet=True)
    if code != 200 or not isinstance(body, dict):
        print("   caches Elementor non vides : lecture WooCommerce refusee")
        return False
    payload = [{"key": md["key"], "id": md["id"], "value": None}
               for md in body.get("meta_data", []) if md.get("key") in cibles]
    restant = []
    if payload:
        code, body = call("PUT", f"/wc/v3/products/{pid}",
                          {"meta_data": payload}, quiet=True)
        restant = [md.get("key") for md in body.get("meta_data", [])
                   if md.get("key") in cibles] \
            if isinstance(body, dict) else ["?"]
        print(f"   caches de la fiche vides : {[m['key'] for m in payload]}"
              f"{' RESTANT ' + str(restant) if restant else ''}")
    vider_cache_global()
    return not restant


def vider_cache_global():
    """Purge le cache Elementor du site (CSS et HTML pre-calcules)."""
    code, _ = call("DELETE", "/elementor/v1/cache", quiet=True)
    print(f"   cache Elementor du site : "
          f"{'vide' if code == 200 else 'echec HTTP ' + str(code)}")
    return code == 200


def aplatir(elements, sortie=None):
    sortie = [] if sortie is None else sortie
    for el in elements:
        sortie.append(el)
        aplatir(el.get("elements", []), sortie)
    return sortie


def classes_de(el):
    """Classes CSS d'un element. Les conteneurs utilisent css_classes,
    les widgets _css_classes. Un element sans reglage renvoie une liste."""
    reglages = el.get("settings")
    if not isinstance(reglages, dict):
        return ""
    valeurs = [reglages.get("css_classes"), reglages.get("_css_classes")]
    return " ".join(v for v in valeurs if isinstance(v, str))


def position_insertion(elements):
    """Index du bloc produit principal, ou 1 par defaut."""
    for i, el in enumerate(elements):
        if CLASSE_BLOC_PRODUIT in classes_de(el):
            return i
    return min(1, len(elements))


def deja_present(elements):
    return any(CLASSE_BLOC_CTA in classes_de(el) for el in aplatir(elements))


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
        print(f"     [{i}] #{el.get('id')} {el.get('elType')} "
              f"{classes_de(el)}")
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


def cmd_update_popup():
    """Reecrit le contenu d'un popup deja cree, sans changer son ID."""
    require_credentials()
    if len(sys.argv) < 3 or not sys.argv[2].isdigit():
        sys.exit("usage : wp-devis-push.py update-popup <popup_id>")
    tid = sys.argv[2]
    popup = charger("devis-02-popup.json")
    brut = json.dumps(popup["content"], ensure_ascii=False,
                      separators=(",", ":"))
    code, body = call("POST", f"/wp/v2/elementor_library/{tid}",
                      {"meta": {"_elementor_data": brut,
                                "_elementor_page_settings":
                                    popup["page_settings"]}})
    if code not in (200, 201):
        sys.exit("ECHEC : " + json.dumps(body, ensure_ascii=False)[:600])
    vider_cache_global()
    print(f"  popup #{tid} mis a jour")


def personnaliser_bloc(bloc, popup_id):
    """Remplace le marqueur par le lien d'ouverture du popup reel."""
    ancien = builder.popup_link(builder.POPUP_PLACEHOLDER)
    nouveau = builder.popup_link(popup_id)
    brut = json.dumps(bloc, ensure_ascii=False).replace(ancien, nouveau)
    if nouveau not in brut:
        sys.exit("lien marqueur introuvable dans le bloc de boutons")
    return json.loads(brut)


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

    bloc = personnaliser_bloc(charger("devis-01-boutons.json")["content"],
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


def inserer_sur(pid, popup_id, essais=4):
    """Insere le bloc sur une fiche. Rejoue en cas de blocage du pare-feu."""
    for essai in range(essais):
        elements, source = lire_donnees(pid)
        if not elements:
            return "illisible"
        if deja_present(elements):
            return "deja present"
        chemin = sauvegarde_path(pid)
        if not chemin.exists():
            chemin.write_text(json.dumps(elements, ensure_ascii=False,
                                         indent=2), encoding="utf-8")
        bloc = personnaliser_bloc(charger("devis-01-boutons.json")["content"],
                                  popup_id)
        pos = position_insertion(elements)
        if ecrire_donnees(pid, elements[:pos] + bloc + elements[pos:], source):
            return "ok"
        time.sleep(6 * (essai + 1))
    return "echec"


def resoudre(reference):
    """Accepte un ID, un slug ou une URL. Renvoie l'ID du contenu."""
    reference = reference.strip().rstrip("/")
    if reference.isdigit():
        return int(reference)
    slug = reference.split("/")[-1]
    for typ in ("product", "pages", "posts"):
        for essai in range(3):
            code, body = call("GET", f"/wp/v2/{typ}?slug={slug}", quiet=True)
            if code == 200 and isinstance(body, list):
                if body:
                    return body[0]["id"]
                break
            time.sleep(4)
    return None


def cmd_insert_batch():
    require_credentials()
    if len(sys.argv) < 4 or not sys.argv[2].isdigit():
        sys.exit("usage : wp-devis-push.py insert-batch <popup_id> "
                 "<fichier_de_references>")
    popup_id = sys.argv[2]
    lignes = [l.strip() for l in pathlib.Path(sys.argv[3])
              .read_text(encoding="utf-8").splitlines() if l.strip()]
    resultats = {}
    for i, ref in enumerate(lignes, 1):
        pid = resoudre(ref)
        if not pid:
            resultats[ref] = "introuvable"
        else:
            resultats[ref] = inserer_sur(pid, popup_id)
        print(f"  [{i}/{len(lignes)}] {ref} -> #{pid} : {resultats[ref]}")
        time.sleep(2)
    print("\n== Bilan ==")
    for etat in sorted(set(resultats.values())):
        noms = [r for r, e in resultats.items() if e == etat]
        print(f"  {etat} : {len(noms)}")
        if etat not in ("ok", "deja present"):
            for n in noms:
                print(f"     {n}")


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
    marqueurs = {
        "bloc CTA": CLASSE_BLOC_CTA in html,
        "lien telephone": "tel:+33130101910" in html,
        "lien d'action popup": 'href="#elementor-action:action=popup:open'
                               in html,
        "popup rendu": 'data-elementor-type="popup"' in html,
        "formulaire": 'name="Demande de devis produit"' in html,
    }
    for nom, present in marqueurs.items():
        print(f"  {nom:22}: {present}")
    motif = r'name="form_fields\[produit\]"[^>]*value="([^"]*)"'
    trouve = re.search(motif, html)
    print(f"  {'prestation transmise':22}: "
          f"{trouve.group(1) if trouve else 'ABSENTE'}")


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "probe"
    {
        "probe": cmd_probe,
        "create-popup": cmd_create_popup,
        "update-popup": cmd_update_popup,
        "set-popup-condition": cmd_set_popup_condition,
        "insert-buttons": cmd_insert_buttons,
        "insert-batch": cmd_insert_batch,
        "restore": cmd_restore,
        "verify": cmd_verify,
    }.get(mode, lambda: sys.exit(f"mode inconnu : {mode}"))()
