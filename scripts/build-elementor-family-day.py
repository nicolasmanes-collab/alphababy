#!/usr/bin/env python3
"""Genere les JSON Elementor du contenu de la page Family Day entreprise.

Cible : alphababy.fr, Elementor 4.2.3 / Elementor Pro 4.2.2, kit global #14.
Sortie : elementor/*.json, importables via Modeles > Import de modeles.

Les blocs existants de la page (H1, description de categorie, filtres en
shortcode, loop grid des 3 formules) ne sont PAS reproduits ici : ils restent
en place dans le template d'archive, pour conserver leurs reglages exacts
(notamment l'ID de requete utilise par le formulaire de filtres).
"""
import json
import hashlib
import pathlib

OUT = pathlib.Path(__file__).resolve().parent.parent / "elementor"

# Palette du kit global #14
C_PRIMARY = "globals/colors?id=primary"        # #EE743A
C_SECONDARY = "globals/colors?id=secondary"    # #80A681
C_TEXT = "globals/colors?id=text"              # #222222
C_WHITE = "globals/colors?id=65cf053"          # #FFFFFF
BEIGE = "#F6F1E5"
ORANGE = "#EE743A"

CONTACT = "https://alphababy.fr/contact/"

_seen = set()


def eid(seed):
    """ID Elementor deterministe : 7 caracteres hexa, comme ceux du site."""
    h = hashlib.md5(seed.encode("utf-8")).hexdigest()[:7]
    i = 0
    while h in _seen:
        i += 1
        h = hashlib.md5(f"{seed}#{i}".encode("utf-8")).hexdigest()[:7]
    _seen.add(h)
    return h


def dim(top, right, bottom, left, unit="px"):
    return {
        "unit": unit, "top": str(top), "right": str(right),
        "bottom": str(bottom), "left": str(left),
        "isLinked": len({top, right, bottom, left}) == 1,
    }


def gaps(row, column=None):
    column = row if column is None else column
    return {"unit": "px", "size": row, "column": str(column),
            "row": str(row), "isLinked": row == column}


def size(px, unit="px"):
    return {"unit": unit, "size": px, "sizes": []}


def container(seed, children, *, bg=None, radius=None, padding=None,
              margin=None, gap=24, width="boxed", extra=None):
    s = {
        "content_width": width,
        "flex_direction": "column",
        "flex_gap": gaps(gap),
    }
    if bg:
        s["background_background"] = "classic"
        s["background_color"] = bg
    if radius:
        s["border_radius"] = dim(radius, radius, radius, radius)
    if padding:
        s["padding"] = dim(*padding)
    if margin:
        s["margin"] = dim(*margin)
    if extra:
        s.update(extra)
    return {
        "id": eid("con:" + seed),
        "elType": "container",
        "isInner": False,
        "settings": s,
        "elements": children,
    }


def heading(text, *, tag="h2", color=C_TEXT, font="LilitaOne", fs=32,
            fs_mobile=26, weight=None, align=None, seed=None):
    s = {
        "title": text,
        "header_size": tag,
        "typography_typography": "custom",
        "typography_font_family": font,
        "typography_font_size": size(fs),
        "typography_font_size_mobile": size(fs_mobile),
        "__globals__": {"title_color": color},
    }
    if weight:
        s["typography_font_weight"] = weight
    if align:
        s["align"] = align
    return {
        "id": eid("h:" + (seed or text)),
        "elType": "widget",
        "widgetType": "heading",
        "settings": s,
        "elements": [],
    }


def text(paragraphs, *, color=C_TEXT, align=None, seed=None):
    if isinstance(paragraphs, str):
        paragraphs = [paragraphs]
    html = "".join(f"<p>{p}</p>" for p in paragraphs)
    settings = {
            "editor": html,
            "typography_typography": "custom",
            "typography_font_family": "Raleway",
            "typography_font_size": size(17),
            "typography_line_height": {"unit": "em", "size": 1.7, "sizes": []},
            "__globals__": {"text_color": color},
    }
    if align:
        settings["align"] = align
    return {
        "id": eid("t:" + (seed or paragraphs[0][:60])),
        "elType": "widget",
        "widgetType": "text-editor",
        "settings": settings,
        "elements": [],
    }


