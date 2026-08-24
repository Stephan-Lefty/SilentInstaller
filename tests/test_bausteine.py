"""Prüft die kleinen Bausteine – Sprache, Fassungsvergleich, Pfade, Profile.

Jeder dieser Fälle stand einmal für einen echten Fehler: der Pfad ``/USER/…``
bei einem Heimatverzeichnis unter der Wurzel, die verschluckte Übersetzung,
der Fassungsvergleich, der 1.10 für älter hielt als 1.9.
"""

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from silentinstaller import i18n, update
from silentinstaller.catalog import slugify


class Fassungsvergleich(unittest.TestCase):
    def test_zahlenfolge(self):
        self.assertEqual(update.als_zahlen("1.4.2"), (1, 4, 2))
        self.assertEqual(update.als_zahlen("v1.4.2"), (1, 4, 2))
        self.assertEqual(update.als_zahlen("1.4.2-beta"), (1, 4, 2))

    def test_was_neuer_ist(self):
        faelle = [
            ("1.4.2", "1.4.1", True),
            ("1.10.0", "1.9.0", True),
            ("2.0.0", "1.99.99", True),
            ("1.4.1", "1.4.1", False),
            ("1.4.0", "1.4.1", False),
        ]
        for gefunden, laufend, erwartet in faelle:
            with self.subTest(gefunden=gefunden, laufend=laufend):
                self.assertEqual(update.ist_neuer(gefunden, laufend), erwartet)

    def test_unsinn_gilt_nicht_als_neuer(self):
        self.assertFalse(update.ist_neuer("kaputt", "1.0.0"))

    def test_abstand_zwischen_zwei_abfragen(self):
        from datetime import date, timedelta

        heute = date.today().isoformat()
        gestern = (date.today() - timedelta(days=5)).isoformat()
        self.assertTrue(update.heute_schon_geprueft(heute))
        self.assertFalse(update.heute_schon_geprueft(gestern))
        self.assertFalse(update.heute_schon_geprueft(""))
        self.assertFalse(update.heute_schon_geprueft("kein datum"))


class Spracherkennung(unittest.TestCase):
    def setUp(self):
        self.vorher = i18n.language()

    def tearDown(self):
        i18n.set_language(self.vorher)

    def _mit_umgebung(self, **werte):
        leer = dict.fromkeys(("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"), "")
        leer.update(werte)
        return mock.patch.dict(os.environ, leer, clear=False)

    def test_deutsch_wird_erkannt(self):
        with self._mit_umgebung(LANG="de_DE.UTF-8"):
            self.assertEqual(i18n.detect_language(), "de")

    def test_andere_sprachen_bekommen_englisch(self):
        for wert in ("en_US.UTF-8", "fr_FR.UTF-8", "C", ""):
            with self.subTest(LANG=wert), self._mit_umgebung(LANG=wert):
                self.assertEqual(i18n.detect_language(), "en")

    def test_liste_in_LANGUAGE(self):
        with self._mit_umgebung(LANGUAGE="de_DE:en_US", LANG="en_US.UTF-8"):
            self.assertEqual(i18n.detect_language(), "de")

    def test_deutsch_gibt_den_schluessel_zurueck(self):
        i18n.set_language("de")
        self.assertEqual(i18n._("Installieren"), "Installieren")

    def test_englisch_uebersetzt(self):
        i18n.set_language("en")
        self.assertEqual(i18n._("Installieren"), "Install")

    def test_unbekannter_text_bleibt_stehen(self):
        i18n.set_language("en")
        self.assertEqual(i18n._("Kommt so nicht vor"), "Kommt so nicht vor")


class Uebersetzungen(unittest.TestCase):
    """Jeder übersetzte Text im Quelltext braucht eine englische Fassung."""

    #: Texte, die nur über eine Variable durch _() laufen und daher beim
    #: Durchsuchen des Quelltextes nicht auftauchen.
    NUR_ZUR_LAUFZEIT = {
        "Automatisch (nativ zuerst)",
        "APT bevorzugen",
        "Pacman bevorzugen",
        "Snap bevorzugen",
        "Flatpak bevorzugen",
        ".deb-Paket bevorzugen",
        "Diese Datei enthält keine SilentInstaller-Auswahl.",
    }

    def _im_quelltext(self):
        import ast

        wurzel = Path(__file__).resolve().parent.parent / "silentinstaller"
        gefunden = set()
        for datei in wurzel.glob("*.py"):
            baum = ast.parse(datei.read_text(encoding="utf-8"))
            for knoten in ast.walk(baum):
                if (
                    isinstance(knoten, ast.Call)
                    and isinstance(knoten.func, ast.Name)
                    and knoten.func.id == "_"
                    and knoten.args
                    and isinstance(knoten.args[0], ast.Constant)
                    and isinstance(knoten.args[0].value, str)
                ):
                    gefunden.add(knoten.args[0].value)
        return gefunden

    def test_keine_luecken(self):
        tabelle = i18n.TRANSLATIONS["en"]
        fehlend = sorted(t for t in self._im_quelltext() if t not in tabelle)
        self.assertEqual(fehlend, [], "ohne englische Fassung")

    def test_keine_karteileichen(self):
        tabelle = set(i18n.TRANSLATIONS["en"])
        verwaist = sorted(
            tabelle - self._im_quelltext() - self.NUR_ZUR_LAUFZEIT
        )
        self.assertEqual(verwaist, [], "übersetzt, aber nirgends verwendet")


