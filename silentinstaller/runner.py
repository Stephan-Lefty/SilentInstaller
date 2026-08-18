"""Bauplan und Ausführung: aus der Auswahl wird ein Shell-Skript, das als root läuft.

Statt jedes Programm einzeln durchzureichen, wird ein einziges, lesbares
Skript erzeugt und mit ``pkexec`` gestartet. Das hat drei Vorteile:

* nur eine einzige Passwortabfrage für den kompletten Durchlauf
* das Skript lässt sich vor dem Start in Ruhe ansehen ("Skript anzeigen")
* Pakete werden gebündelt installiert, was deutlich schneller ist

Der Fortschritt wird über Marker (``@@STEP@@`` …) auf stdout gemeldet und von
der Oberfläche wieder eingesammelt.
"""

from __future__ import annotations

import os
import shlex
import subprocess
import tempfile
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable

from .backends import Resolved
from .distro import Distro

FLATHUB_URL = "https://dl.flathub.org/repo/flathub.flatpakrepo"

MARK_STEP = "@@STEP@@"
MARK_RESULT = "@@RESULT@@"
MARK_DONE = "@@DONE@@"
MARK_CANCELLED = "@@CANCELLED@@"


@dataclass
class Step:
    """Ein Abschnitt des Skripts mit eigenem Fortschrittseintrag."""

    title: str
    body: list[str]
    apps: list[str] = field(default_factory=list)


@dataclass
class Plan:
    steps: list[Step] = field(default_factory=list)
    #: Programme, für die es auf diesem System keine Quelle gibt.
    skipped: list[str] = field(default_factory=list)

    def __bool__(self) -> bool:
        return bool(self.steps)


def _q(value: str) -> str:
    return shlex.quote(str(value))


def _batch_install(command: str, packages: Iterable[str]) -> list[str]:
    """Sammelinstallation mit Einzelfallback, damit ein kaputtes Paket nicht alles kippt."""
    quoted = " ".join(_q(p) for p in packages)
    return [
        f"{command} {quoted} && return 0",
        'echo "Sammelinstallation fehlgeschlagen – versuche die Pakete einzeln ..."',
        "local rc=0 pkg",
        f"for pkg in {quoted}; do",
        f'  {command} "$pkg" || {{ echo "FEHLER: $pkg konnte nicht installiert werden"; rc=1; }}',
        "done",
        "return $rc",
    ]


# -- Bauplan: Installation -------------------------------------------------


