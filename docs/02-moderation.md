# Modération — procédure interne (V2)

> Version publique : `juridique/regles-de-moderation.md`. Ce document décrit ce que l'application doit faire.

## Cycle d'un signalement

```
signale ──► en_revue ──► decide ──► notifie ──► (conteste ──► reexamine ──► clos)
                              └────────────────────────────────────────────► clos
```

| État | Déclencheur | Action de l'app |
|---|---|---|
| `signale` | Formulaire « Signaler » envoyé | Enregistre le signalement ; accusé de réception par e-mail au signalant ; alerte le modérateur |
| `en_revue` | Le modérateur ouvre le dossier, ou le pré-tri IA a mis le message en attente | Le contenu reste visible, sauf si la catégorie est « grave » : masquage provisoire |
| `decide` | Le modérateur choisit : `maintenu`, `masque`, `supprime`, `limitation_7j`, `suspension_30j`, `fermeture` | Applique la mesure ; génère l'exposé des motifs |
| `notifie` | Automatique après la décision | E-mail à l'auteur (exposé des motifs complet) + e-mail au signalant (décision prise) |
| `conteste` | L'auteur ou le signalant répond dans les 30 jours | Rouvre le dossier et le marque prioritaire |
| `reexamine` | Nouvelle décision | Nouvelle notification motivée |
| `clos` | Fin | Conservation 1 an, puis purge automatique |

## Exposé des motifs (DSA art. 17) — gabarit

L'e-mail et la notification dans l'app contiennent obligatoirement :
1. **Mesure** : ce qui a été fait (masquage, suppression, limitation…), sa durée et sa portée.
2. **Faits** : le contenu concerné (extrait + lien) et la date.
3. **Origine** : signalement d'un utilisateur, détection automatisée, ou initiative du modérateur.
4. **Fondement** : la règle précise (article des CGU ou de la Charte) et, pour un contenu illicite, la raison pour laquelle il est jugé illicite.
5. **Automatisation** : indiquer si un outil automatisé a servi à détecter le contenu ou à décider.
6. **Recours** : réexamen par réponse ou par e-mail sous 30 jours ; possibilité de saisir la justice.

## Catégories de motifs (liste fermée dans l'interface)

`haine_discrimination` · `harcelement_menace` · `donnees_personnelles_autrui` · `contenu_sexuel` · `apologie_crime` · `contrefacon` · `spam_publicite` · `usurpation` · `attaque_personnelle` · `desinformation_fait_non_source` · `autre` (explication obligatoire)

Catégories **graves**, avec masquage provisoire automatique dès le signalement : `harcelement_menace`, `donnees_personnelles_autrui`, `contenu_sexuel`, `apologie_crime`.

## Menace pour la vie ou la sécurité (DSA art. 18)

- Bouton **« Alerter les autorités »** dans le dossier, qui génère un résumé exportable : contenu, horodatage, identifiant du compte, données techniques disponibles.
- Procédure : contacter les forces de l'ordre (17 / 112 en cas d'urgence) et signaler sur PHAROS (internet-signalement.gouv.fr).
- Journaliser l'alerte dans le dossier.

## Journal de modération

Chaque action (qui, quoi, quand, motif) est enregistrée dans `journal_moderation`. Le journal n'est **jamais modifiable**, seulement complété.

## Pré-tri automatisé (optionnel)

- Il ne peut que placer un message en `en_revue` (masqué ou non selon le score) et créer un dossier `origine = automatique`.
- **Aucune mesure définitive sans action humaine.**
- Le prestataire doit s'engager à ne pas conserver les textes ni les utiliser pour entraîner ses modèles (à vérifier dans le contrat avant activation).
