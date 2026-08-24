"""Prüft, welche Quelle auf welchem System gewählt wird.

Hier wären die Ubuntu-Fehler aufgefallen: Paketnamen, die es dort nicht gibt,
und die stille Umleitung von apt auf Snap.
"""

import unittest

from silentinstaller import backends, catalog
from silentinstaller.catalog import App
from silentinstaller.distro import Distro

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


class GesamterKatalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.katalog = catalog.load()

    def _ohne_quelle(self, system):
        return [
            app.name
            for app in self.katalog.apps
            if backends.resolve(app, system) is None
        ]

    def test_debian_deckt_alles_ab(self):
        self.assertEqual(
            self._ohne_quelle(DEBIAN), [],
            "unter Debian sollte jeder Eintrag eine Quelle haben",
        )

    def test_ubuntu_hat_hoechstens_wenige_luecken(self):
        luecken = self._ohne_quelle(UBUNTU)
        self.assertLessEqual(
            len(luecken), 3,
            f"zu viele Einträge ohne Quelle unter Ubuntu: {luecken}",
        )

    def test_mint_verhaelt_sich_wie_ubuntu(self):
        self.assertEqual(self._ohne_quelle(MINT), self._ohne_quelle(UBUNTU))

    def test_arch_deckt_fast_alles_ab(self):
        luecken = self._ohne_quelle(ARCH)
        self.assertLessEqual(
            len(luecken), 3, f"zu viele Einträge ohne Quelle unter Arch: {luecken}"
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
