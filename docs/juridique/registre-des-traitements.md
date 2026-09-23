# Registre des activités de traitement (RGPD, art. 30)

*Document interne, à tenir à jour. Non publié. Version 0.1 du 15/09/2026.*
*La CNIL propose aussi un modèle de registre au format tableur : https://www.cnil.fr/fr/RGDP-le-registre-des-activites-de-traitement*

**Responsable du traitement** : Hugo Vézy-Bréhaux, à titre personnel (projet non lucratif) · [À COMPLÉTER : e-mail]
**Délégué à la protection des données** : non désigné (a priori non obligatoire à cette échelle ; à réévaluer si le forum grandit fortement)

---

## T1 — Gestion des comptes utilisateurs
- **Mise en œuvre** : V2
- **Finalité** : création de compte, connexion, gestion des paramètres
- **Base légale** : exécution du contrat (CGU)
- **Personnes concernées** : utilisateurs inscrits (15 ans et plus)
- **Données** : e-mail, pseudonyme, date de l'attestation d'âge, versions des CGU acceptées, dates de création et de dernière connexion
- **Destinataires** : éditeur ; sous-traitant Supabase Inc.
- **Transferts hors UE** : [À VÉRIFIER : sous-traitants ultérieurs Supabase]
- **Durée** : compte actif, puis suppression après 3 ans d'inactivité [À VALIDER] ; conservation légale 1 an après la clôture (décret 2021-1362)
- **Sécurité** : authentification par lien e-mail, règles d'accès RLS, HTTPS, clés secrètes côté serveur uniquement

## T2 — Forum (publication de contributions)
- **Mise en œuvre** : V2
- **Finalité** : publier et afficher les messages
- **Base légale** : exécution du contrat
- **Personnes concernées** : utilisateurs inscrits ; personnes éventuellement citées dans les messages
- **Données** : contenus, dates, identifiant de l'auteur, opinions exprimées publiquement par les utilisateurs
- **Destinataires** : public (messages visibles) ; éditeur ; Supabase Inc.
- **Durée** : jusqu'à suppression ; données d'identification du contributeur conservées 1 an (décret 2021-1362)
- **Sécurité** : RLS (un utilisateur ne modifie que ses contenus), limitation du rythme de publication

## T3 — Signalements et modération
- **Mise en œuvre** : V2
- **Finalité** : traiter les signalements, prendre et motiver les décisions, gérer les contestations
- **Base légale** : obligation légale (DSA art. 16-18 ; LCEN)
- **Personnes concernées** : auteurs signalés, signalants
- **Données** : contenu signalé, motif, nom et e-mail du signalant, décision et motifs, échanges de contestation, recours éventuel à un outil automatisé
- **Destinataires** : éditeur ; autorités sur demande ou en cas de menace pour la vie ou la sécurité (art. 18)
- **Durée** : 1 an après la décision [À VALIDER]
- **Sécurité** : accès réservé au rôle modérateur

## T4 — Pré-tri automatisé des messages (optionnel)
- **Mise en œuvre** : V2, si activé
- **Finalité** : repérer insultes, spam et liens suspects avant vérification humaine
- **Base légale** : intérêt légitime (sécurité du forum)
- **Données** : texte des messages
- **Destinataires** : [À COMPLÉTER : prestataire IA]
- **Transferts hors UE** : [À VÉRIFIER]
- **Durée** : aucune conservation chez le prestataire [À VÉRIFIER dans son contrat]
- **Garantie** : aucune sanction sans vérification humaine

## T5 — Données techniques de connexion
- **Mise en œuvre** : V1 (hébergeur) / V2 (Supabase)
- **Finalité** : sécurité, prévention des abus, obligation légale
- **Base légale** : obligation légale / intérêt légitime
- **Données** : adresse IP, horodatage, identifiants techniques
- **Destinataires** : éditeur ; hébergeurs
- **Durée** : 1 an

## T6 — Sessions vocales
- **Mise en œuvre** : V3
- **Finalité** : enregistrer une discussion, la transcrire, produire un compte rendu, le publier après validation
- **Base légale** : consentement de chaque participant
- **Personnes concernées** : participants inscrits
- **Données** : voix (audio temporaire), transcription, compte rendu, consentements horodatés, validations
- **Destinataires** : participants ; public après validation ; [À COMPLÉTER : prestataire de transcription et de synthèse]
- **Transferts hors UE** : [À VÉRIFIER : prestataire]
- **Durée** : audio supprimé dès la fin de la transcription ; texte conservé jusqu'à suppression
- **Sécurité** : stockage temporaire chiffré, purge automatique vérifiée, anonymisation par défaut (« Participant A/B »)
- **AIPD** : recommandée avant ouverture

## T7 — Demandes d'exercice des droits
- **Mise en œuvre** : V1
- **Finalité** : répondre aux demandes RGPD et aux questions du point de contact
- **Base légale** : obligation légale
- **Données** : identité et coordonnées du demandeur, objet de la demande, réponse
- **Durée** : [À VALIDER : proposition 3 ans après la réponse]
