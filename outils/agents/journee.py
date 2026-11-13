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

Rien n'est publié sans `--ecrire`. Option souple : un contenu qui échoue à une étape
est écarté (il reste en brouillon dans produits/), les autres continuent. Si la journée
est incomplète, rien n'est programmé : les contenus entièrement vérifiés vont dans la
réserve de cartes. Aucun contrôle n'est assoupli pour autant.

Aucune dépendance : bibliothèque standard uniquement.
"""

import argparse
import copy
import datetime as dt
import json
import os
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


CORRECTIONS_MAX = 3
RELECTURES_MAX = 2   # reprises d'un contenu d'après les objections du relecteur


def objections_de(verdict):
    """Transforme le verdict du relecteur en liste d'erreurs à corriger."""
    liste = []
    for v in verdict.get("verdicts", []):
        if v.get("verdict") in ("faux", "inverifiable", "imprecis"):
            ligne = f"[relecture] {v.get('appuie')} — {v.get('verdict')} : {v.get('pourquoi')}"
            if v.get("correction"):
                ligne += f" (piste du relecteur : {v['correction']})"
            liste.append(ligne)
    liste += [f"[relecture, camps déséquilibrés] {x}" for x in verdict.get("camps_desequilibres", [])]
    if not liste:
        liste.append(f"[relecture] avis « {verdict.get('avis')} » sans détail : relis chaque fait "
                     "et vérifie que sa citation le dit vraiment, sans rien ajouter.")
    return liste


