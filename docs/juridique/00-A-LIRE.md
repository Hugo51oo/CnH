# Base juridique de CnH — à lire en premier

> ⚠️ Ces documents sont des **modèles de travail**, rédigés à partir des textes et guides officiels cités plus bas. Ils ne remplacent pas l'avis d'un professionnel du droit. **Fais-les relire avant l'ouverture publique du forum (V2).**

État : brouillon mis à jour le 16/09/2026 · Éditeur : **projet personnel, non professionnel et sans but lucratif**

---

## 1. Ce qui s'applique à CnH, et pourquoi

| Sujet | Ce que ça impose | Quand | Document |
|---|---|---|---|
| **Mentions légales** (éditeur non professionnel, LCEN art. 1-1, II) | Anonymat possible : seuls le nom et l'adresse de l'hébergeur sont obligatoires, à condition de lui avoir communiqué son identité. Pas de SIRET. ⚠️ Si CnH devient une activité professionnelle ou lucrative (publicité, abonnements…), il faudra passer aux mentions d'un professionnel | **Dès la V1** | `mentions-legales.md` |
| **Politique de confidentialité V1** | Version courte publiée sur le site : aucune donnée collectée par l'éditeur, journaux IP de l'hébergeur | **Dès la V1** | `politique-de-confidentialite-v1.md` |
| **RGPD : information des personnes** (V2) | Identité du responsable, finalités, base légale, destinataires, durées, droits, réclamation CNIL, transferts hors UE | V1 (même si presque rien n'est collecté), complet en V2 | `politique-de-confidentialite.md` |
| **RGPD : registre des traitements** | Obligatoire pour les traitements non occasionnels (comptes, forum, modération) | V2 | `registre-des-traitements.md` |
| **Cookies et traceurs** | Traceurs d'authentification et de sécurité exemptés de consentement. Pas de pub, pas de mesure d'audience non exemptée | V1 → V2 | Politique de confidentialité, §8 |
| **Mineurs** | Avant 15 ans, accord d'un parent requis pour les traitements fondés sur le consentement. **Choix retenu : inscription réservée aux 15 ans et plus** | V2 | CGU §3 |
| **DSA : hébergeur de contenus** (règlement UE 2022/2065) | Point de contact autorités (art. 11) et utilisateurs (art. 12) ; CGU décrivant la modération, y compris les outils automatisés (art. 14) ; mécanisme de signalement (art. 16) ; décisions motivées (art. 17) ; alerte aux autorités en cas de menace pour la vie ou la sécurité (art. 18) | V2 | CGU, `regles-de-moderation.md` |
| **DSA : exemption micro/petite entreprise** | Les obligations supplémentaires des plateformes (système interne de réclamation, etc.) ne s'appliquent pas (art. 19). On propose quand même un réexamen par e-mail (bonne pratique) | V2 | `regles-de-moderation.md` |
| **LCEN : conservation des données d'identification** (décret n° 2021-1362) | Données fournies à la création du compte : **1 an** après clôture. Données techniques de connexion : **1 an**. Identité civile : 5 ans, **mais CnH ne la collecte pas** (pseudo + e-mail seulement) | V2 | Politique de confidentialité, registre |
| **Vocal** (conseils CNIL sur les assistants vocaux) | Informer, minimiser, fixer une durée de conservation, transcrire en local si possible, protéger les tiers enregistrés | V3 | CGU §7, `docs/03-vocal.md` |
| **Hébergement** | Supabase : choisir une **région UE précise** (Paris `eu-west-3`) et accepter le DPA. GitHub Pages : gratuit pour un **dépôt public** (dépôt privé = offre payante GitHub Pro), interdit les usages commerciaux et les transactions sensibles (mots de passe). OK pour la V1 statique, **à réévaluer pour la V2** | V1 → V2 | CLAUDE.md |

---

## 2. Champs à compléter (recherche `À COMPLÉTER` dans ce dossier)

**Pour la V1 :**
- [x] E-mail de contact : vezybrehauxhugo@gmail.com (renseigné le 17/09/2026). Il sert aussi de point de contact DSA en V2

**Avant la V2 :**
- [ ] Identité du responsable du traitement dans la politique de confidentialité (exigée par le RGPD dès qu'on collecte des données)
- [ ] Coordonnées de Supabase Inc., à reprendre sur supabase.com/legal, à ajouter dans les mentions légales et la politique
- [ ] Nom de domaine
- [ ] Prestataire de pré-modération IA (V2, optionnel) et de transcription (V3)

## 3. Décisions à valider (propositions par défaut dans les documents)

- [ ] Suppression des comptes inactifs après **3 ans** sans connexion, avec e-mail d'avertissement 30 jours avant
- [ ] À la suppression d'un compte : messages **supprimés** (défaut) ou anonymisés en « Compte supprimé »
- [ ] Conservation des dossiers de modération : **1 an** après la décision
- [ ] Délai cible de traitement des signalements : **48 h** (immédiat si contenu manifestement illicite)
- [ ] Échelle des sanctions (voir `regles-de-moderation.md`)

## 4. Avant chaque étape

**Avant de publier la V1**
- [x] E-mail de contact renseigné dans `mentions-legales.md` et `politique-de-confidentialite-v1.md`, puis `python3 outils/valider_contenu.py`
- [ ] Tes coordonnées communiquées à l'hébergeur (sur GitHub : ton compte)

**Avant d'ouvrir la V2 (forum)**
- [ ] Projet Supabase en région `eu-west-3` (Paris) + DPA accepté
- [ ] Hébergeur compatible avec des comptes utilisateurs
- [ ] CGU, charte, règles de modération et politique de confidentialité complètes, versionnées et acceptées à l'inscription
- [ ] Formulaire de signalement testé de bout en bout
- [ ] Registre des traitements rempli
- [ ] Relecture par un professionnel du droit

**Avant d'ouvrir la V3 (vocal)**
- [ ] Prestataire de transcription choisi : localisation des données, transferts hors UE, durée de conservation chez lui
- [ ] Test : l'audio est réellement supprimé après transcription
- [ ] Analyse d'impact (AIPD) : pas forcément obligatoire ici, mais **recommandée** pour un traitement de voix publié
- [ ] Mise à jour des CGU, de la politique de confidentialité et du registre

---

## 5. Sources officielles utilisées

- Légifrance — Article 1-1 de la loi n° 2004-575 (identification des éditeurs, anonymat des non-professionnels) : https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000049568614
- Service-public (entreprendre) — Mentions obligatoires d'un site professionnel (si CnH devenait une activité pro) : https://entreprendre.service-public.gouv.fr/vosdroits/F31228
- GitHub — Qu'est-ce que GitHub Pages (offres, journaux IP) : https://docs.github.com/en/pages/getting-started-with-github-pages/what-is-github-pages
- CNIL — Information des personnes (RGPD art. 13) : https://www.cnil.fr/fr/conformite-rgpd-information-des-personnes-et-transparence
- CNIL — Registre des activités de traitement (modèle ODS disponible) : https://www.cnil.fr/fr/RGDP-le-registre-des-activites-de-traitement
- CNIL — Cookies et traceurs, que dit la loi : https://www.cnil.fr/fr/cookies-et-autres-traceurs/que-dit-la-loi
- CNIL — Consentement parental avant 15 ans : https://www.cnil.fr/fr/recommandation-4-rechercher-le-consentement-dun-parent-pour-les-mineurs-de-moins-de-15-ans
- CNIL — Assistants vocaux, conseils : https://www.cnil.fr/fr/assistants-vocaux-les-conseils-pour-les-utilisateurs-et-les-professionnels
- EUR-Lex — Règlement (UE) 2022/2065 (DSA) : https://eur-lex.europa.eu/legal-content/FR/TXT/HTML/?uri=CELEX%3A32022R2065
- Arcom — DSA, obligations et services concernés : https://www.arcom.fr/espace-professionnel/reglement-sur-les-services-numeriques-ou-dsa-obligations-et-services-concernes
- Légifrance — Décret n° 2021-1362 (conservation des données d'identification) : https://www.legifrance.gouv.fr/jorf/id/JORFTEXT000044228912
- Supabase — RGPD : https://supabase.com/docs/guides/security/gdpr-compliance · Régions : https://supabase.com/docs/guides/platform/regions · DPA : https://supabase.com/legal/dpa
- GitHub — Limites de GitHub Pages : https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
