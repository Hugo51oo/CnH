#!/usr/bin/env python3
"""
CnH — trouve des URLs de sources candidates pour chaque sujet d'une journée.

    python3 outils/agents/chercher.py outils/agents/sujets/2026-09-20.json --ecrire

C'est la seule étape qui a besoin de naviguer. Trois façons, au choix (`--modele`) :

- `wikipedia` (par défaut, gratuit, sans clé) : on cherche les articles Wikipédia du
  sujet et on récupère **les liens qu'ils citent**. Wikipédia n'est jamais une source
  publiée ; ses références vers l'INSEE, Légifrance, l'UNESCO… le sont. Si une clé
  Gemini est là, Gemini choisit les plus pertinents **dans cette liste**, sans pouvoir
  en ajouter : rien ne peut être inventé.
- `gemini:…` : recherche Google de Gemini (outil `google_search`) — pas ouverte à
  toutes les offres gratuites.
- `openai:…` : recherche web d'OpenAI (API « responses », payante).

Dans tous les cas, le script ne garde que les URLs et **ne croit aucun fait** rapporté
au passage. Les faits viendront
du texte réel des pages, téléchargé ensuite par `documenter.py`.

Le résultat est écrit dans le champ `sources_candidates` du fichier de sujets, où tu
peux — et devrais — le relire, en retirer et en ajouter : le choix des sources reste
une décision éditoriale (règle 1 du projet).

En dernier recours, de plus que te rappeler quels domaines sont
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


class _SansRedirection(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        return None


def resoudre_redirection(url, timeout=15):
    """Les liens de Google sont des redirections (vertexaisearch…) : on lit la vraie adresse
    dans l'en-tête Location, sans aller jusqu'à la page. None si ce n'est pas une redirection."""
    ouvreur = urllib.request.build_opener(
        _SansRedirection, urllib.request.HTTPSHandler(context=fo.CONTEXTE_SSL))
    try:
        ouvreur.open(urllib.request.Request(url, method="HEAD"), timeout=timeout)
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308):
            return e.headers.get("location")
    except (urllib.error.URLError, TimeoutError):
        pass
    return None


def chercher_gemini(question, modele="gemini-flash-latest"):
    """Recherche Google via Gemini (offre gratuite). Retourne (urls, pourquoi, infos).

    On garde deux choses : les URLs que le modèle écrit dans sa réponse, et celles des
    pages que Google lui a réellement renvoyées (groundingChunks), qui ne peuvent pas
    être inventées. Toutes repasseront de toute façon par le téléchargement et la
    vérification des citations."""
    cle = fo.cle_de("gemini")
    if not cle:
        raise fo.ErreurFournisseur(
            "Clé manquante pour gemini : ajoute « GEMINI_API_KEY=… » dans .env.local "
            "(gratuite sur https://aistudio.google.com/apikey).")
    corps = {
        "systemInstruction": {"parts": [{"text": CONSIGNE.format(domaines=", ".join(DOMAINES))}]},
        "contents": [{"role": "user", "parts": [{"text": question}]}],
        "tools": [{"google_search": {}}],
        "generationConfig": {"temperature": 0.2},
    }
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{modele}:generateContent",
        data=json.dumps(corps).encode("utf-8"),
        headers={"content-type": "application/json", "x-goog-api-key": cle,
                 "user-agent": fo.AGENT},
        method="POST")
    with urllib.request.urlopen(req, timeout=300) as r:
        rep = json.loads(r.read().decode("utf-8"))

    candidat = (rep.get("candidates") or [{}])[0]
    texte = "".join(p.get("text", "") for p in (candidat.get("content") or {}).get("parts", []))
    try:
        donnees = fo.extraire_json(texte)
    except ValueError:
        donnees = {}
    urls = list(donnees.get("urls") or [])
    pourquoi = list(donnees.get("pourquoi") or [])
    for morceau in (candidat.get("groundingMetadata") or {}).get("groundingChunks", []):
        web = morceau.get("web") or {}
        vraie = resoudre_redirection(web.get("uri", "")) or web.get("uri", "")
        if vraie and vraie not in urls:
            urls.append(vraie)
            pourquoi.append(f"page renvoyée par Google : {web.get('title', '')}")
    u = rep.get("usageMetadata", {})
    infos = {"modele": f"gemini:{modele}", "tache": "chercher",
             "jetons_entree": u.get("promptTokenCount", 0),
             "jetons_sortie": u.get("candidatesTokenCount", 0), "secondes": 0}
    return urls, pourquoi, infos


