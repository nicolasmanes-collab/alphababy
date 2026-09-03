#!/usr/bin/env python3
"""Genere les blocs Elementor « bouton appel + demande de devis » des fiches produits.

Sorties dans elementor/ :
  devis-01-boutons.json  -> conteneur a inserer en haut de la fiche produit
  devis-02-popup.json    -> contenu du popup « Demande de devis »

Le lien du bouton devis contient le marqueur __POPUP_ID__. Il est remplace par
l'ID reel du popup au moment de l'insertion (scripts/wp-devis-push.py).
"""
import base64
import json
import pathlib

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "elementor"

TELEPHONE = "01 30 10 19 10"
TEL_LIEN = "tel:+33130101910"
EMAIL_DEVIS = "alphababy94@alphababy.fr"

# Destinataire prioritaire de la demande. C'est l'adresse a laquelle le devis
# doit arriver en toutes circonstances, elle est seule en destinataire
# principal du premier envoi, qui part avant tous les autres.
EMAIL_PRIORITAIRE = "devis@alphababy.fr"
# Les autres destinataires internes, en copie du meme envoi.
EMAIL_COPIE = "alphababy94@alphababy.fr,nicolas.manes@seo-monkey.fr"

BLANC = "globals/colors?id=65cf053"
PRIMAIRE = "globals/colors?id=primary"
SECONDAIRE = "globals/colors?id=secondary"
TEXTE = "globals/colors?id=text"
BEIGE = "globals/colors?id=7f6e0fa"


# Marqueur remplace a l'insertion par scripts/wp-devis-push.py.
POPUP_PLACEHOLDER = "__POPUP_ID__"

ICONE_PATH = "M176 216h160c8.84 0 16-7.16 16-16v-16c0-8.84-7.16-16-16-16H176c-8.84 0-16 7.16-16 16v16c0 8.84 7.16 16 16 16zm-16 80c0 8.84 7.16 16 16 16h160c8.84 0 16-7.16 16-16v-16c0-8.84-7.16-16-16-16H176c-8.84 0-16 7.16-16 16v16zm96 121.13c-16.42 0-32.84-5.06-46.86-15.19L0 250.86V464c0 26.51 21.49 48 48 48h416c26.51 0 48-21.49 48-48V250.86L302.86 401.94c-14.02 10.12-30.44 15.19-46.86 15.19zm237.61-254.18c-8.85-6.94-17.24-13.47-29.61-22.81V96c0-26.51-21.49-48-48-48h-77.55c-3.04-2.2-5.87-4.26-9.04-6.56C312.6 29.17 279.2-.35 256 0c-23.2-.35-56.59 29.17-73.41 41.44-3.17 2.3-6 4.36-9.04 6.56H96c-26.51 0-48 21.49-48 48v44.14c-12.37 9.33-20.76 15.87-29.61 22.81A47.995 47.995 0 0 0 0 200.72v10.65l96 69.35V96h320v184.72l96-69.35v-10.65c0-14.74-6.78-28.67-18.39-37.77z"


def popup_link(popup_id):
    """Lien d'ouverture d'un popup Elementor Pro.

    Elementor n'ecoute que les liens dont le href commence par
    `#elementor-action` ou `%23elementor-action` (voir le selecteur du module
    url-actions dans frontend.min.js). Deux contraintes se croisent ici :

    - dans un widget bouton, WordPress passe l'URL a esc_url, qui vide le href
      parce qu'il lit `#elementor-action` comme un protocole inconnu ;
    - la variante encodee `%23elementor-action%3A...` que produit l'editeur
      Elementor est refusee en 503 par le pare-feu d'o2switch, qui bloque les
      sequences %XX multiples. Aucune route de l'API REST ne l'accepte.

    D'ou le choix d'un widget HTML : son contenu est rendu tel quel, sans
    esc_url, donc le lien d'action peut rester en clair.
    """
    reglages = json.dumps({"id": str(popup_id), "toggle": False},
                          separators=(",", ":"))
    jeton = base64.b64encode(reglages.encode("utf-8")).decode("ascii")
    return f"#elementor-action:action=popup:open&settings={jeton}"


ICONE_ENVELOPPE = ("<svg class=\"cta-devis-icone\" viewBox=\"0 0 512 512\" "
                   "width=\"20\" height=\"20\" fill=\"currentColor\" "
                   "aria-hidden=\"true\"><path d=\"__PATH__\"/></svg>")

