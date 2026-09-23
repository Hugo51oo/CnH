#!/usr/bin/env python3
"""
CnH — produit une journée entière (1 problématique + 5 cartes) de bout en bout.

    python3 outils/agents/journee.py sujets/2026-09-19.json                 # essai à blanc
    python3 outils/agents/journee.py sujets/2026-09-19.json --ecrire        # publie si tout passe

Enchaînement, du moins cher au plus cher :
 1. production      — un modèle bon marché écrit les 6 contenus           (jetons externes)
 2. schéma          — `valider_contenu.py` refuse tout ce qui est mal formé   (gratuit)
 3. sources         — `verifier_sources.py` retrouve chaque citation dans la page réelle (gratuit)
 4. qualité         — `verifier_qualite.py` : sources orphelines, clés, doublons… (gratuit)
 5. relecture       — un SECOND modèle essaie de démolir ce qui reste       (jetons externes)
 6. écriture        — fusion dans contenu/cartes.json + programme.json, puis régénération

Un contenu qui échoue à une étape ne passe pas à la suivante : on ne paie pas la
relecture d'un contenu déjà refusé par la vérification gratuite.

Rien n'est publié sans `--ecrire`, et `--ecrire` refuse de s'exécuter si une seule
étape a échoué.

Aucune dépendance : bibliothèque standard uniquement.
"""

import argparse
import copy
import datetime as dt
import json
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
OUTILS = ICI.parent
RACINE = OUTILS.parent
sys.path.insert(0, str(ICI))
sys.path.insert(0, str(OUTILS))

import fournisseurs as fo          # noqa: E402
import produire as prod            # noqa: E402
import verifier_sources as vs      # noqa: E402
import valider_contenu as vc       # noqa: E402
import verifier_qualite as vq      # noqa: E402
import contredire as ct            # noqa: E402

PRODUITS = ICI / "produits"


def titre(n, texte):
    print(f"\n\033[1m{n}. {texte}\033[0m")


def charger_sujets(chemin):
    brut = json.loads(Path(chemin).read_text(encoding="utf-8"))
    if isinstance(brut, list):
        return {"date": None, "sujets": brut}
    return {"date": brut.get("date"), "sujets": brut["sujets"]}


def verifier_le_jour(sujets):
    """Contrôle la composition avant de dépenser quoi que ce soit."""
    pb = [s for s in sujets if s.get("type") == "problematique"]
    cartes = [s for s in sujets if s.get("type", "carte") == "carte"]
    pbs = []
    if len(pb) != 1:
        pbs.append(f"il faut exactement 1 problématique (reçu {len(pb)}).")
    if len(cartes) != 5:
        pbs.append(f"il faut exactement 5 cartes (reçu {len(cartes)}).")
    themes = sorted(c.get("theme") for c in cartes)
    if len(cartes) == 5 and set(themes) != vc.THEMES:
        pbs.append(f"il faut une carte par thème + 1 hors-piste (reçu : {', '.join(themes)}).")
    formats = [c.get("format") for c in cartes]
    if len(cartes) == 5 and len(set(formats)) != 5:
        pbs.append(f"les 5 cartes doivent avoir 5 formats différents (reçu : {', '.join(formats)}).")
    deja = set(prod.ids_publies())
    for s in sujets:
        if s["id"] in deja:
            pbs.append(f"« {s['id']} » existe déjà dans cartes.json.")
    return pbs


def bac_de_validation(contenus_candidats, date, sujets):
    """Valide les nouveaux contenus au milieu des anciens, sans toucher au dépôt."""
    cartes = json.loads((RACINE / "contenu" / "cartes.json").read_text(encoding="utf-8"))
    programme = json.loads((RACINE / "contenu" / "programme.json").read_text(encoding="utf-8"))
    cartes = copy.deepcopy(cartes)
    cartes["contenus"] += contenus_candidats
    if date:
        pb = next(s["id"] for s in sujets if s.get("type") == "problematique")
        programme = copy.deepcopy(programme)
        programme["jours"][date] = {
            "problematique": pb,
            "cartes": [s["id"] for s in sujets if s.get("type", "carte") == "carte"],
        }
    erreurs, index = vc.valider_contenus(cartes["contenus"])
    if date:
        erreurs += vc.valider_programme(programme, index)
    return erreurs, cartes, programme


