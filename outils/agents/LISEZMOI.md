# La chaîne d'agents

Écrire une journée de CnH (1 problématique + 5 cartes, toutes sourcées et
contre-vérifiées) coûte cher si c'est Claude qui fait tout. Cette chaîne confie
l'écriture à un modèle bon marché, fait faire la vérification par du code gratuit,
et ne garde Claude (ou toi) que pour le choix des sujets et l'arbitrage final.

## L'idée

| Étape | Qui | Coût |
|---|---|---|
| 1. Choisir les sujets du jour | toi, ou Claude | quelques phrases |
| 2. Trouver les URLs des sources | `chercher.py` (recherche web d'OpenAI) | jetons **externes** |
| 3. Télécharger le texte réel des pages | `documenter.py` | **0** |
| 4. Écrire les 6 contenus à partir de ces pages | GPT, Mistral, un modèle local… | jetons **externes** |
| 5. Vérifier le schéma | `valider_contenu.py` | **0** |
| 6. Retrouver chaque citation dans la page réelle | `verifier_sources.py` | **0** |
| 7. Garde-fous de qualité | `verifier_qualite.py` | **0** |
| 8. Contredire ce qui reste | un **second** modèle, différent | jetons **externes** |
| 9. Publier | `journee.py --ecrire` | **0** |

### Pourquoi les étapes 2 et 3 existent

**Un modèle appelé par son API ne navigue pas.** Si on lui demande une carte sourcée,
il écrit des URLs et des citations de mémoire : elles ont l'air justes et ne le sont
pas. On lui donne donc le texte réel des pages, et on lui interdit d'écrire autre
chose que ce qu'il y lit. C'est cette contrainte — pas la confiance dans le modèle —
qui rend la chaîne utilisable.

Le point important est l'étape 6 : le script télécharge chaque page citée et cherche
la citation **mot pour mot**. Un modèle qui invente un chiffre invente aussi la
citation censée l'appuyer — et là, ça se voit tout de suite, sans qu'aucun modèle
n'ait à relire quoi que ce soit. C'est ce contrôle qui rend acceptable de confier
l'écriture à un modèle moins cher.

L'étape 6 utilise obligatoirement un modèle **différent** de celui qui a écrit :
un modèle relit très mal ses propres erreurs. Le script refuse le même modèle.

## Installer une clé

Crée `.env.local` **à la racine du projet** (il est déjà dans `.gitignore`, il ne
partira jamais sur GitHub — règle 4 du projet) :

```
MISTRAL_API_KEY=…
OPENAI_API_KEY=…
```

Fournisseurs reconnus : `mistral`, `openai`, `groq`, `deepseek`, `together`,
`anthropic`, et `ollama` (modèle installé sur ta machine, gratuit, aucune clé).

Pour voir ce qui est prêt :

```bash
python3 outils/agents/fournisseurs.py
```

Deux clés de deux fournisseurs différents suffisent : une pour écrire, une pour
contredire. Avec une seule, la relecture adverse est sautée et le script te le dit.

## Produire une journée

```bash
S=outils/agents/sujets/2026-09-20.json

# 1. décrire les sujets (copier un fichier existant et l'éditer)
cp outils/agents/sujets/2026-09-19.json $S

# 2. trouver des URLs de sources, puis LES RELIRE dans le fichier
python3 outils/agents/chercher.py $S --ecrire

# 3. télécharger le texte réel de ces pages
python3 outils/agents/documenter.py $S

# 4. essai à blanc : écrit, vérifie, ne publie rien
python3 outils/agents/journee.py $S --modele openai:gpt-4.1 --relecteur ollama:llama3.1

# 5. publier si tout est passé
python3 outils/agents/journee.py $S --reprendre --ecrire

# 6. contrôle final du site
./outils/tout_verifier.sh
```

Les étapes 2 et 3 se relancent sans rien coûter tant que les pages sont en cache
(`.pages/`). L'étape 4 est la seule vraiment facturée.

`--reprendre` réutilise ce qui est déjà dans `produits/` : après une correction, tu
ne repaies pas la production des contenus déjà bons. `--hors-ligne` rejoue les
vérifications sur les pages déjà téléchargées (cache `.pages/`), sans réseau.

Rien n'est écrit dans `contenu/` sans `--ecrire`, et `--ecrire` s'arrête si une
seule étape a échoué. Un contenu recalé reste dans `produits/` avec, dans son champ
`relecture`, le détail de ce qui cloche.

## Le fichier de sujets

```json
{
  "date": "2026-09-20",
  "sujets": [
    { "id": "pb-…", "type": "problematique", "theme": "histoire-patrimoine",
      "format": "ouverte", "brief": "la question du jour, en une phrase",
      "pistes": ["des faits à aller vérifier", "…"], "reperes": "4", "clivages": "3" },
    { "id": "…", "theme": "cuisine-alimentation", "format": "objet", "brief": "…",
      "liens": ["repas-gastronomique"] }
  ]
}
```

La composition est vérifiée **avant** de dépenser le moindre jeton : 1 problématique,
5 cartes, une par thème + 1 hors-piste, 5 formats différents, aucun id déjà publié.

`brief` et `pistes` disent quoi chercher — jamais quoi écrire. Les pistes sont des
hypothèses à vérifier : la consigne demande explicitement au modèle d'écarter celles
qu'il ne peut pas sourcer, et de le dire dans `ecarte`.

## Ce que le modèle ne décide pas

`produire.py` réimpose après coup l'`id`, le `type`, le `theme`, le `format` et le
`statut`. Un contenu sort toujours en `brouillon` : seul le passage complet de la
chaîne le fait passer en `verifie`. Le modèle ne peut pas s'auto-publier.

## Coût

`journal.jsonl` note chaque appel (modèle, tâche, jetons entrée/sortie, durée).

```bash
python3 - <<'PY'
import json, collections
t = collections.Counter()
for l in open('outils/agents/journal.jsonl'):
    d = json.loads(l); t[d['modele']] += d['jetons_entree'] + d['jetons_sortie']
for m, n in t.most_common(): print(f"{n:>9} jetons  {m}")
PY
```

## Où lancer la chaîne

**Depuis ton propre Terminal**, pas depuis une session Claude. L'environnement dans
lequel Claude travaille passe par un proxy qui bloque la plupart des sites : les pages
reviennent en « 403 Forbidden » et rien ne peut être vérifié. Ta machine, elle, a un
accès normal à Internet.

```bash
cd ~/Downloads/CnH
python3 outils/agents/test_agents.py          # 25 tests, hors ligne, doit dire OK
python3 outils/agents/verifier_sources.py outils/agents/produits/*.json
```

Aucune installation n'est nécessaire : Python 3 est déjà sur le Mac. `pdftotext` y est
aussi, donc les sources PDF sont lisibles.

## Limites, dites franchement

- **Une citation verbatim prouve que la phrase existe dans la page, pas que la page
  a raison.** Le choix des sources reste un travail éditorial : la consigne liste les
  éditeurs acceptés, mais c'est toi qui arbitres.
- Les pages en JavaScript pur (certaines bases publiques) ne rendent aucun texte au
  téléchargement : la vérification les signale comme illisibles plutôt que de les
  valider à l'aveugle. Il faut alors une autre source.
- Les PDF ne sont lus que si `pdftotext` (poppler) est installé.
- Un modèle bon marché écrit moins bien. Les faits sont protégés par la chaîne ; le
  ton, lui, mérite une relecture humaine avant publication.
