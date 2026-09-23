#!/usr/bin/env python3
"""
CnH — un seul point d'entrée pour appeler n'importe quel modèle de langage.

Pourquoi : la production des cartes coûte cher en jetons. On veut pouvoir la confier
à un modèle bon marché (Mistral, un modèle local via Ollama, …) et garder Claude pour
l'orchestration et la relecture. Ce module rend les fournisseurs interchangeables.

Usage :
    from fournisseurs import appeler
    texte, cout = appeler("mistral:mistral-large-latest", systeme="…", message="…", json_attendu=True)

Modèles : "<fournisseur>:<modele>". Fournisseurs connus ci-dessous (FOURNISSEURS).
Clés d'API : variables d'environnement, ou fichier `.env.local` à la racine du projet
(une ligne `MISTRAL_API_KEY=…` par clé). Ce fichier ne doit jamais partir dans git.

Aucune dépendance : bibliothèque standard uniquement.
"""

import json
import os
import time
import urllib.error
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent.parent
JOURNAL = Path(__file__).resolve().parent / "journal.jsonl"

# fournisseur -> (url, variable de clé, style d'API)
FOURNISSEURS = {
    "mistral":   ("https://api.mistral.ai/v1/chat/completions",      "MISTRAL_API_KEY",  "openai"),
    "openai":    ("https://api.openai.com/v1/chat/completions",      "OPENAI_API_KEY",   "openai"),
    "groq":      ("https://api.groq.com/openai/v1/chat/completions", "GROQ_API_KEY",     "openai"),
    "deepseek":  ("https://api.deepseek.com/chat/completions",       "DEEPSEEK_API_KEY", "openai"),
    "together":  ("https://api.together.xyz/v1/chat/completions",    "TOGETHER_API_KEY", "openai"),
    "anthropic": ("https://api.anthropic.com/v1/messages",           "ANTHROPIC_API_KEY", "anthropic"),
    # Ollama tourne sur la machine : aucun coût, aucune clé.
    "ollama":    ("http://localhost:11434/v1/chat/completions",      None,               "openai"),
}

# Ordre de repli : le premier fournisseur dont la clé est présente.
PAR_DEFAUT = ["openai:gpt-4.1", "ollama:llama3.1", "mistral:mistral-large-latest"]


class ErreurFournisseur(RuntimeError):
    pass


def charger_env(racine=RACINE):
    """Lit .env.local sans écraser l'environnement déjà défini."""
    fichier = racine / ".env.local"
    if not fichier.exists():
        return
    for ligne in fichier.read_text(encoding="utf-8").splitlines():
        ligne = ligne.strip()
        if not ligne or ligne.startswith("#") or "=" not in ligne:
            continue
        cle, _, valeur = ligne.partition("=")
        os.environ.setdefault(cle.strip(), valeur.strip().strip("\"'"))


def cle_de(fournisseur):
    charger_env()
    nom = FOURNISSEURS[fournisseur][1]
    return os.environ.get(nom) if nom else ""


def ollama_repond(timeout=1.5):
    """Ollama tourne-t-il vraiment sur cette machine ? (sinon on ne le propose pas)"""
    import socket
    try:
        with socket.create_connection(("localhost", 11434), timeout=timeout):
            return True
    except OSError:
        return False


def disponibles():
    """Modèles réellement utilisables ici, dans l'ordre de préférence."""
    prets = []
    for ref in PAR_DEFAUT:
        f = ref.split(":", 1)[0]
        if FOURNISSEURS[f][1] is None:
            if f == "ollama" and not ollama_repond():
                continue
            prets.append(ref)
        elif cle_de(f):
            prets.append(ref)
    return prets


