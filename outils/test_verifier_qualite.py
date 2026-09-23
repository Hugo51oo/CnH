#!/usr/bin/env python3
"""Tests des garde-fous de qualité. Lancer : python3 outils/test_verifier_qualite.py"""

import copy
import datetime as dt
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import verifier_qualite as vq  # noqa: E402

RACINE = Path(__file__).resolve().parent.parent


class Bac:
    """Un dossier de travail avec une copie des contenus, pour les abîmer sans risque."""

    def __enter__(self):
        self.dossier = tempfile.TemporaryDirectory()
        self.racine = Path(self.dossier.name)
        (self.racine / "contenu").mkdir()
        for nom in ("cartes.json", "programme.json", "preuves.json"):
            source = RACINE / "contenu" / nom
            if source.exists():
                (self.racine / "contenu" / nom).write_text(source.read_text(encoding="utf-8"), encoding="utf-8")
        self.cartes = json.loads((self.racine / "contenu" / "cartes.json").read_text(encoding="utf-8"))
        return self

    def __exit__(self, *args):
        self.dossier.cleanup()

    def carte(self, cid):
        return next(c for c in self.cartes["contenus"] if c["id"] == cid)

    def verifier(self):
        (self.racine / "contenu" / "cartes.json").write_text(
            json.dumps(self.cartes, ensure_ascii=False, indent=2), encoding="utf-8")
        return vq.verifier(racine=self.racine)


class TestContenusReels(unittest.TestCase):
    def test_les_contenus_du_projet_passent(self):
        erreurs, _ = vq.verifier()
        self.assertEqual(erreurs, [], "\n".join(erreurs))


class TestGardeFous(unittest.TestCase):
    def test_source_orpheline_refusee(self):
        with Bac() as bac:
            c = bac.carte("vivre-seul")
            c["sources"].append({"titre": "Jamais citée", "editeur": "X", "url": "https://exemple.org/page",
                                 "consulte_le": "2026-09-01"})
            erreurs, _ = bac.verifier()
            self.assertTrue(any("citée(s) par aucun" in e for e in erreurs), erreurs)

    def test_date_de_consultation_future_refusee(self):
        with Bac() as bac:
            bac.carte("vivre-seul")["sources"][0]["consulte_le"] = "2099-01-01"
            erreurs, _ = bac.verifier()
            self.assertTrue(any("dans le futur" in e for e in erreurs), erreurs)

    def test_cle_trop_longue_refusee(self):
        with Bac() as bac:
            bac.carte("vivre-seul")["reperes"][0]["cle"] = "une clé beaucoup trop longue"
            erreurs, _ = bac.verifier()
            self.assertTrue(any("caractères (maximum" in e for e in erreurs), erreurs)

    def test_deux_camps_identiques_refuses(self):
        with Bac() as bac:
            k = bac.carte("vivre-seul")["clivages"][0]
            k["cote_b"] = k["cote_a"]
            erreurs, _ = bac.verifier()
            self.assertTrue(any("disent la même chose" in e for e in erreurs), erreurs)

    def test_titre_en_double_refuse(self):
        with Bac() as bac:
            bac.carte("vivre-seul")["titre"] = bac.carte("lune-patrimoine")["titre"]
            erreurs, _ = bac.verifier()
            self.assertTrue(any("même titre" in e for e in erreurs), erreurs)

    def test_preuve_sans_citation_refusee(self):
        with Bac() as bac:
            chemin = bac.racine / "contenu" / "preuves.json"
            preuves = json.loads(chemin.read_text(encoding="utf-8"))
            premier = next(iter(preuves))
            preuves[premier]["preuves"][0]["citation"] = "   "
            chemin.write_text(json.dumps(preuves, ensure_ascii=False), encoding="utf-8")
            erreurs, _ = bac.verifier()
            self.assertTrue(any("sans citation" in e for e in erreurs), erreurs)

    def test_url_en_double_avertit(self):
        with Bac() as bac:
            c = bac.carte("vivre-seul")
            c["sources"][1]["url"] = c["sources"][0]["url"]
            _, avertis = bac.verifier()
            self.assertTrue(any("la même URL" in a for a in avertis), avertis)

    def test_date_du_jour_acceptee(self):
        with Bac() as bac:
            bac.carte("vivre-seul")["sources"][0]["consulte_le"] = dt.date.today().isoformat()
            erreurs, _ = bac.verifier()
            self.assertEqual([e for e in erreurs if "futur" in e], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
