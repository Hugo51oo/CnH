# CnH — instructions pour Claude Code

## Le projet
Site/app divertissant, en français : chaque jour **1 grande problématique + 5 cartes** (4 thèmes + 1 hors-piste). Chaque carte suit le principe **base sourcée → ouverture → Repères (encadrés avec chiffre clé) → Ça divise (vignettes réversibles : un camp de chaque côté, chacun avec sa « pièce à l'appui », un fait sourcé dévoilé au survol ou au toucher, et des pistes « À creuser ») → pistes pour dériver → sources repliables**. Pas de quiz, pas de score, pas de pub, pas de traceurs.
Éditeur : **projet personnel, non professionnel et sans but lucratif** (mentions légales anonymes, LCEN art. 1-1, II). Ne rien ajouter de lucratif (pub, paiement) sans revoir les mentions légales. Forum **ouvert à tous** à partir de la V2.

Lire avant toute tâche :
- `docs/00-vision.md` : concept, thèmes, formats, exigence de sources
- `docs/01-fonctionnement.md` : périmètre de chaque phase et critères « terminé quand »
- `docs/juridique/00-A-LIRE.md` : obligations légales et checklists avant chaque phase

Selon la tâche : `docs/02-moderation.md`, `docs/03-vocal.md`, `docs/04-donnees-et-securite.md`.

## Phases (ne jamais anticiper la suivante)
- **V1** : site statique, cartes du jour, archives, pages légales. **Aucune donnée personnelle.**
- **V2** : comptes (lien magique e-mail), forum, signalement, modération (Supabase, région `eu-west-3`).
- **V3** : sessions vocales → transcription → suppression de l'audio → compte rendu publié après validation de tous.

## Stack
- V1 (**construite**) : `index.html` **fichier unique** (HTML/CSS/JS vanilla) qui lit `contenu/donnees.js`, généré depuis `contenu/*.json` par `outils/valider_contenu.py`. Ne jamais modifier `donnees.js` à la main. Aucune dépendance front, aucun CDN. Polices hébergées dans `polices/` (licences OFL incluses), logo cursif en SVG dans l'en-tête et `favicon.svg`.
- V2+ : Supabase (Postgres + RLS, Auth, Storage, Edge Functions). Migrations dans `supabase/migrations/`.
- Dev local : `python3 -m http.server 8000` à la racine.
- Hébergement V1 : GitHub Pages possible (compte `Hugo51oo`). **À réévaluer en V2** : GitHub Pages interdit les usages commerciaux et les transactions sensibles.

## Règles non négociables
1. **Sources** : aucune carte au statut `verifie` sans au moins une source qualifiée (voir `00-vision.md`). Ne jamais inventer un fait, un chiffre ou une URL. La base porte son renvoi (`base_source`) ; chaque repère renvoie à une source de la carte ; chaque camp d'un clivage est appuyé par un fait historique ou matériel sourcé, et les deux positions sont aussi solides l'une que l'autre. En cas de doute : statut `brouillon`.
2. **Zéro traceur** : pas d'analytics, pas de Google Fonts, pas de script tiers. Seul le stockage strictement nécessaire (session, thème) est autorisé.
3. **Pages légales** en lien dans le pied de page de chaque écran, dès la V1.
4. **Secrets** : jamais de clé `service_role` ni de `.env` dans git ou dans le code client.
5. **RLS activé sur toutes les tables**, avec des tests pour chaque règle d'accès (voir `04-donnees-et-securite.md`).
6. **Modération** : aucune sanction automatique. L'IA peut seulement mettre un contenu « en revue ».
7. **Vocal** : pas de démarrage sans le consentement de tous, audio supprimé après transcription (purge testée), publication seulement après validation de tous.
8. **15 ans minimum** pour créer un compte.
9. Les textes juridiques (`docs/juridique/`) ne se modifient **pas** sans demande explicite. Si le code impose un changement, le signaler.
10. **Contenus produits par un modèle** : jamais publiés directement. Ils passent par `outils/agents/` — schéma, citations retrouvées mot pour mot dans la page réelle, garde-fous de qualité, puis contre-lecture par un **autre** modèle. Un contenu sort en `brouillon` et ne devient `verifie` qu'au bout de la chaîne. Les clés d'API vivent dans `.env.local`, jamais dans git.

## Conventions
- Interface, contenus et commentaires en **français** ; identifiants de code en anglais ou en français, mais cohérents dans un même fichier. Tables SQL en français, snake_case.
- Mobile d'abord (360 px), mode clair et sombre, contraste AA, navigation clavier.
- Commits petits et explicites, en français.
- Avant d'ajouter une dépendance ou un service tiers : demander, en expliquant l'impact sur les données personnelles.

## Commandes utiles
- **Tout vérifier d'un coup** : `./outils/tout_verifier.sh` (schéma, tests, qualité, pages légales, ressources externes)
- Valider les contenus et régénérer le site : `python3 outils/valider_contenu.py`
- Garde-fous de qualité : `python3 outils/verifier_qualite.py`
- Programmer une journée : `python3 outils/ajouter_journee.py AAAA-MM-JJ [--ecrire]`
- **Produire une journée avec un modèle externe** : `python3 outils/agents/journee.py outils/agents/sujets/AAAA-MM-JJ.json [--ecrire]` (voir `outils/agents/LISEZMOI.md`)
- Vérifier que chaque citation existe vraiment dans sa source : `python3 outils/agents/verifier_sources.py outils/agents/produits/*.json`
- Construire l'aperçu autonome (test sur téléphone) : `python3 outils/construire_apercu.py`
- Tests : `python3 outils/test_valider_contenu.py`, `python3 outils/test_verifier_qualite.py` et `python3 outils/agents/test_agents.py`
- Voir le site : ouvrir `index.html` (double-clic)
- Lancer une session Claude Code sur une phase : `./lancer-claude-code.sh v1|v2|v3`

## Définition de « terminé »
Les critères de la phase dans `docs/01-fonctionnement.md` sont cochés, le validateur de contenu passe, et rien ne part vers un domaine tiers (onglet Réseau).
