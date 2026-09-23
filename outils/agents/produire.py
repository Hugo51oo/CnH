#!/usr/bin/env python3
"""
CnH — fait produire un contenu (carte ou problématique) par un modèle bon marché.

    python3 outils/agents/produire.py sujets/2026-09-19.json --modele mistral:mistral-large-latest
    python3 outils/agents/produire.py --sujet la-fourchette --brief "…" --theme cuisine-alimentation --format objet

Le modèle reçoit `consigne.md` (le cahier des charges CnH) + le brief du sujet, et rend
un JSON { "contenu": …, "preuves": …, "ecarte": … }. Rien n'est publié à ce stade :
le résultat va dans `outils/agents/produits/` et doit passer `verifier_sources.py`,
`contredire.py` puis `journee.py --ecrire`.

Aucune dépendance : bibliothèque standard uniquement.
"""

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent.parent
sys.path.insert(0, str(ICI))
sys.path.insert(0, str(ICI.parent))

import fournisseurs as fo  # noqa: E402

PRODUITS = ICI / "produits"
SUJETS = ICI / "sujets"
DOSSIERS = ICI / "dossiers"

# Ajouté à la consigne quand on fournit le texte réel des pages : sans cette bride,
# un modèle complète de mémoire et ses citations ne se retrouvent nulle part.
BRIDE = """

## RÈGLE QUI PRIME SUR TOUT LE RESTE
Un dossier documentaire suit ce message : le texte réel des pages retenues, numérotées.
Tu n'écris **que** ce que ce dossier permet d'écrire.
- Aucun fait, chiffre, date ou nom qui ne soit pas dans le dossier, même si tu le sais.
- Le tableau `sources` reprend exactement les URLs du dossier, dans le même ordre et
  avec la même numérotation (SOURCE 1 = source 1).
- Chaque `citation` est copiée-collée depuis le dossier, caractère pour caractère.
- Si le dossier ne permet pas d'écrire un repère ou un camp solide, tu en écris un de
  moins et tu l'expliques dans `ecarte`. Un contenu plus court vaut mieux qu'un contenu
  inventé : une vérification automatique relira chaque citation dans la page d'origine.
"""


def ids_publies():
    cartes = json.loads((RACINE / "contenu" / "cartes.json").read_text(encoding="utf-8"))
    return [c["id"] for c in cartes.get("contenus", [])]


def consigne(aujourdhui):
    texte = (ICI / "consigne.md").read_text(encoding="utf-8")
    # la liste des ids et la date vivent dans le dépôt, pas dans la consigne figée
    debut = texte.find("## Ids déjà publiés")
    fin = texte.find("## Ce que tu rends")
    liste = ", ".join(ids_publies())
    texte = (texte[:debut]
             + "## Ids déjà publiés (pour « liens » ; ne pas les recréer)\n" + liste + "\n\n"
             + texte[fin:])
    return texte.replace("2026-09-18", aujourdhui)


def brief_texte(sujet):
    lignes = [f"Produis le contenu suivant, et lui seul.", ""]
    for cle, libelle in (("id", "id"), ("type", "type"), ("theme", "theme"),
                         ("format", "format")):
        if sujet.get(cle):
            lignes.append(f"- {libelle} : `{sujet[cle]}`")
    if sujet.get("themes_croises"):
        lignes.append(f"- themes_croises : {sujet['themes_croises']}")
    lignes.append(f"- sujet : {sujet.get('brief', '').strip()}")
    if sujet.get("pistes"):
        lignes.append("- pistes de matière factuelle (à vérifier ; n'en garde que ce que tu "
                      "peux sourcer, et écarte le reste) : " + " ; ".join(sujet["pistes"]))
    if sujet.get("liens"):
        lignes.append(f"- `liens` possibles : {', '.join(sujet['liens'])}")
    n_rep = sujet.get("reperes", "3 ou 4")
    n_cli = sujet.get("clivages", "2 ou 3")
    lignes.append(f"- {n_rep} repères, {n_cli} clivages.")
    lignes.append("")
    lignes.append("Réponds uniquement par l'objet JSON demandé.")
    return "\n".join(lignes)


def lire_dossier(sujet, dossiers=DOSSIERS):
    """Le texte réel des pages, s'il a été constitué par documenter.py."""
    fichier = Path(dossiers) / f"{sujet['id']}.md"
    return fichier.read_text(encoding="utf-8") if fichier.exists() else ""


