#!/usr/bin/env python3
"""
CnH — validation des contenus et génération de contenu/donnees.js

Usage (depuis la racine du projet) :
    python3 outils/valider_contenu.py              # valide puis génère contenu/donnees.js
    python3 outils/valider_contenu.py --verifier   # valide seulement, sans rien écrire

Le site lit contenu/donnees.js (et non les JSON directement) : ainsi il
s'ouvre aussi par simple double-clic sur index.html, sans serveur.
Les fichiers JSON restent la source de vérité : on modifie les JSON,
puis on relance ce script.

Code de sortie : 0 si tout est valide, 1 sinon.
Aucune dépendance : Python 3 standard uniquement.
"""

import datetime as dt
import json
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent

THEMES = {
    "histoire-patrimoine",
    "cuisine-alimentation",
    "modes-de-vie-societe",
    "arts-langues-croyances",
    "hors-piste",
}
THEMES_DU_JOUR = THEMES  # 4 thèmes + 1 hors-piste
FORMATS = {"dilemme", "et-si", "chiffre", "objet", "avant-ailleurs", "ouverte"}
TYPES = {"carte", "problematique"}
STATUTS = {"brouillon", "verifie"}
CHAMPS_TEXTE = ("id", "titre", "base", "ouverture")
# Contenu pour nourrir le débat (obligatoire sur les contenus vérifiés)
REPERES_MIN, REPERES_MAX = 2, 6
CLE_MAX = 16          # chiffre ou mot clé affiché en grand dans l'encadré
CLIVAGES_MIN, CLIVAGES_MAX = 2, 4
A_CREUSER_MIN, A_CREUSER_MAX = 1, 2
RE_ID = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
RE_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

# Pages légales publiées dès la V1 : route du site -> fichier source
PAGES = {
    "mentions-legales": "docs/juridique/mentions-legales.md",
    "confidentialite": "docs/juridique/politique-de-confidentialite-v1.md",
}


def date_valide(valeur):
    if not isinstance(valeur, str) or not RE_DATE.match(valeur):
        return False
    try:
        dt.date.fromisoformat(valeur)
        return True
    except ValueError:
        return False


def index_source_valide(valeur, nb_sources):
    """Un renvoi est un numéro de source (1, 2…) ou une liste non vide de numéros."""
    def un(v):
        return isinstance(v, int) and not isinstance(v, bool) and 1 <= v <= nb_sources
    if isinstance(valeur, list):
        return len(valeur) > 0 and len(set(valeur)) == len(valeur) and all(un(v) for v in valeur)
    return un(valeur)


def texte_ok(valeur):
    return isinstance(valeur, str) and bool(valeur.strip())


