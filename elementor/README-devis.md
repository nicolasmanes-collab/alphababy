# Fiches produits : bouton appel + demande de devis

Objectif : ajouter en haut de chaque fiche produit deux boutons, « Une question ?
Appelez-nous » (appel direct) et « Demande de devis » (formulaire), et recevoir
les demandes sur **alphababy94@alphababy.fr**.

Page de test : `https://alphababy.fr/anniversaire-demon-hunter-kpop-ile-de-france/`
(produit `#6424`, DEMON HUNTERS KPOP).

## Ce que contient ce dossier

| Fichier | Contenu | Où il va |
|---|---|---|
| `devis-01-boutons.json` | Conteneur avec les 2 boutons | Fiche produit, juste au-dessus du bloc `page-produit` |
| `devis-02-popup.json` | Popup « Demande de devis » : titre, phrase d'accroche, formulaire | Modèles > Popups |

Générés par `scripts/build-elementor-devis.py`. Pour changer un texte, un champ
ou une couleur : éditer le script, puis le relancer.

```bash
python3 scripts/build-elementor-devis.py
```

## Contexte technique relevé sur le site

- Les fiches produits ne passent pas par un modèle Theme Builder « Produit
  unique ». Chaque produit porte son propre contenu Elementor
  (`data-elementor-type="product-post"`, `data-elementor-id="6424"`). Le bloc de
  boutons est donc à insérer **fiche par fiche**, d'où le script qui prend un ID
  de produit en argument.
- Structure du haut de la fiche `#6424` : conteneur `7b3d5cb9` (bordure beige),
  puis conteneur `d526eb2` de classe `page-produit`. Le bloc de boutons
  s'intercale entre les deux, repéré par la classe `page-produit`, pas par l'ID,
  pour rester valable sur les autres fiches.
- Elementor Pro est actif : le widget Form et les popups sont disponibles.
  Fluent Forms est aussi installé, mais le formulaire de la page Contact est un
  formulaire Elementor Pro. Le popup reste donc sur la même brique.
- Couleurs globales du kit `#14` : `primary #EE743A`, `secondary #80A681`,
  `text #222222`, blanc `65cf053`, beige `7f6e0fa`. Polices Lilita One pour les
  titres, Raleway pour le corps. Rayon 15 px. Le JSON référence les couleurs en
  globales, elles suivront le kit.

## Les deux boutons

- **Orange** : « Une question ? Appelez-nous : 01 30 10 19 10 », lien
  `tel:+33130101910`. Sur mobile, l'appel part directement.
- **Vert** : « Demande de devis », lien d'action Elementor
  `#elementor-action:action=popup:open&settings=…`. L'ID du popup est injecté au
  moment de l'insertion, il n'est pas écrit en dur dans le JSON (marqueur
  `__POPUP_ID__`).
- Côte à côte sur desktop et tablette, l'un sous l'autre sur mobile.

## Le formulaire

Champs visibles : Prénom, Nom, Email, Téléphone (obligatoires), Date de la fête,
Nombre d'enfants, Votre demande (obligatoire, en texte libre), case de
consentement.

Champ caché : `produit`, rempli par la balise dynamique « Titre de l'article ».

Envoi : action e-mail Elementor vers `alphababy94@alphababy.fr`.

- Objet : `Demande de devis : DEMON HUNTERS KPOP`
- Corps : une phrase d'introduction puis `[all-fields]`, c'est à dire tous les
  champs remplis, plus les métadonnées Date, Heure et **URL de la page**.
- `Répondre à` : l'adresse e-mail du client, pour répondre en un clic.
- L'expéditeur reste l'adresse par défaut du site, pour ne pas casser
  l'authentification SPF du domaine.

L'URL de la page est la source fiable pour savoir de quelle prestation il s'agit.
Le champ `produit` est un confort de lecture : à contrôler sur le premier envoi
de test, une balise dynamique dans un popup peut renvoyer le titre du popup au
lieu de celui du produit. Si c'est le cas, le champ est à retirer du script,
l'URL suffit.

Pas de captcha pour l'instant. Si du spam arrive, activer reCAPTCHA v3 dans
Elementor > Réglages > Intégrations, puis ajouter le champ au formulaire.

## Mise en ligne par l'API

Prérequis : un mot de passe d'application WordPress d'un compte administrateur,
dans `.env` (voir le README à la racine).

```bash
set -a && . ./.env && set +a

# 1. Diagnostic, sauvegarde de la fiche avant modification
python3 scripts/wp-devis-push.py probe 6424

# 2. Création du popup, il reste inerte à ce stade
python3 scripts/wp-devis-push.py create-popup

# 3. Publication du popup sur tout le site (il ne s'ouvre qu'au clic)
python3 scripts/wp-devis-push.py set-popup-condition <popup_id>

# 4. Insertion des boutons dans la fiche produit
python3 scripts/wp-devis-push.py insert-buttons <popup_id> 6424

# 5. Controle du rendu publie
python3 scripts/wp-devis-push.py verify 6424
```

Puis vider le cache WP Rocket et régénérer le CSS Elementor
(Elementor > Outils > Régénérer les fichiers CSS).

Retour arrière : `python3 scripts/wp-devis-push.py restore 6424` remet la fiche
telle qu'elle était, à partir de `_produit-6424-avant.json`. Le popup se
désactive en retirant sa condition d'affichage ou en le dépubliant.

## Généralisation aux autres fiches

Le popup est créé une seule fois pour tout le site. Pour chaque nouvelle fiche,
il ne reste que l'étape 4 avec le bon ID de produit :

```bash
python3 scripts/wp-devis-push.py insert-buttons <popup_id> <produit_id>
```

Le script refuse d'insérer deux fois le bloc sur la même fiche, il repère la
classe `bloc-cta-produit`.

## Procédure manuelle, si l'API n'est pas disponible

1. **Popup.** Modèles > Popups > Ajouter. Importer `devis-02-popup.json` ou
   recréer le formulaire à la main. Réglages du popup : largeur 640 px, hauteur
   ajustée au contenu, centré, bouton de fermeture, aucun déclencheur.
   Conditions d'affichage : « Tout le site ». Publier et noter l'ID du popup,
   visible dans l'URL d'édition.
2. **Boutons.** Ouvrir la fiche produit avec Elementor, insérer un conteneur en
   haut, au-dessus du bloc `page-produit`, avec les deux boutons.
   - Bouton 1, lien `tel:+33130101910`.
   - Bouton 2 : onglet Contenu > Lien, coller
     `#elementor-action:action=popup:open&settings=…`. Plus simple depuis
     l'éditeur : choisir Dynamique > Popup > Ouvrir un popup, puis sélectionner
     « Popup - Demande de devis ».
3. **Contrôles.** Envoyer une vraie demande de test et vérifier la réception sur
   `alphababy94@alphababy.fr`, l'objet, le nom de la prestation et l'URL.
4. Vider le cache WP Rocket.

## À valider

- Le libellé exact des boutons.
- La liste des champs du formulaire.
- L'adresse de réception, et si une copie doit partir vers une autre boîte.
- Faut-il aussi un e-mail de confirmation automatique au client ?
