# Spécification d'un contenu CnH (à respecter à la lettre)

Tu produis **un seul contenu** (une carte ou la problématique) pour le site CnH,
au format JSON, prêt à être inséré dans `contenu/cartes.json`.

## Ce qu'est CnH
Un site français de divertissement intelligent. Chaque jour : 1 grande problématique
+ 5 cartes. Une carte pose **une base sourcée**, puis **une ouverture** (question),
puis des **repères**, puis **« Ça divise »** (deux camps, chacun appuyé par un fait
sourcé), puis des **pistes pour dériver**. Ce n'est pas un quiz : il n'y a pas de
bonne réponse. Ton : curieux, simple, direct, tutoiement, jamais moralisateur.

## Exigence de sources — non négociable
- **Aucun fait, chiffre, date ou citation inventé.** Aucune URL inventée.
- Sources acceptées : institutions (Insee, DEPP, ADEME, Anses, ministères,
  Légifrance, Conseil d'État, UNESCO, BnF/Gallica, POP, Our World in Data),
  publications académiques ou éditoriales vérifiées (The Conversation France,
  OpenEdition, Smarthistory, World History Encyclopedia), collections en accès
  ouvert (The Met Open Access, Smithsonian, Europeana).
- **Interdites** : Wikipédia (peut servir à trouver des pistes, jamais comme source),
  blogs sans auteur, sites de quiz, contenus générés par IA.
- Tu dois **ouvrir chaque page** que tu cites (WebFetch/WebSearch) et en extraire une
  **citation verbatim** qui appuie le fait que tu écris. Si tu ne trouves pas la
  citation, tu changes de fait — tu ne l'écris pas.
- URLs en `https://` uniquement, pointant vers une **page précise** (pas une page
  d'accueil nue).
- Chaque source doit servir au moins une fois (base, repère ou fait). Pas de source
  décorative.

## Schéma JSON exact

```json
{
  "id": "identifiant-en-minuscules-avec-tirets",
  "type": "carte",                     // ou "problematique"
  "theme": "histoire-patrimoine",      // histoire-patrimoine | cuisine-alimentation | modes-de-vie-societe | arts-langues-croyances | hors-piste
  "themes_croises": ["a", "b"],        // UNIQUEMENT si theme = hors-piste : 2 thèmes différents
  "format": "chiffre",                 // dilemme | et-si | chiffre | objet | avant-ailleurs | ouverte
  "titre": "Titre court et concret",
  "base": "2 à 4 phrases de fait, sourcées, sans opinion. Max 600 caractères.",
  "base_source": 1,                    // numéro (ou liste de numéros) de source qui appuie la base
  "ouverture": "La question qui ouvre la réflexion, en tutoiement, finit par « ? »",
  "reperes": [                         // 3 ou 4 (min 2, max 6)
    { "cle": "6 millions", "texte": "Une phrase factuelle sourcée.", "source": 1 }
  ],
  "clivages": [                        // 2 ou 3 (min 2, max 4)
    {
      "question": "Formulation courte du désaccord ?",
      "cote_a": "Le meilleur argument du premier camp, en 2-3 phrases. Max 700 car.",
      "cote_b": "Le meilleur argument du camp opposé, aussi solide. Max 700 car.",
      "fait_a": { "texte": "Fait historique ou matériel qui appuie A.", "source": 2 },
      "fait_b": { "texte": "Fait historique ou matériel qui appuie B.", "source": 3 },
      "a_creuser": ["Une notion", "Une autre piste"]   // 1 ou 2, jamais d'affirmation à vérifier
    }
  ],
  "derives": ["Une piste pour continuer", "Une autre", "Une troisième"],
  "liens": ["id-d-une-autre-carte"],   // facultatif, uniquement des ids existants (liste plus bas)
  "sources": [
    {
      "titre": "Titre exact de la page",
      "editeur": "Nom de l'institution ou du média",
      "url": "https://…/page-precise",
      "consulte_le": "2026-09-18"
    }
  ],
  "statut": "verifie",
  "verifie_le": "2026-09-18"
}
```

Contraintes mécaniques (un validateur les refuse sinon) :
- `cle` d'un repère : **16 caractères maximum**, deux repères ne peuvent pas avoir la même.
- `source` : le **numéro** de la source dans `sources` (1 = première), ou une liste de numéros.
  Jamais le titre de la source, jamais une chaîne de caractères.
- Les deux camps d'un clivage ne doivent pas dire la même chose, et aucun ne doit être
  un épouvantail : ce sont les deux meilleures versions du désaccord.
- Le fait d'un camp doit rester exact **lu hors contexte** : il appuie le camp sans le trancher.
- Dates `consulte_le` / `verifie_le` : **2026-09-18** (aujourd'hui), jamais dans le futur.

## Ids déjà publiés (pour « liens » ; ne pas les recréer)
pb-ce-quon-transmet, lune-patrimoine, repas-gastronomique, vivre-seul,
langues-qui-s-eteignent, met-open-access, pb-qui-paie-ce-quon-garde,
restaurer-a-l-identique, qui-decide-du-bon, machines-du-quotidien,
eglises-de-la-republique, la-cantine

## Ce que tu rends
**Uniquement** un objet JSON, sans texte autour et sans bloc markdown, de cette forme :

```json
{
  "contenu": { … l'objet décrit plus haut … },
  "preuves": [
    { "appuie": "base", "source": 1, "citation": "phrase VERBATIM copiée de la page" },
    { "appuie": "repere 1", "source": 1, "citation": "…" },
    { "appuie": "clivage 1 fait_a", "source": 2, "citation": "…" }
  ],
  "ecarte": ["ce que tu as renoncé à écrire faute de source solide"]
}
```

Une preuve par fait publié : la base, chaque repère, chaque `fait_a`, chaque `fait_b`.

La `citation` est **recopiée mot pour mot** depuis la page citée, jamais reformulée,
jamais tronquée au milieu d'un mot. Une vérification automatique la recherchera dans
la page réelle : une citation approximative fait rejeter tout le contenu. Mieux vaut
un fait de moins qu'une citation reconstituée de mémoire.

Chaque affirmation doit avoir **au moins une citation d'une phrase entière** (une
trentaine de caractères au minimum). Tu peux en ajouter d'autres, y compris de courts
fragments — mais un fragment court n'est accepté que s'il se retrouve **exactement**
dans la page. Ne découpe pas une phrase en petits morceaux : recopie la phrase.