def icon_list(items, *, icon="fas fa-check", icon_color=C_PRIMARY,
              text_color=C_TEXT, seed=""):
    repeater = []
    for it in items:
        label, url = (it if isinstance(it, tuple) else (it, None))
        entry = {
            "text": label,
            "selected_icon": {"value": icon, "library": "fa-solid"},
            "_id": eid("li:" + seed + label[:40]),
        }
        if url:
            entry["link"] = {"url": url, "is_external": "", "nofollow": "",
                             "custom_attributes": ""}
        repeater.append(entry)
    return {
        "id": eid("il:" + seed + items[0][0] if isinstance(items[0], tuple)
                  else "il:" + seed + items[0][:40]),
        "elType": "widget",
        "widgetType": "icon-list",
        "settings": {
            "icon_list": repeater,
            "space_between": size(12),
            "icon_size": size(16),
            "icon_typography_typography": "custom",
            "icon_typography_font_family": "Raleway",
            "icon_typography_font_size": size(17),
            "__globals__": {"icon_color": icon_color, "text_color": text_color},
        },
        "elements": [],
    }


def button(label, url=CONTACT, *, align="left", bg=C_PRIMARY,
           fg=C_WHITE, fg_hover=C_WHITE, seed=None):
    return {
        "id": eid("b:" + (seed or label)),
        "elType": "widget",
        "widgetType": "button",
        "settings": {
            "text": label,
            "link": {"url": url, "is_external": "", "nofollow": "",
                     "custom_attributes": ""},
            "align": align,
            "size": "md",
            "typography_typography": "custom",
            "typography_font_family": "Raleway",
            "typography_font_size": size(18),
            "typography_font_weight": "600",
            "border_radius": dim(15, 15, 15, 15),
            "text_padding": dim(16, 32, 16, 32),
            "__globals__": {
                "background_color": bg,
                "button_text_color": fg,
                "hover_color": fg_hover,
                "button_background_hover_color": C_SECONDARY,
            },
        },
        "elements": [],
    }


def accordion(pairs, *, seed="faq"):
    items, children = [], []
    for question, answer in pairs:
        items.append({
            "item_title": question,
            "_id": eid("ai:" + seed + question[:40]),
        })
        children.append({
            "id": eid("ac:" + seed + question[:40]),
            "elType": "container",
            "isInner": True,
            "settings": {"content_width": "full", "flex_gap": gaps(0)},
            "elements": [text(answer, seed="faq:" + question[:40])],
        })
    return {
        "id": eid("acc:" + seed),
        "elType": "widget",
        "widgetType": "nested-accordion",
        "settings": {
            "items": items,
            "title_tag": "h3",
            "default_state": "all_collapsed",
            "title_typography_typography": "custom",
            "title_typography_font_family": "Raleway",
            "title_typography_font_size": size(19),
            "title_typography_font_weight": "600",
            "header_padding": dim(18, 20, 18, 20),
            "content_padding": dim(0, 20, 18, 20),
            "__globals__": {"title_normal_color": C_TEXT},
        },
        "elements": children,
    }


def dump(name, title, content, doc_type="container"):
    payload = {
        "version": "0.4",
        "title": title,
        "type": doc_type,
        "content": content,
        "page_settings": [],
    }
    path = OUT / name
    path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(f"{path.relative_to(OUT.parent)}  ({path.stat().st_size} octets)")