STYLE_DEVIS = """<style>
.cta-devis{display:flex}
.cta-devis-lien{flex:1;display:inline-flex;align-items:center;
justify-content:center;gap:10px;background:var(--e-global-color-secondary,#80A681);
color:var(--e-global-color-65cf053,#fff);border-radius:15px;padding:18px 34px;
font-family:"Raleway",sans-serif;font-weight:700;font-size:18px;
line-height:1.2;text-transform:uppercase;letter-spacing:.5px;
text-align:center;text-decoration:none;transition:background .2s}
.cta-devis-lien:hover,.cta-devis-lien:focus{
background:var(--e-global-color-primary,#EE743A);
color:var(--e-global-color-65cf053,#fff)}
@media (max-width:1024px){.cta-devis-lien{font-size:16px}}
@media (max-width:767px){.cta-devis-lien{font-size:15px;padding:14px 18px}}
</style>"""


def bouton_devis_html(popup_id):
    """Bouton devis en widget HTML, seule forme qui garde le lien d'action."""
    return (STYLE_DEVIS + "<div class=\"cta-devis\">"
            f"<a class=\"cta-devis-lien\" href=\"{popup_link(popup_id)}\">"
            + ICONE_ENVELOPPE.replace("__PATH__", ICONE_PATH)
            + "<span>Demande de devis</span></a></div>")


def px(valeur, lie=True):
    return {"unit": "px", "top": str(valeur), "right": str(valeur),
            "bottom": str(valeur), "left": str(valeur), "isLinked": lie}


def padding(haut, droite, bas, gauche):
    return {"unit": "px", "top": str(haut), "right": str(droite),
            "bottom": str(bas), "left": str(gauche), "isLinked": False}


def bouton(eid, texte, lien, icone, fond, fond_survol):
    return {
        "id": eid,
        "elType": "widget",
        "widgetType": "button",
        "settings": {
            "text": texte,
            "link": {"url": lien, "is_external": "", "nofollow": "",
                     "custom_attributes": ""},
            "align": "center",
            "size": "md",
            "selected_icon": {"value": icone, "library": "fa-solid"},
            "icon_indent": {"unit": "px", "size": 10, "sizes": []},
            "typography_typography": "custom",
            "typography_font_family": "Raleway",
            "typography_font_size": {"unit": "px", "size": 18, "sizes": []},
            "typography_font_size_tablet": {"unit": "px", "size": 16,
                                            "sizes": []},
            "typography_font_size_mobile": {"unit": "px", "size": 15,
                                            "sizes": []},
            "typography_font_weight": "700",
            "typography_text_transform": "uppercase",
            "typography_letter_spacing": {"unit": "px", "size": 0.5,
                                          "sizes": []},
            "border_radius": px(15),
            "text_padding": padding(18, 34, 18, 34),
            "text_padding_mobile": padding(14, 18, 14, 18),
            "_element_width": "initial",
            "_element_custom_width": {"unit": "%", "size": 100, "sizes": []},
            "__globals__": {
                "background_color": fond,
                "button_text_color": BLANC,
                "hover_color": BLANC,
                "button_background_hover_color": fond_survol,
            },
        },
        "elements": [],
    }


def bloc_boutons():
    """Conteneur a inserer juste au-dessus du bloc produit."""
    conteneur = {
        "id": "d3v1s00",
        "elType": "container",
        "isInner": False,
        "settings": {
            "content_width": "boxed",
            "flex_direction": "row",
            "flex_direction_mobile": "column",
            "flex_justify_content": "center",
            "flex_align_items": "stretch",
            "flex_wrap": "wrap",
            "flex_gap": {"unit": "px", "size": 20, "column": "20",
                         "row": "15", "isLinked": False},
            "padding": padding(10, 20, 25, 20),
            "padding_mobile": padding(5, 15, 20, 15),
            "css_classes": "bloc-cta-produit",
        },
        "elements": [
            {
                "id": "d3v1s01",
                "elType": "container",
                "isInner": True,
                "settings": {
                    "content_width": "full",
                    "flex_direction": "column",
                    "width": {"unit": "%", "size": 48, "sizes": []},
                    "width_mobile": {"unit": "%", "size": 100, "sizes": []},
                    "padding": px(0),
                },
                "elements": [
                    bouton("d3v1s02",
                           f"Une question ? Appelez-nous : {TELEPHONE}",
                           TEL_LIEN, "fas fa-phone-alt",
                           PRIMAIRE, SECONDAIRE),
                ],
            },
            {
                "id": "d3v1s03",
                "elType": "container",
                "isInner": True,
                "settings": {
                    "content_width": "full",
                    "flex_direction": "column",
                    "width": {"unit": "%", "size": 48, "sizes": []},
                    "width_mobile": {"unit": "%", "size": 100, "sizes": []},
                    "padding": px(0),
                },
                "elements": [
                    {
                        "id": "d3v1s05",
                        "elType": "widget",
                        "widgetType": "html",
                        "settings": {
                            "html": bouton_devis_html(POPUP_PLACEHOLDER),
                        },
                        "elements": [],
                    },
                ],
            },
        ],
    }
    return {
        "version": "0.4",
        "title": "Fiche produit - boutons appel et devis",
        "type": "container",
        "content": [conteneur],
        "page_settings": [],
    }


