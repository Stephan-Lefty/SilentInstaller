"""Prüft die erzeugten Shell-Skripte.

Diese Skripte laufen mit Root-Rechten. Ein Tippfehler darin wäre nicht nur
ärgerlich, sondern könnte ein System beschädigen – deshalb wird jedes erzeugte
Skript gegen »bash -n« geprüft.
"""

import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

from silentinstaller import backends, catalog, runner
from silentinstaller.catalog import App
from silentinstaller.distro import Distro

SYSTEME = {
    "debian": Distro(id="debian", name="Debian", family="debian", managers={"apt"}),
    "ubuntu": Distro(id="ubuntu", name="Ubuntu", family="debian",
                     managers={"apt", "snap"}, id_like=["debian"]),
    "arch": Distro(id="manjaro", name="Manjaro", family="arch",
                   managers={"pacman"}, id_like=["arch"]),
}


def pruefe_syntax(pruefling, skript: str) -> None:
    """Lässt bash die Syntax prüfen, ohne etwas auszuführen."""
    bash = shutil.which("bash")
    if not bash:
        pruefling.skipTest("bash nicht vorhanden")
    with tempfile.NamedTemporaryFile("w", suffix=".sh", delete=False) as datei:
        datei.write(skript)
        pfad = Path(datei.name)
    try:
        ergebnis = subprocess.run(
            [bash, "-n", str(pfad)], capture_output=True, text=True, timeout=30
        )
        pruefling.assertEqual(
            ergebnis.returncode, 0, f"Syntaxfehler im Skript:\n{ergebnis.stderr}"
        )
    finally:
        pfad.unlink(missing_ok=True)


class GesamterKatalog(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.katalog = catalog.load()

    def _posten(self, system):
        return [
            gefunden
            for app in self.katalog.apps
            if (gefunden := backends.resolve(app, system))
        ]

    def test_installationsskript_ist_gueltig(self):
        for name, system in SYSTEME.items():
            with self.subTest(system=name):
                plan = runner.build_install_plan(self._posten(system), system)
                self.assertTrue(plan.steps, "leerer Bauplan")
                pruefe_syntax(self, runner.render_script(plan, "/tmp/abbruch"))

    def test_entfernungsskript_ist_gueltig(self):
        for name, system in SYSTEME.items():
            for purge in (False, True):
                with self.subTest(system=name, purge=purge):
                    plan = runner.build_remove_plan(
                        self._posten(system), system, purge=purge
                    )
                    pruefe_syntax(self, runner.render_script(plan))

    def test_namen_mit_sonderzeichen_werden_entschaerft(self):
        """Ein Paketname darf niemals als eigener Befehl durchschlagen.

        Geprüft wird nicht der Wortlaut, sondern die Wirkung: Das erzeugte
        Skript wird tatsächlich ausgeführt – mit »echo« statt »apt-get«, damit
        nichts Echtes geschieht. Schlüge der Name durch, entstünde dabei eine
        Datei, die es nicht geben darf.
        """
        with tempfile.TemporaryDirectory() as ordner:
            spur = Path(ordner) / "hier-war-jemand"
            boesartig = App(
                id="probe", name="Probe",
                sources={"apt": {"packages": [f"harmlos; touch {spur}"]}},
            )
            posten = [backends.resolve(boesartig, SYSTEME["debian"])]
            skript = runner.render_script(
                runner.build_install_plan(posten, SYSTEME["debian"])
            )
            pruefe_syntax(self, skript)

            # Kein echter Paketverwalter – nur die Struktur soll laufen.
            harmlos = skript.replace("apt-get install -y", "echo würde-installieren")
            harmlos = harmlos.replace("apt-get update", "true")

            bash = shutil.which("bash")
            if not bash:
                self.skipTest("bash nicht vorhanden")
            subprocess.run(
                [bash, "-c", harmlos], capture_output=True, text=True, timeout=30
            )
            self.assertFalse(
                spur.exists(),
                "der Paketname wurde als eigener Befehl ausgeführt",
            )

    def test_auch_titel_und_pfade_sind_entschaerft(self):
        """Anführungszeichen im Namen dürfen das Skript nicht aufbrechen."""
        knifflig = App(
            id="probe", name="Probe",
            sources={"deb": {"url": "https://beispiel.test/a'b\"c.deb"}},
        )
        posten = [backends.resolve(knifflig, SYSTEME["debian"])]
        pruefe_syntax(
            self,
            runner.render_script(
                runner.build_install_plan(posten, SYSTEME["debian"])
            ),
        )


class Reihenfolge(unittest.TestCase):
    """Die Schritte müssen in einer Reihenfolge stehen, die aufgeht."""

    def setUp(self):
        self.katalog = catalog.load()
        self.system = SYSTEME["debian"]
        posten = [
            gefunden
            for app in self.katalog.apps
            if (gefunden := backends.resolve(app, self.system))
        ]
        self.titel = [
            schritt.title
            for schritt in runner.build_install_plan(posten, self.system).steps
        ]

    def _erster(self, teil):
        for nummer, titel in enumerate(self.titel):
            if teil in titel:
                return nummer
        return None

    def test_paketbereiche_vor_dem_aktualisieren(self):
        bereiche = self._erster("Paketbereiche freischalten")
        aktualisieren = self._erster("Paketlisten aktualisieren")
        if bereiche is not None and aktualisieren is not None:
            self.assertLess(bereiche, aktualisieren)

    def test_fremdquellen_vor_dem_aktualisieren(self):
        quelle = self._erster("Fremdquelle einrichten")
        aktualisieren = self._erster("Paketlisten aktualisieren")
        if quelle is not None and aktualisieren is not None:
            self.assertLess(quelle, aktualisieren)

    def test_aktualisieren_vor_der_installation(self):
        aktualisieren = self._erster("Paketlisten aktualisieren")
        installation = self._erster("über APT installieren")
        if aktualisieren is not None and installation is not None:
            self.assertLess(aktualisieren, installation)


class Schutzvorrichtungen(unittest.TestCase):
    def test_hilfsfunktion_gegen_doppelte_quellen_ist_enthalten(self):
        """Ohne sie kann apt vollständig blockiert werden."""
        system = SYSTEME["debian"]
        katalog = catalog.load()
        brave = katalog.by_id("brave")
        self.assertIsNotNone(brave, "Eintrag brave fehlt")
        posten = [backends.resolve(brave, system)]
        skript = runner.render_script(runner.build_install_plan(posten, system))
        self.assertIn("si_quelle_woanders", skript)
        self.assertIn("wird nicht doppelt angelegt", skript)

    def test_abbruchdatei_wird_beachtet(self):
        plan = runner.Plan(steps=[runner.Step("Probe", ["true"])])
        skript = runner.render_script(plan, "/tmp/abbruch")
        self.assertIn("SI_CANCEL=/tmp/abbruch", skript)
        self.assertIn(runner.MARK_CANCELLED, skript)


if __name__ == "__main__":
    unittest.main()