def produire(sujet, modele, aujourdhui, temperature=0.2, dossiers=DOSSIERS):
    dossier = lire_dossier(sujet, dossiers)
    systeme = consigne(aujourdhui) + (BRIDE if dossier else "")
    message = brief_texte(sujet)
    if dossier:
        message += "\n\n" + dossier
    else:
        print(f"    ! {sujet['id']} : aucun dossier documentaire. Le modèle va écrire de "
              f"mémoire et ses citations seront rejetées. Lance documenter.py d'abord.")
    texte, infos = fo.appeler(
        modele,
        systeme=systeme,
        message=message,
        json_attendu=True,
        temperature=temperature,
        tache=f"produire:{sujet.get('id')}",
    )
    resultat = fo.extraire_json(texte)
    contenu = resultat.get("contenu") or resultat
    # garde-fous : le modèle ne décide ni de l'id, ni du thème, ni du statut
    contenu["id"] = sujet["id"]
    contenu["type"] = sujet.get("type", "carte")
    contenu["theme"] = sujet["theme"]
    contenu["format"] = sujet["format"]
    if sujet.get("themes_croises"):
        contenu["themes_croises"] = sujet["themes_croises"]
    contenu["statut"] = "brouillon"          # ne devient « verifie » qu'après les contrôles
    contenu["verifie_le"] = aujourdhui
    for src in contenu.get("sources") or []:
        src.setdefault("consulte_le", aujourdhui)
    return {"contenu": contenu,
            "preuves": resultat.get("preuves") or [],
            "ecarte": resultat.get("ecarte") or [],
            "production": infos}


def main():
    ap = argparse.ArgumentParser(description="Fait produire un ou plusieurs contenus CnH.")
    ap.add_argument("sujets", nargs="?", help="fichier JSON de sujets (liste ou {sujets: […]})")
    ap.add_argument("--modele", default=None, help="ex. mistral:mistral-large-latest")
    ap.add_argument("--sujet", help="id d'un sujet unique (sans fichier)")
    ap.add_argument("--brief", default="", help="description du sujet, avec --sujet")
    ap.add_argument("--theme", default="histoire-patrimoine")
    ap.add_argument("--format", dest="format_", default="ouverte")
    ap.add_argument("--type", default="carte")
    ap.add_argument("--sortie", default=str(PRODUITS))
    ap.add_argument("--date", default=dt.date.today().isoformat())
    args = ap.parse_args()

    modele = args.modele or (fo.disponibles() or [None])[0]
    if not modele:
        print("Aucun modèle disponible : ajoute une clé dans .env.local "
              "(voir outils/agents/LISEZMOI.md), ou lance Ollama en local.")
        return 1

    if args.sujets:
        brut = json.loads(Path(args.sujets).read_text(encoding="utf-8"))
        liste = brut["sujets"] if isinstance(brut, dict) else brut
    elif args.sujet:
        liste = [{"id": args.sujet, "type": args.type, "theme": args.theme,
                  "format": args.format_, "brief": args.brief}]
    else:
        ap.error("donne un fichier de sujets ou --sujet")

    sortie = Path(args.sortie)
    sortie.mkdir(parents=True, exist_ok=True)
    jetons = 0
    for sujet in liste:
        print(f"→ {sujet['id']} ({modele}) …", flush=True)
        try:
            resultat = produire(sujet, modele, args.date)
        except Exception as e:
            print(f"  ✗ {type(e).__name__} : {e}")
            continue
        cible = sortie / f"{sujet['id']}.json"
        cible.write_text(json.dumps(resultat, ensure_ascii=False, indent=2), encoding="utf-8")
        i = resultat["production"]
        jetons += i["jetons_entree"] + i["jetons_sortie"]
        print(f"  ✓ {cible.relative_to(RACINE)} — {i['jetons_entree']}+{i['jetons_sortie']} jetons, "
              f"{i['secondes']} s"
              + (f" — écarté : {'; '.join(resultat['ecarte'][:2])}" if resultat["ecarte"] else ""))
    print(f"\nTotal : {jetons} jetons chez {modele.split(':')[0]} (aucun jeton Claude).")
    print("Étape suivante : python3 outils/agents/verifier_sources.py "
          f"{sortie.relative_to(RACINE)}/*.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
