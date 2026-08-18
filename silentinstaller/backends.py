"""Auflösung der Installationsquelle und Erkennung bereits installierter Programme."""

from __future__ import annotations

import shutil
import subprocess
from dataclasses import dataclass, field

from .catalog import App, SOURCE_KINDS
from .distro import Distro

#: Reihenfolge, in der Quellen gewählt werden, wenn nichts anderes gesetzt ist.
NATIVE_FIRST = ("apt", "pacman", "deb", "flatpak", "script")
FLATPAK_FIRST = ("flatpak", "apt", "pacman", "deb", "script")


@dataclass
class Resolved:
    """Die für dieses System gewählte Quelle eines Programms."""

    app: App
    kind: str
    data: dict

    @property
    def packages(self) -> list[str]:
        if self.kind in ("apt", "pacman"):
            return [str(p) for p in self.data.get("packages", [])]
        if self.kind == "flatpak":
            ref = self.data.get("ref")
            return [str(ref)] if ref else []
        return []

    @property
    def label(self) -> str:
        return {
            "apt": "APT",
            "pacman": "Pacman",
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
        if data and distro.supports(kind):
            return Resolved(app=app, kind=kind, data=dict(data))
    return None


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
    flatpak: set[str] = field(default_factory=set)
    _cache: dict[str, tuple[bool, str | None]] = field(default_factory=dict, repr=False)

    @classmethod
    def collect(cls, distro: Distro) -> "InstalledIndex":
        index = cls()
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
        for kind in ("apt", "pacman", "deb"):
            data = app.sources.get(kind)
            if not data:
                continue
            store = self.apt if kind in ("apt", "deb") else self.pacman
            packages = [str(p) for p in data.get("packages", [])]
            if packages and all(p in store for p in packages):
                return True, kind
        ref = (app.sources.get("flatpak") or {}).get("ref")
        if ref and ref in self.flatpak:
            return True, "flatpak"
        if app.check_command and shutil.which(app.check_command):
            return True, None
        return False, None
