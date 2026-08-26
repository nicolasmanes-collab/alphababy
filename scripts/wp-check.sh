#!/usr/bin/env bash
# Verifie l'acces a l'API REST WordPress avec un mot de passe d'application.
#
# Usage :
#   cp .env.example .env && $EDITOR .env
#   set -a && . ./.env && set +a
#   ./scripts/wp-check.sh
set -uo pipefail

: "${WP_URL:?WP_URL manquant (ex: https://exemple.fr)}"
: "${WP_USER:?WP_USER manquant}"
: "${WP_APP_PASSWORD:?WP_APP_PASSWORD manquant}"

BASE="${WP_URL%/}"

echo "== 1. API REST joignable =="
code=$(curl -sS -o /dev/null -w '%{http_code}' "$BASE/wp-json/")
echo "GET $BASE/wp-json/ -> HTTP $code"
if [ "$code" != "200" ]; then
  echo "L'API REST ne repond pas en 200. Verifier qu'elle n'est pas desactivee"
  echo "par un plugin de securite ou une regle serveur, puis relancer."
  exit 1
fi

echo
echo "== 2. Authentification =="
body=$(mktemp)
code=$(curl -sS -o "$body" -w '%{http_code}' \
  -u "$WP_USER:$WP_APP_PASSWORD" \
  "$BASE/wp-json/wp/v2/users/me?context=edit")
echo "GET $BASE/wp-json/wp/v2/users/me -> HTTP $code"

case "$code" in
  200)
    echo "Connexion OK. Compte :"
    if command -v jq >/dev/null 2>&1; then
      jq '{id, slug, name, roles, capabilities: (.capabilities | keys | length)}' "$body"
    else
      head -c 600 "$body"; echo
    fi
    ;;
  401)
    echo "Identifiants refuses. Pistes :"
    echo "  - l'identifiant doit etre le login WordPress ou l'email du compte"
    echo "  - le mot de passe d'application est valable tel quel, espaces inclus"
    echo "  - certains hebergeurs suppriment l'en-tete Authorization :"
    echo "    ajouter la regle CGIPassAuth / rewrite dans le .htaccess"
    head -c 400 "$body"; echo
    ;;
  403)
    echo "Authentifie mais sans les droits, ou bloque par un pare-feu applicatif."
    head -c 400 "$body"; echo
    ;;
  *)
    head -c 400 "$body"; echo
    ;;
esac

rm -f "$body"
