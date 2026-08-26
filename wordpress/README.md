# Correctif affichage alphababy.fr

## Symptome

Sur toutes les pages, le site est comprime dans une colonne d'environ 200 px a
gauche de l'ecran, les elements de l'en-tete se superposent, le reste de la
fenetre est blanc.

## Cause

Un plugin de reservation enregistre la feuille de style `jquery-ui-style` vers
le CDN Google, en construisant l'URL depuis la version de jQuery UI livree par
le coeur WordPress :

```
//ajax.googleapis.com/ajax/libs/jqueryui/1.14.2/themes/smoothness/jquery-ui.css
```

Le CDN Google ne publie jQuery UI que jusqu'a la 1.12.1. Verifie le 26/08/2026 :

| Version | ajax.googleapis.com |
|---|---|
| 1.12.1 | 200 |
| 1.13.2 | 200 |
| 1.14.2 | **404** |

WordPress 7.1 livre la 1.14.2. L'URL renvoie donc la page d'erreur 404 de
Google, qui est du HTML.

WP Rocket 3.23.3.2 minifie cette reponse et la ressert depuis
`/wp-content/cache/min/1/ajax/libs/jqueryui/1.14.2/themes/smoothness/jquery-ui.min.css`
avec l'en-tete `Content-Type: text/css`. Le navigateur l'accepte alors comme
une feuille de style valide et applique les regles du bloc `<style>` de la page
d'erreur :

```css
* { margin: 0; padding: 0 }
html { padding: 15px; font: 15px/22px arial }
body { margin: 7% auto 0; max-width: 390px; min-height: 180px; padding: 30px 0 15px }
* > body { padding-right: 205px }
```

C'est le `max-width: 390px` sur `body` qui comprime le site. Servie
directement par Google, la reponse porte `Content-Type: text/html` et le
navigateur la refuse : le probleme n'apparait qu'a cause de la remise en cache
par WP Rocket.

## Mesures

Rendu de la page d'accueil dans Chromium, fenetre de 1440 px.

| Element | Avant | Apres |
|---|---|---|
| `body` largeur | 390 px | 1440 px |
| `body` max-width | 390px | none |
| `html` padding | 15px | 0px |
| `header` largeur | 185 px | 1440 px |

## Correctif immediat

Exclure le fichier de la minification WP Rocket. Reglages, Optimisation des
fichiers, « Fichiers CSS exclus », ajouter :

```
/ajax/libs/jqueryui/(.*)
```

puis vider le cache. WP Rocket cesse de resservir la page d'erreur en
`text/css`, le navigateur la refuse a nouveau et la mise en page revient.

## Correctif definitif

Deposer `mu-plugins/alphababy-fix-jquery-ui-style.php` dans
`wp-content/mu-plugins/` sur le serveur. Il retire la feuille de style
uniquement si elle pointe encore vers `ajax.googleapis.com`, donc il devient
inerte des que le plugin d'origine est corrige ou que la feuille passe en
local.

Cette feuille renvoyant une 404, elle n'a jamais rien style : la retirer ne
change pas l'apparence, elle supprime la corruption et une requete inutile.