def _requete(url, corps, entetes, timeout):
    donnees = json.dumps(corps).encode("utf-8")
    req = urllib.request.Request(url, data=donnees, headers=entetes, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def appeler(modele, systeme, message, json_attendu=False, temperature=0.2,
            max_jetons=8000, essais=3, timeout=180, tache=""):
    """Retourne (texte, infos). `infos` contient les jetons consommés et la durée."""
    if ":" not in modele:
        raise ErreurFournisseur(f"Modèle « {modele} » : il faut la forme « fournisseur:modele ».")
    fournisseur, nom = modele.split(":", 1)
    if fournisseur not in FOURNISSEURS:
        raise ErreurFournisseur(f"Fournisseur « {fournisseur} » inconnu ({', '.join(FOURNISSEURS)}).")
    url, var_cle, style = FOURNISSEURS[fournisseur]
    cle = cle_de(fournisseur)
    if var_cle and not cle:
        raise ErreurFournisseur(
            f"Clé manquante pour {fournisseur} : ajoute « {var_cle}=… » dans .env.local "
            f"à la racine du projet (ce fichier ne doit pas partir dans git)."
        )

    if style == "anthropic":
        entetes = {"content-type": "application/json", "x-api-key": cle,
                   "anthropic-version": "2023-06-01"}
        corps = {"model": nom, "max_tokens": max_jetons, "temperature": temperature,
                 "system": systeme, "messages": [{"role": "user", "content": message}]}
    else:
        entetes = {"content-type": "application/json"}
        if cle:
            entetes["authorization"] = f"Bearer {cle}"
        corps = {"model": nom, "temperature": temperature, "max_tokens": max_jetons,
                 "messages": [{"role": "system", "content": systeme},
                              {"role": "user", "content": message}]}
        if json_attendu:
            corps["response_format"] = {"type": "json_object"}

    debut = time.time()
    derniere = None
    for essai in range(1, essais + 1):
        try:
            rep = _requete(url, corps, entetes, timeout)
            break
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:400]
            derniere = f"HTTP {e.code} — {detail}"
            # 429 / 5xx : on réessaie en patientant, le reste est définitif
            if e.code not in (408, 409, 429) and e.code < 500:
                raise ErreurFournisseur(f"{modele} : {derniere}") from None
        except (urllib.error.URLError, TimeoutError) as e:
            derniere = str(e)
        if essai < essais:
            time.sleep(min(2 ** essai * 5, 60))
    else:
        raise ErreurFournisseur(f"{modele} : {essais} tentatives échouées — {derniere}")

    if style == "anthropic":
        texte = "".join(b.get("text", "") for b in rep.get("content", []))
        u = rep.get("usage", {})
        entree, sortie = u.get("input_tokens", 0), u.get("output_tokens", 0)
    else:
        texte = rep["choices"][0]["message"]["content"]
        u = rep.get("usage", {})
        entree, sortie = u.get("prompt_tokens", 0), u.get("completion_tokens", 0)

    infos = {"modele": modele, "tache": tache, "jetons_entree": entree,
             "jetons_sortie": sortie, "secondes": round(time.time() - debut, 1)}
    try:
        with JOURNAL.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"quand": time.strftime("%Y-%m-%dT%H:%M:%S"), **infos},
                               ensure_ascii=False) + "\n")
    except OSError:
        pass
    return texte, infos


def extraire_json(texte):
    """Récupère l'objet JSON d'une réponse, même entourée de texte ou de ```json."""
    texte = texte.strip()
    if texte.startswith("```"):
        texte = texte.split("```", 2)[1]
        if texte.lstrip().startswith("json"):
            texte = texte.lstrip()[4:]
        texte = texte.rsplit("```", 1)[0] if "```" in texte else texte
    debut, fin = texte.find("{"), texte.rfind("}")
    if debut == -1 or fin == -1:
        raise ValueError("aucun objet JSON dans la réponse du modèle")
    return json.loads(texte[debut:fin + 1])


if __name__ == "__main__":
    charger_env()
    print("Modèles prêts ici :", ", ".join(disponibles()) or "aucun (ajoute une clé dans .env.local)")
    for f, (url, var, style) in FOURNISSEURS.items():
        etat = "local" if var is None else ("clé présente" if cle_de(f) else "clé absente")
        print(f"  {f:10} {etat:14} {url}")