class Kennungen(unittest.TestCase):
    def test_umlaute_werden_umschrieben(self):
        self.assertEqual(slugify("Büro & Dokumente"), "buero-dokumente")
        self.assertEqual(slugify("Grafik & Foto"), "grafik-foto")

    def test_nur_sonderzeichen_ergibt_ersatz(self):
        self.assertEqual(slugify("!!!"), "eintrag")

    def test_gleiches_ergebnis_bei_wiederholung(self):
        einmal = slugify("Mein Programm")
        self.assertEqual(slugify(einmal), einmal)


class PfadPlatzhalter(unittest.TestCase):
    """Der eigene Benutzername gehört nicht in die Oberfläche."""

    def _anzeige_pfad(self):
        from silentinstaller.uihelpers import anzeige_pfad

        return anzeige_pfad

    def test_heimatverzeichnis_wird_ersetzt(self):
        anzeige_pfad = self._anzeige_pfad()
        with mock.patch.dict(os.environ, {"HOME": "/home/anna"}):
            self.assertEqual(
                anzeige_pfad("/home/anna/.config/x"), "/home/USER/.config/x"
            )
            self.assertEqual(anzeige_pfad("/home/anna"), "/home/USER")

    def test_wurzelnaher_fall_nutzt_die_tilde(self):
        anzeige_pfad = self._anzeige_pfad()
        with mock.patch.dict(os.environ, {"HOME": "/root"}):
            self.assertEqual(anzeige_pfad("/root/.config/x"), "~/.config/x")

    def test_fremde_pfade_bleiben(self):
        anzeige_pfad = self._anzeige_pfad()
        with mock.patch.dict(os.environ, {"HOME": "/home/anna"}):
            self.assertEqual(anzeige_pfad("/opt/etwas"), "/opt/etwas")
            self.assertEqual(
                anzeige_pfad("/home/annabelle/x"), "/home/annabelle/x",
                "ein längerer Name darf nicht mitgerissen werden",
            )


class ProfileUndAuswahl(unittest.TestCase):
    """Speichern und Laden müssen verlustfrei sein."""

    def setUp(self):
        self.ordner = tempfile.TemporaryDirectory()
        self.patch = mock.patch.dict(
            os.environ, {"XDG_CONFIG_HOME": self.ordner.name}
        )
        self.patch.start()

    def tearDown(self):
        self.patch.stop()
        self.ordner.cleanup()

    def test_profil_hin_und_zurueck(self):
        from silentinstaller import catalog

        geladen = catalog.load()
        auswahl = {"firefox", "git", "vlc"} & {a.id for a in geladen.apps}
        catalog.save_profile("Büro-PC", geladen, auswahl)

        profile = catalog.list_profiles()
        self.assertEqual(len(profile), 1)
        self.assertEqual(profile[0].name, "Büro-PC")
        self.assertEqual(set(profile[0].apps), auswahl)

    def test_gleicher_name_ersetzt_statt_zu_haeufen(self):
        from silentinstaller import catalog

        geladen = catalog.load()
        catalog.save_profile("Probe", geladen, {"git"})
        catalog.save_profile("Probe", geladen, {"vlc"})
        self.assertEqual(len(catalog.list_profiles()), 1)

    def test_aehnliche_namen_kollidieren_nicht(self):
        from silentinstaller import catalog

        geladen = catalog.load()
        catalog.save_profile("Büro-PC", geladen, {"git"})
        catalog.save_profile("Buero PC", geladen, {"vlc"})
        self.assertEqual(len(catalog.list_profiles()), 2)

    def test_eigene_programme_wandern_mit(self):
        """Sonst wäre eine Auswahldatei auf einem anderen Rechner wertlos."""
        from silentinstaller import catalog
        from silentinstaller.catalog import App

        geladen = catalog.load()
        geladen.upsert(App(
            id="mein-werkzeug", name="Mein Werkzeug", category="system",
            sources={"apt": {"packages": ["meins"]}}, builtin=False,
        ))
        ziel = Path(self.ordner.name) / "auswahl.json"
        catalog.export_selection(ziel, geladen, {"mein-werkzeug", "git"})

        inhalt = json.loads(ziel.read_text(encoding="utf-8"))
        self.assertEqual(
            [a["id"] for a in inhalt["custom_apps"]], ["mein-werkzeug"]
        )

        frisch = catalog.load()
        self.assertIsNone(frisch.by_id("mein-werkzeug"))
        ergebnis = catalog.import_selection(ziel, frisch)
        self.assertIn("mein-werkzeug", ergebnis.selected)
        self.assertIsNotNone(frisch.by_id("mein-werkzeug"))

    def test_fremde_datei_wird_abgelehnt(self):
        from silentinstaller import catalog

        fremd = Path(self.ordner.name) / "fremd.json"
        fremd.write_text('{"format": "etwas anderes"}', encoding="utf-8")
        with self.assertRaises(catalog.CatalogError):
            catalog.import_selection(fremd, catalog.load())

    def test_kaputte_profildatei_stoert_nicht(self):
        from silentinstaller import catalog

        geladen = catalog.load()
        catalog.save_profile("Heil", geladen, {"git"})
        (catalog.profile_dir() / "kaputt.json").write_text(
            "{ das ist kein json", encoding="utf-8"
        )
        self.assertEqual(len(catalog.list_profiles()), 1)


if __name__ == "__main__":
    unittest.main()