def build_install_plan(items: list[Resolved], distro: Distro) -> Plan:
    plan = Plan()

    apt_packages: list[str] = []
    apt_apps: list[str] = []
    pacman_packages: list[str] = []
    pacman_apps: list[str] = []
    flatpak_refs: list[str] = []
    flatpak_apps: list[str] = []
    repos: list[tuple[Resolved, dict]] = []
    components: list[str] = []
    debs: list[Resolved] = []
    scripts: list[Resolved] = []

    for item in items:
        if item.kind == "apt":
            apt_packages.extend(item.packages)
            apt_apps.append(item.app.id)
            if item.data.get("repo"):
                repos.append((item, item.data["repo"]))
            components.extend(item.data.get("components", []))
        elif item.kind == "pacman":
            pacman_packages.extend(item.packages)
            pacman_apps.append(item.app.id)
        elif item.kind == "flatpak":
            flatpak_refs.extend(item.packages)
            flatpak_apps.append(item.app.id)
        elif item.kind == "deb":
            debs.append(item)
            if item.data.get("repo"):
                repos.append((item, item.data["repo"]))
        elif item.kind == "script":
            scripts.append(item)

    needs_apt = bool(apt_packages or debs or repos or flatpak_refs) and distro.native_manager == "apt"

    if repos or (needs_apt and components):
        plan.steps.append(Step("Grundwerkzeuge für Fremdquellen bereitstellen", [
            "apt-get update -qq",
            "apt-get install -y curl gnupg ca-certificates apt-transport-https",
        ]))

    if components:
        unique = sorted(set(components))
        plan.steps.append(Step(
            f"Paketbereiche freischalten ({', '.join(unique)})",
            [f"si_enable_components {' '.join(_q(c) for c in unique)}"],
        ))

    for item, repo in repos:
        plan.steps.append(Step(
            f"Fremdquelle einrichten: {item.app.name}",
            [
                "si_add_repo {} {} {} {}".format(
                    _q(repo.get("id", item.app.id)),
                    _q(repo.get("key_url", "")),
                    _q(repo.get("keyring", f"/usr/share/keyrings/silentinstaller-{item.app.id}.gpg")),
                    _q(repo.get("line", "")),
                )
            ],
            apps=[item.app.id],
        ))

    # Vorbereitungen gehören vor die eigentliche Installation – etwa das
    # Bestätigen einer Lizenz per debconf oder das Freischalten einer Architektur.
    for item in items:
        if item.app.pre_install.strip():
            plan.steps.append(Step(
                f"Vorbereitung für {item.app.name}",
                item.app.pre_install.strip().splitlines(),
                apps=[item.app.id],
            ))

    if needs_apt:
        plan.steps.append(Step("Paketlisten aktualisieren", ["apt-get update"]))

    if apt_packages:
        plan.steps.append(Step(
            f"{len(apt_packages)} Paket(e) über APT installieren",
            _batch_install("apt-get install -y", dict.fromkeys(apt_packages)),
            apps=apt_apps,
        ))

    if pacman_packages:
        plan.steps.append(Step(
            f"{len(pacman_packages)} Paket(e) über Pacman installieren",
            _batch_install(
                "pacman -S --needed --noconfirm", dict.fromkeys(pacman_packages)
            ),
            apps=pacman_apps,
        ))

    for item in debs:
        url = item.data.get("url", "")
        plan.steps.append(Step(
            f"{item.app.name} als .deb-Paket installieren",
            [
                'local tmp rc',
                'tmp="$(mktemp -d)"',
                f'curl -fL --retry 2 -o "$tmp/paket.deb" {_q(url)} || {{ rm -rf "$tmp"; return 1; }}',
                'apt-get install -y "$tmp/paket.deb"',
                "rc=$?",
                'rm -rf "$tmp"',
                "return $rc",
            ],
            apps=[item.app.id],
        ))

    if flatpak_refs:
        setup = ["command -v flatpak >/dev/null 2>&1 || {"]
        if distro.native_manager == "apt":
            setup.append("  apt-get install -y flatpak || return 1")
        elif distro.native_manager == "pacman":
            setup.append("  pacman -S --needed --noconfirm flatpak || return 1")
        else:
            setup.append('  echo "Flatpak fehlt und kann hier nicht nachinstalliert werden"; return 1')
        setup.append("}")
        setup.append(
            f"flatpak remote-add --if-not-exists flathub {_q(FLATHUB_URL)}"
        )
        plan.steps.append(Step("Flatpak und Flathub einrichten", setup))

        plan.steps.append(Step(
            f"{len(flatpak_refs)} Programm(e) über Flatpak installieren",
            _batch_install(
                "flatpak install -y --system --noninteractive flathub",
                dict.fromkeys(flatpak_refs),
            ),
            apps=flatpak_apps,
        ))

    for item in scripts:
        body = item.data.get("install", "").strip()
        if body:
            plan.steps.append(Step(
                f"{item.app.name} einrichten",
                body.splitlines(),
                apps=[item.app.id],
            ))

    for item in items:
        if item.app.post_install.strip():
            plan.steps.append(Step(
                f"Nacharbeiten für {item.app.name}",
                item.app.post_install.strip().splitlines(),
                apps=[item.app.id],
            ))

    return plan


# -- Bauplan: Entfernen ----------------------------------------------------


