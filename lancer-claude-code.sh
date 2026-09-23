#!/usr/bin/env bash
# ------------------------------------------------------------------
# CnH — lance une session Claude Code sur une phase du projet
#
# Usage :
#   ./lancer-claude-code.sh          -> phase V1 (par défaut)
#   ./lancer-claude-code.sh v2       -> phase V2 (forum)
#   ./lancer-claude-code.sh v3       -> phase V3 (vocal)
#   ./lancer-claude-code.sh statut   -> champs juridiques restant à compléter
#
# Compatible avec le bash 3.2 fourni par macOS.
# ------------------------------------------------------------------
set -euo pipefail

DOSSIER="$(cd "$(dirname "$0")" && pwd)"
cd "$DOSSIER"

MARQUEURS='À (COMPLÉTER|VALIDER|VÉRIFIER)'

aide() {
  sed -n '3,11p' "$0" | sed 's/^# \{0,1\}//'
}

# Liste les champs juridiques non remplis. Retourne 0 s'il en reste.
champs_restants() {
  local resultats
  resultats="$(grep -rcE --exclude=00-A-LIRE.md "$MARQUEURS" docs/juridique 2>/dev/null | grep -v ':0$' || true)"
  if [ -n "$resultats" ]; then
    echo "Champs à traiter dans docs/juridique :"
    echo "$resultats" | sed 's#^docs/juridique/#  - #; s#:# : #'
    return 0
  fi
  return 1
}

PHASE="${1:-v1}"

case "$PHASE" in
  v1|v2|v3) ;;
  statut)
    if champs_restants; then exit 0; fi
    echo "Aucun champ [À COMPLÉTER / À VALIDER / À VÉRIFIER] restant."
    exit 0
    ;;
  -h|--help|aide)
    aide
    exit 0
    ;;
  *)
    echo "Phase inconnue : « $PHASE ». Attendu : v1, v2, v3 ou statut."
    exit 1
    ;;
esac

PROMPT="prompts/${PHASE}.md"

# --- Vérifications de base ---------------------------------------
for fichier in CLAUDE.md "$PROMPT" docs/juridique/00-A-LIRE.md; do
  if [ ! -f "$fichier" ]; then
    echo "Fichier manquant : $fichier (lance ce script depuis le dossier du projet)."
    exit 1
  fi
done

if ! command -v claude >/dev/null 2>&1; then
  echo "Claude Code n'est pas installé ou pas dans le PATH."
  echo "Installation recommandée (macOS) :"
  echo "  curl -fsSL https://claude.ai/install.sh | bash"
  echo "Autres méthodes : https://code.claude.com/docs/en/setup"
  exit 1
fi

# --- Garde-fous juridiques selon la phase -------------------------
echo ""
echo "=== CnH — phase $(echo "$PHASE" | tr '[:lower:]' '[:upper:]') ==="
echo ""

if champs_restants; then
  echo ""
  if [ "$PHASE" = "v1" ]; then
    echo "OK pour développer en V1. Les mentions légales devront être complètes AVANT la mise en ligne."
  else
    echo "⚠️  La phase $PHASE touche des données personnelles."
    echo "   Tu peux développer en local, mais rien ne doit être mis en ligne tant que"
    echo "   la checklist de docs/juridique/00-A-LIRE.md n'est pas complète."
    printf "Continuer en local ? (o/N) "
    read -r reponse
    case "$reponse" in
      o|O|oui|OUI) ;;
      *) echo "Arrêt."; exit 1 ;;
    esac
  fi
  echo ""
fi

if [ "$PHASE" != "v1" ] && ! command -v supabase >/dev/null 2>&1; then
  echo "ℹ️  La CLI Supabase n'est pas installée. Claude Code te proposera de l'installer."
  echo "   Doc : https://supabase.com/docs/guides/local-development/cli/getting-started"
  echo ""
fi

# --- Dépôt git -----------------------------------------------------
if command -v git >/dev/null 2>&1 && [ ! -d .git ]; then
  git init -q
  echo "Dépôt git initialisé."
  if git config user.name >/dev/null 2>&1 && git config user.email >/dev/null 2>&1; then
    git add -A
    git commit -q -m "Kit de démarrage CnH (docs, juridique, contenus)"
    echo "Premier commit créé."
  else
    echo "ℹ️  git user.name / user.email non configurés : pas de commit initial."
  fi
  echo ""
fi

# --- Lancement -------------------------------------------------------
echo "Lancement de Claude Code avec $PROMPT…"
exec claude "$(cat "$PROMPT")"