def erreurs_par_contenu(erreurs, donnees):
    """{id: [erreurs]} pour les contenus produits aujourd'hui que cite chaque erreur."""
    groupes = {}
    for e in erreurs:
        for nom in donnees:
            if f"« {nom} »" in e:
                groupes.setdefault(nom, []).append(e)
    return groupes


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
    fichiers, recales = [], {}
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
            recales[s["id"]] = f"production impossible — {type(e).__name__}"
            continue
        cible.write_text(json.dumps(resultat, ensure_ascii=False, indent=2), encoding="utf-8")
        i = resultat["production"]
        print(f"  ✓ {s['id']} — {i['jetons_entree']}+{i['jetons_sortie']} jetons, {i['secondes']} s")
        fichiers.append(cible)

    donnees = {f.stem: json.loads(f.read_text(encoding="utf-8")) for f in fichiers}

    def ecarter(nom, raison):
        # Option souple : un contenu raté ne fait pas perdre la journée. Il reste en
        # brouillon dans produits/ ; les autres ne passent pas un contrôle de moins.
        recales[nom] = raison
        donnees.pop(nom, None)
        print(f"  ✗ {nom} écarté : {raison} (reste en brouillon dans produits/)")

    # Étapes 2 et 3, en boucle : schéma puis citations. Un modèle bon marché écrit vite
    # mais suit moins bien les consignes : plutôt que de tout jeter, on lui renvoie ses
    # erreurs précises, et chaque correction repasse par les DEUX contrôles.
    par_id = {s["id"]: s for s in sujets}
    approuves = set()   # contenus déjà acceptés par la relecture adverse
    for passe in range(1, RELECTURES_MAX + 2):
        objections, raison_rejet = {}, {}
        tour = 0
        while True:
            tour += 1
            if not donnees:
                print("✗ Aucun contenu ne passe les contrôles : rien à publier.")
                return 1
            if recales:
                date = None   # journée incomplète : rien n'est programmé, on garnit la réserve
            candidats = [d["contenu"] for d in donnees.values()]
            titre(2, "Schéma (gratuit)" + (f" — tour {tour}" if tour > 1 else ""))
            erreurs, cartes_bac, programme_bac = bac_de_validation(
                [{**c, "statut": "verifie"} for c in candidats], date, sujets)
            for e in erreurs:
                print(f"  - {e}")
            if erreurs:
                a_corriger = erreurs_par_contenu(erreurs, donnees)
                hors_contenus = [e for e in erreurs if not any(e in l for l in a_corriger.values())]
                if hors_contenus:
                    # une erreur qu'aucune correction de contenu ne réglera
                    print("✗ Contenus mal formés : corrige la consigne ou relance la production.")
                    return 1
                if tour > CORRECTIONS_MAX:
                    for nom in a_corriger:
                        ecarter(nom, f"schéma encore invalide après {CORRECTIONS_MAX} corrections")
                    continue
            else:
                print("✓ Tous les contenus respectent le schéma.")
                titre(3, "Sources et citations (gratuit)")
                a_corriger = {}
                for nom, d in donnees.items():
                    e, a, lues = vs.verifier_contenu(d["contenu"], d.get("preuves") or [],
                                                     hors_ligne=args.hors_ligne)
                    for x in a:
                        print(f"  ! {x}")
                    for x in e:
                        print(f"  - {x}")
                    print(f"  {'✓' if not e else '✗'} {nom} — {lues} page(s) lue(s)")
                    if e:
                        # les citations « presque exactes » sont à recopier au passage
                        a_corriger[nom] = e + [x for x in a if "pas identique" in x]
                if not a_corriger:
                    print("✓ Chaque fait publié est retrouvé mot pour mot dans sa source.")
                    break
                if tour > CORRECTIONS_MAX:
                    for nom in a_corriger:
                        ecarter(nom, "citations introuvables dans les sources")
                    continue
            print(f"  → correction {tour}/{CORRECTIONS_MAX} par {modele} : {', '.join(a_corriger)}")
            for nom, liste in a_corriger.items():
                try:
                    corrige = prod.corriger(par_id[nom], donnees[nom], liste, modele, aujourdhui)
                except Exception as e:
                    ecarter(nom, f"correction impossible — {type(e).__name__} — {e}")
                    continue
                corrige["production"] = {**donnees[nom].get("production", {}),
                                         "corrections": tour}
                donnees[nom] = corrige
                (PRODUITS / f"{nom}.json").write_text(
                    json.dumps(corrige, ensure_ascii=False, indent=2), encoding="utf-8")

        titre(4, "Qualité (gratuit)")
        for nom, d in donnees.items():
            retirees = prod.elaguer_sources(d)
            if retirees:
                print(f"  · {nom} : {retirees} source(s) jamais citée(s) retirée(s), renvois renumérotés")
                (PRODUITS / f"{nom}.json").write_text(
                    json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
        erreurs, cartes_bac, programme_bac = bac_de_validation(
            [{**d["contenu"], "statut": "verifie"} for d in donnees.values()], date, sujets)
        if erreurs:
            for e in erreurs:
                print(f"  - {e}")
            print("✗ Le rangement des sources a cassé le schéma : à examiner.")
            return 1
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
                if nom in approuves:
                    print(f"  = {nom} (déjà approuvé)")
                    continue
                try:
                    verdict, infos = ct.contredire(d, relecteur, par_id.get(nom))
                except Exception as e:
                    print(f"  ✗ {nom} : relecture impossible — {type(e).__name__} : {e}")
                    a_reprendre.add(nom)
                    objections[nom] = None    # panne technique : rien à corriger
                    continue
                d["relecture"] = {**verdict, "modele": relecteur}
                (PRODUITS / f"{nom}.json").write_text(
                    json.dumps(d, ensure_ascii=False, indent=2), encoding="utf-8")
                graves = [v for v in verdict.get("verdicts", [])
                          if v.get("verdict") in ("faux", "inverifiable")]
                if graves or verdict.get("avis") != "publiable":
                    a_reprendre.add(nom)
                if verdict.get("hors_sujet") or verdict.get("avis") == "a-jeter":
                    # rien à corriger : les sources ou l'angle ne conviennent pas
                    a_reprendre.add(nom)
                    objections[nom] = None
                    raison_rejet[nom] = ("hors sujet — " + str(verdict["hors_sujet"])
                                         if verdict.get("hors_sujet") else "jugé à jeter par la relecture")
                elif nom in a_reprendre:
                    objections[nom] = objections_de(verdict)
                else:
                    approuves.add(nom)
                print(f"  {'✓' if nom not in a_reprendre else '✗'} {nom} — « {verdict.get('avis')} », "
                      f"{len(graves)} grave(s)")
                for v in graves:
                    print(f"      [{v.get('verdict')}] {v.get('appuie')} : {v.get('pourquoi')}")
                for x in verdict.get("camps_desequilibres", []):
                    print(f"      [camps] {x}")
                if verdict.get("hors_sujet"):
                    print(f"      [hors sujet] {verdict['hors_sujet']}")
        corriges = 0
        for nom in sorted(a_reprendre):
            if objections.get(nom) is None:
                ecarter(nom, raison_rejet.get(nom, "relecture adverse impossible"))
                continue
            if passe > RELECTURES_MAX:
                ecarter(nom, f"encore recalé par la relecture après {RELECTURES_MAX} reprise(s)")
                continue
            print(f"  → reprise {passe}/{RELECTURES_MAX} de {nom} d'après la relecture")
            try:
                corrige = prod.corriger(par_id[nom], donnees[nom], objections[nom], modele, aujourdhui)
            except Exception as e:
                ecarter(nom, f"reprise impossible — {type(e).__name__} — {e}")
                continue
            corrige["production"] = {**donnees[nom].get("production", {}), "reprises": passe}
            donnees[nom] = corrige
            (PRODUITS / f"{nom}.json").write_text(
                json.dumps(corrige, ensure_ascii=False, indent=2), encoding="utf-8")
            corriges += 1
        if not corriges:
            break
        # les contenus repris repassent par TOUS les contrôles, puis par une nouvelle relecture

    if not donnees:
        print("✗ Aucun contenu ne passe la relecture : rien à publier.")
        return 1
    if recales:
        date = None

    titre(6, "Publication")
    if recales:
        print(f"  ! Journée incomplète : {len(donnees)} contenu(s) vérifié(s) vont dans la réserve, "
              "aucune journée n'est programmée.")
        for nom, raison in recales.items():
            print(f"  ! écarté : {nom} — {raison}")
        if os.environ.get("GITHUB_ACTIONS"):
            print(f"::warning::Journée incomplète, {len(recales)} contenu(s) écarté(s) : "
                  + ", ".join(recales))
    if not args.ecrire:
        print("  (essai à blanc) Tout le reste est passé. Relance avec --ecrire pour publier.")
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
