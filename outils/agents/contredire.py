#!/usr/bin/env python3
"""
CnH — passe adverse : un second modèle, différent du premier, essaie de démolir le contenu.

    python3 outils/agents/contredire.py produits/*.json --modele openai:gpt-4.1

Il ne réécrit rien : il rend un verdict par affirmation. Tout contenu qui reçoit un
verdict « faux » ou « invérifiable » reste en brouillon et t'est signalé. C'est la
deuxième moitié du garde-fou (la première, `verifier_sources.py`, ne coûte rien).

Règle : le modèle qui contredit ne doit pas être celui qui a produit — sinon il
valide ses propres erreurs. Le script refuse le même modèle sauf `--meme-modele`.

Aucune dépendance : bibliothèque standard uniquement.
"""

import argparse
import json
import sys
from pathlib import Path

ICI = Path(__file__).resolve().parent
RACINE = ICI.parent.parent
sys.path.insert(0, str(ICI))

import fournisseurs as fo  # noqa: E402

CONSIGNE = """Tu es relecteur pour un site français d'éducation populaire. On te donne une
fiche déjà rédigée, ses sources et les citations censées l'appuyer. Ton travail n'est pas
de réécrire : c'est de chercher ce qui cloche.

Pour chaque affirmation publiée (la base, chaque repère, chaque fait d'un camp), donne un verdict :
- "ok" : l'affirmation est exacte et la citation l'appuie réellement.
- "imprecis" : globalement juste, mais la formulation dépasse ce que dit la source
  (chiffre arrondi, date approximative, portée élargie, « en France » au lieu de « en 2016 »…).
- "faux" : l'affirmation contredit la source, ou la source ne parle pas de ça.
- "inverifiable" : la citation n'établit pas l'affirmation (hors sujet, trop vague).

Vérifie aussi :
- qu'aucun camp n'est un épouvantail : les deux positions doivent être les meilleures
  versions du désaccord, également défendables ;
- qu'un fait reste exact lu hors contexte ;
- qu'aucune source n'est un blog, un site de quiz, Wikipédia, ou un contenu généré ;
- que rien ne ressemble à un chiffre inventé ou à une URL plausible mais fabriquée.

Réponds UNIQUEMENT par un objet JSON :
{
  "verdicts": [ {"appuie": "repere 2", "verdict": "imprecis", "pourquoi": "…", "correction": "…"} ],
  "camps_desequilibres": ["clivage 1 : le côté B est un épouvantail parce que …"],
  "sources_douteuses": ["source 3 : blog sans auteur"],
  "avis": "publiable" | "a-corriger" | "a-jeter"
}
Sois sévère : mieux vaut signaler un doute que laisser passer une erreur."""


def resume(donnees):
    """Ce qu'on envoie au relecteur : les affirmations, les sources, les citations."""
    c = donnees["contenu"]
    lignes = [f"# {c.get('titre')} ({c.get('id')}) — {c.get('theme')} / {c.get('format')}", ""]
    lignes.append(f"BASE : {c.get('base')}")
    lignes.append(f"OUVERTURE : {c.get('ouverture')}")
    for i, r in enumerate(c.get("reperes") or [], 1):
        lignes.append(f"REPERE {i} [{r.get('cle')}] (source {r.get('source')}) : {r.get('texte')}")
    for i, k in enumerate(c.get("clivages") or [], 1):
        lignes.append(f"CLIVAGE {i} : {k.get('question')}")
        lignes.append(f"  COTE A : {k.get('cote_a')}")
        lignes.append(f"  FAIT A (source {(k.get('fait_a') or {}).get('source')}) : "
                      f"{(k.get('fait_a') or {}).get('texte')}")
        lignes.append(f"  COTE B : {k.get('cote_b')}")
        lignes.append(f"  FAIT B (source {(k.get('fait_b') or {}).get('source')}) : "
                      f"{(k.get('fait_b') or {}).get('texte')}")
    lignes += ["", "SOURCES :"]
    for i, s in enumerate(c.get("sources") or [], 1):
        lignes.append(f"  {i}. {s.get('titre')} — {s.get('editeur')} — {s.get('url')}")
    lignes += ["", "CITATIONS FOURNIES COMME PREUVES :"]
    for p in donnees.get("preuves") or []:
        lignes.append(f"  [{p.get('appuie')}] source {p.get('source')} : « {p.get('citation')} »")
    return "\n".join(lignes)


def contredire(donnees, modele):
    texte, infos = fo.appeler(modele, systeme=CONSIGNE, message=resume(donnees),
                              json_attendu=True, temperature=0,
                              tache=f"contredire:{donnees['contenu'].get('id')}")
    return fo.extraire_json(texte), infos


def main():
    ap = argparse.ArgumentParser(description="Contre-vérifie des contenus CnH avec un second modèle.")
    ap.add_argument("fichiers", nargs="+")
    ap.add_argument("--modele", default=None)
    ap.add_argument("--meme-modele", action="store_true",
                    help="autorise le même modèle que la production (déconseillé)")
    args = ap.parse_args()

    modele = args.modele or (fo.disponibles() or [None])[0]
    if not modele:
        print("Aucun modèle disponible : voir outils/agents/LISEZMOI.md.")
        return 1

    refuses = 0
    for chemin in args.fichiers:
        chemin = Path(chemin)
        donnees = json.loads(chemin.read_text(encoding="utf-8"))
        produit_par = (donnees.get("production") or {}).get("modele")
        if produit_par == modele and not args.meme_modele:
            print(f"✗ {chemin.name} : produit par {modele}. Un modèle ne se relit pas lui-même "
                  f"— choisis un autre --modele (ou --meme-modele en connaissance de cause).")
            refuses += 1
            continue
        verdict, infos = contredire(donnees, modele)
        donnees["relecture"] = {**verdict, "modele": modele}
        chemin.write_text(json.dumps(donnees, ensure_ascii=False, indent=2), encoding="utf-8")

        graves = [v for v in verdict.get("verdicts", [])
                  if v.get("verdict") in ("faux", "inverifiable")]
        tièdes = [v for v in verdict.get("verdicts", []) if v.get("verdict") == "imprecis"]
        avis = verdict.get("avis", "?")
        marque = "✓" if avis == "publiable" and not graves else "✗"
        if marque == "✗":
            refuses += 1
        print(f"{marque} {donnees['contenu'].get('id')} — avis « {avis} », "
              f"{len(graves)} grave(s), {len(tièdes)} imprécision(s) "
              f"({infos['jetons_entree']}+{infos['jetons_sortie']} jetons)")
        for v in graves + tièdes:
            print(f"    [{v.get('verdict')}] {v.get('appuie')} : {v.get('pourquoi')}")
        for d in verdict.get("camps_desequilibres", []):
            print(f"    [camps] {d}")
        for s in verdict.get("sources_douteuses", []):
            print(f"    [source] {s}")

    print(f"\n{refuses} contenu(s) à reprendre." if refuses
          else "\n✓ Aucun contenu refusé par la relecture.")
    return 1 if refuses else 0


if __name__ == "__main__":
    sys.exit(main())
