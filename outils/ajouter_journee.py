#!/usr/bin/env python3
"""
CnH — programmer une journée sans se tromper.

Usage (depuis la racine du projet) :
    python3 outils/ajouter_journee.py 2026-09-19                  # propose une journée valide
    python3 outils/ajouter_journee.py 2026-09-19 --ecrire         # l'écrit dans programme.json
    python3 outils/ajouter_journee.py 2026-09-19 --pb mon-id --cartes a,b,c,d,e --ecrire

Règles respectées : 1 problématique vérifiée + 5 cartes vérifiées, une par thème
(4 thèmes + 1 hors-piste), 5 formats différents, et on évite de reprendre les cartes
des journées voisines. Le script ne fait aucune requête réseau.

Code de sortie : 0 si la journée proposée (ou écrite) est valide, 1 sinon.
"""

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(Path(__file__).resolve().parent))
import valider_contenu as vc  # noqa: E402

THEMES_ORDRE = ["histoire-patrimoine", "cuisine-alimentation", "modes-de-vie-societe", "arts-langues-croyances", "hors-piste"]


def charger():
    cartes = json.loads((RACINE / "contenu" / "cartes.json").read_text(encoding="utf-8"))
    programme = json.loads((RACINE / "contenu" / "programme.json").read_text(encoding="utf-8"))
    return cartes, programme


def derniere_utilisation(programme):
    """id de contenu -> date la plus récente où il a été programmé."""
    vu = {}
    for date, jour in (programme.get("jours") or {}).items():
        for cid in [jour.get("problematique")] + list(jour.get("cartes") or []):
            if cid and (cid not in vu or date > vu[cid]):
                vu[cid] = date
    return vu


def proposer(cartes, programme, date):
    contenus = [c for c in cartes.get("contenus", []) if c.get("statut") == "verifie"]
    vu = derniere_utilisation(programme)
    lointain = "0000-00-00"

    pbs = sorted([c for c in contenus if c.get("type") == "problematique"], key=lambda c: (vu.get(c["id"], lointain), c["id"]))
    if not pbs:
        return None, ["Aucune problématique vérifiée dans contenu/cartes.json."]

    choix, formats, erreurs = [], set(), []
    for theme in THEMES_ORDRE:
        candidates = sorted([c for c in contenus if c.get("type") == "carte" and c.get("theme") == theme],
                            key=lambda c: (vu.get(c["id"], lointain), c["id"]))
        if not candidates:
            erreurs.append(f"Aucune carte vérifiée pour le thème « {theme} ».")
            continue
        libres = [c for c in candidates if c.get("format") not in formats]
        retenue = (libres or candidates)[0]
        if retenue.get("format") in formats:
            erreurs.append(f"Thème « {theme} » : impossible de trouver un format différent des autres "
                           f"(« {retenue.get('format')} » déjà pris). Ajoute une carte d'un autre format.")
        formats.add(retenue.get("format"))
        choix.append(retenue)

    jour = {"problematique": pbs[0]["id"], "cartes": [c["id"] for c in choix]}
    return jour, erreurs


def main(argv=None):
    ap = argparse.ArgumentParser(description="Programmer une journée de CnH.")
    ap.add_argument("date", help="date au format AAAA-MM-JJ")
    ap.add_argument("--pb", help="identifiant de la problématique (sinon : la moins récemment utilisée)")
    ap.add_argument("--cartes", help="5 identifiants séparés par des virgules")
    ap.add_argument("--ecrire", action="store_true", help="écrire la journée dans contenu/programme.json")
    a = ap.parse_args(argv)

    try:
        dt.date.fromisoformat(a.date)
    except ValueError:
        print(f"✗ Date invalide : {a.date} (attendu AAAA-MM-JJ)")
        return 1

    cartes, programme = charger()
    if a.date in (programme.get("jours") or {}):
        print(f"! Le {a.date} est déjà programmé : {programme['jours'][a.date]}")

    if a.pb or a.cartes:
        if not (a.pb and a.cartes):
            print("✗ Donne à la fois --pb et --cartes, ou aucun des deux.")
            return 1
        jour = {"problematique": a.pb, "cartes": [x.strip() for x in a.cartes.split(",") if x.strip()]}
        avertis = []
    else:
        jour, avertis = proposer(cartes, programme, a.date)
        if jour is None:
            for e in avertis:
                print(f"✗ {e}")
            return 1

    for e in avertis:
        print(f"! {e}")

    # Validation par le même code que le site
    erreurs, index = vc.valider_contenus(cartes.get("contenus"))
    if erreurs:
        print("✗ contenu/cartes.json est invalide, corrige-le d'abord :")
        for e in erreurs[:5]:
            print(f"  - {e}")
        return 1
    essai = {"jours": dict(programme.get("jours") or {})}
    essai["jours"][a.date] = jour
    erreurs = vc.valider_programme(essai, index)
    if erreurs:
        print("✗ Cette journée ne respecte pas les règles :")
        for e in erreurs:
            print(f"  - {e}")
        return 1

    print(f"✓ Journée valide pour le {a.date} :")
    print(f"  problématique : {jour['problematique']} — {index[jour['problematique']]['titre']}")
    for cid in jour["cartes"]:
        c = index[cid]
        print(f"  {c['theme']:<24} {c['format']:<15} {cid} — {c['titre']}")

    if not a.ecrire:
        print("\n(rien n'a été écrit : relance avec --ecrire pour l'enregistrer)")
        return 0

    programme.setdefault("jours", {})[a.date] = jour
    (RACINE / "contenu" / "programme.json").write_text(
        json.dumps(programme, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"\n✓ contenu/programme.json mis à jour. Lance maintenant : python3 outils/valider_contenu.py")
    return 0


if __name__ == "__main__":
    sys.exit(main())
