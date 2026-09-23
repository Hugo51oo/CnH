#!/usr/bin/env python3
"""
CnH — trouve des URLs de sources candidates pour chaque sujet d'une journée.

    python3 outils/agents/chercher.py outils/agents/sujets/2026-09-20.json --ecrire

C'est la seule étape qui a besoin de naviguer. Elle passe par la recherche web
d'OpenAI (API « responses », outil `web_search`) : le modèle cherche, le script ne
garde que les URLs et **ne croit aucun fait** rapporté au passage. Les faits viendront
du texte réel des pages, téléchargé ensuite par `documenter.py`.

Le résultat est écrit dans le champ `sources_candidates` du fichier de sujets, où tu
peux — et devrais — le relire, en retirer et en ajouter : le choix des sources reste
une décision éditoriale (règle 1 du projet).

Sans clé OpenAI, le script ne fait rien de plus que te rappeler quels domaines sont
acceptés : tu peux toujours remplir `sources_candidates` à la main.

Aucune dépendance : bibliothèque standard uniquement.
"""

import argparse
import json
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent.parent
sys.path.insert(0, str(ICI))

import fournisseurs as fo  # noqa: E402

# Domaines acceptés comme source d'un fait publié (voir docs/00-vision.md).
# Tout le reste est écarté automatiquement, y compris Wikipédia.
DOMAINES = [
    # institutions françaises
    "insee.fr", "gouv.fr", "legifrance.gouv.fr", "vie-publique.fr", "senat.fr",
    "assemblee-nationale.fr", "ccomptes.fr", "conseil-etat.fr", "ademe.fr", "anses.fr",
    "inrae.fr", "ined.fr", "cnrs.fr", "ars.sante.fr", "education.gouv.fr",
    "culture.gouv.fr", "pop.culture.gouv.fr", "francearchives.gouv.fr",
    "archives-nationales.culture.gouv.fr", "bnf.fr", "gallica.bnf.fr", "data.gouv.fr",
    # international
    "unesco.org", "who.int", "oecd.org", "europa.eu", "un.org", "worldbank.org",
    "ourworldindata.org",
    # académique et éditorial vérifié
    "theconversation.com", "openedition.org", "persee.fr", "cairn.info", "hal.science",
    "smarthistory.org", "worldhistory.org",
    # collections ouvertes et musées
    "metmuseum.org", "si.edu", "europeana.eu", "quaibranly.fr", "louvre.fr",
    "britishmuseum.org", "museeprotestant.org", "chateauversailles.fr",
    "citedelarchitecture.fr", "mucem.org", "rmn.fr", "pompidou.fr",
]

CONSIGNE = """Tu cherches des sources pour une fiche documentaire française.

Tu rends UNIQUEMENT des URLs de pages précises (pas des pages d'accueil, pas des
résultats de recherche), en https, et uniquement sur ces domaines :
{domaines}

Interdits : Wikipédia, blogs, presse généraliste, sites de quiz, agrégateurs, PDF de
plus de 200 pages. Une page par fait potentiel ; privilégie les pages qui contiennent
des chiffres datés, des textes de loi, ou des analyses signées.

Réponds uniquement par un objet JSON :
{{"urls": ["https://…", "https://…"], "pourquoi": ["ce que chaque page apporte", "…"]}}

Entre 5 et 9 URLs. Si tu n'en trouves pas assez sur ces domaines, rends-en moins :
une URL inventée ou approximative fait échouer toute la chaîne."""


def domaine_accepte(url):
    hote = re.sub(r"^https://", "", url.strip()).split("/")[0].lower()
    return any(hote == d or hote.endswith("." + d) for d in DOMAINES)


def chercher_openai(question, modele="gpt-4.1", max_essais=2):
    """Recherche web via l'API « responses » d'OpenAI. Retourne (urls, pourquoi)."""
    cle = fo.cle_de("openai")
    if not cle:
        raise fo.ErreurFournisseur(
            "Clé manquante pour openai : ajoute « OPENAI_API_KEY=… » dans .env.local, "
            "ou remplis « sources_candidates » à la main.")
    corps = {
        "model": modele,
        "tools": [{"type": "web_search"}],
        "instructions": CONSIGNE.format(domaines=", ".join(DOMAINES)),
        "input": question,
    }
    req = urllib.request.Request(
        "https://api.openai.com/v1/responses",
        data=json.dumps(corps).encode("utf-8"),
        headers={"content-type": "application/json", "authorization": f"Bearer {cle}"},
        method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        rep = json.loads(r.read().decode("utf-8"))

    texte = ""
    for item in rep.get("output", []):
        for bloc in item.get("content", []) or []:
            if bloc.get("type") in ("output_text", "text"):
                texte += bloc.get("text", "")
    u = rep.get("usage", {})
    infos = {"modele": f"openai:{modele}", "tache": "chercher",
             "jetons_entree": u.get("input_tokens", 0),
             "jetons_sortie": u.get("output_tokens", 0), "secondes": 0}
    donnees = fo.extraire_json(texte)
    return donnees.get("urls") or [], donnees.get("pourquoi") or [], infos


def question_du_sujet(sujet):
    morceaux = [f"Sujet : {sujet.get('brief', sujet['id'])}"]
    if sujet.get("pistes"):
        morceaux.append("Pistes à documenter : " + " ; ".join(sujet["pistes"]))
    morceaux.append("Trouve les pages officielles ou académiques qui portent ces faits.")
    return "\n".join(morceaux)


def main():
    ap = argparse.ArgumentParser(description="Trouve des sources candidates pour une journée CnH.")
    ap.add_argument("sujets")
    ap.add_argument("--modele", default="gpt-4.1")
    ap.add_argument("--ecrire", action="store_true",
                    help="écrit les URLs dans le fichier de sujets")
    ap.add_argument("--seulement", help="ne traiter qu'un id")
    args = ap.parse_args()

    chemin = Path(args.sujets)
    brut = json.loads(chemin.read_text(encoding="utf-8"))
    sujets = brut["sujets"] if isinstance(brut, dict) else brut

    total = 0
    for s in sujets:
        if args.seulement and s["id"] != args.seulement:
            continue
        if s.get("sources_candidates"):
            print(f"  = {s['id']} — {len(s['sources_candidates'])} URL(s) déjà là, on n'y touche pas.")
            continue
        try:
            urls, pourquoi, infos = chercher_openai(question_du_sujet(s), args.modele)
        except Exception as e:
            print(f"  ✗ {s['id']} : {type(e).__name__} — {e}")
            continue
        gardees = [u for u in urls if u.startswith("https://") and domaine_accepte(u)]
        ecartees = [u for u in urls if u not in gardees]
        s["sources_candidates"] = gardees
        total += infos["jetons_entree"] + infos["jetons_sortie"]
        print(f"  ✓ {s['id']} — {len(gardees)} URL(s) retenue(s)"
              + (f", {len(ecartees)} hors domaines acceptés" if ecartees else ""))
        for u, p in zip(gardees, pourquoi):
            print(f"      {u}\n        → {p}")
        for u in ecartees:
            print(f"      écartée (domaine non accepté) : {u}")

    if args.ecrire:
        chemin.write_text(json.dumps(brut, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"\n✓ URLs écrites dans {chemin}. Relis-les avant la suite : "
              f"une source vaut ce que vaut son éditeur.")
        print(f"  Étape suivante : python3 outils/agents/documenter.py {chemin}")
    else:
        print("\n(essai à blanc) Relance avec --ecrire pour enregistrer ces URLs.")
    print(f"{total} jetons chez OpenAI (aucun jeton Claude).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