# Liens cités par Wikipédia qui ne sont pas des pages de contenu (notices d'autorité,
# catalogues, identifiants) : inutiles comme source d'un fait.
HOTES_SANS_CONTENU = ("data.bnf.fr", "catalogue.bnf.fr", "isni", "viaf", "idref",
                      "wikidata", "archive.org/details")


def _api_wikipedia(langue, parametres, timeout=30):
    import urllib.parse
    parametres = {**parametres, "format": "json", "formatversion": "2"}
    url = f"https://{langue}.wikipedia.org/w/api.php?" + urllib.parse.urlencode(parametres)
    req = urllib.request.Request(url, headers={"user-agent": fo.AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def liens_cites_par_wikipedia(requete, langue="fr", articles=2):
    """URLs citées par les premiers articles Wikipédia trouvés pour `requete`."""
    trouves = _api_wikipedia(langue, {"action": "query", "list": "search",
                                      "srsearch": requete, "srlimit": articles})
    titres = [r["title"] for r in trouves.get("query", {}).get("search", [])]
    if not titres:
        return []
    pages = _api_wikipedia(langue, {"action": "query", "prop": "extlinks",
                                    "titles": "|".join(titres), "ellimit": "max"})
    liens = []
    for page in pages.get("query", {}).get("pages", []):
        for lien in page.get("extlinks", []):
            liens.append((lien.get("url", ""), page.get("title", "")))
    return liens


def candidates_wikipedia(sujet):
    """(url, article) acceptables pour ce sujet, sans doublon, dans l'ordre de découverte."""
    requetes = [sujet.get("brief", sujet["id"])] + list(sujet.get("pistes") or [])
    vues, gardees, erreurs = set(), [], []
    for requete in requetes:
        try:
            liens = liens_cites_par_wikipedia(requete)
        except (urllib.error.URLError, TimeoutError, ValueError) as e:
            erreurs.append(f"{type(e).__name__} — {getattr(e, 'reason', e)}")
            continue
        for url, article in liens:
            url = url.strip()
            if url.startswith("http://"):
                url = "https://" + url[len("http://"):]
            if (url in vues or not url.startswith("https://") or not domaine_accepte(url)
                    or any(h in url for h in HOTES_SANS_CONTENU)):
                continue
            vues.add(url)
            gardees.append((url, article))
    if erreurs and len(erreurs) == len(requetes):
        # tout a échoué : ce n'est pas « aucune source », c'est Wikipédia injoignable
        raise urllib.error.URLError(f"Wikipédia injoignable ({erreurs[0]})")
    return gardees


TRI = """Tu choisis des sources pour une fiche documentaire française. On te donne un sujet,
des pistes, et une liste numérotée d'URLs (citées par des articles Wikipédia sur le sujet).
Choisis les {n} URLs les plus susceptibles de contenir des faits précis (chiffres datés,
textes de loi, analyses) sur CE sujet. Tu ne peux choisir QUE dans la liste.
Réponds uniquement par un objet JSON : {{"numeros": [3, 1, 7], "pourquoi": ["…", "…", "…"]}}"""


def chercher_wikipedia(sujet, trieur=None, garder=9):
    """Retourne (urls, pourquoi, infos). `trieur` = modèle qui choisit dans la liste."""
    candidates = candidates_wikipedia(sujet)
    infos = {"modele": "wikipedia", "tache": "chercher", "jetons_entree": 0,
             "jetons_sortie": 0, "secondes": 0}
    if len(candidates) <= garder or not trieur:
        return ([u for u, _ in candidates[:garder]],
                [f"citée par l'article Wikipédia « {a} »" for _, a in candidates[:garder]], infos)
    liste = "\n".join(f"{i}. {u}  (cité par « {a} »)" for i, (u, a) in enumerate(candidates, 1))
    message = (f"Sujet : {sujet.get('brief', sujet['id'])}\n"
               f"Pistes : {' ; '.join(sujet.get('pistes') or [])}\n\nURLs :\n{liste}")
    numeros, pourquoi, derniere = [], [], None
    for _ in range(2):
        try:
            texte, infos = fo.appeler(trieur, systeme=TRI.format(n=garder), message=message,
                                      json_attendu=True, max_jetons=4000, temperature=0,
                                      tache=f"chercher:{sujet['id']}")
            choix = fo.extraire_json(texte)
            numeros = [n for n in choix.get("numeros", []) if isinstance(n, int)
                       and 1 <= n <= len(candidates)]
            pourquoi = [str(x) for x in choix.get("pourquoi", [])]
        except Exception as e:
            derniere = f"{type(e).__name__} — {e}"
        if numeros:
            break
    if not numeros:
        # Garder les liens « au hasard » donnerait des sources hors sujet : on s'arrête.
        raise fo.ErreurFournisseur(f"tri des sources par {trieur} impossible ({derniere}).")
    urls = [candidates[n - 1][0] for n in numeros[:garder]]
    pourquoi = (pourquoi + [""] * len(urls))[:len(urls)]
    return urls, pourquoi, infos


def chercher(sujet, modele):
    """`modele` = « wikipedia », ou « fournisseur:nom » ; sans préfixe, OpenAI (ancien usage)."""
    if modele == "wikipedia":
        trieur = next((m for m in fo.disponibles() if not m.startswith("ollama:")), None)
        return chercher_wikipedia(sujet, trieur)
    fournisseur, _, nom = modele.rpartition(":")
    if fournisseur == "gemini":
        return chercher_gemini(question_du_sujet(sujet), nom)
    return chercher_openai(question_du_sujet(sujet), nom)


def modele_par_defaut():
    return "wikipedia"


def question_du_sujet(sujet):
    morceaux = [f"Sujet : {sujet.get('brief', sujet['id'])}"]
    if sujet.get("pistes"):
        morceaux.append("Pistes à documenter : " + " ; ".join(sujet["pistes"]))
    morceaux.append("Trouve les pages officielles ou académiques qui portent ces faits.")
    return "\n".join(morceaux)


def main():
    ap = argparse.ArgumentParser(description="Trouve des sources candidates pour une journée CnH.")
    ap.add_argument("sujets")
    ap.add_argument("--modele", default=None,
                    help="wikipedia (gratuit, par défaut), gemini:… ou openai:…")
    ap.add_argument("--ecrire", action="store_true",
                    help="écrit les URLs dans le fichier de sujets")
    ap.add_argument("--seulement", help="ne traiter qu'un id")
    args = ap.parse_args()

    chemin = Path(args.sujets)
    brut = json.loads(chemin.read_text(encoding="utf-8"))
    sujets = brut["sujets"] if isinstance(brut, dict) else brut

    modele = args.modele or modele_par_defaut()
    total, sans_source = 0, []
    for s in sujets:
        if args.seulement and s["id"] != args.seulement:
            continue
        if s.get("sources_candidates"):
            print(f"  = {s['id']} — {len(s['sources_candidates'])} URL(s) déjà là, on n'y touche pas.")
            continue
        try:
            urls, pourquoi, infos = chercher(s, modele)
        except Exception as e:
            print(f"  ✗ {s['id']} : {type(e).__name__} — {e}")
            sans_source.append(s["id"])
            continue
        gardees = [u for u in urls if u.startswith("https://") and domaine_accepte(u)]
        ecartees = [u for u in urls if u not in gardees]
        s["sources_candidates"] = gardees
        total += infos["jetons_entree"] + infos["jetons_sortie"]
        if not gardees:
            sans_source.append(s["id"])
        print(f"  {'✓' if gardees else '✗'} {s['id']} — {len(gardees)} URL(s) retenue(s)"
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
    print(f"{total} jetons chez {modele.split(':')[0]} (aucun jeton Claude).")
    if sans_source:
        print(f"✗ Aucune source pour : {', '.join(sans_source)}. Sans source, rien ne peut "
              f"être écrit : ajoute des URLs à la main dans « sources_candidates », ou des "
              f"pistes plus précises, puis relance.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
