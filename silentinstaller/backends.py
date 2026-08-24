"""Auflösung der Installationsquelle und Erkennung bereits installierter Programme."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field

from .catalog import App, SOURCE_KINDS
from .distro import Distro

#: Reihenfolge, in der Quellen gewählt werden, wenn nichts anderes gesetzt ist.
NATIVE_FIRST = ("apt", "pacman", "snap", "deb", "flatpak", "script")
FLATPAK_FIRST = ("flatpak", "apt", "pacman", "snap", "deb", "script")


@dataclass
class Resolved:
    """Die für dieses System gewählte Quelle eines Programms."""

    app: App
    kind: str
    data: dict

    @property
    def packages(self) -> list[str]:
        if self.kind in ("apt", "pacman", "snap"):
            return [str(p) for p in self.data.get("packages", [])]
        if self.kind == "flatpak":
            ref = self.data.get("ref")
            return [str(ref)] if ref else []
        return []

    @property
    def classic(self) -> bool:
        """Braucht dieses Snap-Paket den Zugriff aufs ganze System?"""
        return self.kind == "snap" and bool(self.data.get("classic"))

    @property
    def label(self) -> str:
        return {
            "apt": "APT",
            "pacman": "Pacman",
            "snap": "Snap",
            "flatpak": "Flatpak",
            "deb": ".deb-Paket",
            "script": "Skript",
        }.get(self.kind, self.kind)


def resolve(app: App, distro: Distro, prefer_flatpak: bool = False) -> Resolved | None:
    """Wählt die passende Quelle für ein Programm – oder None, wenn keine passt."""
    order: list[str] = []
    order.extend(k for k in app.prefer if k in SOURCE_KINDS)
    order.extend(FLATPAK_FIRST if prefer_flatpak else NATIVE_FIRST)

    seen: set[str] = set()
    for kind in order:
        if kind in seen:
            continue
        seen.add(kind)
        data = app.sources.get(kind)
        if not data or not distro.supports(kind):
            continue
        aufgeloest = fuer_distro(data, distro)
        # Eine Quelle lässt sich für ein bestimmtes System abschalten, indem
        # ihre Paketliste dort leer bleibt – etwa weil das Paket unter Ubuntu
        # gar nicht existiert und stattdessen der Snap genommen werden soll.
        if kind in ("apt", "pacman", "snap") and not aufgeloest.get("packages"):
            continue
        return Resolved(app=app, kind=kind, data=aufgeloest)
    return None


def fuer_distro(data: dict, distro: Distro) -> dict:
    """Setzt distributionsabhängige Angaben ein.

    Manche Paketnamen unterscheiden sich zwischen den Abkömmlingen einer
    Familie: Der Browser heißt unter Debian »firefox-esr«, unter Ubuntu
    »firefox«. Über ``je_distro`` lässt sich das hinterlegen, wobei die
    speziellste Übereinstimmung gewinnt – ein Eintrag für Linux Mint schlägt
    den für Ubuntu, dieser den für Debian.
    """
    ergebnis = dict(data)
    varianten = ergebnis.pop("je_distro", None)
    if not isinstance(varianten, dict):
        return ergebnis

    for kennung in distro.abstammung:
        besonderheit = varianten.get(kennung)
        if isinstance(besonderheit, dict):
            ergebnis.update(besonderheit)
            break
    return ergebnis


# -- Erkennung des Installationsstands -------------------------------------


def _run(args: list[str]) -> str:
    try:
        result = subprocess.run(
            args, capture_output=True, text=True, timeout=60, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return ""
    return result.stdout if result.returncode == 0 else ""


@dataclass
class InstalledIndex:
    """Momentaufnahme aller installierten Pakete – einmal erfragt, oft benutzt."""

    apt: set[str] = field(default_factory=set)
    pacman: set[str] = field(default_factory=set)
    snap: set[str] = field(default_factory=set)
    flatpak: set[str] = field(default_factory=set)
    #: Das System, auf das sich die Aufnahme bezieht – nötig, weil Paketnamen
    #: sich zwischen Abkömmlingen unterscheiden.
    distro: Distro = field(default_factory=Distro)
    _cache: dict[str, tuple[bool, str | None]] = field(default_factory=dict, repr=False)

    @classmethod
    def collect(cls, distro: Distro) -> "InstalledIndex":
        index = cls(distro=distro)
        if "apt" in distro.managers and shutil.which("dpkg-query"):
            out = _run(
                [
                    "dpkg-query",
                    "-W",
                    "-f=${binary:Package} ${db:Status-Status}\n",
                ]
            )
            for line in out.splitlines():
                name, _, status = line.partition(" ")
                if status.strip() == "installed":
                    index.apt.add(name.split(":", 1)[0])
        if "pacman" in distro.managers:
            index.pacman = {
                line.split(" ", 1)[0] for line in _run(["pacman", "-Qq"]).splitlines()
            }
        if "snap" in distro.managers:
            # Die erste Zeile ist die Überschrift, die erste Spalte der Name.
            out = _run(["snap", "list"])
            index.snap = {
                zeile.split()[0]
                for zeile in out.splitlines()[1:]
                if zeile.strip()
            }
        if "flatpak" in distro.managers:
            out = _run(["flatpak", "list", "--app", "--columns=application"])
            index.flatpak = {line.strip() for line in out.splitlines() if line.strip()}
        return index

    def has(self, kind: str, name: str) -> bool:
        return name in getattr(self, kind, set())

    def app_state(self, app: App) -> tuple[bool, str | None]:
        """Gibt (installiert?, über welche Quelle) zurück.

        Geprüft werden alle hinterlegten Quellen, nicht nur die bevorzugte –
        ein per Flatpak installiertes Programm soll auch dann als vorhanden
        gelten, wenn eigentlich APT bevorzugt wird.
        """
        cached = self._cache.get(app.id)
        if cached is not None:
            return cached
        state = self._app_state_uncached(app)
        self._cache[app.id] = state
        return state

    def _app_state_uncached(self, app: App) -> tuple[bool, str | None]:
        for kind in ("apt", "pacman", "snap", "deb"):
            data = app.sources.get(kind)
            if not data:
                continue
            # Unter Ubuntu heißt der Browser anders als unter Debian – ohne
            # diese Auflösung würde er dort nie als vorhanden erkannt.
            data = fuer_distro(data, self.distro)
            store = {
                "apt": self.apt,
                "deb": self.apt,
                "pacman": self.pacman,
                "snap": self.snap,
            }[kind]
            packages = [str(p) for p in data.get("packages", [])]
            if packages and all(p in store for p in packages):
                return True, kind
        ref = (app.sources.get("flatpak") or {}).get("ref")
        if ref and ref in self.flatpak:
            return True, "flatpak"
        if app.check_command and shutil.which(app.check_command):
            return True, None
        return False, None