# ---------------------------------------------------------------------------
# BLOC A : introduction, a placer sous le H1 et au-dessus des filtres
# ---------------------------------------------------------------------------
bloc_a = [
    container(
        "intro",
        [
            text([
                "Envie d’organiser un Family Day pour votre entreprise et d’offrir "
                "à vos collaborateurs et à leurs familles une vraie journée de "
                "partage, sans passer des heures à tout organiser ? AlphaBaby prend "
                "en charge l’organisation de votre Family Day de A à Z : animations, "
                "ateliers, décoration et goodies, pour un évènement d’entreprise "
                "clé en main.",
                "Chaque année, ce type d’évènement (aussi appelé Kids Day ou jour de "
                "la famille en entreprise) rassemble collaborateurs, conjoints et "
                "enfants autour d’une journée festive et conviviale. C’est devenu une "
                "véritable tradition dans la vie de nombreuses entreprises, CSE, COS "
                "et CCAS, qui y voient un moyen simple de renforcer les liens au sein "
                "de leurs équipes.",
                "Que vous souhaitiez une animation ludique dans vos locaux, un "
                "évènement en plein air ou une formule sur mesure autour du thème de "
                "votre choix, notre agence évènementielle construit avec vous le "
                "programme adapté à votre entreprise et à votre budget.",
            ], seed="intro"),
            button("Demandez votre devis gratuit", seed="cta-intro"),
        ],
        margin=(25, 0, 0, 0),
        gap=20,
    ),
]

# ---------------------------------------------------------------------------
# BLOC B : titre de section, a placer juste au-dessus de la loop grid
# ---------------------------------------------------------------------------
bloc_b = [
    container(
        "titre-formules",
        [heading("Nos formules Family Day", align="center", seed="h2-formules")],
        margin=(30, 0, 0, 0),
        gap=0,
    ),
]

# ---------------------------------------------------------------------------
# BLOC C : contenu SEO, a placer sous la loop grid
# ---------------------------------------------------------------------------
confiance = container(
    "confiance",
    [
        heading("Pourquoi les entreprises nous font confiance",
                seed="h2-confiance"),
        icon_list([
            "Une agence spécialiste de l’animation enfants depuis 1996",
            "Une note de 5/5 sur plus de 250 avis Google",
            "Des formules clé en main, de la préparation à la coordination "
            "le jour J",
            "Des animateurs professionnels, formés et passionnés",
            "Un devis personnalisé, adapté à votre budget et à vos attentes",
            "Des évènements sur mesure : Family Day, arbre de Noël, "
            "lancement de produit",
        ], seed="confiance"),
        text(
            "Notre offre s’adapte à chaque occasion et à chaque structure, avec "
            "un tarif adapté aux besoins spécifiques de votre entreprise. Dans le "
            "cadre de leur politique sociale, de nombreux CSE organisent d’ailleurs "
            "cet évènement chaque année.",
            seed="confiance-p",
        ),
    ],
    bg=BEIGE,
    radius=15,
    padding=(40, 40, 40, 40),
    margin=(0, 0, 50, 0),
    gap=20,
)

