#!/usr/bin/env python3
"""
CnH — constitue le dossier documentaire d'un sujet, à partir d'URLs choisies.

    python3 outils/agents/documenter.py outils/agents/sujets/2026-09-20.json

Pourquoi cette étape existe : un modèle appelé par son API **ne navigue pas**. S'il
écrit une carte de mémoire, ses citations seront approximatives et `verifier_sources.py`
les rejettera toutes. On lui donne donc le texte réel des pages, et on lui interdit
d'écrire autre chose que ce qu'il y lit.

Effet de bord heureux : le choix des sources redevient un acte éditorial humain
(règle 1 du projet), au lieu d'être délégué à un modèle qui « se souvient » d'une URL.

Chaque sujet du fichier porte une liste `sources_candidates` (des URLs). Le script
télécharge chaque page, en extrait le texte et écrit un dossier dans `dossiers/<id>.md`.
Les pages illisibles (JavaScript pur, 403, PDF sans pdftotext) sont signalées : à toi
de les remplacer par une source lisible.

Aucune dépendance : bibliothèque standard uniquement.
"""

import argparse
import json
import re
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent.parent
sys.path.insert(0, str(ICI))

import verifier_sources as vs  # noqa: E402

DOSSIERS = ICI / "dossiers"
# de quoi écrire une carte sans noyer le modèle (ni la facture)
CARACTERES_PAR_PAGE = 12000


def resserrer(texte, limite=CARACTERES_PAR_PAGE):
    """Garde le texte utile : on enlève les blancs, les menus répétés, et on coupe."""
    texte = re.sub(r"\n{3,}", "\n\n", texte)
    lignes, vues = [], set()
    for ligne in texte.splitlines():
        ligne = re.sub(r"[ \t]+", " ", ligne).strip()
        if len(ligne) < 3:
            continue
        # les éléments de navigation reviennent à l'identique des dizaines de fois
        if len(ligne) < 60:
            if ligne in vues:
                continue
            vues.add(ligne)
        lignes.append(ligne)
    resserre = "\n".join(lignes)
    if len(resserre) > limite:
        resserre = resserre[:limite] + "\n[… page tronquée ici …]"
    return resserre


def dossier_du_sujet(sujet, hors_ligne=False, limite=CARACTERES_PAR_PAGE):
    """Retourne (markdown, urls_lues, urls_illisibles)."""
    urls = sujet.get("sources_candidates") or []
    morceaux = [f"# Dossier documentaire — {sujet['id']}", ""]
    morceaux.append("Voici le texte réel des pages retenues. Tu ne peux citer que ce qui")
    morceaux.append("se trouve ci-dessous, et la numérotation des sources est celle-ci.")
    morceaux.append("")
    lues, illisibles = [], []
    n = 0
    for url in urls:
        texte, err = vs.lire_page(url, hors_ligne=hors_ligne)
        if err:
            illisibles.append((url, err))
            continue
        n += 1
        lues.append(url)
        morceaux.append(f"## SOURCE {n} — {url}")
        morceaux.append("")
        morceaux.append(resserrer(texte, limite))
        morceaux.append("")
    return "\n".join(morceaux), lues, illisibles


def main():
    ap = argparse.ArgumentParser(description="Constitue les dossiers documentaires d'une journée.")
    ap.add_argument("sujets")
    ap.add_argument("--hors-ligne", action="store_true")
    ap.add_argument("--caracteres", type=int, default=CARACTERES_PAR_PAGE,
                    help="longueur maximale gardée par page (défaut 12000)")
    args = ap.parse_args()

    brut = json.loads(Path(args.sujets).read_text(encoding="utf-8"))
    sujets = brut["sujets"] if isinstance(brut, dict) else brut
    DOSSIERS.mkdir(parents=True, exist_ok=True)

    manquants, total = [], 0
    for s in sujets:
        urls = s.get("sources_candidates") or []
        if not urls:
            manquants.append(s["id"])
            print(f"  ! {s['id']} : aucune URL dans « sources_candidates ».")
            continue
        md, lues, illisibles = dossier_du_sujet(s, hors_ligne=args.hors_ligne,
                                                limite=args.caracteres)
        cible = DOSSIERS / f"{s['id']}.md"
        cible.write_text(md, encoding="utf-8")
        total += len(md)
        print(f"  ✓ {s['id']} — {len(lues)} page(s), {len(md) // 1000} k caractères")
        for url, err in illisibles:
            print(f"      illisible ({err}) : {url}")
        if len(lues) < 3:
            print(f"      ! seulement {len(lues)} source(s) lisible(s) : ajoute des URLs, "
                  f"sinon la carte sera pauvre ou invérifiable.")

    if manquants:
        print(f"\n✗ {len(manquants)} sujet(s) sans sources : {', '.join(manquants)}")
        print("  Ajoute « sources_candidates »: [\"https://…\"] à chacun.")
        return 1
    print(f"\n✓ Dossiers écrits dans {DOSSIERS.relative_to(RACINE)} "
          f"({total // 1000} k caractères au total).")
    print("  Étape suivante : python3 outils/agents/journee.py " + args.sujets)
    return 0


if __name__ == "__main__":
    sys.exit(main())
