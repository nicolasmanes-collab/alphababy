# Fiches produits : bouton appel + demande de devis

Deux boutons en haut de la fiche produit : appel direct au 01 30 10 19 10, et
« Demande de devis » qui ouvre un popup contenant un formulaire. Les demandes
partent sur **alphababy94@alphababy.fr**, et le client reçoit un accusé de
réception.

En ligne depuis le 02/09/2026 sur **30 fiches produits**, dont la fiche de
test `https://alphababy.fr/anniversaire-demon-hunter-kpop-ile-de-france/`
(produit `#6424`). Popup **#8994 « Popup - Demande de devis »**, affiché sur
tout le site, ouvert uniquement au clic. La liste des fiches traitées est dans
`elementor/fiches-traitees.txt`.

## Ce que contient ce dossier

| Fichier | Contenu | Où il va |
|---|---|---|
| `devis-01-boutons.json` | Conteneur avec les 2 boutons | Fiche produit, juste au-dessus du bloc `page-produit` |
| `devis-02-popup.json` | Popup : titre, accroche, formulaire | Modèles > Popups |
| `_produit-<id>-avant.json` | Sauvegarde de la fiche avant modification | Sert au retour arrière |

Générés par `scripts/build-elementor-devis.py`. Pour changer un texte, un champ
ou une couleur : éditer le script, le relancer, puis republier.

```bash
python3 scripts/build-elementor-devis.py
```

## Contexte technique relevé sur le site

- Les fiches produits ne passent pas par un modèle Theme Builder « Produit
  unique ». Chaque produit porte son propre contenu Elementor
  (`data-elementor-type="product-post"`). Le bloc de boutons s'insère donc
  fiche par fiche, d'où le script qui prend un ID de produit en argument.
- Sur `#6424`, le haut de page est le conteneur `7b3d5cb9` (bordure beige) puis
  le conteneur `d526eb2` de classe `page-produit`. Le bloc s'intercale entre les
  deux. Il est repéré par la classe `page-produit`, pas par l'ID, pour rester
  valable sur les autres fiches.
- Elementor Pro est actif : widget Form et popups disponibles. Fluent Forms est
  installé mais le formulaire de la page Contact est un formulaire Elementor
  Pro, on reste donc sur la même brique.
- Couleurs globales du kit `#14` : `primary #EE743A`, `secondary #80A681`,
  `text #222222`, blanc `65cf053`, beige `7f6e0fa`. Lilita One pour les titres,
  Raleway pour le corps, rayon 15 px.

### Deux contraintes qui expliquent la forme du code

**1. Le bouton devis est un widget HTML, pas un widget bouton.**

Elementor n'ouvre un popup que sur un lien dont le `href` commence par
`#elementor-action` ou `%23elementor-action` (sélecteur du module `url-actions`,
`elementor/assets/js/frontend.min.js`). Or :

- dans un widget bouton, WordPress passe l'URL par `esc_url`, qui vide le href :
  il lit `#elementor-action` comme un protocole inconnu ;
- la variante encodée `%23elementor-action%3A…` que produit l'éditeur Elementor
  est refusée par le pare-feu de l'hébergement, voir le point 2.

Le contenu d'un widget HTML est rendu tel quel, sans `esc_url`. Le lien d'action
y reste donc en clair et Elementor le reconnaît. Le style du bouton est embarqué
dans le même widget, avec les couleurs du kit en variables CSS.

**2. Le pare-feu d'o2switch bloque certaines écritures de l'API REST.**

Réponse `503` avec une page « Test de sécurité / Security check », sur
`/wp-json/wp/v2/*` comme sur `/wp-json/elementor/v1/*`, quel que soit le format
d'envoi (JSON, JSON avec `%`, formulaire encodé). Motifs relevés :

| Contenu envoyé | Résultat |
|---|---|
| Deux séquences `%XX` ou plus (`%3A`, `%3D`, `%26`) | bloqué |
| Une balise `<script>` | bloqué |
| `<a href="…">` contenant `&amp;` | bloqué |
| Le lien d'action en clair `#elementor-action:action=popup:open&settings=…` | passe |

S'y ajoutent des blocages intermittents sur des contenus anodins : en cas de
`503` ou de `Connection reset`, relancer la commande, elle finit par passer.

Si o2switch assouplit cette règle sur `/wp-json`, le bouton pourra redevenir un
widget bouton Elementor classique. Ce n'est pas nécessaire, tout fonctionne en
l'état.

## Les deux boutons

- **Orange** : « Une question ? Appelez-nous : 01 30 10 19 10 », lien
  `tel:+33130101910`. Sur mobile l'appel part directement.
- **Vert** : « Demande de devis », ouvre le popup `#8994`.
- Côte à côte sur desktop et tablette, l'un sous l'autre sur mobile.

## Le formulaire

Champs : Prénom, Nom, Email, Téléphone (obligatoires), Date de la fête, Nombre
d'enfants, Votre demande (obligatoire), case de consentement. Plus un champ
caché `produit`, rempli par la balise dynamique « Titre de l'article ».

Contrôlé sur la page en ligne : le champ caché renvoie bien `DEMON HUNTERS
KPOP`, le titre du produit, pas celui du popup.

Deux envois à la validation, dans cet ordre :

