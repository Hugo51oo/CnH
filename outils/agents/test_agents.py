#!/usr/bin/env python3
"""Tests de la chaîne d'agents. Lancer : python3 outils/agents/test_agents.py

Aucun appel réseau, aucun appel à un modèle : on vérifie la mécanique
(normalisation, détection d'une citation inventée, garde-fous de composition)."""

import json
import sys
import tempfile
import unittest
from pathlib import Path

ICI = Path(__file__).resolve().parent
sys.path.insert(0, str(ICI))
sys.path.insert(0, str(ICI.parent))

import fournisseurs as fo        # noqa: E402
import verifier_sources as vs    # noqa: E402
import journee as jo             # noqa: E402
import chercher as ch           # noqa: E402
import documenter as doc        # noqa: E402

PAGE = """<html><head><title>Insee</title><style>p{color:red}</style></head><body>
<h1>Les ménages d’une seule personne</h1>
<p>En 2020, 37&nbsp;% des ménages français étaient composés d’une seule personne,
contre 20&nbsp;% en 1968.</p>
<script>var x = "phrase invisible dans un script";</script>
</body></html>"""


def bac_page(citation_page=PAGE):
    """Un cache de pages pré-rempli : la vérification n'ira jamais sur le réseau."""
    dossier = tempfile.TemporaryDirectory()
    cache = Path(dossier.name)
    url = "https://exemple.insee.fr/statistiques/menages"
    import re
    nom = re.sub(r"[^a-zA-Z0-9]+", "_", url)[:120] + ".txt"
    (cache / nom).write_text(vs.sans_balises(citation_page), encoding="utf-8")
    return dossier, cache, url


def contenu_type(url):
    return {
        "id": "essai", "type": "carte", "theme": "modes-de-vie-societe", "format": "chiffre",
        "titre": "Essai", "base": "Base.", "base_source": 1, "ouverture": "Et alors ?",
        "reperes": [], "clivages": [], "derives": ["a", "b"],
        "sources": [{"titre": "Insee", "editeur": "Insee", "url": url,
                     "consulte_le": "2026-09-18"}],
        "statut": "brouillon",
    }


class TestTexte(unittest.TestCase):
    def test_normalisation_ignore_typographie_et_accents(self):
        a = vs.normaliser("37 % des ménages français étaient composés d’une seule personne")
        b = vs.normaliser("37 % des menages francais etaient composes d'une seule personne")
        self.assertEqual(a, b)

    def test_le_script_n_est_pas_du_texte_de_page(self):
        self.assertNotIn("invisible", vs.sans_balises(PAGE))

    def test_extraction_json_entoure_de_texte(self):
        self.assertEqual(fo.extraire_json('Voici :\n```json\n{"a": 1}\n```\nvoilà.'), {"a": 1})


class TestCitations(unittest.TestCase):
    def verifier(self, citation, page=PAGE):
        dossier, cache, url = bac_page(page)
        try:
            contenu = contenu_type(url)
            preuves = [{"appuie": "base", "source": 1, "citation": citation}]
            return vs.verifier_contenu(contenu, preuves, hors_ligne=True, cache=cache)
        finally:
            dossier.cleanup()

    def test_citation_exacte_acceptee(self):
        e, a, _ = self.verifier("En 2020, 37 % des ménages français étaient composés "
                                "d’une seule personne")
        self.assertEqual(e, [])
        self.assertEqual(a, [])

    def test_citation_inventee_refusee(self):
        e, _, _ = self.verifier("En 2020, 42 % des ménages français vivaient seuls selon "
                                "une étude de l’Insee publiée cette année-là")
        self.assertTrue(any("introuvable" in x for x in e), e)

    def test_citation_presque_exacte_signalee(self):
        e, a, _ = self.verifier("En 2020, 37 % des menages francais etaient composes "
                                "d'une seule persone")   # une coquille
        self.assertEqual(e, [])
        self.assertTrue(any("pas identique" in x for x in a), a)

    def test_citation_trop_courte_refusee(self):
        e, _, _ = self.verifier("37 %")
        self.assertTrue(any("assez longue" in x for x in e), e)

    def test_preuve_manquante_pour_un_repere(self):
        dossier, cache, url = bac_page()
        try:
            contenu = contenu_type(url)
            contenu["reperes"] = [{"cle": "37 %", "texte": "…", "source": 1}]
            preuves = [{"appuie": "base", "source": 1,
                        "citation": "En 2020, 37 % des ménages français étaient "
                                    "composés d’une seule personne"}]
            e, _, _ = vs.verifier_contenu(contenu, preuves, hors_ligne=True, cache=cache)
            self.assertTrue(any("aucune preuve archivée pour « repere 1" in x for x in e), e)
        finally:
            dossier.cleanup()

    def test_source_non_https_refusee(self):
        dossier, cache, url = bac_page()
        try:
            contenu = contenu_type(url)
            contenu["sources"][0]["url"] = "http://exemple.org/page"
            e, _, _ = vs.verifier_contenu(contenu, [{"appuie": "base", "source": 1,
                                                     "citation": "x" * 40}],
                                          hors_ligne=True, cache=cache)
            self.assertTrue(any("https://" in x for x in e), e)
        finally:
            dossier.cleanup()


