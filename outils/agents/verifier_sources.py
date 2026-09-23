#!/usr/bin/env python3
"""
CnH — vérifie que les sources existent et que chaque citation s'y trouve vraiment.

C'est le garde-fou qui remplace la relecture humaine (ou celle d'un modèle cher) :
il ne coûte aucun jeton. Pour chaque contenu produit, il télécharge chaque page citée,
en extrait le texte, et cherche la citation verbatim déclarée dans les preuves.

    python3 outils/agents/verifier_sources.py fichier.json [fichier.json …]
    python3 outils/agents/verifier_sources.py --cache dossier/   (réutilise les pages déjà lues)

Format attendu de chaque fichier : { "contenu": {…}, "preuves": […] }
(ou directement un contenu, si un fichier de preuves porte le même nom + « .preuves.json »).

Code de sortie : 0 si tout est vérifié, 1 sinon.
Aucune dépendance : bibliothèque standard uniquement.
"""

import argparse
import difflib
import gzip
import html
import json
import re
import sys
import unicodedata
import urllib.error
import urllib.request
import zlib
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent.parent
CACHE = Path(__file__).resolve().parent / ".pages"
NAVIGATEUR = "Mozilla/5.0 (compatible; CnH-verification/1.0; +projet personnel, non commercial)"
# en dessous de ce score, la citation est considérée comme reconstituée, pas copiée
SEUIL = 0.92
EXTRAIT_MIN = 25


# ---------------------------------------------------------------- texte

def sans_balises(brut):
    """Texte lisible d'une page HTML, sans dépendance externe."""
    brut = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", brut)
    brut = re.sub(r"(?s)<!--.*?-->", " ", brut)
    brut = re.sub(r"(?i)<(br|/p|/div|/li|/h[1-6]|/tr)\s*/?>", "\n", brut)
    brut = re.sub(r"(?s)<[^>]+>", " ", brut)
    return html.unescape(brut)


def normaliser(texte):
    """Compare ce qui compte : on ignore la casse, les accents, les espaces et la
    typographie (apostrophes courbes, tirets longs, espaces insécables)."""
    texte = unicodedata.normalize("NFKD", texte)
    texte = "".join(c for c in texte if not unicodedata.combining(c))
    texte = texte.replace("’", "'").replace("‘", "'")
    texte = texte.replace("“", '"').replace("”", '"')
    texte = re.sub(r"[‐-―−]", "-", texte)
    texte = re.sub(r"[   ​]", " ", texte)
    texte = re.sub(r"[^\w\s%€$.,;:!?()/'\"-]", " ", texte, flags=re.UNICODE)
    return re.sub(r"\s+", " ", texte).strip().lower()


