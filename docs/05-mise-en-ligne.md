# Mettre CnH en ligne (GitHub Pages)

Mis à jour le 18/09/2026. La V1 est un site statique : il n'y a rien à installer sur un serveur, il suffit de publier les fichiers.

## 1. Vérifier en local, avant tout envoi

```bash
cd ~/Downloads/CnH
python3 outils/valider_contenu.py      # doit afficher « ✓ Contenus valides »
python3 outils/test_valider_contenu.py # doit afficher « OK »
```

Puis ouvre `index.html` (double-clic) et regarde la journée du jour, une carte dépliée, les archives et les mentions légales.

## 2. Le dépôt GitHub

- Dépôt : `Hugo51oo/CnH`.
- **Il doit être public** : GitHub Pages n'est gratuit que pour un dépôt public (sinon il faut une offre payante GitHub Pro).
- **Les fichiers doivent être à la racine du dépôt**, pas dans un sous-dossier `CnH/`. À la racine on doit voir : `index.html`, `favicon.svg`, `contenu/`, `polices/`, `docs/`, `outils/`, `README.md`, `CLAUDE.md`, `.gitignore`.

Deux façons d'envoyer les fichiers :

**A. Par le site GitHub** (le plus simple) : sur la page du dépôt, *Add file → Upload files*, puis glisse le contenu du dossier CnH (et pas le dossier lui-même). Les fichiers `.woff2` du dossier `polices/` doivent être envoyés eux aussi.

**B. En ligne de commande** (à faire toi-même, avec ton compte) :

```bash
cd ~/Downloads/CnH
git init && git add . && git commit -m "CnH V1"
git branch -M main
git remote add origin https://github.com/Hugo51oo/CnH.git
git push -u origin main
```

## 3. Activer Pages

Sur le dépôt : *Settings → Pages → Build and deployment → Source : Deploy from a branch → Branch : `main` / `(root)` → Save*.
Au bout d'une à deux minutes, le site est sur **https://hugo51oo.github.io/CnH/**.

## 4. Vérifier une fois en ligne

- [ ] La page du jour s'affiche, avec la problématique et les 5 cartes.
- [ ] Une carte se déplie, une vignette se retourne, une pièce à l'appui se dévoile.
- [ ] Les pages Mentions légales et Confidentialité s'ouvrent, l'adresse de contact est cliquable.
- [ ] Les polices s'affichent (titres en Fraunces) : sinon, le dossier `polices/` n'a pas été envoyé.
- [ ] Onglet Réseau du navigateur : **aucune requête vers un autre domaine** que celui du site.
- [ ] Sur téléphone : rien ne déborde à l'horizontale.

## 5. Rappels juridiques (voir `docs/juridique/00-A-LIRE.md`)

- L'éditeur reste **anonyme** : c'est permis pour un particulier non professionnel (LCEN art. 1-1, II), à condition d'avoir communiqué son identité à l'hébergeur — ton compte GitHub joue ce rôle.
- L'hébergeur indiqué dans les mentions légales est **GitHub Inc.** : si le site déménage, il faut changer cette mention.
- L'adresse de contact publiée sur le site est **vezybrehauxhugo@gmail.com** ; une adresse publique attire du spam, tu peux en créer une dédiée et la remplacer dans `mentions-legales.md` et `politique-de-confidentialite-v1.md`, puis relancer le validateur.
- Pas de publicité, pas de paiement, pas de compte utilisateur en V1 : GitHub Pages interdit les usages commerciaux, et les mentions légales actuelles supposent un projet **sans but lucratif**.

## 6. Publier une nouvelle journée

1. Ajouter les contenus dans `contenu/cartes.json` (sources vérifiées, preuves dans `contenu/preuves.json`).
2. Ajouter la date dans `contenu/programme.json` : 1 problématique + 5 cartes (4 thèmes + 1 hors-piste, 5 formats différents).
3. `python3 outils/valider_contenu.py` puis renvoyer `contenu/` sur GitHub.