def build_remove_plan(items: list[Resolved], distro: Distro, purge: bool = False) -> Plan:
    plan = Plan()

    apt_packages: list[str] = []
    pacman_packages: list[str] = []
    flatpak_refs: list[str] = []
    scripts: list[Resolved] = []

    for item in items:
        if item.kind in ("apt", "deb"):
            apt_packages.extend(item.packages or item.data.get("packages", []))
        elif item.kind == "pacman":
            pacman_packages.extend(item.packages)
        elif item.kind == "flatpak":
            flatpak_refs.extend(item.packages)
        elif item.kind == "script":
            scripts.append(item)

    if apt_packages:
        verb = "purge" if purge else "remove"
        plan.steps.append(Step(
            f"{len(apt_packages)} Paket(e) über APT entfernen",
            [
                f"apt-get {verb} -y {' '.join(_q(p) for p in dict.fromkeys(apt_packages))}",
                "apt-get autoremove -y",
            ],
            apps=[i.app.id for i in items if i.kind in ("apt", "deb")],
        ))

    if pacman_packages:
        flags = "-Rns" if purge else "-Rs"
        plan.steps.append(Step(
            f"{len(pacman_packages)} Paket(e) über Pacman entfernen",
            [
                f"pacman {flags} --noconfirm "
                f"{' '.join(_q(p) for p in dict.fromkeys(pacman_packages))}"
            ],
            apps=[i.app.id for i in items if i.kind == "pacman"],
        ))

    if flatpak_refs:
        plan.steps.append(Step(
            f"{len(flatpak_refs)} Programm(e) über Flatpak entfernen",
            [
                "flatpak uninstall -y --system --noninteractive "
                f"{' '.join(_q(r) for r in dict.fromkeys(flatpak_refs))}",
                "flatpak uninstall -y --unused --noninteractive || true",
            ],
            apps=[i.app.id for i in items if i.kind == "flatpak"],
        ))

    for item in scripts:
        body = (item.data.get("remove") or "").strip()
        if body:
            plan.steps.append(Step(
                f"{item.app.name} entfernen",
                body.splitlines(),
                apps=[item.app.id],
            ))
        else:
            plan.skipped.append(item.app.name)

    return plan


# -- Skripterzeugung -------------------------------------------------------

HELPERS = r'''
si_add_repo() {
  # $1=Kennung  $2=Schlüssel-URL  $3=Keyring-Datei  $4=sources.list-Zeile
  local key
  install -d -m 0755 "$(dirname "$3")" /etc/apt/sources.list.d
  key="$(mktemp)"
  if ! curl -fsSL --retry 2 -o "$key" "$2"; then
    echo "Signaturschlüssel konnte nicht geladen werden: $2"
    rm -f "$key"
    return 1
  fi
  if grep -q "BEGIN PGP PUBLIC KEY" "$key"; then
    gpg --dearmor --yes -o "$3" <"$key" || { rm -f "$key"; return 1; }
  else
    install -m 0644 "$key" "$3" || { rm -f "$key"; return 1; }
  fi
  rm -f "$key"
  chmod 0644 "$3"
  printf '%s\n' "$4" >"/etc/apt/sources.list.d/$1.list"
}

si_enable_components() {
  # Schaltet contrib/non-free in den offiziellen Debian-/Ubuntu-Quellen frei.
  local c f
  for c in "$@"; do
    for f in /etc/apt/sources.list /etc/apt/sources.list.d/debian.sources \
             /etc/apt/sources.list.d/ubuntu.sources; do
      [ -f "$f" ] || continue
      case "$f" in
        *.sources)
          grep -q "^Components:" "$f" || continue
          grep -qE "^Components:.*[[:space:]]$c([[:space:]]|$)" "$f" && continue
          sed -i "s/^Components:.*/& $c/" "$f"
          ;;
        *)
          grep -qE "^deb[[:space:]].*[[:space:]]$c([[:space:]]|$)" "$f" && continue
          sed -i -E "/^deb[[:space:]].*[[:space:]]main([[:space:]]|\$)/ s/\$/ $c/" "$f"
          ;;
      esac
      echo "Paketbereich '$c' in $f freigeschaltet"
    done
  done
  return 0
}
'''


