#!/usr/bin/env python3
"""Tests du validateur de contenu. Lancer : python3 outils/test_valider_contenu.py"""

import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import valider_contenu as vc  # noqa: E402

RACINE = Path(__file__).resolve().parent.parent


def charger_exemples():
    cartes = json.loads((RACINE / "contenu" / "cartes.json").read_text(encoding="utf-8"))
    programme = json.loads((RACINE / "contenu" / "programme.json").read_text(encoding="utf-8"))
    return cartes, programme


class TestContenusReels(unittest.TestCase):
    def test_contenus_du_projet_valides(self):
        erreurs, donnees = vc.valider()
        self.assertEqual(erreurs, [], "\n".join(erreurs))
        self.assertIn("mentions-legales", donnees["pages"])
        self.assertIn("confidentialite", donnees["pages"])


class TestRegles(unittest.TestCase):
    def setUp(self):
        self.cartes, self.programme = charger_exemples()
        self.contenus = copy.deepcopy(self.cartes["contenus"])

    def erreurs_contenus(self):
        erreurs, _ = vc.valider_contenus(self.contenus)
        return erreurs

    def carte(self, cid):
        return next(c for c in self.contenus if c["id"] == cid)

    def test_carte_verifiee_sans_source_refusee(self):
        self.carte("vivre-seul")["sources"] = []
        erreurs = self.erreurs_contenus()
        self.assertTrue(any("au moins une source" in e for e in erreurs), erreurs)

    def test_brouillon_sans_source_accepte(self):
        c = self.carte("vivre-seul")
        c["sources"] = []
        c["statut"] = "brouillon"
        c.pop("reperes", None)
        c.pop("clivages", None)
        # la carte devient un brouillon : on retire les liens des autres contenus vers elle
        for autre in self.contenus:
            if autre is not c and isinstance(autre.get("liens"), list):
                autre["liens"] = [l for l in autre["liens"] if l != "vivre-seul"]
        self.assertEqual(self.erreurs_contenus(), [])

    def test_carte_verifiee_sans_reperes_refusee(self):
        del self.carte("lune-patrimoine")["reperes"]
        self.assertTrue(any("reperes" in e for e in self.erreurs_contenus()))

    def test_ancien_champ_a_savoir_signale(self):
        c = self.carte("lune-patrimoine")
        c["a_savoir"] = c.pop("reperes")
        self.assertTrue(any("renommé" in e for e in self.erreurs_contenus()))

    def test_repere_sans_cle_refuse(self):
        del self.carte("vivre-seul")["reperes"][0]["cle"]
        self.assertTrue(any("repère n°1" in e and "cle" in e for e in self.erreurs_contenus()))

    def test_carte_verifiee_avec_un_seul_clivage_refusee(self):
        c = self.carte("lune-patrimoine")
        c["clivages"] = c["clivages"][:1]
        self.assertTrue(any("clivages" in e for e in self.erreurs_contenus()))

    def test_repere_sans_source_refuse(self):
        del self.carte("vivre-seul")["reperes"][0]["source"]
        self.assertTrue(any("repère n°1" in e for e in self.erreurs_contenus()))

    def test_renvoi_vers_source_inexistante_refuse(self):
        self.carte("vivre-seul")["reperes"][0]["source"] = 99
        self.assertTrue(any("numéro d'une source" in e for e in self.erreurs_contenus()))

    def test_renvoi_liste_de_sources_accepte(self):
        self.carte("vivre-seul")["reperes"][0]["source"] = [1, 2]
        self.assertEqual(self.erreurs_contenus(), [])

    def test_clivage_sans_second_camp_refuse(self):
        del self.carte("repas-gastronomique")["clivages"][0]["cote_b"]
        self.assertTrue(any("cote_b" in e for e in self.erreurs_contenus()))

    def test_clivage_sans_fait_historique_refuse(self):
        del self.carte("repas-gastronomique")["clivages"][1]["fait_a"]
        self.assertTrue(any("fait_a" in e for e in self.erreurs_contenus()))

    def test_fait_sans_source_refuse(self):
        del self.carte("repas-gastronomique")["clivages"][1]["fait_b"]["source"]
        self.assertTrue(any("fait_b" in e for e in self.erreurs_contenus()))

    def test_a_creuser_trop_long_refuse(self):
        self.carte("lune-patrimoine")["clivages"][0]["a_creuser"] = ["a", "b", "c"]
        self.assertTrue(any("a_creuser" in e for e in self.erreurs_contenus()))

    def test_base_sans_source_refusee(self):
        del self.carte("vivre-seul")["base_source"]
        self.assertTrue(any("base_source" in e for e in self.erreurs_contenus()))

    def test_url_non_https_refusee(self):
        self.carte("lune-patrimoine")["sources"][0]["url"] = "http://exemple.org"
        self.assertTrue(any("https://" in e for e in self.erreurs_contenus()))

    def test_lien_introuvable_refuse(self):
        self.carte("lune-patrimoine")["liens"] = ["carte-qui-n-existe-pas"]
        self.assertTrue(any("introuvable" in e for e in self.erreurs_contenus()))

    def test_id_en_double_refuse(self):
        self.contenus.append(copy.deepcopy(self.carte("lune-patrimoine")))
        self.assertTrue(any("en double" in e for e in self.erreurs_contenus()))

    def test_theme_inconnu_refuse(self):
        self.carte("vivre-seul")["theme"] = "sport"
        self.assertTrue(any("thème" in e for e in self.erreurs_contenus()))

    def test_hors_piste_sans_croisement_refuse(self):
        del self.carte("met-open-access")["themes_croises"]
        self.assertTrue(any("hors-piste" in e for e in self.erreurs_contenus()))

    def test_programme_formats_en_double_refuse(self):
        _, index = vc.valider_contenus(self.contenus)
        self.carte("vivre-seul")["format"] = "objet"  # même format que lune-patrimoine
        erreurs = vc.valider_programme(self.programme, index)
        self.assertTrue(any("formats différents" in e for e in erreurs), erreurs)

    def test_programme_quatre_cartes_refuse(self):
        _, index = vc.valider_contenus(self.contenus)
        prog = copy.deepcopy(self.programme)
        jour = next(iter(prog["jours"].values()))
        jour["cartes"] = jour["cartes"][:4]
        self.assertTrue(any("exactement 5" in e for e in vc.valider_programme(prog, index)))

    def test_generation_du_fichier_donnees(self):
        erreurs, donnees = vc.valider()
        self.assertEqual(erreurs, [])
        with tempfile.TemporaryDirectory() as dossier:
            (Path(dossier) / "contenu").mkdir()
            cible = vc.ecrire_donnees(donnees, racine=Path(dossier))
            texte = cible.read_text(encoding="utf-8")
            self.assertTrue(texte.strip().startswith("/*"))
            self.assertIn("window.CNH_DONNEES = ", texte)
            self.assertNotIn("</script", texte.lower())
            json_part = texte.split("window.CNH_DONNEES = ", 1)[1].rstrip().rstrip(";")
            relu = json.loads(json_part)
            self.assertEqual(len(relu["contenus"]), len(donnees["contenus"]))


if __name__ == "__main__":
    unittest.main(verbosity=2)
