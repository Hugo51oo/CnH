#!/usr/bin/env bash
# CnH — lance automatiquement la chaîne d'agents pour la journée du jour.
#
# Sujets : outils/agents/sujets/AAAA-MM-JJ.json s'il existe ; sinon, la première journée
# de la file d'attente outils/agents/sujets/a-venir/ (ordre alphabétique), datée du jour.
# Garder quelques journées d'avance dans la file suffit à ne jamais rater un matin.
#
# Tourne chaque matin sur GitHub Actions (.github/workflows/journee.yml), gratuitement.
# Se lance aussi à la main depuis le Terminal du Mac, avec les clés dans .env.local.
#
# Tout est journalisé dans outils/agents/journal_auto.log. Rien n'est écrit dans
# contenu/ ni poussé sur GitHub tant que toutes les étapes n'ont pas réussi.

set -uo pipefail
cd "$(dirname "$0")/../.."   # racine du projet (ce script vit dans outils/agents/)

JOUR="$(date +%F)"
SUJETS="outils/agents/sujets/${JOUR}.json"
LOG="outils/agents/journal_auto.log"

horodater() { echo "[$(date '+%Y-%m-%d %H:%M:%S')] $*" | tee -a "$LOG"; }

echo "" >> "$LOG"
horodater "=== Lancement automatique pour le ${JOUR} ==="

if [ ! -f "$SUJETS" ]; then
  SUIVANT="$(ls outils/agents/sujets/a-venir/*.json 2>/dev/null | head -n 1)"
  if [ -z "$SUIVANT" ]; then
    horodater "Aucun sujet pour aujourd'hui et file d'attente vide (outils/agents/sujets/a-venir/) — rien à faire. Le site tourne sur les cartes déjà publiées."
    exit 0
  fi
  horodater "Pas de sujets datés du jour : on prend ${SUIVANT} dans la file d'attente."
  git mv "$SUIVANT" "$SUJETS" 2>/dev/null || mv "$SUIVANT" "$SUJETS"
  python3 - "$SUJETS" "$JOUR" <<'PY_DATE'
import json, sys
chemin, jour = sys.argv[1], sys.argv[2]
brut = json.load(open(chemin, encoding="utf-8"))
brut["date"] = jour
open(chemin, "w", encoding="utf-8").write(json.dumps(brut, ensure_ascii=False, indent=2) + "\n")
PY_DATE
fi

if ! python3 outils/agents/fournisseurs.py 2>&1 | grep -q "clé présente"; then
  horodater "✗ Aucune clé d'API (GEMINI_API_KEY, GROQ_API_KEY…) dans .env.local ou dans les secrets GitHub — impossible de continuer."
  exit 1
fi

horodater "1/5 — recherche des sources (chercher.py)"
if ! python3 outils/agents/chercher.py "$SUJETS" --ecrire >>"$LOG" 2>&1; then
  horodater "✗ échec de la recherche de sources — arrêt, rien publié."
  exit 1
fi

horodater "2/5 — téléchargement et tri des pages (documenter.py)"
if ! python3 outils/agents/documenter.py "$SUJETS" --condenser >>"$LOG" 2>&1; then
  horodater "✗ échec du documenter — arrêt, rien publié."
  exit 1
fi

horodater "3/5 — production, vérification et publication (journee.py --ecrire)"
if ! python3 outils/agents/journee.py "$SUJETS" --ecrire >>"$LOG" 2>&1; then
  horodater "✗ la chaîne a refusé de publier (détail dans ce journal, section ci-dessus) — rien n'a été écrit dans contenu/."
  exit 1
fi

horodater "4/5 — contrôle final (tout_verifier.sh)"
if ! ./outils/tout_verifier.sh >>"$LOG" 2>&1; then
  horodater "✗ tout_verifier.sh a échoué après publication — À VÉRIFIER À LA MAIN, rien n'a été poussé sur GitHub."
  exit 1
fi

horodater "5/5 — commit et push"
git add contenu/cartes.json contenu/programme.json contenu/preuves.json contenu/donnees.js \
        outils/agents/sujets/
if git diff --cached --quiet; then
  horodater "Rien à committer (étrange si la publication a réussi) — arrêt."
  exit 0
fi
git commit -m "Journée du ${JOUR} : contenus produits et vérifiés automatiquement" >>"$LOG" 2>&1
if git push origin main >>"$LOG" 2>&1; then
  horodater "✓ Journée du ${JOUR} publiée et poussée sur GitHub."
  osascript -e "display notification \"Contenu du ${JOUR} publié sur CnH\" with title \"CnH\"" 2>/dev/null || true
else
  horodater "✗ Le commit a réussi mais le push a échoué — à pousser à la main."
  exit 1
fi