sections = [
    heading("Qu’est-ce qu’un Family Day en entreprise ?", seed="h2-definition"),
    text([
        "Un Family Day est un évènement organisé par une entreprise pour ses "
        "salariés, leurs conjoints et leurs enfants. Aussi appelé Kids Day ou "
        "journée de la famille, il consiste à ouvrir, le temps d’une journée porte "
        "ouverte, l’environnement de travail habituel aux proches des "
        "collaborateurs.",
        "Contrairement à une soirée d’entreprise classique, le Family Day place "
        "les enfants au cœur de la journée, avec un programme d’animations ludiques "
        "pensé pour tous les âges. C’est l’occasion, pour les familles, de découvrir "
        "l’entreprise, ses métiers et son quotidien, dans un cadre convivial plutôt "
        "qu’institutionnel.",
    ], seed="definition"),

    heading("Pourquoi organiser un Family Day en entreprise ?", seed="h2-pourquoi"),
    text([
        "Le Family Day n’est pas qu’une simple journée festive, à la différence "
        "d’une soirée d’entreprise classique. C’est une occasion de remercier les "
        "salariés pour leur engagement tout au long de l’année, de renforcer les "
        "liens et la cohésion au sein des équipes.",
        "Ce moment de partage crée du lien entre collaborateurs, valorise la "
        "culture d’entreprise et nourrit le sentiment d’appartenance. Il permet "
        "aussi d’associer les familles à la vie de l’entreprise et de rappeler "
        "l’attention portée à l’équilibre entre vie professionnelle et vie "
        "personnelle, ce qui contribue à l’image de l’employeur et à la motivation "
        "des équipes.",
        "Après une année de travail, il est légitime de vouloir marquer le coup. "
        "C’est une initiative corporate et fédératrice, qui réunit salariés et "
        "familles autour d’un même esprit d’équipe et d’un moment de team building. "
        "Placer chaque collaborateur au cœur de ce moment renforce sa reconnaissance "
        "et contribue à une image de marque employeur attractive. Pour beaucoup de "
        "directions, c’est autant un choix stratégique qu’un moment de plaisir "
        "partagé.",
        "Parmi les avantages d’un Family Day pour l’entreprise : un impact positif "
        "sur la marque employeur, une meilleure communication interne, un climat "
        "social apaisé et un accueil chaleureux des familles de collaborateurs qui, "
        "souvent, n’ont jamais mis les pieds dans les locaux de l’entreprise.",
    ], seed="pourquoi"),

    heading("Comment organiser un Family Day d’entreprise ?", seed="h2-comment"),
    text(
        "L’organisation d’un Family Day se prépare généralement plusieurs semaines "
        "en amont. Avec AlphaBaby, vous n’avez qu’une chose à faire : nous présenter "
        "vos besoins. Nous construisons avec vous le programme et gérons le reste.",
        seed="comment-intro",
    ),
    icon_list([
        "Définir l’objectif et le nombre de participants attendus",
        "Fixer un budget et une date",
        "Choisir un lieu adapté : locaux de l’entreprise, salle de réception ou "
        "espace extérieur",
        "Sélectionner le type d’événement et la formule souhaitée",
        "Prévoir les animations, les goodies et la décoration",
        "Confier la coordination du jour J à notre équipe",
    ], icon="fas fa-circle-check", seed="etapes"),
    text([
        "Un délai de préparation suffisant est généralement nécessaire pour gérer "
        "chaque point technique dans de bonnes conditions. Dès le premier contact, "
        "notre agence agit comme un véritable partenaire, en charge de la gestion "
        "administrative comme de la coordination logistique. Résultat : une journée "
        "sans stress, où vous profitez de l’évènement autant que vos équipes.",
        "Chaque étape est pensée pour vous simplifier la vie : de la définition du "
        "besoin jusqu’à la remise en état du lieu après l’évènement, notre équipe "
        "reste votre interlocuteur unique, du premier contact au jour J.",
    ], seed="comment-suite"),

    heading("Quelles animations pour un Family Day d’entreprise ?",
            seed="h2-animations"),
    text(
        "Le choix des animations fait toute la différence pour créer une ambiance "
        "festive et fédératrice. AlphaBaby propose plusieurs formules, à la carte "
        "ou clé en main :",
        seed="animations-intro",
    ),
    icon_list([
        ("Family Day sur mesure, une animation créée autour de vos valeurs",
         "https://alphababy.fr/family-day-sur-mesure/"),
        ("Family Day fête foraine, avec des stands de jeux façon kermesse",
         "https://alphababy.fr/family-day-une-journee-a-la-fete-foraine/"),
        ("Family Day Jeux Olympiques, avec des défis sportifs et un esprit "
         "d’équipe",
         "https://alphababy.fr/family-day-une-journee-aux-jeux-olympiques/"),
    ], seed="formules-liens"),
    text([
        "Chaque formule peut être personnalisée selon le thème et les valeurs de "
        "votre entreprise, pour un évènement unique à chaque édition. Selon vos "
        "envies, nous proposons aussi des animations sportives, des animations "
        "musicales, un atelier de sculpture de ballons ou un atelier maquillage pour "
        "les enfants, animés par une équipe habituée au jeune public. Nos ateliers "
        "créatifs peuvent également s’orienter vers la découverte, avec par exemple "
        "des ateliers sciences pour enfants, pour varier les activités enfants "
        "proposées lors de votre Family Day. Nous intervenons aussi bien pour un "
        "Family Day que pour un séminaire ou la privatisation de vos locaux.",
        "Une idée précise en tête, une question sur nos formules ou sur le prix des "
        f"animations ? <a href=\"{CONTACT}\">Contactez-nous</a>, nous construisons "
        "la formule avec vous.",
    ], seed="animations-suite"),

    heading("Quel lieu choisir pour votre Family Day ?", seed="h2-lieu"),
    text(
        "Le lieu joue un rôle essentiel dans la réussite de votre évènement. "
        "Plusieurs options s’offrent à vous selon la taille de votre entreprise et "
        "le nombre de participants :",
        seed="lieu-intro",
    ),
    icon_list([
        "Vos locaux professionnels, pour un cadre familier et chaleureux",
        "Une salle de réception privatisée, moderne et accessible",
        "Un espace extérieur ou un nouvel espace évènementiel en plein air",
        "Un parc, un jardin ou un lieu de caractère, pour une ambiance plus grande "
        "et festive",
    ], icon="fas fa-location-dot", seed="lieux"),
    text(
        "AlphaBaby vous conseille dans le choix du lieu en fonction de votre "
        "budget, de la capacité souhaitée et de vos envies. Qu’il s’agisse d’un "
        "petit comité ou d’un grand groupe, chaque participant trouve sa place. À "
        "Paris comme dans le reste de l’Île-de-France, en centre-ville comme en "
        "périphérie, ces prestations ne sont pas réservées uniquement aux grandes "
        "entreprises : nous adaptons chaque formule au public concerné et à la "
        "taille de votre structure.",
        seed="lieu-suite",
    ),

    heading("Quel budget prévoir pour un Family Day d’entreprise ?",
            seed="h2-budget"),
    text([
        "Le budget d’un Family Day varie selon plusieurs critères : le nombre de "
        "collaborateurs et de familles, le type d’animations choisi, le lieu retenu "
        "et les prestations complémentaires comme le traiteur ou les goodies. Le "
        "prix des animations dépend aussi du nombre d’animateurs mobilisés et de la "
        "durée de la prestation. Nos formules démarrent à partir de 2 500 € pour la "
        "formule Jeux Olympiques, et à partir de 3 500 € pour les formules sur "
        "mesure et fête foraine.",
        "Une organisation en amont permet de mieux anticiper les frais et d’ajuster "
        "les prestations à votre enveloppe budgétaire.",
        "AlphaBaby établit une estimation personnalisée pour chaque projet, sans "
        "engagement de votre part. Vous savez à quoi vous attendre, sans mauvaise "
        "surprise.",
    ], seed="budget"),
    button("Recevoir mon estimation gratuite", seed="cta-budget"),

    heading("Quelles idées d’activités pour un Family Day inoubliable ?",
            seed="h2-idees"),
    text(
        "Voici quelques idées de Family Day qui plaisent particulièrement aux "
        "familles :",
        seed="idees-intro",
    ),
    icon_list([
        "Stands façon kermesse (chamboule-tout, pêche aux canards, piscine à "
        "balles, mini-tournoi de football), pour une ambiance familiale et bon "
        "enfant",
        "Ateliers créatifs et ateliers découverte, à partager entre parents et "
        "enfants",
        "Olympiades d’entreprise, avec des défis sportifs par équipe",
        "Animation musicale et coin photo, pour prolonger le souvenir de la journée",
        "Structures gonflables, pour le plaisir des plus petits",
    ], icon="fas fa-star", seed="idees"),
    text(
        "Ces activités ludiques favorisent le partage et l’esprit de convivialité "
        "entre collègues et familles. Ouvertes à tous les publics, elles permettent "
        "aux plus petits comme aux plus grands de découvrir de nouvelles activités, "
        "lors d’une véritable réunion de famille au sein de l’entreprise.",
        seed="idees-suite",
    ),

    heading("Comment impliquer les collaborateurs dans un Family Day ?",
            seed="h2-impliquer"),
    text([
        "L’implication des salariés commence en amont de l’évènement, par exemple "
        "en recueillant leur avis sur le thème ou la formule via un sondage interne. "
        "Le jour J, certains collaborateurs peuvent aussi participer activement, en "
        "encadrant un atelier, en accueillant les familles à leur arrivée ou en "
        "accompagnant un groupe d’enfants tout au long du programme.",
        "Cette participation renforce le sentiment d’appartenance et transforme le "
        "Family Day en projet collectif, porté par l’équipe elle-même plutôt que "
        "subi comme un évènement organisé d’en haut.",
    ], seed="impliquer"),

    heading("Comment rendre votre Family Day mémorable ?", seed="h2-memorable"),
    text([
        "Le souvenir d’un beau Family Day se construit dans les détails : une "
        "décoration soignée, des animateurs chaleureux, des goodies personnalisés et "
        "une formule pensée pour vos valeurs.",
        "AlphaBaby veille à garantir une ambiance festive du début à la fin, avec "
        "une équipe d’intervenants professionnels qui assure la qualité et la "
        "fluidité de chaque moment. Chaque réalisation est pensée spécialement pour "
        "votre entreprise, pour de belles retrouvailles et des moments conviviaux "
        "entre collègues. Le résultat : une expérience conviviale et inoubliable, "
        "dont vos collaborateurs et leurs familles se souviendront longtemps.",
    ], seed="memorable"),

    heading("Pourquoi choisir AlphaBaby pour le Family Day de votre entreprise ?",
            seed="h2-alphababy"),
    text([
        "Depuis 1996, AlphaBaby accompagne les familles et les entreprises dans "
        "l’organisation d’évènements festifs. Notre équipe d’animateurs "
        "professionnels met son savoir-faire au service de votre Family Day, quel "
        "que soit le nombre de participants.",
        "Nos animateurs bénéficient d’une formation continue et d’un vrai "
        "savoir-faire technique, au service d’un évènement social réussi. De "
        "nombreuses entreprises et CSE nous font confiance et nous recommandent, "
        "année après année, avec une note de 5/5 sur plus de 250 avis Google.",
        "Nous proposons des formules clé en main, de la préparation à la "
        "coordination logistique, pour un évènement simple à organiser et une "
        "expérience de qualité garantie.",
        "Notre connaissance du jeune public et notre matériel (structures "
        "gonflables, stands de jeux) nous permettent de réunir collaborateurs, "
        "conjoints et enfants autour d’un évènement sans stress, avec une "
        "communication fluide à chaque étape.",
        "Découvrez aussi nos autres services pour vos évènements d’entreprise : "
        "l’<a href=\"https://alphababy.fr/entreprise-evenementiel-noel-ile-de-france/\">"
        "arbre de Noël d’entreprise</a> ou l’<a href=\""
        "https://alphababy.fr/entreprise-anniversaire-ile-de-france/\">anniversaire "
        "d’entreprise</a>.",
    ], seed="alphababy"),

    heading("Un Family Day partout en Île-de-France", seed="h2-idf"),
    text(
        "Que votre entreprise soit basée à Paris, en petite ou en grande couronne, "
        "notre agence évènementielle se déplace dans toute l’Île-de-France pour "
        "organiser votre Family Day. Nous adaptons chaque prestation à la taille de "
        "vos locaux, au nombre de participants et aux spécificités de votre secteur "
        "d’activité.",
        seed="idf",
    ),
]

