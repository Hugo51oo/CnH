# CnH — spécifications de fonctionnement

> Chaque phase se termine avant de commencer la suivante. Ne pas coder de fonctionnalité V2/V3 pendant la V1.

---

## V1 — Les cartes du jour (site statique, sans compte)

### Écrans
1. **Aujourd'hui** (accueil)
   - La **problématique du jour** en grand, avec sa base, son ouverture et ses pistes de dérive.
   - Les **5 cartes** en dessous. Chaque carte est repliée (titre + thème) et se déplie au toucher.
   - Sous chaque carte : sources (lien + éditeur), et liens « Pour dériver → » vers d'autres cartes.
2. **Carte** (`#/carte/<id>`) : une carte seule, avec ses liens de dérive. On peut enchaîner les cartes à l'infini par ces liens.
3. **Archives** : liste des jours passés, filtrable par thème.
4. **À propos** : le principe base → ouverture → dérive et l'exigence de sources.
5. **Pages légales** : mentions légales et politique de confidentialité V1, en lien dans le pied de page de toutes les pages.

### Sélection du jour
- Le fichier `contenu/programme.json` associe une date (fuseau **Europe/Paris**) à `{ problematique, cartes[5] }`.
- Si la date du jour n'est pas programmée : **rotation déterministe** (graine = date AAAA-MM-JJ) parmi les cartes au statut `verifie`, en respectant 1 carte par thème + 1 hors-piste et 5 formats différents.
- Une carte au statut `brouillon` n'apparaît **jamais** sur le site.

### Format des contenus
Voir `contenu/cartes.json`. Champs :

| Champ | Type | Obligatoire | Note |
|---|---|---|---|
| `id` | texte (slug) | oui | unique, stable |
| `type` | `carte` \| `problematique` | oui | |
| `theme` | code thème | oui | voir `00-vision.md` |
| `themes_croises` | [code, code] | si `hors-piste` | |
| `format` | code format | oui | |
| `titre` | texte | oui | court |
| `base` | texte | oui | 1 à 3 phrases, fait sourcé |
| `base_source` | numéro ou liste | oui si `verifie` | la ou les sources qui appuient la base ; affichées en renvoi [n] à la fin de la base |
| `ouverture` | texte | oui | la question principale |
| `reperes` | [{cle, texte, source}] | oui si `verifie` (2 à 6) | `cle` = chiffre ou mot clé (16 caractères max) ; `source` = numéro (1, 2…) ou liste de numéros ([4, 1]) des sources de la carte |
| `clivages` | [{question, cote_a, cote_b, fait_a, fait_b, a_creuser}] | oui si `verifie` (2 à 4) | `fait_a` / `fait_b` = {texte, source}, affichés comme « Pièce à l'appui » ; `a_creuser` = 1 à 2 notions à rechercher |
| `derives` | [texte] | oui | 1 à 3 pistes |
| `liens` | [id] | non | cartes liées |
| `sources` | [{titre, editeur, url, consulte_le}] | oui (≥ 1) | sources qualifiées uniquement |
| `statut` | `brouillon` \| `verifie` | oui | |
| `verifie_le` | date | si `verifie` | |

**Tout vérifier en une commande** : `./outils/tout_verifier.sh` (schéma, tests, qualité, pages légales, absence de ressource externe). Pour programmer une journée : `python3 outils/ajouter_journee.py AAAA-MM-JJ [--ecrire]`.

Le **script de validation** `python3 outils/valider_contenu.py` vérifie les points ci-dessous, puis génère `contenu/donnees.js` (lu par le site). Tests : `python3 outils/test_valider_contenu.py`. Il vérifie :
- le schéma et l'unicité des id ;
- l'existence des liens ;
- au moins une source pour chaque carte `verifie` ;
- la cohérence du programme (4 thèmes + 1 hors-piste, 5 formats différents).

Les **garde-fous de qualité** `python3 outils/verifier_qualite.py` (tests : `outils/test_verifier_qualite.py`) refusent en plus : une source citée par aucun renvoi, une date de consultation dans le futur, deux repères de même clé, deux camps identiques, deux cartes de même titre, une preuve sans citation. Ils avertissent pour une URL en double, une base trop longue, une ouverture qui n'est pas une question, ou une carte sans preuve archivée.

