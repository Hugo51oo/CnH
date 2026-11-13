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

import http.client
import json
import os
import ssl
import time
import urllib.error
import urllib.request
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent.parent


def _contexte_ssl():
    """Le Python de python.org sur Mac n'a aucun certificat tant qu'on n'a pas lancé son
    « Install Certificates.command » : toutes les connexions HTTPS échouent alors avec
    CERTIFICATE_VERIFY_FAILED. On se rabat sur les certificats fournis par macOS."""
    contexte = ssl.create_default_context()
    chemins = ssl.get_default_verify_paths()
    vides = not any(c and os.path.exists(c) for c in (chemins.cafile, chemins.capath))
    if vides and os.path.exists("/etc/ssl/cert.pem"):
        contexte.load_verify_locations("/etc/ssl/cert.pem")
    return contexte


# Toutes les requêtes de la chaîne (urllib.request.urlopen) passent par ce contexte.
CONTEXTE_SSL = _contexte_ssl()
urllib.request.install_opener(
    urllib.request.build_opener(urllib.request.HTTPSHandler(context=CONTEXTE_SSL)))
JOURNAL = Path(__file__).resolve().parent / "journal.jsonl"

# fournisseur -> (url, variable de clé, style d'API)
FOURNISSEURS = {
    # Gemini et Groq ont une offre gratuite, sans carte bancaire : la chaîne peut tourner à 0 €.
    # API native : son mode « compatible OpenAI » mêle des bouts de raisonnement à la réponse
    "gemini":    ("https://generativelanguage.googleapis.com/v1beta/models/{modele}:generateContent",
                  "GEMINI_API_KEY", "gemini"),
    # OpenRouter : modèles « :free » (Gemma, Qwen, Nemotron…), sans carte bancaire.
    "openrouter": ("https://openrouter.ai/api/v1/chat/completions",  "OPENROUTER_API_KEY", "openai"),
    # Cohere : clé d'essai gratuite (1 000 appels/mois, usage non commercial — c'est le cas de CnH).
    "cohere":    ("https://api.cohere.ai/compatibility/v1/chat/completions", "COHERE_API_KEY", "openai"),
    "mistral":   ("https://api.mistral.ai/v1/chat/completions",      "MISTRAL_API_KEY",  "openai"),
    "openai":    ("https://api.openai.com/v1/chat/completions",      "OPENAI_API_KEY",   "openai"),
    "groq":      ("https://api.groq.com/openai/v1/chat/completions", "GROQ_API_KEY",     "openai"),
    "deepseek":  ("https://api.deepseek.com/chat/completions",       "DEEPSEEK_API_KEY", "openai"),
    "together":  ("https://api.together.xyz/v1/chat/completions",    "TOGETHER_API_KEY", "openai"),
    "anthropic": ("https://api.anthropic.com/v1/messages",           "ANTHROPIC_API_KEY", "anthropic"),
    # Ollama tourne sur la machine : aucun coût, aucune clé.
    "ollama":    ("http://localhost:11434/v1/chat/completions",      None,               "openai"),
}

# Ordre de repli : le premier fournisseur dont la clé est présente. Les offres gratuites
# d'abord : Gemini écrit, Groq (un autre modèle, comme l'exige la relecture) contredit.
PAR_DEFAUT = ["gemini:gemini-3.5-flash", "groq:openai/gpt-oss-120b", "ollama:llama3.1",
              "openai:gpt-4.1", "mistral:mistral-large-latest"]



AGENT = "CnH-chaine-agents/1.0 (+https://hugo51oo.github.io/CnH/)"


class ErreurFournisseur(RuntimeError):
    pass


class Surcharge(ErreurFournisseur):
    """Le fournisseur refuse pour l'instant (surcharge, quota par minute) : un autre
    modèle du même fournisseur peut répondre."""