def main():
    ap = argparse.ArgumentParser(description="Produit et contrôle une journée CnH complète.")
    ap.add_argument("sujets")
    ap.add_argument("--modele", default=None, help="modèle qui produit")
    ap.add_argument("--relecteur", default=None, help="modèle qui contredit (doit différer)")
    ap.add_argument("--ecrire", action="store_true", help="publie si toutes les étapes passent")
    ap.add_argument("--reprendre", action="store_true",
                    help="réutilise les contenus déjà produits dans produits/")
    ap.add_argument("--hors-ligne", action="store_true",
                    help="vérifie les citations sur les pages déjà en cache")
    args = ap.parse_args()

    plan = charger_sujets(args.sujets)
    sujets, date = plan["sujets"], plan["date"]
    aujourdhui = dt.date.today().isoformat()

    titre(0, "Composition de la journée")
    pbs = verifier_le_jour(sujets)
    for p in pbs:
        print(f"  - {p}")
    if pbs:
        print("✗ Corrige le fichier de sujets avant de dépenser des jetons.")
        return 1
    print(f"✓ 1 problématique + 5 cartes, 5 thèmes, 5 formats"
          + (f", programmés le {date}." if date else "."))

    # avec --reprendre, un contenu déjà écrit n'a plus besoin de son dossier
    deja = {f.stem for f in PRODUITS.glob("*.json")} if args.reprendre else set()
    sans_dossier = [s["id"] for s in sujets
                    if s["id"] not in deja and not prod.lire_dossier(s)]
    if sans_dossier:
        print(f"\n✗ Aucun dossier documentaire pour : {', '.join(sans_dossier)}")
        print("  Un modèle appelé par son API ne navigue pas : sans le texte réel des pages,")
        print("  il cite de mémoire et tout sera rejeté à l'étape 3. Lance d'abord :")
        print(f"    python3 outils/agents/documenter.py {args.sujets}")
        return 1

    prets = fo.disponibles()
    modele = args.modele or (prets[0] if prets else None)
    relecteur = args.relecteur or next((m for m in prets if m != modele), None)
    if not modele:
        print("\n✗ Aucun modèle disponible. Ajoute une clé dans .env.local "
              "(voir outils/agents/LISEZMOI.md) ou lance Ollama.")
        return 1

    titre(1, f"Production ({modele})")
    PRODUITS.mkdir(parents=True, exist_ok=True)
    fichiers, echecs = [], []
    for s in sujets:
        cible = PRODUITS / f"{s['id']}.json"
        if args.reprendre and cible.exists():
            print(f"  = {s['id']} (déjà produit)")
            fichiers.append(cible)
            continue
        try:
            resultat = prod.produire(s, modele, aujourdhui)
        except Exception as e:
            print(f"  ✗ {s['id']} : {type(e).__name__} — {e}")
            echecs.append(s["id"])
            continue
        cible.write_text(json.dumps(resultat, ensure_ascii=False, indent=2), encoding="utf-8")
        i = resultat["production"]
        print(f"  ✓ {s['id']} — {i['jetons_entree']}+{i['jetons_sortie']} jetons, {i['secondes']} s")
        fichiers.append(cible)
    if echecs:
        print(f"✗ {len(echecs)} contenu(s) non produits : {', '.join(echecs)}")
        return 1

    donnees = {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in fichiers}
    candidats = [d["contenu"] for d in donnees.values()]

    titre(2, "Schéma (gratuit)")
    erreurs, cartes_bac, programme_bac = bac_de_validation(
        [{**c, "statut": "verifie"} for c in candidats], date, sujets)
    for e in erreurs:
        print(f"  - {e}")
    if erreurs:
        print("✗ Contenus mal formés : corrige la consigne ou relance la production.")
        return 1
    print("✓ Tous les contenus respectent le schéma.")

    titre(3, "Sources et citations (gratuit)")
    refuses = set()
    for nom, d in donnees.items():
        e, a, lues = vs.verifier_contenu(d["contenu"], d.get("preuves") or [],
                                         hors_ligne=args.hors_ligne)
        for x in a:
            print(f"  ! {x}")
        for x in e:
            print(f"  - {x}")
        print(f"  {'✓' if not e else '✗'} {nom} — {lues} page(s) lue(s)")
        if e:
            refuses.add(nom)
    if refuses:
        print(f"✗ {len(refuses)} contenu(s) dont les citations ne se retrouvent pas "
              f"dans les sources : {', '.join(sorted(refuses))}")
        return 1
    print("✓ Chaque fait publié est retrouvé mot pour mot dans sa source.")

    titre(4, "Qualité (gratuit)")
    bac = ICI / ".bac"
    (bac / "contenu").mkdir(parents=True, exist_ok=True)
    (bac / "contenu" / "cartes.json").write_text(
        json.dumps({**cartes_bac,
                    "contenus": [{**c, "statut": "verifie"} if c["id"] in donnees else c
                                 for c in cartes_bac["contenus"]]},
                   ensure_ascii=False, indent=2), encoding="utf-8")
    (bac / "contenu" / "programme.json").write_text(
        json.dumps(programme_bac, ensure_ascii=False, indent=2), encoding="utf-8")
    preuves_bac = json.loads((RACINE / "contenu" / "preuves.json").read_text(encoding="utf-8")) \
        if (RACINE / "contenu" / "preuves.json").exists() else {}
    for nom, d in donnees.items():
        preuves_bac[nom] = {"sources": d["contenu"].get("sources") or [],
                            "preuves": d.get("preuves") or []}
    (bac / "contenu" / "preuves.json").write_text(
        json.dumps(preuves_bac, ensure_ascii=False, indent=2), encoding="utf-8")
    err_q, av_q = vq.verifier(racine=bac)
    for a in av_q:
        print(f"  ! {a}")
    for e in err_q:
        print(f"  - {e}")
    if err_q:
        print("✗ Garde-fous de qualité : à corriger avant publication.")
        return 1
    print(f"✓ Qualité : rien à corriger ({len(av_q)} avertissement(s)).")

    titre(5, f"Relecture adverse ({relecteur or 'aucun second modèle'})")
    if not relecteur:
        print("  ! Un seul modèle disponible : la relecture adverse est sautée.")
        print("  ! Ajoute une deuxième clé (un modèle ne relit pas ses propres erreurs).")
        a_reprendre = set()
    else:
        a_reprendre = set()
        for nom, d in donnees.items():
            try:
                verdict, infos = ct.contredire(d, relecteur)
            except Exception as e:
                print(f"  ✗ {nom} : relecture impossible — {type(e).__name__} : {e}")
                a_reprendre.add(nom)
                continue
            d["relecture"] = {**verdict, "modele": relecteur}
            (PRODUITS / f"{nom}.json").write_text(
                json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
            graves = [v for v in verdict.get("verdicts", [])
                      if v.get("verdict") in ("faux", "inverifiable")]
            if graves or verdict.get("avis") != "publiable":
                a_reprendre.add(nom)
            print(f"  {'✓' if nom not in a_reprendre else '✗'} {nom} — « {verdict.get('avis')} », "
                  f"{len(graves)} grave(s)")
            for v in graves:
                print(f"      [{v.get('verdict')}] {v.get('appuie')} : {v.get('pourquoi')}")
            for x in verdict.get("camps_desequilibres", []):
                print(f"      [camps] {x}")
    if a_reprendre:
        print(f"✗ {len(a_reprendre)} contenu(s) recalés par la relecture : "
              f"{', '.join(sorted(a_reprendre))}")
        return 1

    titre(6, "Publication")
    if not args.ecrire:
        print("  (essai à blanc) Tout est passé. Relance avec --ecrire pour publier.")
        return 0

    cartes = json.loads((RACINE / "contenu" / "cartes.json").read_text(encoding="utf-8"))
    cartes["contenus"] += [{**d["contenu"], "statut": "verifie"} for d in donnees.values()]
    (RACINE / "contenu" / "cartes.json").write_text(
        json.dumps(cartes, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if date:
        programme = json.loads((RACINE / "contenu" / "programme.json").read_text(encoding="utf-8"))
        programme["jours"][date] = programme_bac["jours"][date]
        programme["jours"] = dict(sorted(programme["jours"].items()))
        (RACINE / "contenu" / "programme.json").write_text(
            json.dumps(programme, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    chemin_preuves = RACINE / "contenu" / "preuves.json"
    preuves = json.loads(chemin_preuves.read_text(encoding="utf-8")) if chemin_preuves.exists() else {}
    for nom, d in donnees.items():
        preuves[nom] = {"sources": d["contenu"].get("sources") or [],
                        "preuves": d.get("preuves") or []}
    chemin_preuves.write_text(json.dumps(preuves, ensure_ascii=False, indent=2) + "\n",
                              encoding="utf-8")

    erreurs, donnees_site = vc.valider()
    if erreurs:
        print("✗ Le dépôt ne valide plus après écriture :")
        for e in erreurs:
            print(f"  - {e}")
        return 1
    vc.ecrire_donnees(donnees_site)
    print(f"✓ {len(donnees)} contenu(s) publiés"
          + (f", journée du {date} programmée" if date else "")
          + ", contenu/donnees.js régénéré.")
    print("  Vérifie l'ensemble : ./outils/tout_verifier.sh")
    return 0


if __name__ == "__main__":
    sys.exit(main())
