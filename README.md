# CnH

Chaque jour, une grande problématique et 5 cartes pour réfléchir à des sujets dont on parle peu : **base sourcée → ouverture → dérive**.

## Voir le site

Double-clique sur **`index.html`** : le site s'ouvre dans ton navigateur, sans rien installer.

## Ajouter ou modifier des cartes

1. Modifie `contenu/cartes.json` (les cartes) et `contenu/programme.json` (quelle carte quel jour).
2. Dans le Terminal, depuis ce dossier :
   ```bash
   python3 outils/valider_contenu.py
   ```
   Le script vérifie tout (sources, liens, 1 carte par thème, 5 formats différents). S'il n'y a pas d'erreur, il met à jour le site.
3. Recharge `index.html`.

Une carte en `"statut": "brouillon"` n'apparaît jamais sur le site. Un jour non programmé affiche une sélection automatique parmi les cartes vérifiées.

Avant de publier, une seule commande vérifie tout (schéma, tests, qualité des sources, pages légales, aucune ressource externe) :

```bash
./outils/tout_verifier.sh
```

## Continuer avec Claude Code

1. **Ouvre un terminal dans ce dossier** (Finder → clic droit sur le dossier → *Nouveau terminal au dossier*), ou tape :
   ```bash
   cd ~/Downloads/CnH
   ```
2. **Vérifie ce qui reste à compléter côté juridique** :
   ```bash
   ./lancer-claude-code.sh statut
   ```
3. **Lance Claude Code** (améliorations de la V1) :
   ```bash
   ./lancer-claude-code.sh
   ```
   Le script vérifie que tout est en place, initialise git, puis ouvre Claude Code avec le prompt de démarrage de la phase. Plus tard : `./lancer-claude-code.sh v2`, puis `v3`.

> Si macOS refuse d'exécuter le script : `chmod +x lancer-claude-code.sh`, ou lance-le avec `bash lancer-claude-code.sh`.

## Contenu du dossier

| Chemin | Rôle |
|---|---|
| `index.html` | **Le site** (V1) : problématique + 5 cartes du jour, archives, pages légales |
| `outils/` | Validateur de contenu (génère `contenu/donnees.js`), garde-fous de qualité, planificateur de journée et leurs tests |
| `outils/tout_verifier.sh` | **Une seule commande** avant de publier : schéma, tests, qualité, pages légales, ressources externes |
| `outils/agents/` | Chaîne qui fait écrire les cartes par un modèle externe (Mistral, GPT, local…) et vérifie chaque citation dans la page réelle — voir son `LISEZMOI.md` |
| `CLAUDE.md` | Règles du projet, lues automatiquement par Claude Code |
| `lancer-claude-code.sh` | Script de lancement par phase (v1, v2, v3, statut) |
| `prompts/` | Prompt de démarrage de chaque phase |
| `docs/00-vision.md` | Concept, thèmes, formats de questions, exigence de sources |
| `docs/01-fonctionnement.md` | Spécifications V1 / V2 / V3 et critères « terminé quand » |
| `docs/02-moderation.md` | Procédure interne de modération |
| `docs/03-vocal.md` | Spécification des sessions vocales |
| `docs/04-donnees-et-securite.md` | Modèle de données Supabase, règles d'accès, purges |
| `docs/05-mise-en-ligne.md` | Comment publier le site sur GitHub Pages et le vérifier |
| `docs/juridique/` | **Base juridique** : checklist, mentions légales, CGU, charte, règles de modération, confidentialité, registre |
| `contenu/` | Cartes vérifiées, programme des jours, `preuves.json` (citations verbatim qui appuient chaque fait) et `donnees.js` généré (ne pas modifier à la main) |
| `polices/` | Polices du site (Fraunces, Figtree), hébergées localement, avec leurs licences |
| `favicon.svg` | Icône d'onglet : le logo cursif « CnH » |

## Important

Les documents juridiques sont des **modèles à compléter et à faire relire** par un professionnel du droit avant l'ouverture du forum. Commence par `docs/juridique/00-A-LIRE.md`.