def valider_debat(c, ref, nb_sources):
    """Vérifie « reperes » (encadrés sourcés) et « clivages » (vignettes : deux camps, un fait chacun, pistes à creuser)."""
    erreurs = []
    verifie = c.get("statut") == "verifie"
    msg_source = f"doit être le numéro d'une source de la carte (1 à {nb_sources}) ou une liste de numéros"

    if "a_savoir" in c:
        erreurs.append(f"{ref} : le champ « a_savoir » a été renommé « reperes » (avec un champ « cle » par point).")

    reperes = c.get("reperes")
    if reperes is None:
        reperes = []
    if not isinstance(reperes, list):
        erreurs.append(f"{ref} : « reperes » doit être une liste.")
        reperes = []
    if verifie and not REPERES_MIN <= len(reperes) <= REPERES_MAX:
        erreurs.append(f"{ref} : « reperes » doit contenir {REPERES_MIN} à {REPERES_MAX} points pour une carte vérifiée.")
    for k, point in enumerate(reperes):
        pref = f"{ref}, repère n°{k + 1}"
        if not isinstance(point, dict):
            erreurs.append(f"{pref} : doit être un objet.")
            continue
        if not texte_ok(point.get("texte")):
            erreurs.append(f"{pref} : texte manquant.")
        if not texte_ok(point.get("cle")) or len(point.get("cle", "")) > CLE_MAX:
            erreurs.append(f"{pref} : « cle » (chiffre ou mot clé) manquante ou trop longue ({CLE_MAX} caractères max).")
        if not index_source_valide(point.get("source"), nb_sources):
            erreurs.append(f"{pref} : « source » {msg_source}.")

    clivages = c.get("clivages")
    if clivages is None:
        clivages = []
    if not isinstance(clivages, list):
        erreurs.append(f"{ref} : « clivages » doit être une liste.")
        clivages = []
    if verifie and not CLIVAGES_MIN <= len(clivages) <= CLIVAGES_MAX:
        erreurs.append(f"{ref} : « clivages » doit contenir {CLIVAGES_MIN} à {CLIVAGES_MAX} points clivants pour une carte vérifiée.")
    for k, cl in enumerate(clivages):
        cref = f"{ref}, clivage n°{k + 1}"
        if not isinstance(cl, dict):
            erreurs.append(f"{cref} : doit être un objet.")
            continue
        for champ in ("question", "cote_a", "cote_b"):
            if not texte_ok(cl.get(champ)):
                erreurs.append(f"{cref} : champ « {champ} » manquant.")
        if texte_ok(cl.get("cote_a")) and cl.get("cote_a") == cl.get("cote_b"):
            erreurs.append(f"{cref} : les deux positions sont identiques.")
        for champ in ("fait_a", "fait_b"):
            f = cl.get(champ)
            if f is None:
                if verifie:
                    erreurs.append(f"{cref} : « {champ} » manquant (un fait historique sourcé par camp).")
                continue
            if not isinstance(f, dict) or not texte_ok(f.get("texte")):
                erreurs.append(f"{cref} : « {champ} » doit contenir un texte.")
                continue
            if not index_source_valide(f.get("source"), nb_sources):
                erreurs.append(f"{cref}, {champ} : « source » {msg_source}.")
        creuser = cl.get("a_creuser")
        if creuser is None:
            if verifie:
                erreurs.append(f"{cref} : « a_creuser » manquant ({A_CREUSER_MIN} à {A_CREUSER_MAX} notions ou faits à rechercher).")
        elif (not isinstance(creuser, list) or not A_CREUSER_MIN <= len(creuser) <= A_CREUSER_MAX
              or any(not texte_ok(x) for x in creuser)):
            erreurs.append(f"{cref} : « a_creuser » doit contenir {A_CREUSER_MIN} à {A_CREUSER_MAX} notions.")
        if "source" in cl:
            erreurs.append(f"{cref} : « source » n'est plus utilisé au niveau du clivage ; les sources vont dans « fait_a » et « fait_b ».")
    return erreurs


