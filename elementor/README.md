# Family Day entreprise, contenu Elementor

Contenu optimisé pour `https://alphababy.fr/entreprise/family-day/`.

## Ce que contient ce dossier

| Fichier | Contenu | Où le placer |
|---|---|---|
| `family-day-01-introduction.json` | Chapô en 3 paragraphes + bouton devis | Sous le H1, au-dessus des filtres |
| `family-day-02-titre-formules.json` | H2 « Nos formules Family Day » | Juste au-dessus de la loop grid |
| `family-day-03-contenu-seo.json` | Bloc réassurance, 11 sections H2, FAQ en accordéon, CTA final | Sous la loop grid |

Les fichiers sont générés par `scripts/build-elementor-family-day.py`.
Pour modifier un texte, éditer le script puis le relancer :

```bash
python3 scripts/build-elementor-family-day.py
```

## Contexte technique relevé sur le site

La page n'est pas une page WordPress. C'est l'archive de la catégorie produit
`family-day` (terme `#133`), rendue par le template Elementor Theme Builder
« Product Archive » `#3948`.

Ce template est partagé par toutes les catégories produits. Y ajouter le
contenu Family Day l'afficherait aussi sur les archives arbre de Noël,
anniversaire, etc. D'où la procédure de duplication ci-dessous.

Éléments du template à conserver tels quels :

- H1 `#e4addc3`, dans le bandeau orange `#b310804`
- widget « Description de l'archive » `#29df642`
- widget shortcode des filtres `#0e5ef82`
- **loop grid `#f54fd5c`** (template loop item `#1641`), qui affiche les
  3 formules Family Day. Le formulaire de filtres cible cette requête via
  l'ID de requête `products_filtered`. Recréer ce widget casserait les filtres.

Réglages du site utilisés par les JSON : kit global `#14`, couleurs
`primary #EE743A`, `secondary #80A681`, `text #222222`, beige `#F6F1E5`,
polices LilitaOne pour les H2 et Raleway pour le corps, rayon de bordure 15 px.
Les couleurs sont référencées en globales, elles suivront donc le kit.

## Etat de l'integration

Faite par API le 28/08/2026. Modele Elementor **#8977 « Modèle catégorie
Family Day »**, type `product-archive`, cree avec
`scripts/wp-elementor-push.py create-archive`.

- Contenu verifie sur le site : 70 elements, 1 H1, 15 H2, FAQ en accordeon
  de 8 questions, 5 listes a puces, 3 boutons.
- Loop grid `#f54fd5c` reinseree telle quelle : `template_id=1641`,
  `post_query_query_id='products_filtered'`, `post_query_post_type='current_query'`.
  Le formulaire de filtres continue donc de cibler la bonne requete.
- Shortcode des filtres `#0e5ef82` reinsere tel quel.
- H1 passe du titre d'archive dynamique au texte
  « Family Day en entreprise : une organisation clé en main ».
- Widget « Description de l'archive » `#29df642` retire, remplace par la
  nouvelle introduction.
- **Conditions d'affichage vides** : le modele est inerte, la page en ligne
  est inchangee tant que la condition n'est pas posee.

Sauvegarde du template d'origine `#3948` avant modification :
`elementor/_archive-3948-actuel.json`. Le template `#3948` lui-meme n'a pas
ete touche.

### Mise en ligne

```bash
set -a && . ./.env && set +a
python3 scripts/wp-elementor-push.py set-condition 8977
```

Pose la condition « Archive produits > Catégorie de produit > Family day »
(terme #133). C'est la convention deja en place sur le site : `#8975` cible
Arbre de Noel (#131), `#4392` cible Entreprise (#130), `#4385` cible En
famille (#119). Elementor donne la priorite a la condition la plus precise,
donc `#8977` prend le dessus sur `#3948` uniquement sur cette categorie.

Retour arriere : reposer des conditions vides sur `#8977`, ou depublier le
modele. La page reprend aussitot le rendu de `#3948`.

### Apercu local

```bash
python3 scripts/preview-elementor.py \
  elementor/_archive-family-day-fusionne.json apercu.html
```

Reconstitue le rendu a partir du JSON, avec les polices et la palette du kit
global. Elementor ne permet pas de previsualiser publiquement un modele de
bibliotheque.

### Reste a faire manuellement

- **Title et meta description**, dans Rank Math sur le terme de categorie :
  Produits > Categories > Family day > Modifier > onglet Rank Math.
  - Titre : `Family Day en Entreprise | Organisation Clé en Main - AlphaBaby`
  - Meta description : `Organisez le Family Day de votre entreprise avec AlphaBaby : animations, ateliers et thèmes sur mesure pour vos collaborateurs et leurs familles. Devis gratuit.`
- Vider le cache WP Rocket apres la mise en ligne.

## Procedure manuelle, si l'API n'est pas disponible

1. **Sauvegarder.** Modèles > Theme Builder > Archive produit > template
   actuel > Exporter. Conserver le fichier hors du site.

2. **Dupliquer le template.** Sur le même écran, dupliquer le template
   d'archive produit et renommer le duplicata
   « Archive produit - Family Day ».

3. **Conditions d'affichage du duplicata.** Catégorie de produit > `Family day`.
   Ne pas toucher aux conditions du template d'origine : Elementor donne la
   priorité à la condition la plus précise, les autres archives continuent
   d'utiliser le template général.

4. **Importer les blocs.** Modèles > Modèles enregistrés > Importer des
   modèles > déposer les 3 fichiers JSON.

5. **Ouvrir le duplicata dans Elementor** et faire les 3 insertions via
   l'icône dossier > Mes modèles, en respectant l'ordre du tableau ci-dessus.

6. **Mettre à jour le H1.** Cliquer sur le titre « Family day », retirer la
   balise dynamique et saisir :
   `Family Day en entreprise : une organisation clé en main`

7. **Description de catégorie.** Le widget « Description de l'archive » affiche
   encore l'ancien chapô, redondant avec la nouvelle introduction. Le supprimer
   dans le duplicata, ou remplacer le texte du terme dans
   Produits > Catégories > Family day.

8. **Ne pas modifier** le widget shortcode des filtres ni la loop grid.

9. **Title et meta description.** Produits > Catégories > Family day >
   Modifier > onglet Rank Math :
   - Titre : `Family Day en Entreprise | Organisation Clé en Main - AlphaBaby`
   - Meta description : `Organisez le Family Day de votre entreprise avec AlphaBaby : animations, ateliers et thèmes sur mesure pour vos collaborateurs et leurs familles. Devis gratuit.`

10. **Publier**, puis vider le cache WP Rocket et régénérer le CSS Elementor
    (Elementor > Outils > Régénérer les fichiers CSS).

## Points à valider avant publication

- Les mentions « atelier maquillage » et « ateliers sciences pour enfants »
  dans la section animations, ainsi que les exemples de stands
  (chamboule-tout, pêche aux canards, piscine à balles, mini-tournoi de
  football) et les « structures gonflables » dans la section idées
  d'activités : à confirmer comme prestations réellement proposées.
- Les commentaires « À valider avec vous » du brief ne sont pas dans les JSON.
- Le bloc CTA final orange « Parlons de votre Family Day » est un ajout, il ne
  figure pas dans le brief. À retirer si non souhaité.
- Les 3 liens internes ajoutés dans la liste des formules pointent vers les
  fiches produits `family-day-sur-mesure`,
  `family-day-une-journee-a-la-fete-foraine` et
  `family-day-une-journee-aux-jeux-olympiques`.
- Les boutons pointent vers `https://alphababy.fr/contact/`.
