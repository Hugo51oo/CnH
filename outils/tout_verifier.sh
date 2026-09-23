#!/usr/bin/env bash
# CnH — tout vérifier en une commande.
#   ./outils/tout_verifier.sh            (validation, tests, qualité)
#   ./outils/tout_verifier.sh --ecrire   (régénère aussi contenu/donnees.js)
# Aucune requête réseau. Code de sortie 0 si tout passe.

set -u
cd "$(dirname "$0")/.." || exit 1

vert=$'\033[32m'; rouge=$'\033[31m'; gras=$'\033[1m'; fin=$'\033[0m'
rates=0
etape() { printf '\n%s== %s%s\n' "$gras" "$1" "$fin"; }
bilan() { if [ "$1" -eq 0 ]; then printf '%s✓ %s%s\n' "$vert" "$2" "$fin"; else printf '%s✗ %s%s\n' "$rouge" "$2" "$fin"; rates=$((rates+1)); fi; }

etape "Schéma des contenus"
if [ "${1:-}" = "--ecrire" ]; then
  python3 outils/valider_contenu.py; bilan $? "contenus valides, contenu/donnees.js régénéré"
else
  python3 outils/valider_contenu.py --verifier; bilan $? "contenus valides"
fi

etape "Tests du validateur"
python3 outils/test_valider_contenu.py 2>&1 | tail -3
bilan ${PIPESTATUS[0]} "tests du validateur"

etape "Qualité des contenus"
python3 outils/verifier_qualite.py; bilan $? "garde-fous de qualité"

etape "Tests des garde-fous"
if [ -f outils/test_verifier_qualite.py ]; then
  python3 outils/test_verifier_qualite.py 2>&1 | tail -3
  bilan ${PIPESTATUS[0]} "tests des garde-fous"
fi

etape "Tests de la chaîne d'agents"
if [ -f outils/agents/test_agents.py ]; then
  python3 outils/agents/test_agents.py 2>&1 | tail -3
  bilan ${PIPESTATUS[0]} "tests de la chaîne d'agents"
fi

etape "Aucune clé d'API dans le dépôt"
fuite=$(grep -rlE '(sk-[A-Za-z0-9]{20,}|API_KEY=[A-Za-z0-9])' --exclude-dir=.git --exclude=.gitignore --exclude=tout_verifier.sh . 2>/dev/null | grep -v '^./.env' | wc -l | tr -d ' ')
if [ "$fuite" = "0" ]; then bilan 0 "aucune clé en clair"; else bilan 1 "$fuite fichier(s) contiennent peut-être une clé"; grep -rlE '(sk-[A-Za-z0-9]{20,}|API_KEY=[A-Za-z0-9])' --exclude-dir=.git --exclude=.gitignore --exclude=tout_verifier.sh . 2>/dev/null | grep -v '^./.env'; fi

etape "Pages légales"
manque=$(grep -rl "À COMPLÉTER" docs/juridique/mentions-legales.md docs/juridique/politique-de-confidentialite-v1.md 2>/dev/null | wc -l | tr -d ' ')
if [ "$manque" = "0" ]; then bilan 0 "aucun champ à compléter dans les pages publiées"; else bilan 1 "$manque page(s) légale(s) encore à compléter"; fi

etape "Rien ne part vers un domaine tiers"
tiers=$(grep -oE '(src|href)="https?://[^"]+' index.html | grep -v 'www.w3.org' | wc -l | tr -d ' ')
if [ "$tiers" = "0" ]; then bilan 0 "aucune ressource externe dans index.html"; else bilan 1 "$tiers ressource(s) externe(s) dans index.html"; grep -oE '(src|href)="https?://[^"]+' index.html | grep -v 'www.w3.org'; fi

printf '\n'
if [ "$rates" -eq 0 ]; then
  printf '%s%sTout est bon. Le site est prêt à être publié.%s\n' "$gras" "$vert" "$fin"
else
  printf '%s%s%s étape(s) à corriger.%s\n' "$gras" "$rouge" "$rates" "$fin"
fi
exit "$rates"