def valider_contenus(contenus):
    """Retourne (liste d'erreurs, index id -> contenu)."""
    erreurs = []
    index = {}

    if not isinstance(contenus, list) or not contenus:
        return ["cartes.json : la liste « contenus » est vide ou absente."], index

    for i, c in enumerate(contenus):
        ref = f"contenu n°{i + 1}"
        if not isinstance(c, dict):
            erreurs.append(f"{ref} : doit être un objet.")
            continue
        cid = c.get("id")
        if isinstance(cid, str) and cid:
            ref = f"« {cid} »"

        for champ in CHAMPS_TEXTE:
            if not isinstance(c.get(champ), str) or not c.get(champ).strip():
                erreurs.append(f"{ref} : champ « {champ} » manquant ou vide.")

        if isinstance(cid, str) and cid:
            if not RE_ID.match(cid):
                erreurs.append(f"{ref} : id invalide (minuscules, chiffres et tirets uniquement).")
            if cid in index:
                erreurs.append(f"{ref} : id en double.")
            index[cid] = c

        if c.get("type") not in TYPES:
            erreurs.append(f"{ref} : type « {c.get('type')} » inconnu (attendu : {', '.join(sorted(TYPES))}).")
        if c.get("theme") not in THEMES:
            erreurs.append(f"{ref} : thème « {c.get('theme')} » inconnu.")
        if c.get("format") not in FORMATS:
            erreurs.append(f"{ref} : format « {c.get('format')} » inconnu.")
        if c.get("statut") not in STATUTS:
            erreurs.append(f"{ref} : statut « {c.get('statut')} » inconnu (brouillon ou verifie).")

        if c.get("theme") == "hors-piste":
            croises = c.get("themes_croises")
            if (
                not isinstance(croises, list)
                or len(croises) != 2
                or len(set(croises)) != 2
                or any(t not in THEMES - {"hors-piste"} for t in croises)
            ):
                erreurs.append(f"{ref} : une carte hors-piste doit croiser 2 thèmes différents (themes_croises).")

        derives = c.get("derives")
        if (
            not isinstance(derives, list)
            or not 1 <= len(derives) <= 3
            or any(not isinstance(d, str) or not d.strip() for d in derives)
        ):
            erreurs.append(f"{ref} : « derives » doit contenir 1 à 3 pistes.")

        liens = c.get("liens", [])
        if not isinstance(liens, list) or any(not isinstance(l, str) for l in liens):
            erreurs.append(f"{ref} : « liens » doit être une liste d'identifiants.")

        sources = c.get("sources")
        if not isinstance(sources, list):
            sources = []
            erreurs.append(f"{ref} : « sources » doit être une liste.")
        if c.get("statut") == "verifie":
            if not sources:
                erreurs.append(f"{ref} : une carte vérifiée doit avoir au moins une source.")
            if not index_source_valide(c.get("base_source"), len(sources)):
                erreurs.append(f"{ref} : « base_source » manquant ou invalide (la base doit renvoyer à une source).")
            if not date_valide(c.get("verifie_le")):
                erreurs.append(f"{ref} : « verifie_le » manquant ou invalide (AAAA-MM-JJ).")
        erreurs += valider_debat(c, ref, len(sources))

        for j, s in enumerate(sources):
            sref = f"{ref}, source n°{j + 1}"
            if not isinstance(s, dict):
                erreurs.append(f"{sref} : doit être un objet.")
                continue
            for champ in ("titre", "editeur", "url"):
                if not isinstance(s.get(champ), str) or not s.get(champ).strip():
                    erreurs.append(f"{sref} : champ « {champ} » manquant.")
            if isinstance(s.get("url"), str) and not s["url"].startswith("https://"):
                erreurs.append(f"{sref} : l'URL doit commencer par https://")
            if not date_valide(s.get("consulte_le")):
                erreurs.append(f"{sref} : « consulte_le » manquant ou invalide (AAAA-MM-JJ).")

    # (voir valider_debat pour « a_savoir » et « clivages »)

    # Liens vers d'autres contenus
    for cid, c in index.items():
        for lien in c.get("liens", []) if isinstance(c.get("liens"), list) else []:
            if lien == cid:
                erreurs.append(f"« {cid} » : un contenu ne peut pas pointer vers lui-même.")
            elif lien not in index:
                erreurs.append(f"« {cid} » : lien vers « {lien} » introuvable.")
            elif index[lien].get("statut") != "verifie" and c.get("statut") == "verifie":
                erreurs.append(f"« {cid} » : lien vers « {lien} », qui est encore en brouillon.")

    return erreurs, index