def champ(custom_id, libelle, type_champ, largeur="100", requis=False,
          placeholder=None, extra=None):
    item = {
        "_id": custom_id,
        "custom_id": custom_id,
        "field_type": type_champ,
        "field_label": libelle,
        "width": largeur,
        "required": "true" if requis else "",
    }
    if placeholder is not None:
        item["placeholder"] = placeholder
    if extra:
        item.update(extra)
    return item


def widget_formulaire():
    champs = [
        champ("prenom", "Prénom", "text", "50", True, "Prénom *"),
        champ("nom", "Nom", "text", "50", True, "Nom *"),
        champ("email", "Email", "email", "50", True, "Email *"),
        champ("telephone", "Téléphone", "tel", "50", True, "Téléphone *"),
        champ("date_fete", "Date de la fête", "date", "50", False,
              "Date de la fête"),
        champ("nb_enfants", "Nombre d'enfants", "number", "50", False,
              "Nombre d'enfants", {"min": "1"}),
        champ("demande", "Votre demande", "textarea", "100", True,
              "Votre demande : ville, horaire souhaité, âge des enfants, "
              "options, questions…", {"rows": "4"}),
        champ("rgpd", "Consentement", "acceptance", "100", True, None, {
            "acceptance_text": "J'accepte d'être recontacté(e) par AlphaBaby "
                               "au sujet de ma demande.",
        }),
        {
            "_id": "produit",
            "custom_id": "produit",
            "field_type": "hidden",
            "field_label": "Prestation",
            "width": "100",
            "field_value": "",
            "__dynamic__": {
                "field_value": "[elementor-tag id=\"prd0001\" "
                               "name=\"post-title\" settings=\"%7B%7D\"]",
            },
        },
    ]
    return {
        "id": "d3v1s20",
        "elType": "widget",
        "widgetType": "form",
        "settings": {
            "form_name": "Demande de devis produit",
            "form_fields": champs,
            "button_text": "Envoyer ma demande",
            "button_size": "md",
            "button_width": "100",
            "button_align": "center",
            "step_next_label": "Suivant",
            "step_previous_label": "Précédent",
            "submit_actions": ["email", "email2"],
            "email_to": EMAIL_PRIORITAIRE,
            "email_cc": EMAIL_COPIE,
            "email_subject": "Demande de devis : [field id=\"produit\"]",
            "email_content": (
                "<p>Nouvelle demande de devis envoyée depuis le site.</p>"
                "[all-fields]"
            ),
            "email_content_type": "html",
            "email_from_name": "Site AlphaBaby",
            "email_reply_to": "[field id=\"email\"]",
            "form_metadata": ["date", "time", "page_url"],
            "email_to_2": "[field id=\"email\"]",
            "email_subject_2": "Votre demande de devis AlphaBaby",
            "email_content_2": (
                "<p>Bonjour [field id=\"prenom\"],</p>"
                "<p>Nous avons bien reçu votre demande de devis et nous "
                "revenons vers vous très vite.</p>"
                "<p>Voici le récapitulatif de ce que vous nous avez "
                "transmis :</p>"
                "[all-fields]"
                "<p>Une question d'ici là ? Appelez-nous au "
                f"{TELEPHONE}, du lundi au vendredi de 9h30 à 17h30.</p>"
                "<p>À très bientôt,<br>L'équipe AlphaBaby<br>"
                "Créateur de fêtes depuis 1996</p>"
            ),
            "email_content_type_2": "html",
            "email_from_name_2": "AlphaBaby",
            "email_reply_to_2": EMAIL_DEVIS,
            "form_metadata_2": [],

            "success_message": "Merci, votre demande est bien reçue. "
                               "Nous revenons vers vous très vite. Pour une "
                               f"réponse immédiate : {TELEPHONE}.",
            "error_message": "Une erreur est survenue, merci de réessayer ou "
                             f"de nous appeler au {TELEPHONE}.",
            "required_field_message": "Ce champ est obligatoire.",
            "mark_required": "yes",
            "show_labels": "",
            "field_typography_typography": "custom",
            "field_typography_font_family": "Raleway",
            "field_typography_font_size": {"unit": "px", "size": 16,
                                           "sizes": []},
            "field_border_radius": px(10),
            "button_typography_typography": "custom",
            "button_typography_font_family": "Raleway",
            "button_typography_font_size": {"unit": "px", "size": 18,
                                            "sizes": []},
            "button_typography_font_weight": "700",
            "button_typography_text_transform": "uppercase",
            "button_border_radius": px(15),
            "button_text_padding": padding(16, 30, 16, 30),
            "__globals__": {
                "button_background_color": PRIMAIRE,
                "button_text_color": BLANC,
                "button_background_hover_color": SECONDAIRE,
                "button_hover_color": BLANC,
            },
        },
        "elements": [],
    }


