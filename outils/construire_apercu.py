#!/usr/bin/env python3
"""
CnH — construit une page d'aperçu autonome (un seul fichier, aucune ressource externe).

Usage (depuis la racine du projet) :
    python3 outils/construire_apercu.py [chemin/de/sortie.html]

Pourquoi : pour tester le site sur un téléphone, on le publie comme page unique.
Cette page doit se suffire à elle-même — les polices deviennent des « data: »,
`contenu/donnees.js` est recopié dans la page, et le mode sombre reçoit en plus
une variante `:root[data-theme="dark"]` pour les aperçus qui forcent le thème.

Le fichier produit ne contient ni doctype, ni <html>, ni <head>, ni <body> :
c'est l'hébergeur d'aperçu qui fournit cette enveloppe.

Aucune dépendance : Python 3 standard uniquement. Aucune requête réseau.
"""

import base64
import re
import sys
from pathlib import Path

RACINE = Path(__file__).resolve().parent.parent
SORTIE_PAR_DEFAUT = RACINE / "apercu" / "cnh.html"


def polices_en_data(css: str) -> str:
    """Remplace chaque url("polices/…woff2") par la police elle-même, en base64."""
    manquantes = []

    def remplacer(m):
        chemin = RACINE / m.group(1)
        if not chemin.exists():
            manquantes.append(m.group(1))
            return m.group(0)
        b64 = base64.b64encode(chemin.read_bytes()).decode("ascii")
        return f'url("data:font/woff2;base64,{b64}")'

    css = re.sub(r'url\("(polices/[^"]+\.woff2)"\)', remplacer, css)
    if manquantes:
        raise SystemExit("Polices introuvables : " + ", ".join(manquantes))
    return css


def theme_force(css: str) -> str:
    """Duplique le bloc sombre en `:root[data-theme="dark"]`, pour les aperçus
    qui imposent un thème au lieu de suivre le réglage du système."""
    debut = css.find("@media (prefers-color-scheme: dark) {")
    if debut == -1:
        raise SystemExit("Bloc « prefers-color-scheme: dark » introuvable dans index.html.")
    ouvert, i = 0, debut
    while i < len(css):
        if css[i] == "{":
            ouvert += 1
        elif css[i] == "}":
            ouvert -= 1
            if ouvert == 0:
                break
        i += 1
    bloc = css[debut:i + 1]

    interieur = bloc[bloc.find("{") + 1:bloc.rfind("}")]
    jetons = interieur[interieur.find("{") + 1:interieur.rfind("}")]

    # le bloc d'origine ne doit pas écraser un thème clair explicitement demandé
    corrige = bloc.replace(":root {", ':root:not([data-theme="light"]) {', 1)
    return css.replace(bloc, corrige + '\n:root[data-theme="dark"] {' + jetons + "}\n", 1)


def construire() -> str:
    page = (RACINE / "index.html").read_text(encoding="utf-8")
    donnees = (RACINE / "contenu" / "donnees.js").read_text(encoding="utf-8")

    # 1. on ne garde que ce qui va dans la page : <title>, description, <style>, <body>
    titre = re.search(r"<title>.*?</title>", page, re.S).group(0)
    desc = re.search(r'<meta name="description"[^>]*>', page).group(0)
    style = re.search(r"<style>(.*?)</style>", page, re.S).group(1)
    corps = page[page.index("<body>") + len("<body>"):page.index("</body>")]

    style = theme_force(polices_en_data(style))

    # 2. les contenus remplacent le <script src=…>, qui n'existe pas dans un fichier unique
    corps = corps.replace(
        '<script src="contenu/donnees.js"></script>',
        "<script>\n" + donnees.replace("</script", "<\\/script") + "\n</script>",
        1,
    )
    # 3. l'icône d'onglet est fournie par l'hébergeur d'aperçu
    corps = re.sub(r'\s*<link rel="icon"[^>]*>', "", corps)

    return titre + "\n" + desc + "\n<style>\n" + style + "\n</style>\n" + corps


def main():
    sortie = Path(sys.argv[1]) if len(sys.argv) > 1 else SORTIE_PAR_DEFAUT
    html = construire()
    for interdit in ('src="http', "src='http", 'href="http://', 'href="https://'):
        if interdit in html.replace('href="https://www.w3.org', ""):
            raise SystemExit(f"L'aperçu contient une ressource externe ({interdit}).")
    sortie.parent.mkdir(parents=True, exist_ok=True)
    sortie.write_text(html, encoding="utf-8")
    print(f"✓ Aperçu construit : {sortie} ({len(html) / 1024:.0f} Ko)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