def valider_programme(programme, index):
    erreurs = []
    jours = programme.get("jours") if isinstance(programme, dict) else None
    if not isinstance(jours, dict):
        return ["programme.json : objet « jours » manquant."]

    for date, jour in sorted(jours.items()):
        ref = f"programme du {date}"
        if not date_valide(date):
            erreurs.append(f"{ref} : date invalide (AAAA-MM-JJ).")
        if not isinstance(jour, dict):
            erreurs.append(f"{ref} : doit être un objet.")
            continue

        pb = jour.get("problematique")
        if pb not in index:
            erreurs.append(f"{ref} : problématique « {pb} » introuvable.")
        else:
            if index[pb].get("type") != "problematique":
                erreurs.append(f"{ref} : « {pb} » n'est pas une problématique.")
            if index[pb].get("statut") != "verifie":
                erreurs.append(f"{ref} : « {pb} » est en brouillon.")

        cartes = jour.get("cartes")
        if not isinstance(cartes, list) or len(cartes) != 5:
            erreurs.append(f"{ref} : il faut exactement 5 cartes.")
            continue
        if len(set(cartes)) != 5:
            erreurs.append(f"{ref} : une carte apparaît deux fois.")

        trouvees = []
        for cid in cartes:
            if cid not in index:
                erreurs.append(f"{ref} : carte « {cid} » introuvable.")
                continue
            carte = index[cid]
            if carte.get("type") != "carte":
                erreurs.append(f"{ref} : « {cid} » n'est pas une carte.")
            if carte.get("statut") != "verifie":
                erreurs.append(f"{ref} : « {cid} » est en brouillon.")
            trouvees.append(carte)

        if len(trouvees) == 5:
            themes = sorted(c.get("theme") for c in trouvees)
            if set(themes) != THEMES_DU_JOUR or len(set(themes)) != 5:
                erreurs.append(f"{ref} : il faut une carte par thème + 1 hors-piste (reçu : {', '.join(themes)}).")
            formats = [c.get("format") for c in trouvees]
            if len(set(formats)) != 5:
                erreurs.append(f"{ref} : les 5 cartes doivent avoir 5 formats différents (reçu : {', '.join(formats)}).")
    return erreurs


def lire_json(chemin, erreurs):
    try:
        with open(chemin, encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        erreurs.append(f"Fichier introuvable : {chemin.relative_to(RACINE)}")
    except json.JSONDecodeError as e:
        erreurs.append(f"{chemin.relative_to(RACINE)} : JSON invalide (ligne {e.lineno}, colonne {e.colno}) — {e.msg}")
    return None


def valider(racine=RACINE):
    """Valide les contenus. Retourne (erreurs, données prêtes à publier ou None)."""
    erreurs = []
    cartes = lire_json(racine / "contenu" / "cartes.json", erreurs)
    programme = lire_json(racine / "contenu" / "programme.json", erreurs)
    if erreurs:
        return erreurs, None

    e_contenus, index = valider_contenus(cartes.get("contenus") if isinstance(cartes, dict) else None)
    erreurs += e_contenus
    erreurs += valider_programme(programme, index)

    pages = {}
    for route, fichier in PAGES.items():
        chemin = racine / fichier
        if chemin.exists():
            pages[route] = chemin.read_text(encoding="utf-8")
        else:
            erreurs.append(f"Page légale introuvable : {fichier}")

    donnees = {
        "genere_le": dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        # Seuls les contenus vérifiés sont publiés.
        "contenus": [c for c in cartes.get("contenus", []) if isinstance(c, dict) and c.get("statut") == "verifie"],
        "programme": programme,
        "pages": pages,
    }
    return erreurs, donnees


def ecrire_donnees(donnees, racine=RACINE):
    cible = racine / "contenu" / "donnees.js"
    texte = json.dumps(donnees, ensure_ascii=False, indent=2)
    # Empêche une fermeture de balise <script> accidentelle dans un texte
    texte = texte.replace("</", "<\\/")
    cible.write_text(
        "/* Fichier généré par outils/valider_contenu.py — ne pas modifier à la main.\n"
        "   Modifier contenu/cartes.json ou contenu/programme.json, puis relancer le script. */\n"
        f"window.CNH_DONNEES = {texte};\n",
        encoding="utf-8",
    )
    return cible


def main(argv):
    verifier_seulement = "--verifier" in argv
    erreurs, donnees = valider()
    if erreurs:
        print(f"✗ {len(erreurs)} problème(s) dans les contenus :")
        for e in erreurs:
            print(f"  - {e}")
        print("Rien n'a été généré. Corrige puis relance.")
        return 1

    nb_cartes = sum(1 for c in donnees["contenus"] if c.get("type") == "carte")
    nb_pb = sum(1 for c in donnees["contenus"] if c.get("type") == "problematique")
    nb_jours = len(donnees["programme"].get("jours", {}))
    print(f"✓ Contenus valides : {nb_cartes} carte(s), {nb_pb} problématique(s), {nb_jours} jour(s) programmé(s).")
    if verifier_seulement:
        return 0
    cible = ecrire_donnees(donnees)
    print(f"✓ {cible.relative_to(RACINE)} mis à jour.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