def bloc_popup():
    conteneur = {
        "id": "d3v1s10",
        "elType": "container",
        "isInner": False,
        "settings": {
            "content_width": "full",
            "flex_direction": "column",
            "flex_gap": {"unit": "px", "size": 12, "column": "12",
                         "row": "12", "isLinked": True},
            "padding": padding(30, 30, 30, 30),
            "padding_mobile": padding(20, 18, 20, 18),
            "border_radius": px(15),
            "background_background": "classic",
            "__globals__": {"background_color": BLANC},
        },
        "elements": [
            {
                "id": "d3v1s11",
                "elType": "widget",
                "widgetType": "heading",
                "settings": {
                    "title": "Demande de devis",
                    "header_size": "h2",
                    "align": "center",
                    "typography_typography": "custom",
                    "typography_font_family": "Lilita One",
                    "typography_font_size": {"unit": "px", "size": 32,
                                             "sizes": []},
                    "typography_font_size_mobile": {"unit": "px", "size": 26,
                                                    "sizes": []},
                    "__globals__": {"title_color": SECONDAIRE},
                },
                "elements": [],
            },
            {
                "id": "d3v1s12",
                "elType": "widget",
                "widgetType": "text-editor",
                "settings": {
                    "editor": "<p>Dites-nous en quelques mots ce que vous "
                              "souhaitez, nous vous répondons rapidement "
                              "avec un devis personnalisé.</p>",
                    "align": "center",
                    "typography_typography": "custom",
                    "typography_font_family": "Raleway",
                    "typography_font_size": {"unit": "px", "size": 16,
                                             "sizes": []},
                    "typography_line_height": {"unit": "em", "size": 1.6,
                                               "sizes": []},
                    "__globals__": {"text_color": TEXTE},
                },
                "elements": [],
            },
            widget_formulaire(),
        ],
    }
    return {
        "version": "0.4",
        "title": "Popup - Demande de devis",
        "type": "popup",
        "content": [conteneur],
        "page_settings": {
            "a11y_navigation": "yes",
            "width": {"unit": "px", "size": 640, "sizes": []},
            "width_mobile": {"unit": "vw", "size": 92, "sizes": []},
            "height": "fit_to_content",
            "horizontal_position": "center",
            "vertical_position": "center",
            "position": "center center",
            "close_button": "yes",
            
            "prevent_scroll": "yes",
            "entrance_animation": "fadeInUp",
            "entrance_animation_duration": {"unit": "px", "size": 0.6,
                                            "sizes": []},
            "overlay_background_background": "classic",
            "overlay_background_color": "rgba(0,0,0,0.6)",
            "border_radius": px(15),
            "triggers": {},
            "timing": {},
        },
    }


def main():
    OUT.mkdir(exist_ok=True)
    fichiers = {
        "devis-01-boutons.json": bloc_boutons(),
        "devis-02-popup.json": bloc_popup(),
    }
    for nom, contenu in fichiers.items():
        chemin = OUT / nom
        chemin.write_text(
            json.dumps(contenu, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8")
        print(f"  ecrit : {chemin.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