class TestFragments(unittest.TestCase):
    """Un fait peut être appuyé par plusieurs fragments : un court est accepté
    s'il se retrouve tel quel ET qu'une citation longue couvre la même affirmation."""

    def preuves(self, citations):
        dossier, cache, url = bac_page()
        try:
            return vs.verifier_contenu(
                contenu_type(url),
                [{"appuie": "base", "source": 1, "citation": c} for c in citations],
                hors_ligne=True, cache=cache)
        finally:
            dossier.cleanup()

    def test_fragment_court_accepte_s_il_est_exact_et_accompagne(self):
        e, a, _ = self.preuves(["En 2020, 37 % des m\u00e9nages fran\u00e7ais \u00e9taient compos\u00e9s "
                                "d\u2019une seule personne", "contre 20 % en 1968"])
        self.assertEqual(e, [])

    def test_fragment_court_refuse_s_il_n_est_pas_exact(self):
        e, _, _ = self.preuves(["En 2020, 37 % des m\u00e9nages fran\u00e7ais \u00e9taient compos\u00e9s "
                                "d\u2019une seule personne", "contre 25 % en 1968"])
        self.assertTrue(any("ne se retrouve pas tel quel" in x for x in e), e)

    def test_que_des_fragments_courts_refuse(self):
        e, _, _ = self.preuves(["37 %", "en 1968"])
        self.assertTrue(any("assez longue" in x for x in e), e)


class TestPageInjoignable(unittest.TestCase):
    """Une page qu'on n'a pas pu lire n'est pas une citation fausse."""

    def test_source_illisible_ne_dit_pas_que_le_fait_est_faux(self):
        with tempfile.TemporaryDirectory() as vide:
            contenu = contenu_type("https://exemple.insee.fr/page-absente-du-cache")
            preuves = [{"appuie": "base", "source": 1,
                        "citation": "une citation parfaitement plausible et assez longue"}]
            e, a, _ = vs.verifier_contenu(contenu, preuves, hors_ligne=True, cache=Path(vide))
            self.assertTrue(any("illisible" in x for x in e), e)
            self.assertFalse(any("n'est pas prouvé" in x for x in e), e)
            self.assertTrue(any("non vérifiée" in x for x in a), a)


class TestCompositionDuJour(unittest.TestCase):
    def sujets(self, **remplace):
        base = [
            {"id": "n-pb", "type": "problematique", "theme": "histoire-patrimoine", "format": "ouverte"},
            {"id": "n-a", "theme": "histoire-patrimoine", "format": "chiffre"},
            {"id": "n-b", "theme": "cuisine-alimentation", "format": "objet"},
            {"id": "n-c", "theme": "modes-de-vie-societe", "format": "et-si"},
            {"id": "n-d", "theme": "arts-langues-croyances", "format": "avant-ailleurs"},
            {"id": "n-e", "theme": "hors-piste", "format": "dilemme"},
        ]
        base = [{**s, **remplace.get(s["id"], {})} for s in base]
        return [s for s in base if s["id"] not in remplace.get("_retirer", [])]

    def test_journee_complete_acceptee(self):
        self.assertEqual(jo.verifier_le_jour(self.sujets()), [])

    def test_deux_fois_le_meme_format_refuse(self):
        pbs = jo.verifier_le_jour(self.sujets(**{"n-b": {"format": "chiffre"}}))
        self.assertTrue(any("formats différents" in p for p in pbs), pbs)

    def test_theme_manquant_refuse(self):
        pbs = jo.verifier_le_jour(self.sujets(**{"n-e": {"theme": "cuisine-alimentation"}}))
        self.assertTrue(any("une carte par thème" in p for p in pbs), pbs)

    def test_id_deja_publie_refuse(self):
        pbs = jo.verifier_le_jour(self.sujets(**{"n-a": {"id": "vivre-seul"}}))
        self.assertTrue(any("existe déjà" in p for p in pbs), pbs)


class TestSources(unittest.TestCase):
    def test_domaine_qualifie_accepte(self):
        self.assertTrue(ch.domaine_accepte("https://www.insee.fr/fr/statistiques/6047822"))
        self.assertTrue(ch.domaine_accepte("https://theconversation.com/fr/article-x"))

    def test_wikipedia_refusee(self):
        self.assertFalse(ch.domaine_accepte("https://fr.wikipedia.org/wiki/Fourchette"))

    def test_domaine_imite_refuse(self):
        self.assertFalse(ch.domaine_accepte("https://insee.fr.exemple.com/page"))

    def test_dossier_resserre_enleve_les_menus_repetes(self):
        texte = "\n".join(["Accueil", "Menu", "Accueil", "Menu",
                           "Une phrase de contenu qui n'appara\u00eet qu'une fois."])
        r = doc.resserrer(texte)
        self.assertEqual(r.count("Accueil"), 1)
        self.assertIn("qu'une fois", r)

    def test_dossier_tronque_les_pages_trop_longues(self):
        # des lignes toutes différentes : rien à dédoublonner, seule la coupe agit
        long = "\n".join(f"Phrase de contenu num\u00e9ro {i}, assez longue pour compter."
                         for i in range(2000))
        r = doc.resserrer(long, limite=500)
        self.assertLess(len(r), 700)
        self.assertIn("tronqu\u00e9e", r)


class TestFournisseurs(unittest.TestCase):
    def test_modele_mal_forme_refuse(self):
        with self.assertRaises(fo.ErreurFournisseur):
            fo.appeler("mistral-large", systeme="a", message="b")

    def test_fournisseur_inconnu_refuse(self):
        with self.assertRaises(fo.ErreurFournisseur):
            fo.appeler("magie:modele", systeme="a", message="b")

    def test_cle_absente_dit_quoi_faire(self):
        import os
        ancienne = os.environ.pop("MISTRAL_API_KEY", None)
        try:
            with self.assertRaises(fo.ErreurFournisseur) as ctx:
                fo.appeler("mistral:mistral-large-latest", systeme="a", message="b")
            self.assertIn(".env.local", str(ctx.exception))
        finally:
            if ancienne:
                os.environ["MISTRAL_API_KEY"] = ancienne


if __name__ == "__main__":
    unittest.main(verbosity=2)