def render_script(plan: Plan, cancel_file: str = "") -> str:
    """Erzeugt das vollständige Shell-Skript zu einem Bauplan."""
    lines = [
        "#!/usr/bin/env bash",
        "# Erzeugt von SilentInstaller – dieses Skript läuft mit Root-Rechten.",
        "export DEBIAN_FRONTEND=noninteractive",
        "export NEEDRESTART_MODE=a",
        "export LC_ALL=C.UTF-8",
        f"SI_TOTAL={len(plan.steps)}",
        f"SI_CANCEL={_q(cancel_file)}",
        "SI_FAILED=0",
        HELPERS,
    ]

    for index, step in enumerate(plan.steps, start=1):
        lines.append(f"SI_TITLE_{index}={_q(step.title)}")
        lines.append(f"si_step_{index}() {{")
        lines.extend(f"  {line}" for line in step.body)
        lines.append("}")
        lines.append("")

    lines.extend(
        [
            'for i in $(seq 1 "$SI_TOTAL"); do',
            '  if [ -n "$SI_CANCEL" ] && [ -e "$SI_CANCEL" ]; then',
            f'    printf "{MARK_CANCELLED}\\n"',
            "    break",
            "  fi",
            '  title_var="SI_TITLE_$i"',
            f'  printf "{MARK_STEP}%s@@%s@@%s\\n" "$i" "$SI_TOTAL" "${{!title_var}}"',
            '  "si_step_$i"',
            "  rc=$?",
            f'  printf "{MARK_RESULT}%s@@%s\\n" "$i" "$rc"',
            '  [ "$rc" -ne 0 ] && SI_FAILED=$((SI_FAILED + 1))',
            "done",
            f'printf "{MARK_DONE}%s\\n" "$SI_FAILED"',
            'exit "$SI_FAILED"',
        ]
    )
    return "\n".join(lines) + "\n"


# -- Ausführung ------------------------------------------------------------


class ScriptRunner:
    """Führt ein Skript als root aus und meldet jede Zeile per Rückruf.

    Die Rückrufe laufen im Arbeitsthread – die Oberfläche muss sie selbst
    auf den Hauptthread umlenken.
    """

    def __init__(self) -> None:
        self._process: subprocess.Popen | None = None
        self._workdir: Path | None = None
        self.cancel_file: Path | None = None

    def prepare(self) -> Path:
        """Legt das Arbeitsverzeichnis an und gibt den Pfad der Abbruchdatei zurück."""
        self._workdir = Path(tempfile.mkdtemp(prefix="silentinstaller-"))
        self.cancel_file = self._workdir / "abbruch"
        return self.cancel_file

    def start(
        self,
        script: str,
        on_line: Callable[[str], None],
        on_finished: Callable[[int, str | None], None],
    ) -> None:
        if self._workdir is None:
            self.prepare()
        assert self._workdir is not None

        script_path = self._workdir / "silentinstall.sh"
        script_path.write_text(script, encoding="utf-8")
        script_path.chmod(0o755)

        threading.Thread(
            target=self._worker,
            args=(script_path, on_line, on_finished),
            daemon=True,
        ).start()

    def _worker(
        self,
        script_path: Path,
        on_line: Callable[[str], None],
        on_finished: Callable[[int, str | None], None],
    ) -> None:
        command = self._privilege_command(script_path)
        if command is None:
            on_finished(
                -1,
                "Weder pkexec noch sudo gefunden. Bitte 'policykit-1' bzw. "
                "'polkit' installieren oder das Skript manuell als root starten.",
            )
            return

        try:
            self._process = subprocess.Popen(
                command,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                bufsize=1,
                errors="replace",
            )
        except OSError as exc:
            on_finished(-1, f"Start fehlgeschlagen: {exc}")
            return

        assert self._process.stdout is not None
        for line in self._process.stdout:
            on_line(line.rstrip("\n"))

        code = self._process.wait()
        error = None
        if code == 126:
            error = "Die Rechteanfrage wurde abgebrochen."
        elif code == 127:
            error = "Die Rechteanfrage wurde abgelehnt."
        on_finished(code, error)

    @staticmethod
    def _privilege_command(script_path: Path) -> list[str] | None:
        import shutil as _shutil

        if os.geteuid() == 0:
            return ["/bin/bash", str(script_path)]
        if _shutil.which("pkexec"):
            return ["pkexec", "/bin/bash", str(script_path)]
        if _shutil.which("sudo"):
            # Nur brauchbar, wenn bereits ein gültiges sudo-Ticket vorliegt.
            return ["sudo", "-n", "/bin/bash", str(script_path)]
        return None

    def cancel(self) -> None:
        """Bittet das Skript, nach dem laufenden Schritt aufzuhören.

        Ein hartes Abschießen käme nicht durch pkexec hindurch und würde außerdem
        riskieren, die Paketdatenbank in halbfertigem Zustand zu hinterlassen.
        """
        if self.cancel_file is not None:
            try:
                self.cancel_file.touch()
            except OSError:
                pass

    def cleanup(self) -> None:
        if self._workdir is not None:
            import shutil as _shutil

            _shutil.rmtree(self._workdir, ignore_errors=True)
            self._workdir = None
            self.cancel_file = None