1. **Vers l'agence**, en premier
   - Destinataire principal : **`devis@alphababy.fr`**. C'est l'adresse
     prioritaire, celle à laquelle la demande doit arriver en toutes
     circonstances.
   - En copie : `alphababy94@alphababy.fr` et `nicolas.manes@seo-monkey.fr`.
   - Objet : `Demande de devis : DEMON HUNTERS KPOP`
   - Corps : une phrase d'introduction puis tous les champs, plus la date,
     l'heure et l'URL de la page d'où part la demande.
   - `Répondre à` : l'adresse du client, pour répondre en un clic.
2. **Vers le client**, en second, accusé de réception avec le récapitulatif de
   sa demande et le numéro de téléphone de l'agence.

### Ce qui protège l'adresse prioritaire

- Les trois adresses internes reçoivent **un seul message**, avec
  `devis@alphababy.fr` en destinataire principal et les deux autres en copie.
  Un seul envoi consommé sur le quota sortant de l'hébergement, au lieu de
  trois. Si un serveur destinataire refuse une adresse en copie, le message
  part quand même aux autres.
- Cet envoi est **le premier** de la file. L'accusé de réception au client part
  après : c'est lui qui saute en cas de quota atteint, pas la demande.
- Filet de sécurité indépendant du mail : Elementor **enregistre chaque
  demande** dans WordPress, dans Elementor > Envois. Même si un message se
  perd, la demande reste consultable et exportable.

Pour aller plus loin sur la fiabilité de la remise, faire partir les mails par
SMTP authentifié plutôt que par la fonction mail de l'hébergement mutualisé.
C'est le point faible restant, il ne dépend pas du formulaire.

L'expéditeur reste l'adresse par défaut du site, pour ne pas casser
l'authentification SPF du domaine.

Pas de captcha. Si du spam arrive, activer reCAPTCHA v3 dans Elementor >
Réglages > Intégrations, puis ajouter le champ au formulaire.

## Mise en ligne par l'API

Prérequis : un mot de passe d'application WordPress d'un compte administrateur,
dans `.env` (voir le README à la racine).

```bash
set -a && . ./.env && set +a

# Diagnostic, sauvegarde de la fiche avant modification
python3 scripts/wp-devis-push.py probe 6424

# Le popup, une seule fois pour tout le site
python3 scripts/wp-devis-push.py create-popup
python3 scripts/wp-devis-push.py set-popup-condition <popup_id>

# Les boutons, sur une fiche
python3 scripts/wp-devis-push.py insert-buttons <popup_id> 6424

# Controle du rendu publie
python3 scripts/wp-devis-push.py verify 6424
```

`update-popup <popup_id>` republie le contenu et les réglages du popup sans
changer son ID, après une modification du script de génération.

Chaque écriture vide les caches Elementor : les métas `_elementor_css`,
`_elementor_page_assets` et `_elementor_element_cache` de la fiche, puis le
cache global via `DELETE /wp-json/elementor/v1/cache`. Sans cela la page
continue de servir l'ancien rendu. Vider aussi WP Rocket au moindre doute.

Retour arrière : `python3 scripts/wp-devis-push.py restore 6424` remet la fiche
telle qu'elle était. Le popup se désactive en retirant sa condition d'affichage
ou en le dépubliant.

## Généralisation aux autres fiches

Le popup existe déjà, il ne reste que l'insertion du bloc. Une fiche :

```bash
python3 scripts/wp-devis-push.py insert-buttons 8994 <produit_id>
python3 scripts/wp-devis-push.py verify <produit_id>
```

Plusieurs fiches d'un coup, à partir d'un fichier d'IDs ou d'URLs, une par
ligne :

```bash
python3 scripts/wp-devis-push.py insert-batch 8994 elementor/fiches-traitees.txt
```

`insert-batch` résout les URLs en identifiants, rejoue jusqu'à 4 fois en cas de
blocage du pare-feu et affiche un bilan. Sur le lot des 30 fiches, 2 sont
passées en échec au premier tour et sont passées à la relance.

Le script refuse d'insérer deux fois le bloc sur la même fiche, il repère la
classe `bloc-cta-produit`.

## Contrôles faits

- **Les 30 pages contrôlées une par une** sur le rendu public : bloc présent,
  lien `tel:`, lien d'action du popup, formulaire, et nom de la prestation
  correct dans le champ caché. 30 sur 30 conformes.
- Rendu de la page en ligne : bloc présent, lien `tel:` correct, lien d'action
  du popup intact, popup rendu dans la page, champ `produit` rempli avec le
  titre du produit.
- Ouverture du popup au clic, vérifiée dans un navigateur sur une copie locale
  de la page servie en localhost, avec les scripts Elementor du site : le popup
  s'affiche et le formulaire est visible. Chromium ne joint pas alphababy.fr
  depuis l'environnement d'exécution, d'où la copie locale.

## Reste à faire

- Envoi de test validé le 02/09/2026 sur la fiche DEMON HUNTERS KPOP, mail bien
  reçu. À refaire après l'ajout du second destinataire, pour vérifier que la
  demande arrive aussi sur `nicolas.manes@seo-monkey.fr`.
- Décider des fiches suivantes : il reste des produits du catalogue non
  traités.
