# Sessions vocales — spécification (V3)

## Principe

Des participants inscrits discutent à voix haute d'une problématique. L'app enregistre, transcrit, **supprime l'audio**, puis génère un compte rendu. Rien n'est publié sans l'accord de chacun.

## Parcours

1. **Créer une session**, depuis une problématique ou une carte. L'organisateur obtient un lien d'invitation (valable 24 h).
2. **Rejoindre** : chaque participant se connecte avec son compte. Pas de participant anonyme.
3. **Écran de consentement individuel** (obligatoire pour chaque participant) :
   - ce qui est enregistré : la voix, pendant la session ;
   - ce qui est gardé : la transcription et le compte rendu. **L'audio est supprimé dès la fin de la transcription** ;
   - qui y aura accès : les participants, puis le public après validation de tous ;
   - la possibilité de retirer son accord et ses passages ;
   - case à cocher + bouton « J'accepte d'être enregistré ». Le consentement est horodaté.
4. **Démarrage** : possible seulement quand **tous** les participants présents ont consenti. Rappel à l'écran : « Assurez-vous que personne d'autre n'est enregistré. »
5. **Pendant** : bandeau rouge fixe « ● Enregistrement en cours », chrono, bouton **Pause** et **Arrêter** accessible à chaque participant. Durée max : 60 min.
6. **Fin** : l'audio est envoyé au service de transcription → transcription reçue → **audio supprimé** (stockage + prestataire) → suppression journalisée.
7. **Relecture** : chaque participant voit la transcription et peut **masquer ses passages**. Les noms sont remplacés par « Participant A/B/C » par défaut ; chacun peut choisir d'afficher son pseudo.
8. **Compte rendu** généré par IA à partir de la transcription validée :
   - idées fortes ;
   - points d'accord et de désaccord ;
   - questions restées ouvertes ;
   - pistes de dérive vers d'autres cartes.
9. **Validation finale** par **chaque** participant. Publication dans le fil de la problématique uniquement quand tous ont validé. Si quelqu'un refuse ou ne répond pas sous 7 jours : pas de publication, et suppression de la transcription.

## Garde-fous techniques

- **Pas de stockage audio durable.** Fichier temporaire dans un bucket privé, avec une durée de vie maximale (ex. 1 h) et un job de purge qui supprime tout fichier plus ancien, même si la transcription a échoué.
- **Transcription locale en priorité** si la qualité en français est suffisante (modèle exécuté dans le navigateur ou sur l'appareil). Sinon, un prestataire qui garantit : pas de conservation, pas d'entraînement, localisation des données connue.
- La clé du prestataire reste **côté serveur** (Supabase Edge Function), jamais dans le navigateur.
- Test automatisé de la purge dans la CI.
- Un participant qui supprime son compte fait retirer ses passages des transcriptions non publiées. Pour les transcriptions publiées : anonymisation.

## Données (voir `04-donnees-et-securite.md`)

Tables : `sessions_vocales`, `participants_session`, `transcriptions`, `comptes_rendus`.