def meilleur_score(citation, page):
    """Score de présence de la citation dans la page (1.0 = trouvée telle quelle).

    On s'ancre sur des fragments du début, du milieu et de la fin de la citation,
    puis on compare une fenêtre de la même longueur : une coquille fait baisser le
    score de peu, une phrase reconstituée le fait chuter."""
    c, p = normaliser(citation), normaliser(page)
    if not c or not p:
        return 0.0, ""
    if c in p:
        return 1.0, c
    n = len(c)
    positions = set()
    for depart in (0, n // 3, 2 * n // 3, max(0, n - 18)):
        fragment = c[depart:depart + 18]
        if len(fragment) < 10:
            continue
        for m in re.finditer(re.escape(fragment), p):
            positions.add(max(0, m.start() - depart))
    if not positions:
        # aucun fragment de 18 caractères en commun : ce n'est pas une copie
        return 0.0, ""
    meilleur, extrait = 0.0, ""
    for pos in sorted(positions)[:50]:
        fenetre = p[pos:pos + n]
        r = difflib.SequenceMatcher(None, c, fenetre).ratio()
        if r > meilleur:
            meilleur, extrait = r, fenetre[:200]
    return meilleur, extrait


# ---------------------------------------------------------------- réseau

def lire_page(url, cache=CACHE, hors_ligne=False, timeout=45):
    """Télécharge une page (ou la relit depuis le cache). Retourne (texte, erreur)."""
    cache.mkdir(parents=True, exist_ok=True)
    nom = re.sub(r"[^a-zA-Z0-9]+", "_", url)[:120] + ".txt"
    fichier = cache / nom
    if fichier.exists():
        return fichier.read_text(encoding="utf-8"), None
    if hors_ligne:
        return "", "page absente du cache (mode hors ligne)"
    req = urllib.request.Request(url, headers={
        "User-Agent": NAVIGATEUR,
        "Accept": "text/html,application/xhtml+xml,application/pdf;q=0.8,*/*;q=0.5",
        "Accept-Language": "fr-FR,fr;q=0.9,en;q=0.6",
        "Accept-Encoding": "gzip, deflate",
    })
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            donnees = r.read()
            encodage = (r.headers.get("Content-Encoding") or "").lower()
            if encodage == "gzip":
                donnees = gzip.decompress(donnees)
            elif encodage == "deflate":
                donnees = zlib.decompress(donnees, -zlib.MAX_WBITS)
            type_mime = (r.headers.get("Content-Type") or "").lower()
            charset = "utf-8"
            if "charset=" in type_mime:
                charset = type_mime.split("charset=", 1)[1].split(";")[0].strip() or "utf-8"
            if "pdf" in type_mime or url.lower().endswith(".pdf"):
                texte = texte_de_pdf(donnees)
                if texte is None:
                    return "", "PDF : installe pdftotext (poppler) pour vérifier cette source"
            else:
                texte = sans_balises(donnees.decode(charset, "replace"))
    except urllib.error.HTTPError as e:
        return "", f"HTTP {e.code}"
    except Exception as e:  # réseau, TLS, DNS, redirection cassée…
        return "", f"{type(e).__name__} : {e}"
    fichier.write_text(texte, encoding="utf-8")
    return texte, None


def texte_de_pdf(donnees):
    """Texte d'un PDF via pdftotext s'il est installé, sinon None."""
    import shutil
    import subprocess
    import tempfile
    if not shutil.which("pdftotext"):
        return None
    with tempfile.NamedTemporaryFile(suffix=".pdf", delete=False) as f:
        f.write(donnees)
        chemin = f.name
    try:
        r = subprocess.run(["pdftotext", "-q", chemin, "-"], capture_output=True, timeout=120)
        return r.stdout.decode("utf-8", "replace")
    except Exception:
        return None
    finally:
        Path(chemin).unlink(missing_ok=True)


# ---------------------------------------------------------------- vérification

def numeros(valeur):
    return valeur if isinstance(valeur, list) else [valeur]


def verifier_contenu(contenu, preuves, hors_ligne=False, cache=CACHE):
    """Retourne (erreurs, avertissements, pages_lues).

    Une page injoignable n'est pas une citation fausse : les deux cas sont
    distingués, parce que confondre les deux ferait rejeter du bon travail."""
    erreurs, avertis = [], []
    cid = contenu.get("id", "?")
    sources = contenu.get("sources") or []
    pages, lues = {}, 0
    illisibles, bloquees = {}, 0

    for i, src in enumerate(sources, 1):
        url = (src.get("url") or "").strip()
        if not url.startswith("https://"):
            erreurs.append(f"source {i} : l'URL doit commencer par https:// ({url!r})")
            continue
        texte, err = lire_page(url, cache=cache, hors_ligne=hors_ligne)
        if err:
            illisibles[i] = (url, err)
            erreurs.append(f"source {i} ({url}) : illisible — {err}")
            if "403" in err or "Tunnel connection failed" in err:
                bloquees += 1
        else:
            lues += 1
        pages[i] = texte

    if bloquees and bloquees == len(illisibles) and not lues:
        erreurs.append(
            "toutes les sources ont été bloquées par le proxy réseau de cet environnement. "
            "Ce n'est pas un problème de contenu : relance cette vérification depuis ton "
            "propre Terminal (cd vers le dossier du projet, puis la même commande). "
            "Les scripts n'ont besoin que de Python 3.")

    attendu = ["base"]
    attendu += [f"repere {i}" for i in range(1, len(contenu.get("reperes") or []) + 1)]
    for i in range(1, len(contenu.get("clivages") or []) + 1):
        attendu += [f"clivage {i} fait_a", f"clivage {i} fait_b"]
    couverts = {(p.get("appuie") or "").strip().lower() for p in preuves}
    for a in attendu:
        if a.lower() not in couverts:
            erreurs.append(f"aucune preuve archivée pour « {a} »")

    # un fait peut être appuyé par plusieurs fragments : on regarde d'abord
    # si chaque affirmation dispose d'au moins une citation assez longue
    longueur_max = {}
    for p in preuves:
        a = (p.get("appuie") or "?").strip().lower()
        longueur_max[a] = max(longueur_max.get(a, 0), len(normaliser(p.get("citation") or "")))

    for p in preuves:
        appuie = p.get("appuie", "?")
        citation = (p.get("citation") or "").strip()
        court = len(normaliser(citation)) < EXTRAIT_MIN
        if court and longueur_max.get(appuie.strip().lower(), 0) < EXTRAIT_MIN:
            erreurs.append(f"preuve « {appuie} » : aucune citation assez longue pour être "
                           f"vérifiable (il en faut une d'au moins {EXTRAIT_MIN} caractères)")
            continue
        refs = [n for n in numeros(p.get("source")) if isinstance(n, int)]
        if not refs:
            erreurs.append(f"preuve « {appuie} » : numéro de source manquant ou invalide")
            continue
        meilleur, extrait = 0.0, ""
        lisibles = 0
        for n in refs:
            if n not in pages:
                erreurs.append(f"preuve « {appuie} » : source {n} hors des {len(sources)} sources")
                continue
            if n in illisibles:
                continue
            lisibles += 1
            score, ex = meilleur_score(citation, pages[n])
            if score > meilleur:
                meilleur, extrait = score, ex
        if not lisibles:
            # la page n'a pas pu être lue : on ne sait rien, ni en bien ni en mal
            avertis.append(f"preuve « {appuie} » : non vérifiée, "
                           f"source {refs[0]} illisible ici.")
            continue
        if meilleur >= 1.0:
            continue
        if court:
            # un fragment court ne se juge pas à la ressemblance : trop de faux positifs.
            # Il doit se retrouver tel quel, ou il ne compte pas.
            erreurs.append(f"preuve « {appuie} » : le fragment « {citation} » ne se retrouve "
                           f"pas tel quel dans la source.")
            continue
        if meilleur >= SEUIL:
            avertis.append(f"preuve « {appuie} » : citation proche mais pas identique "
                           f"(score {meilleur:.2f}) — à recopier exactement")
        else:
            erreurs.append(f"preuve « {appuie} » : citation introuvable dans la source "
                           f"(score {meilleur:.2f}). Le fait n'est pas prouvé.")

    return [f"« {cid} » : {e}" for e in erreurs], [f"« {cid} » : {a}" for a in avertis], lues


def charger(chemin):
    """Accepte {contenu, preuves} ou un contenu seul accompagné de <nom>.preuves.json."""
    donnees = json.loads(Path(chemin).read_text(encoding="utf-8"))
    if "contenu" in donnees:
        return donnees["contenu"], donnees.get("preuves") or []
    voisin = Path(str(chemin).replace(".json", ".preuves.json"))
    preuves = []
    if voisin.exists():
        brut = json.loads(voisin.read_text(encoding="utf-8"))
        entree = brut.get(donnees.get("id")) if isinstance(brut, dict) else None
        preuves = (entree or {}).get("preuves") or (brut if isinstance(brut, list) else [])
    return donnees, preuves


def main():
    ap = argparse.ArgumentParser(description="Vérifie les sources et les citations d'un contenu CnH.")
    ap.add_argument("fichiers", nargs="+")
    ap.add_argument("--hors-ligne", action="store_true",
                    help="n'utilise que les pages déjà en cache")
    ap.add_argument("--cache", default=str(CACHE))
    args = ap.parse_args()

    total_err, total_av, total_pages = [], [], 0
    for chemin in args.fichiers:
        contenu, preuves = charger(chemin)
        if not preuves:
            total_err.append(f"{chemin} : aucune preuve fournie, rien ne peut être vérifié.")
            continue
        e, a, lues = verifier_contenu(contenu, preuves, hors_ligne=args.hors_ligne,
                                      cache=Path(args.cache))
        total_err += e
        total_av += a
        total_pages += lues
        etat = "✓" if not e else "✗"
        print(f"{etat} {contenu.get('id')} — {len(preuves)} preuve(s), {lues} page(s) lue(s)")

    for a in total_av:
        print(f"  ! {a}")
    for e in total_err:
        print(f"  - {e}")
    if total_err:
        print(f"\n✗ {len(total_err)} problème(s) : ces contenus ne peuvent pas être publiés.")
        return 1
    print(f"\n✓ Toutes les citations retrouvées dans les pages ({total_pages} page(s) lue(s))."
          + (f" {len(total_av)} à recopier plus exactement." if total_av else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
