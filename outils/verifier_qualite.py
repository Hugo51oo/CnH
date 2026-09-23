#!/usr/bin/env python3
"""
CnH — garde-fous de qualité sur les contenus (hors ligne, aucune requête réseau).

Usage (depuis la racine du projet) :
    python3 outils/verifier_qualite.py

Ce script complète `valider_contenu.py`, qui vérifie le schéma. Ici on vérifie ce qui
fait la valeur d'une carte : des sources réellement utilisées, des dates cohérentes,
des clés lisibles, et une preuve archivée pour chaque fait publié.

Code de sortie : 0 si aucune erreur (les avertissements ne bloquent pas), 1 sinon.
Aucune dépendance : Python 3 standard uniquement.
"""

import datetime as dt
import json
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
CLE_MAX = 16
LONGUEUR_BASE_MAX = 600
LONGUEUR_CAMP_MAX = 700


def numeros(valeur):
    return valeur if isinstance(valeur, list) else [valeur]


def charger(chemin, erreurs):
    try:
        return json.loads(chemin.read_text(encoding="utf-8"))
    except FileNotFoundError:
        erreurs.append(f"Fichier introuvable : {chemin.relative_to(RACINE)}")
    except json.JSONDecodeError as e:
        erreurs.append(f"{chemin.relative_to(RACINE)} : JSON invalide (ligne {e.lineno}) — {e.msg}")
    return None


