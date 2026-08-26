# alphababy

Acces a WordPress via l'API REST et un mot de passe d'application.

## Configuration

```bash
cp .env.example .env
# renseigner WP_USER et WP_APP_PASSWORD dans .env
```

Le mot de passe d'application se genere dans WordPress : Utilisateurs, puis le
profil du compte, section « Mots de passe d'application ». Il n'est affiche
qu'une fois. Aucun secret ne doit etre commite : `.env` est ignore par git.

## Verifier la connexion

```bash
set -a && . ./.env && set +a
./scripts/wp-check.sh
```

Le script teste d'abord que `/wp-json/` repond, puis l'authentification sur
`/wp-json/wp/v2/users/me`, et affiche le compte et ses roles en cas de succes.

## Acces reseau

`alphababy.fr` est autorise par la politique reseau de l'environnement : le
script s'execute sans erreur depuis une session Claude Code distante. Si un
autre domaine est ajoute plus tard, l'appel echoue avec un 403 sur le CONNECT
tant qu'il n'est pas ajoute aux domaines autorises.
Voir https://code.claude.com/docs/en/claude-code-on-the-web

## Perimetre verifie

Le compte utilise est administrateur. Les espaces de noms suivants repondent en
200 avec le mot de passe d'application : `wp/v2` (articles, pages, medias,
utilisateurs), `wc/v3` (produits, commandes) et `rankmath/v1`.
