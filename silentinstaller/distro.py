"""Erkennung der laufenden Distribution und der verfügbaren Paketverwalter."""

from __future__ import annotations

import shutil
from dataclasses import dataclass, field
from pathlib import Path

OS_RELEASE = Path("/etc/os-release")

DEBIAN_IDS = {
    "debian", "ubuntu", "linuxmint", "pop", "elementary", "zorin", "raspbian",
    "devuan", "mx", "kali", "deepin", "neon", "tuxedo", "lmde", "parrot",
}
ARCH_IDS = {
    "arch", "archlinux", "manjaro", "endeavouros", "garuda", "artix",
    "cachyos", "arcolinux", "archcraft", "rebornos",
}

FAMILY_DEBIAN = "debian"
FAMILY_ARCH = "arch"
FAMILY_UNKNOWN = "unknown"


@dataclass
class Distro:
    """Beschreibt das System, auf dem SilentInstaller gerade läuft."""

    id: str = "unknown"
    name: str = "Unbekanntes System"
    version: str = ""
    family: str = FAMILY_UNKNOWN
    managers: set[str] = field(default_factory=set)
    #: Inhalt von ID_LIKE – etwa ["ubuntu", "debian"] bei Linux Mint.
    id_like: list[str] = field(default_factory=list)

    @property
    def native_manager(self) -> str | None:
        if self.family == FAMILY_DEBIAN and "apt" in self.managers:
            return "apt"
        if self.family == FAMILY_ARCH and "pacman" in self.managers:
            return "pacman"
        return None

    @property
    def pretty(self) -> str:
        return f"{self.name} {self.version}".strip()

    @property
    def abstammung(self) -> list[str]:
        """Kennung und Herkunft, vom Speziellen zum Allgemeinen.

        Für Linux Mint etwa ``["linuxmint", "ubuntu", "debian"]`` – so lässt
        sich ein Paketname für Ubuntu hinterlegen, den Mint mitbenutzt.
        """
        kette = [self.id]
        kette.extend(k for k in self.id_like if k not in kette)
        return kette

    def stammt_von(self, kennung: str) -> bool:
        return kennung in self.abstammung

    def supports(self, kind: str) -> bool:
        """Kann eine Quellen-Art genutzt werden?"""
        if kind in ("apt", "pacman"):
            return kind == self.native_manager
        if kind == "deb":
            return self.native_manager == "apt"
        if kind == "flatpak":
            # Flatpak wird bei Bedarf nachinstalliert, gilt also auch dann als
            # nutzbar, wenn es noch nicht vorhanden ist.
            return self.native_manager is not None or "flatpak" in self.managers
        if kind == "snap":
            # Snap ist auf Ubuntu und Abkömmlingen zu Hause. Anderswo lässt es
            # sich nachrüsten, gilt aber nur als nutzbar, wenn es schon da ist –
            # sonst würde SilentInstaller ungefragt einen zweiten Paketdienst
            # samt Hintergrunddienst auf den Rechner holen.
            return "snap" in self.managers or self.stammt_von("ubuntu")
        if kind == "script":
            return True
        return False


def _parse_os_release(path: Path = OS_RELEASE) -> dict[str, str]:
    data: dict[str, str] = {}
    try:
        text = path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return data
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        data[key.strip()] = value.strip().strip('"').strip("'")
    return data


def _family_from(ids: list[str]) -> str:
    for candidate in ids:
        if candidate in DEBIAN_IDS:
            return FAMILY_DEBIAN
        if candidate in ARCH_IDS:
            return FAMILY_ARCH
    return FAMILY_UNKNOWN


def detect() -> Distro:
    """Liest /etc/os-release und prüft, welche Paketverwalter vorhanden sind."""
    info = _parse_os_release()
    os_id = info.get("ID", "unknown").lower()
    id_like = info.get("ID_LIKE", "").lower().split()

    family = _family_from([os_id, *id_like])
    if family == FAMILY_UNKNOWN:
        # Letzter Ausweg: am vorhandenen Paketverwalter festmachen.
        if shutil.which("apt-get"):
            family = FAMILY_DEBIAN
        elif shutil.which("pacman"):
            family = FAMILY_ARCH

    managers = {
        name
        for name, binary in (
            ("apt", "apt-get"),
            ("pacman", "pacman"),
            ("flatpak", "flatpak"),
            ("snap", "snap"),
        )
        if shutil.which(binary)
    }

    return Distro(
        id=os_id,
        name=info.get("NAME", info.get("PRETTY_NAME", "Unbekanntes System")),
        version=info.get("VERSION_ID", ""),
        family=family,
        managers=managers,
        id_like=id_like,
    )