def verifier(racine=RACINE, aujourdhui=None):
    """Retourne (erreurs, avertissements)."""
    erreurs, avertis = [], []
    aujourdhui = aujourdhui or dt.date.today()

    cartes = charger(racine / "contenu" / "cartes.json", erreurs)
    if cartes is None:
        return erreurs, avertis
    chemin_preuves = racine / "contenu" / "preuves.json"
    preuves = json.loads(chemin_preuves.read_text(encoding="utf-8")) if chemin_preuves.exists() else {}

    contenus = cartes.get("contenus", [])
    titres = {}

    for c in contenus:
        cid = c.get("id", "?")
        sources = c.get("sources") or []
        n = len(sources)

        # Titres : pas de doublon, on s'y repère par le titre dans l'interface
        titre = (c.get("titre") or "").strip().lower()
        if titre and titre in titres:
            erreurs.append(f"« {cid} » : même titre que « {titres[titre]} ».")
        titres[titre] = cid

        # Renvois : dans les bornes, et chaque source doit servir au moins une fois
        utilisees = set()
        def note(valeur, ou):
            for x in numeros(valeur):
                if isinstance(x, int) and 1 <= x <= n:
                    utilisees.add(x)
                else:
                    erreurs.append(f"« {cid} » : renvoi vers la source {x} ({ou}), hors des {n} sources.")

        if c.get("base_source") is not None:
            note(c.get("base_source"), "base")
        for i, r in enumerate(c.get("reperes") or [], 1):
            note(r.get("source"), f"repère {i}")
            cle = (r.get("cle") or "").strip()
            if len(cle) > CLE_MAX:
                erreurs.append(f"« {cid} » : clé « {cle} » = {len(cle)} caractères (maximum {CLE_MAX}).")
            if not (r.get("texte") or "").strip():
                erreurs.append(f"« {cid} » : repère {i} sans texte.")
        cles = [(r.get("cle") or "").strip().lower() for r in (c.get("reperes") or [])]
        if len(set(cles)) != len(cles):
            erreurs.append(f"« {cid} » : deux repères ont la même clé.")

        for i, k in enumerate(c.get("clivages") or [], 1):
            for cote in ("fait_a", "fait_b"):
                fait = k.get(cote) or {}
                note(fait.get("source"), f"clivage {i} {cote}")
                if not (fait.get("texte") or "").strip():
                    erreurs.append(f"« {cid} » : clivage {i}, {cote} sans texte.")
            for cote in ("cote_a", "cote_b"):
                if len(k.get(cote) or "") > LONGUEUR_CAMP_MAX:
                    avertis.append(f"« {cid} » : clivage {i}, {cote} fait plus de {LONGUEUR_CAMP_MAX} caractères.")
            if (k.get("cote_a") or "").strip().lower() == (k.get("cote_b") or "").strip().lower():
                erreurs.append(f"« {cid} » : clivage {i}, les deux camps disent la même chose.")

        if c.get("statut") == "verifie":
            orphelines = [i for i in range(1, n + 1) if i not in utilisees]
            if orphelines:
                erreurs.append(f"« {cid} » : source(s) {orphelines} citée(s) par aucun repère ni aucun fait.")

        # URLs : pas de doublon, pas de page d'accueil nue
        vues = {}
        for j, src in enumerate(sources, 1):
            url = (src.get("url") or "").strip()
            if url in vues:
                avertis.append(f"« {cid} » : sources {vues[url]} et {j} pointent la même URL.")
            vues[url] = j
            if re.fullmatch(r"https://[^/]+/?", url):
                avertis.append(f"« {cid} » : la source {j} renvoie vers un site entier, pas vers une page précise.")
            if not (src.get("editeur") or "").strip():
                erreurs.append(f"« {cid} » : source {j} sans éditeur.")
            d = src.get("consulte_le")
            if isinstance(d, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", d):
                if dt.date.fromisoformat(d) > aujourdhui:
                    erreurs.append(f"« {cid} » : source {j} consultée le {d}, dans le futur.")

        d = c.get("verifie_le")
        if isinstance(d, str) and re.fullmatch(r"\d{4}-\d{2}-\d{2}", d) and dt.date.fromisoformat(d) > aujourdhui:
            erreurs.append(f"« {cid} » : vérifié le {d}, dans le futur.")

        if len(c.get("base") or "") > LONGUEUR_BASE_MAX:
            avertis.append(f"« {cid} » : la base fait plus de {LONGUEUR_BASE_MAX} caractères.")
        if not (c.get("ouverture") or "").rstrip().endswith("?"):
            avertis.append(f"« {cid} » : l'ouverture ne se termine pas par une question.")

        # Preuves archivées : une citation verbatim par fait publié
        if c.get("statut") == "verifie":
            attendu = 1 + len(c.get("reperes") or []) + 2 * len(c.get("clivages") or [])
            entree = preuves.get(cid)
            if not entree:
                avertis.append(f"« {cid} » : aucune preuve archivée dans contenu/preuves.json.")
            else:
                liste = entree.get("preuves") or []
                if len(liste) < attendu:
                    avertis.append(f"« {cid} » : {len(liste)} preuves archivées pour {attendu} faits publiés.")
                for p in liste:
                    if not (p.get("citation") or "").strip():
                        erreurs.append(f"« {cid} » : preuve « {p.get('appuie')} » sans citation.")
                    for x in numeros(p.get("source")):
                        if not (isinstance(x, int) and 1 <= x <= n):
                            erreurs.append(f"« {cid} » : preuve « {p.get('appuie')} » renvoie à la source {x}, hors bornes.")

    # Programme : une carte ne revient pas deux jours de suite
    programme = charger(racine / "contenu" / "programme.json", erreurs) or {}
    jours = sorted((programme.get("jours") or {}).items())
    for (d1, j1), (d2, j2) in zip(jours, jours[1:]):
        communes = set(j1.get("cartes") or []) & set(j2.get("cartes") or [])
        if communes and (dt.date.fromisoformat(d2) - dt.date.fromisoformat(d1)).days == 1:
            avertis.append(f"programme : {', '.join(sorted(communes))} apparaît le {d1} et le {d2}, deux jours de suite.")

    return erreurs, avertis


def main():
    erreurs, avertis = verifier()
    for a in avertis:
        print(f"  ! {a}")
    if erreurs:
        print(f"✗ {len(erreurs)} problème(s) de qualité :")
        for e in erreurs:
            print(f"  - {e}")
        return 1
    print(f"✓ Qualité des contenus : rien à corriger" + (f" ({len(avertis)} avertissement(s))" if avertis else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
