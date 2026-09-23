# Données et sécurité (V2–V3)

> Modèle logique à implémenter en migrations Supabase (`supabase/migrations/`). Noms de tables en français et en snake_case. Toutes les tables ont **RLS activé**.

## Configuration Supabase

- Région : **`eu-west-3` (Paris)**. Choisir une région UE précise, pas le regroupement « Europe », qui inclut Londres et Zurich.
- Accepter le **DPA** Supabase avant d'ouvrir au public.
- Auth : **lien magique e-mail** uniquement. Désactiver les autres fournisseurs.
- Clé `service_role` : **uniquement** dans les Edge Functions et les variables d'environnement serveur. Jamais dans le code client ni dans git.
- `.env` et `supabase/.temp` sont dans `.gitignore`.

## Tables

### V2
| Table | Colonnes principales | Lecture | Écriture |
|---|---|---|---|
| `profils` | `id` (= auth.users.id), `pseudo` (unique), `role` (`membre`\|`moderateur`), `age_atteste_le`, `cree_le`, `derniere_connexion_le`, `statut` (`actif`\|`limite`\|`suspendu`\|`ferme`), `limite_jusqu_au` | Public : `pseudo` seulement (via une vue) ; soi-même : tout | Soi-même : `pseudo` ; modérateur : `statut`, `limite_jusqu_au` |
| `acceptations` | `id`, `profil_id`, `document` (`cgu`\|`charte`\|`moderation`\|`confidentialite`), `version`, `accepte_le` | Soi-même | Insertion par soi-même uniquement |
| `fils` | `id`, `type` (`problematique`\|`carte`\|`derive`), `ref_contenu` (id carte), `titre`, `cree_par`, `cree_le` | Public | Membre actif (type `derive`) ; système (autres types) |
| `messages` | `id`, `fil_id`, `auteur_id`, `parent_id` (1 niveau), `texte`, `etat` (`visible`\|`en_revue`\|`masque`\|`supprime`), `cree_le`, `modifie_le` | Public si `visible` ; auteur : les siens | Auteur actif : insertion ; modification < 15 min ; suppression. Modérateur : `etat` |
| `reactions` | `message_id`, `profil_id`, `cree_le` (PK composite) | Public (compte agrégé) | Soi-même |
| `signalements` | `id`, `message_id`, `signalant_id` (nullable si reçu par e-mail), `signalant_nom`, `signalant_email`, `motif`, `explication`, `bonne_foi` (bool, doit être vrai), `origine` (`utilisateur`\|`automatique`\|`email`), `etat`, `cree_le` | Signalant : les siens ; modérateur : tout | Membre : insertion ; modérateur : `etat` |
| `decisions` | `id`, `signalement_id`, `mesure`, `duree_jours`, `regle`, `explication`, `automatisation_utilisee` (bool), `decide_par`, `decide_le`, `notifie_le` | Auteur concerné + modérateur | Modérateur |
| `contestations` | `id`, `decision_id`, `auteur_id`, `texte`, `cree_le`, `reponse`, `repondu_le` | Auteur + modérateur | Auteur : insertion ; modérateur : réponse |
| `journal_moderation` | `id`, `acteur_id`, `action`, `cible_type`, `cible_id`, `details` (jsonb), `cree_le` | Modérateur | Insertion seule via trigger ou fonction (aucun UPDATE ni DELETE) |

### V3
| Table | Colonnes principales | Accès |
|---|---|---|
| `sessions_vocales` | `id`, `fil_id`, `organisateur_id`, `etat` (`attente`\|`enregistrement`\|`transcription`\|`relecture`\|`validation`\|`publie`\|`abandonne`), `audio_supprime_le`, `cree_le` | Participants |
| `participants_session` | `session_id`, `profil_id`, `lettre` (A, B…), `consenti_le`, `retire_le`, `afficher_pseudo` (bool), `valide_le` | Soi-même + participants de la session |
| `transcriptions` | `id`, `session_id`, `segments` (jsonb : lettre, début, fin, texte, masqué) | Participants ; public après publication (segments non masqués) |
| `comptes_rendus` | `id`, `session_id`, `idees_fortes`, `accords`, `desaccords`, `questions_ouvertes`, `derives`, `genere_le` | Participants ; public après publication |

## Tâches planifiées (pg_cron ou Edge Function planifiée)

| Tâche | Fréquence | Effet |
|---|---|---|
| `purge_audio` | toutes les 15 min | Supprime tout audio de plus d'1 h, puis journalise |
| `purge_moderation` | quotidienne | Supprime les dossiers clos depuis plus d'1 an |
| `comptes_inactifs` | quotidienne | Avertit par e-mail à 3 ans moins 30 jours d'inactivité, puis supprime à 3 ans [durées à valider] |
| `conservation_legale` | quotidienne | Purge les données d'identification conservées depuis plus d'1 an après la fermeture du compte |
| `sessions_expirees` | quotidienne | Abandonne les sessions non validées sous 7 jours et supprime leurs transcriptions |

## Tests de sécurité à écrire

- Un membre ne lit pas les signalements d'autrui.
- Un membre ne modifie pas le message d'autrui ni un message de plus de 15 min.
- Un compte `suspendu` ou `limite` ne peut pas publier.
- `journal_moderation` refuse UPDATE et DELETE, même pour un modérateur.
- Un non-participant ne lit pas une transcription non publiée.
- La publication échoue si un participant n'a pas validé.
