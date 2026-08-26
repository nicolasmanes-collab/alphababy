# Images manquantes sur alphababy.fr

Diagnostic du 26/08/2026.

## Symptome

De nombreuses images ne s'affichent pas, sur presque toutes les pages.

## Cause

Ce n'est pas un defaut d'affichage, c'est un desaccord entre la base de
donnees et le disque. La mediatheque pointe vers des fichiers qui ne sont pas
la ou elle les cherche.

Une conversion WebP est passee sur le site. Elle a converti les fichiers sur
le disque et supprime les originaux, mais la correspondance en base n'a ete
mise a jour que partiellement. Trois situations coexistent :

| Cas | La base declare | Le disque contient | Reparable |
|---|---|---|---|
| A | `image.jpeg` | `image.webp` | oui, en base |
| B | `image.webp` | `image.jpg` ou `image.png` | oui, en base |
| C | `image.webp` | rien | non, restauration |

Les cas A et B sont des erreurs de nom : le fichier existe, WordPress le
cherche sous la mauvaise extension. Le cas C correspond a des fichiers
reellement absents du disque.

Le plugin « Image Optimization - Optimize Images and Convert WebP » 1.7.6 est
installe et **desactive**. C'est le suspect le plus coherent avec ce que l'on
observe, mais l'attribution n'est pas prouvee : rien dans les donnees
accessibles a distance ne permet de dire avec certitude quel outil a fait
quoi, ni quand. « Better Search Replace » est egalement actif et permet ce
type de remplacement en masse.

## Pourquoi c'est reste invisible

Rank Math redirige toutes les 404 du site vers la page d'accueil :

```
GET /nimporte-quoi          ->  301
location: https://alphababy.fr
x-redirect-by: Rank Math
```

Une image manquante ne renvoie donc pas une erreur franche, elle renvoie 200
et du HTML. Rien n'apparait dans les journaux d'erreur et les verificateurs
de liens ne signalent rien. C'est aussi mauvais pour le referencement :
Google traite ces redirections comme des soft 404.

## Mesures

Rendu et crawl des 166 URL des sitemaps, puis test de chaque image referencee.

| Mesure | Valeur |
|---|---|
| Pages parcourues | 166 |
| Pages avec au moins une image cassee | 163 |
| Fichiers manquants distincts referencees | 119 |
| Emplacements d'images casses | 1262 |

Repartition de ces 119 fichiers :

| Cas | Fichiers | Emplacements |
|---|---|---|
| Reparables en base (cas A et B) | 36 | 684 |
| A restaurer depuis une sauvegarde (cas C) | 83 | 578 |

Le script repare donc un peu plus de la moitie des emplacements casses sans
qu'aucun fichier n'ait besoin d'etre restaure.

Les 83 fichiers perdus se concentrent sur quelques dossiers :
`2025/09` (24), `2025/08` (20), `2026/01` (17), `2024/04` (9), `2023/10` (7).

Les fichiers les plus penalisants sont ceux des gabarits partages, presents
sur presque toutes les pages :

| Pages | Fichier | Role probable |
|---|---|---|
| 163 | `2023/10/IMG_2614-scaled.jpeg` | gabarit global |
| 163 | `2025/07/ALPHA-SPECTACLE-scaled-1-scaled.webp` | gabarit global |
| 76 | `2023/10/enfants.webp` | bloc de reassurance |
| 76 | `2023/10/horaires.webp` | bloc de reassurance |
| 75 | `2023/10/reserver.webp` | bloc de reassurance |
| 25 | `2025/08/{INFOVISTA,vancleff,appen,mediamatrie}.webp` | carrousel logos clients |

Reparer une dizaine de fichiers corrige donc la majeure partie du visible.

## Correctifs

### 1. Cas A et B, en base

```bash
# inventaire, n'ecrit rien
wp eval-file wordpress/scripts/audit-medias.php

# applique les corrections
wp eval-file wordpress/scripts/audit-medias.php -- --apply
```

Le script cherche, pour chaque attachment dont le fichier declare est absent,
le meme nom sous une autre extension. S'il le trouve il corrige
`_wp_attached_file`, les tailles derivees et `post_mime_type`. Il ecrit deux
CSV dans les uploads, les recuperables et les perdus.

Lance sur le serveur, il lit le disque directement : son inventaire est
exhaustif, contrairement a un test a distance que le pare-feu de
l'hebergeur limite.

Vider le cache WP Rocket ensuite.

### 2. Cas C, restauration

Les fichiers du CSV `audit-medias-perdus.csv` doivent etre restaures depuis
une sauvegarde. Ils sont regroupes par dossier, une restauration ciblee de
`wp-content/uploads/2023/10`, `2025/07` et `2025/08` couvre l'essentiel du
visible. Duplicator Pro est installe sur le site, et l'hebergeur o2switch
conserve ses propres sauvegardes.

### 3. Retablir les 404

Rank Math, General Settings, Redirections, « Fallback behavior » : repasser
sur « Default (404) » au lieu de la redirection vers l'accueil.

A faire apres la restauration, pas avant : sinon les images encore manquantes
passeront de « page d'accueil renvoyee en 200 » a « 404 franche », ce qui est
plus correct mais rend le probleme visible dans les outils de suivi tant qu'il
n'est pas regle.

### 4. Les SVG

20 fichiers `.svg` ont ete convertis en `.webp`. Un SVG est vectoriel, sa
version WebP est matricielle donc floue au-dela de sa taille de conversion.
Le script les fera reapparaitre, mais en qualite degradee. Pour des logos ou
des pictogrammes, reimporter les SVG d'origine.

## Prevention

Avant toute nouvelle conversion de masse : sauvegarde complete, et
verification que l'outil met a jour `_wp_attached_file`,
`_wp_attachment_metadata` et `post_mime_type` de facon coherente. Une
conversion qui reecrit les fichiers sans reecrire les trois produit exactement
la situation decrite ici.
