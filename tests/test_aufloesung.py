"""Prüft, welche Quelle auf welchem System gewählt wird.

Hier wären die Ubuntu-Fehler aufgefallen: Paketnamen, die es dort nicht gibt,
und die stille Umleitung von apt auf Snap.
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest import mock

from silentinstaller import backends, catalog
from silentinstaller.catalog import App
from silentinstaller.distro import Distro

#: Nur die mitgelieferte Liste, ohne den persönlichen Katalog aus
#: ``~/.config/silentinstaller``. Ohne das hingen diese Tests davon ab, wer
#: sie ausführt: Wer dort eigene Programme einträgt, bekäme Fehlschläge, die
#: mit dem Code nichts zu tun haben. Auf GitHubs Rechnern fiel das nie auf,
#: weil es dort keinen persönlichen Katalog gibt.
OHNE_PERSOENLICHEN = Path("/nicht-vorhanden/catalog.json")

DEBIAN = Distro(id="debian", name="Debian", family="debian", managers={"apt"})
UBUNTU = Distro(
    id="ubuntu", name="Ubuntu", family="debian",
    managers={"apt", "snap"}, id_like=["debian"],
)
MINT = Distro(
    id="linuxmint", name="Linux Mint", family="debian",
    managers={"apt", "snap"}, id_like=["ubuntu", "debian"],
)
ARCH = Distro(
    id="manjaro", name="Manjaro", family="arch",
    managers={"pacman"}, id_like=["arch"],
)
FREMD = Distro(id="fedora", name="Fedora", family="unknown", managers=set())


class Abstammung(unittest.TestCase):
    def test_kette_vom_speziellen_zum_allgemeinen(self):
        self.assertEqual(MINT.abstammung, ["linuxmint", "ubuntu", "debian"])
        self.assertEqual(DEBIAN.abstammung, ["debian"])

    def test_stammt_von(self):
        self.assertTrue(MINT.stammt_von("ubuntu"))
        self.assertTrue(MINT.stammt_von("debian"))
        self.assertFalse(DEBIAN.stammt_von("ubuntu"))

    def test_snap_gilt_nur_wo_es_hingehoert(self):
        self.assertTrue(UBUNTU.supports("snap"), "Ubuntu bringt Snap mit")
        self.assertTrue(MINT.supports("snap"), "Mint erbt das von Ubuntu")
        self.assertFalse(
            DEBIAN.supports("snap"),
            "auf Debian ohne snapd darf nicht ungefragt nachgerüstet werden",
        )
        mit_snapd = Distro(id="debian", family="debian", managers={"apt", "snap"})
        self.assertTrue(mit_snapd.supports("snap"), "vorhandenes snapd zählt")


class QuelleJeSystem(unittest.TestCase):
    def test_paketname_je_distribution(self):
        app = App(
            id="probe", name="Probe",
            sources={"apt": {
                "packages": ["firefox-esr"],
                "je_distro": {"ubuntu": {"packages": ["firefox"]}},
            }},
        )
        self.assertEqual(backends.resolve(app, DEBIAN).packages, ["firefox-esr"])
        self.assertEqual(backends.resolve(app, UBUNTU).packages, ["firefox"])
        self.assertEqual(
            backends.resolve(app, MINT).packages, ["firefox"],
            "Mint muss die Angabe für Ubuntu erben",
        )

    def test_speziellere_angabe_gewinnt(self):
        app = App(
            id="probe", name="Probe",
            sources={"apt": {
                "packages": ["allgemein"],
                "je_distro": {
                    "ubuntu": {"packages": ["fuer-ubuntu"]},
                    "linuxmint": {"packages": ["fuer-mint"]},
                },
            }},
        )
        self.assertEqual(backends.resolve(app, MINT).packages, ["fuer-mint"])
        self.assertEqual(backends.resolve(app, UBUNTU).packages, ["fuer-ubuntu"])

    def test_leere_liste_schaltet_quelle_ab(self):
        """So weicht Ubuntu von APT auf Snap aus."""
        app = App(
            id="probe", name="Probe",
            sources={
                "apt": {"packages": ["gibtsnicht"],
                        "je_distro": {"ubuntu": {"packages": []}}},
                "snap": {"packages": ["ersatz"]},
            },
        )
        self.assertEqual(backends.resolve(app, DEBIAN).kind, "apt")
        self.assertEqual(backends.resolve(app, UBUNTU).kind, "snap")

    def test_ohne_passende_quelle_kommt_nichts(self):
        app = App(id="probe", name="Probe", sources={"pacman": {"packages": ["x"]}})
        self.assertIsNone(backends.resolve(app, DEBIAN))
        self.assertIsNone(backends.resolve(app, FREMD))

    def test_classic_wird_erkannt(self):
        app = App(
            id="probe", name="Probe",
            sources={"snap": {"packages": ["code"], "classic": True}},
        )
        aufgeloest = backends.resolve(app, UBUNTU)
        self.assertTrue(aufgeloest.classic)


class MenueintraegeErkennen(unittest.TestCase):
    """Programme, die in keinem Paketverzeichnis stehen.

    Linux führt kein gemeinsames Verzeichnis der installierten Programme –
    dpkg kennt nur Debian-Pakete, pacman nur Arch-Pakete, Flatpak und Snap
    nur ihre eigenen. Was mit einem eigenen Einrichtungsskript nach
    ``~/.local`` wandert, steht in keinem davon. Übrig bleibt der
    Menüeintrag nach XDG.
    """

    def setUp(self):
        self.ordner = tempfile.TemporaryDirectory()
        self.menue = Path(self.ordner.name) / "applications"
        self.menue.mkdir()
        # Beide Variablen auf den Testordner, damit die echten Einträge des
        # ausführenden Rechners nicht hineinspielen.
        self.umgebung = mock.patch.dict(
            os.environ,
            {"XDG_DATA_HOME": self.ordner.name, "XDG_DATA_DIRS": self.ordner.name},
        )
        self.umgebung.start()

    def tearDown(self):
        self.umgebung.stop()
        self.ordner.cleanup()

    def _eintrag(self, name):
        (self.menue / name).write_text(
            "[Desktop Entry]\nType=Application\nName=Probe\n", encoding="utf-8"
        )

    def _zustand(self, app):
        return backends.InstalledIndex.collect(DEBIAN).app_state(app)[0]

    def test_ohne_befehl_zaehlt_der_menueintrag(self):
        self._eintrag("probe.desktop")
        app = App(id="probe", name="Probe", check_desktop=["probe.desktop"])
        self.assertTrue(self._zustand(app))

    def test_ohne_menueintrag_gilt_es_als_nicht_installiert(self):
        """Die Gegenprobe – sonst meldete die Prüfung immer »vorhanden«."""
        app = App(id="probe", name="Probe", check_desktop=["probe.desktop"])
        self.assertFalse(self._zustand(app))

    def test_einer_von_mehreren_genuegt(self):
        """Manche Programme legen mehrere Einträge an, etwa einen zum Erfassen."""
        self._eintrag("zweiter.desktop")
        app = App(
            id="probe", name="Probe",
            check_desktop=["erster.desktop", "zweiter.desktop"],
        )
        self.assertTrue(self._zustand(app))

    def test_ohne_angabe_wird_nichts_gefunden(self):
        """Ein leeres Feld darf nicht versehentlich alles treffen."""
        self._eintrag("probe.desktop")
        app = App(id="probe", name="Probe")
        self.assertFalse(self._zustand(app))

    def test_angabe_uebersteht_die_runde_durch_die_datei(self):
        app = App(id="probe", name="Probe", check_desktop=["a.desktop"],
                  sources={"apt": {"packages": ["x"]}})
        wieder = App.from_dict(app.to_dict())
        self.assertEqual(wieder.check_desktop, ["a.desktop"])


class GesamterKatalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.katalog = catalog.load(OHNE_PERSOENLICHEN)

    def _ohne_quelle(self, system):
        return [
            app.name
            for app in self.katalog.apps
            if backends.resolve(app, system) is None
        ]

    #: Einträge, für die es auf dem jeweiligen System bewusst keine Quelle
    #: gibt. Jede Lücke ist geprüft und begründet – wächst die Liste
    #: unbemerkt, schlägt der Test an; schließt sich eine Lücke, ebenfalls.
    BEKANNTE_LUECKEN = {
        # VirtualBox wurde aus Debian entfernt, VeraCrypt gibt es dort nicht
        # und auf Flathub nicht mehr. Für beide steht Ersatz im Katalog:
        # virt-manager, GNOME Boxes und Cryptomator.
        "debian": {"VirtualBox", "VeraCrypt"},
        # fastfetch kam erst mit Ubuntu 24.10 und hat kein Snap.
        "ubuntu": {"fastfetch", "VeraCrypt"},
        # Synaptic und das Flatpak-Modul für GNOME Software sind
        # Debian-eigene Werkzeuge.
        "arch": {"Synaptic", "Flatpak in „Software“ einbinden"},
    }

    def test_luecken_sind_die_bekannten(self):
        for name, system in (("debian", DEBIAN), ("ubuntu", UBUNTU), ("arch", ARCH)):
            with self.subTest(system=name):
                self.assertEqual(
                    set(self._ohne_quelle(system)),
                    self.BEKANNTE_LUECKEN[name],
                    "Die Lücken haben sich geändert – Katalog prüfen und diese "
                    "Liste anpassen",
                )

    def test_mint_verhaelt_sich_wie_ubuntu(self):
        self.assertEqual(self._ohne_quelle(MINT), self._ohne_quelle(UBUNTU))

    def test_der_grossteil_ist_ueberall_zu_haben(self):
        for name, system in (("debian", DEBIAN), ("ubuntu", UBUNTU), ("arch", ARCH)):
            with self.subTest(system=name):
                abgedeckt = sum(
                    1 for app in self.katalog.apps if backends.resolve(app, system)
                )
                anteil = abgedeckt / len(self.katalog.apps)
                self.assertGreater(
                    anteil, 0.95, f"nur {abgedeckt} von {len(self.katalog.apps)}"
                )

    def test_auf_fremdem_system_bleibt_alles_leer(self):
        self.assertEqual(len(self._ohne_quelle(FREMD)), len(self.katalog.apps))

    def test_keine_stille_umleitung_auf_snap(self):
        """Wo Ubuntu über apt einen Snap unterschieben würde, nehmen wir ihn offen."""
        heikel = {"firefox", "chromium", "thunderbird"}
        for kennung in heikel:
            app = self.katalog.by_id(kennung)
            if app is None:
                continue
            with self.subTest(app=kennung):
                gewaehlt = backends.resolve(app, UBUNTU)
                self.assertIsNotNone(gewaehlt)
                self.assertNotEqual(
                    gewaehlt.kind, "apt",
                    "apt würde hier stillschweigend einen Snap installieren",
                )


if __name__ == "__main__":
    unittest.main()