### Contraintes techniques V1
- `index.html` en **fichier unique** (HTML + CSS + JS vanilla), qui lit `contenu/donnees.js`. Ce fichier est généré à partir des JSON par le validateur, ce qui permet d'ouvrir le site par simple double-clic, sans serveur.
- **Aucun traceur, aucune police ni script externe** qui déposerait un cookie. Polices hébergées avec le site dans `polices/` (Fraunces et Figtree, SIL OFL, voir `polices/LISEZMOI.md`) ; logo cursif « CnH » en SVG (`favicon.svg` pour l'onglet).
- **Mobile d'abord**, lisible à 360 px, mode clair et sombre, contrastes AA, navigation au clavier.
- Hébergement statique (GitHub Pages possible en V1). Développement local : `python3 -m http.server`.

### Terminé quand
*V1 construite le 15/09/2026, vérifiée dans Chromium (mobile et desktop, clair et sombre, en local et par double-clic).*
- [x] La journée du 15/09/2026 affiche la problématique + les 5 cartes d'exemple
- [x] La rotation fonctionne pour une date non programmée (déterministe : même date = mêmes cartes)
- [x] Le validateur de contenu passe, et échoue sur une carte sans source (11 tests)
- [x] Les pages légales sont présentes et en lien partout (les champs `[À COMPLÉTER]` restent à remplir avant publication)
- [x] Aucune requête vers un domaine tiers
- [ ] Publication en ligne (après avoir complété les mentions légales)

---

## V2 — Comptes et forum ouvert

### Fonctionnalités
1. **Inscription / connexion** par **lien magique e-mail** (Supabase Auth, sans mot de passe).
   - À l'inscription : pseudonyme, case « J'ai 15 ans ou plus », acceptation des CGU + Charte + Règles de modération. Les versions acceptées sont enregistrées.
2. **Fils de discussion**
   - 1 fil par problématique du jour + 1 fil par carte.
   - Possibilité de créer un fil « dérive » rattaché à une carte.
3. **Messages** : texte simple (Markdown limité : gras, italique, liens), 1 niveau de réponse, modification pendant 15 min, suppression par l'auteur.
4. **Réaction unique** « 💡 ça m'a fait réfléchir » (compteur, pas de vote négatif).
5. **Signaler** sur chaque message : formulaire conforme au DSA art. 16 (motif, explication, nom, e-mail, case bonne foi), puis accusé de réception.
6. **Espace modération** (rôle `moderateur`) : file des signalements, décision, motif pré-rempli par règle, notification motivée (art. 17), journal.
7. **Paramètres du compte** : changer de pseudo, **exporter mes données** (JSON), **supprimer mon compte**.
8. **Notifications e-mail** minimales : décision de modération, modification des CGU.

### Anti-abus
- Limite de publication : 1 message / 30 s, 30 messages / jour, plus stricte pendant les 24 premières heures d'un compte.
- Liens désactivés pour les comptes de moins de 7 jours.
- Pré-tri IA optionnel : met un message en attente (`en_revue`) mais **ne sanctionne jamais seul**.

### Terminé quand
- [ ] Toutes les cases « Avant d'ouvrir la V2 » de `juridique/00-A-LIRE.md` sont cochées
- [ ] Tests RLS : un utilisateur ne peut ni lire les signalements des autres, ni modifier un message qui n'est pas le sien
- [ ] Parcours signalement → décision → notification → contestation testé
- [ ] Suppression de compte et export testés

---

## V3 — Sessions vocales

Voir `03-vocal.md`.

### Terminé quand
- [ ] Toutes les cases « Avant d'ouvrir la V3 » de `juridique/00-A-LIRE.md` sont cochées
- [ ] Test automatisé : aucun fichier audio ne subsiste après la transcription (ni en cas d'échec au-delà du délai de purge)
- [ ] Publication impossible sans la validation de tous les participants