corps = container(
    "corps",
    sections,
    margin=(0, 0, 50, 0),
    gap=18,
)

faq = container(
    "faq",
    [
        heading("FAQ : tout savoir sur le Family Day en entreprise",
                seed="h2-faq"),
        accordion([
            ("Comment organiser un Family Day en entreprise ?",
             "Il faut définir un objectif, un budget et une date, choisir un lieu "
             "adapté, puis sélectionner la formule et les animations souhaitées. "
             "AlphaBaby prend en charge l’organisation de bout en bout, de la "
             "préparation à la coordination le jour J, pour un évènement sans stress "
             "pour vos équipes."),
            ("Quelles animations pour un Family Day ?",
             "Family Day sur mesure, fête foraine façon kermesse ou Jeux Olympiques : "
             "les formules s’adaptent à l’âge des participants et à l’ambiance "
             "souhaitée. Chaque formule peut être complétée par des animations "
             "sportives, musicales ou créatives."),
            ("Quels sont les tarifs pour un Family Day ?",
             "Le prix des animations dépend du nombre de participants, du type de "
             "prestation et du lieu choisi. Nos formules démarrent à partir de "
             "2 500 €. Une estimation personnalisée est établie pour chaque projet, "
             "sur devis, sans engagement de votre part."),
            ("Pourquoi organiser un Family Day ?",
             "Pour remercier les salariés, renforcer les liens et la cohésion "
             "d’équipe, valoriser la culture d’entreprise et créer un moment de "
             "partage avec les familles des collaborateurs. C’est aussi un des "
             "avantages du Family Day pour l’image de l’employeur."),
            ("Quel est l’objectif d’un Family Day ?",
             "Renforcer le sentiment d’appartenance des salariés, en leur "
             "permettant, ainsi qu’à leurs familles, de vivre une journée porte "
             "ouverte au sein de l’entreprise, dans un cadre convivial plutôt "
             "qu’institutionnel, propice à la découverte de l’entreprise."),
            ("Quelles idées d’activités pour un Family Day ?",
             "Stands façon kermesse, ateliers créatifs, jeux en bois, photo souvenir "
             "ou défis sportifs en équipe : varier les activités ludiques rend "
             "l’évènement plus original et convivial, pour petits et grands."),
            ("Comment impliquer les collaborateurs dans un Family Day ?",
             "En les associant en amont au choix du thème ou de la formule, par "
             "exemple via un sondage interne, et en leur proposant de participer "
             "activement le jour J, en encadrant un atelier ou en accueillant les "
             "familles."),
            ("Comment rendre le Family Day mémorable ?",
             "En soignant la décoration, en confiant l’animation à des "
             "professionnels et en offrant des goodies personnalisés. Chaque détail, "
             "du programme au lieu choisi, contribue à créer un souvenir inoubliable "
             "pour les familles."),
        ]),
    ],
    bg=BEIGE,
    radius=15,
    padding=(40, 40, 40, 40),
    margin=(0, 0, 50, 0),
    gap=20,
)

cta_final = container(
    "cta-final",
    [
        heading("Parlons de votre Family Day", color=C_WHITE, align="center",
                seed="h2-cta"),
        text(
            "Dites-nous ce que vous avez en tête. Nous vous répondons avec un "
            "programme et un devis personnalisé, gratuit et sans engagement.",
            color=C_WHITE, align="center", seed="cta-final-p",
        ),
        button("Demander mon devis gratuit", align="center",
               bg=C_WHITE, fg=C_PRIMARY, seed="cta-final-btn"),
    ],
    bg=ORANGE,
    radius=15,
    padding=(45, 40, 45, 40),
    margin=(0, 0, 50, 0),
    gap=18,
    extra={"flex_align_items": "center"},
)

bloc_c = [confiance, corps, faq, cta_final]


if __name__ == "__main__":
    OUT.mkdir(exist_ok=True)
    dump("family-day-01-introduction.json",
         "Family Day entreprise - 01 Introduction", bloc_a)
    dump("family-day-02-titre-formules.json",
         "Family Day entreprise - 02 Titre formules", bloc_b)
    dump("family-day-03-contenu-seo.json",
         "Family Day entreprise - 03 Contenu SEO et FAQ", bloc_c)
