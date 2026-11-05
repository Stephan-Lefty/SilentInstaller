"""Prüft den mitgelieferten Katalog auf innere Stimmigkeit.

Ein Fehler hier trifft alle Benutzer gleichzeitig, deshalb sind die Prüfungen
streng: doppelte Kennungen, unbekannte Kategorien, Quellen ohne Inhalt.
"""

import json
import unittest
from pathlib import Path

from silentinstaller import catalog
from silentinstaller.catalog import SOURCE_KINDS

#: Nur die mitgelieferte Liste, ohne den persönlichen Katalog aus
#: ``~/.config/silentinstaller``. Ohne das hingen diese Tests davon ab, wer
#: sie ausführt: Wer dort eigene Programme einträgt, bekäme Fehlschläge, die
#: mit dem Code nichts zu tun haben. Auf GitHubs Rechnern fiel das nie auf,
#: weil es dort keinen persönlichen Katalog gibt.
OHNE_PERSOENLICHEN = Path("/nicht-vorhanden/catalog.json")


class KatalogAufbau(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with catalog.BUILTIN_CATALOG.open(encoding="utf-8") as datei:
            cls.roh = json.load(datei)
        cls.apps = cls.roh["apps"]
        cls.kategorien = {k["id"] for k in cls.roh["categories"]}

    def test_kennungen_sind_eindeutig(self):
        kennungen = [a["id"] for a in self.apps]
        doppelte = {k for k in kennungen if kennungen.count(k) > 1}
        self.assertEqual(doppelte, set(), "doppelte Kennungen im Katalog")

    def test_jede_kategorie_ist_bekannt(self):
        for app in self.apps:
            with self.subTest(app=app["id"]):
                self.assertIn(app["category"], self.kategorien)

    def test_jeder_eintrag_hat_mindestens_eine_quelle(self):
        for app in self.apps:
            with self.subTest(app=app["id"]):
                quellen = {k: v for k, v in app.get("sources", {}).items() if v}
                self.assertTrue(quellen, "Eintrag ohne jede Quelle")

    def test_nur_bekannte_quellenarten(self):
        for app in self.apps:
            for art in app.get("sources", {}):
                with self.subTest(app=app["id"], art=art):
                    self.assertIn(art, SOURCE_KINDS)

    def test_paketlisten_sind_gefuellt(self):
        """Eine leere Paketliste ist nur als Abschaltung je Distribution erlaubt."""
        for app in self.apps:
            for art in ("apt", "pacman", "snap"):
                quelle = app.get("sources", {}).get(art)
                if not quelle:
                    continue
                with self.subTest(app=app["id"], art=art):
                    self.assertTrue(
                        quelle.get("packages"),
                        "Paketliste leer – gehört unter je_distro",
                    )

    def test_flatpak_hat_eine_kennung(self):
        for app in self.apps:
            quelle = app.get("sources", {}).get("flatpak")
            if quelle:
                with self.subTest(app=app["id"]):
                    self.assertTrue(quelle.get("ref"))

    def test_fremdquellen_sind_vollstaendig(self):
        """Fehlt ein Feld, entsteht eine kaputte Zeile in sources.list.d."""
        for app in self.apps:
            for art in ("apt", "deb"):
                repo = app.get("sources", {}).get(art, {}).get("repo")
                if not repo:
                    continue
                with self.subTest(app=app["id"]):
                    for feld in ("id", "key_url", "keyring", "line"):
                        self.assertIn(feld, repo, f"{feld} fehlt")
                    self.assertIn(
                        repo["keyring"],
                        repo["line"],
                        "signed-by verweist auf einen anderen Schlüssel als angelegt",
                    )

    def test_je_distro_hat_bekannte_form(self):
        for app in self.apps:
            for art, quelle in app.get("sources", {}).items():
                varianten = quelle.get("je_distro")
                if varianten is None:
                    continue
                with self.subTest(app=app["id"], art=art):
                    self.assertIsInstance(varianten, dict)
                    for kennung, besonderheit in varianten.items():
                        self.assertIsInstance(kennung, str)
                        self.assertIsInstance(besonderheit, dict)

    def test_englische_fassung_vorhanden(self):
        """Ohne sie stünde auf einem englischen System deutscher Text."""
        for app in self.apps:
            with self.subTest(app=app["id"]):
                self.assertTrue(
                    app.get("description_en"), "englische Beschreibung fehlt"
                )
        for kategorie in self.roh["categories"]:
            with self.subTest(kategorie=kategorie["id"]):
                self.assertTrue(kategorie.get("name_en"))

    def test_katalog_laesst_sich_laden(self):
        geladen = catalog.load(OHNE_PERSOENLICHEN)
        self.assertEqual(len(geladen.apps), len(self.apps))
        self.assertTrue(geladen.used_categories())


if __name__ == "__main__":
    unittest.main()