# Modèles de rechange quand le modèle demandé reste surchargé (fréquent sur les offres
# gratuites). Même fournisseur, donc la règle « relecteur différent » tient toujours.
REPLIS = {
    "gemini:gemini-3.5-flash": ["gemini:gemini-flash-latest", "gemini:gemini-3.1-flash-lite"],
}


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
    # Certains fournisseurs (Groq, derrière Cloudflare) refusent l'agent « Python-urllib »
    entetes = {"user-agent": AGENT, **entetes}
    req = urllib.request.Request(url, data=donnees, headers=entetes, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def appeler(modele, systeme, message, json_attendu=False, temperature=0.2,
            max_jetons=8000, essais=3, timeout=180, tache=""):
    """Retourne (texte, infos). `infos` contient les jetons consommés et la durée.

    Si le modèle reste surchargé, essaie ses modèles de rechange (REPLIS) ; `infos["modele"]`
    dit lequel a réellement répondu."""
    candidats = [modele] + REPLIS.get(modele, [])
    for i, candidat in enumerate(candidats):
        try:
            return _appeler(candidat, systeme, message, json_attendu, temperature,
                            max_jetons, essais, timeout, tache)
        except Surcharge:
            if i == len(candidats) - 1:
                raise
            print(f"    ({candidat} surchargé : on essaie {candidats[i + 1]})")


def _appeler(modele, systeme, message, json_attendu, temperature, max_jetons, essais,
             timeout, tache):
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
    elif style == "gemini":
        url = url.format(modele=nom)
        entetes = {"content-type": "application/json", "x-goog-api-key": cle}
        # Le raisonnement interne compte dans maxOutputTokens : sans marge, la réponse est
        # coupée au milieu (JSON incomplet). Raisonnement court + marge.
        config = {"temperature": temperature, "maxOutputTokens": max_jetons + 16000,
                  "thinkingConfig": {"thinkingLevel": "low"}}
        if json_attendu:
            config["responseMimeType"] = "application/json"
        corps = {"systemInstruction": {"parts": [{"text": systeme}]},
                 "contents": [{"role": "user", "parts": [{"text": message}]}],
                 "generationConfig": config}
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
        attente = min(2 ** essai * 5, 60)
        try:
            rep = _requete(url, corps, entetes, timeout)
            break
        except urllib.error.HTTPError as e:
            detail = e.read().decode("utf-8", "replace")[:400]
            derniere = f"HTTP {e.code} — {detail}"
            # 429 / 5xx : on réessaie en patientant, le reste est définitif
            if e.code not in (408, 409, 429) and e.code < 500:
                raise ErreurFournisseur(f"{modele} : {derniere}") from None
            # Les offres gratuites limitent les jetons par minute et disent combien attendre
            attente = delai_demande(e.headers.get("retry-after")) or attente
        except (urllib.error.URLError, TimeoutError, ConnectionError,
                http.client.HTTPException) as e:
            # coupures passagères (Wi-Fi, serveur surchargé qui raccroche) : on réessaie
            derniere = f"{type(e).__name__} — {e}"
        if essai < essais:
            time.sleep(attente)
    else:
        # On n'arrive ici qu'après des pannes passagères (surcharge, délai dépassé, coupure) :
        # les erreurs définitives (clé refusée, requête invalide) sont levées plus haut.
        raise Surcharge(f"{modele} : {essais} tentatives échouées — {derniere}")

    if style == "anthropic":
        texte = "".join(b.get("text", "") for b in rep.get("content", []))
        u = rep.get("usage", {})
        entree, sortie = u.get("input_tokens", 0), u.get("output_tokens", 0)
    elif style == "gemini":
        candidat = (rep.get("candidates") or [{}])[0]
        if candidat.get("finishReason") == "MAX_TOKENS":
            raise ErreurFournisseur(f"{modele} : réponse coupée (longueur maximale atteinte).")
        # les parties « thought » sont le raisonnement interne du modèle, pas la réponse
        texte = "".join(p.get("text", "") for p in (candidat.get("content") or {}).get("parts", [])
                        if not p.get("thought"))
        u = rep.get("usageMetadata", {})
        entree = u.get("promptTokenCount", 0)
        sortie = u.get("candidatesTokenCount", 0) + u.get("thoughtsTokenCount", 0)
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


def delai_demande(valeur, plafond=90):
    """Secondes d'attente demandées par l'en-tête Retry-After (None si absent ou illisible)."""
    try:
        return min(max(float(valeur), 1), plafond)
    except (TypeError, ValueError):
        return None


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
