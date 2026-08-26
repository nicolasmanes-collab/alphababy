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

Depuis une session Claude Code distante, l'appel echoue avec un 403 sur le
CONNECT si le domaine n'est pas autorise par la politique reseau de
l'environnement. Il faut ajouter `alphababy.fr` aux domaines autorises.
Voir https://code.claude.com/docs/en/claude-code-on-the-web
