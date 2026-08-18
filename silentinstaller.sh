#!/usr/bin/env bash
#
# SilentInstaller – Starter / launcher
#
# Prüft, ob die GTK4-Anbindung für Python vorhanden ist, bietet die fehlenden
# Pakete zur Nachinstallation an und startet dann die Oberfläche.
#
# Checks whether the GTK4 bindings for Python are present, offers to install
# the missing packages and then starts the interface.
#
set -uo pipefail

HIER="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"

rot=$'\e[31m'; gruen=$'\e[32m'; gelb=$'\e[33m'; fett=$'\e[1m'; aus=$'\e[0m'

# Sprache aus der Umgebung ableiten – dieselbe Regel wie in der Oberfläche.
sprache=en
case "${LANGUAGE:-${LC_ALL:-${LC_MESSAGES:-${LANG:-}}}}" in
  de*|*:de*) sprache=de ;;
esac

# Gibt je nach Sprache den ersten oder zweiten Text aus.
sag() { if [ "$sprache" = de ]; then printf '%s\n' "$1"; else printf '%s\n' "$2"; fi; }

fehler() { printf '%s%s%s\n' "$rot" "$(sag "$1" "$2")" "$aus" >&2; }
ok()     { printf '%s✓%s %s\n' "$gruen" "$aus" "$(sag "$1" "$2")"; }

familie() {
  local id id_like
  if [ -r /etc/os-release ]; then
    # shellcheck disable=SC1091
    . /etc/os-release
    id="${ID:-}"; id_like="${ID_LIKE:-}"
    case " $id $id_like " in
      *debian*|*ubuntu*) echo debian; return ;;
      *arch*|*manjaro*)  echo arch;   return ;;
    esac
  fi
  command -v apt-get >/dev/null 2>&1 && { echo debian; return; }
  command -v pacman  >/dev/null 2>&1 && { echo arch;   return; }
  echo unbekannt
}

pruefe_python() {
  python3 - <<'PY' 2>/dev/null
import gi
gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")
from gi.repository import Adw, Gtk  # noqa: F401
PY
}

installiere_abhaengigkeiten() {
  local art="$1" antwort
  local -a befehl
  case "$art" in
    debian)
      befehl=(apt-get install -y python3 python3-gi python3-gi-cairo
              gir1.2-gtk-4.0 gir1.2-adw-1 pkexec)
      ;;
    arch)
      befehl=(pacman -S --needed --noconfirm python python-gobject gtk4
              libadwaita polkit)
      ;;
    *)
      fehler "Unbekanntes System – bitte python3-gi, GTK 4 und libadwaita von Hand installieren." \
             "Unknown system — please install python3-gi, GTK 4 and libadwaita manually."
      return 1
      ;;
  esac

  printf '\n%s%s%s\n' "$fett" \
    "$(sag "Es fehlen noch ein paar Grundlagen:" "A few basics are still missing:")" "$aus"
  printf '  %s\n\n' "${befehl[*]}"

  read -r -p "$(sag "Jetzt mit Root-Rechten installieren? [J/n] " \
                    "Install them now with root privileges? [Y/n] ")" antwort
  case "${antwort:-j}" in
    [nN]*) return 1 ;;
  esac

  if [ "$art" = debian ]; then
    sudo apt-get update || return 1
    # Das Polkit-Paket heißt je nach Debian-Fassung pkexec oder policykit-1.
    sudo "${befehl[@]}" || sudo apt-get install -y python3 python3-gi \
      python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 policykit-1 || return 1
  else
    sudo "${befehl[@]}" || return 1
  fi
  ok "Grundlagen installiert." "Basics installed."
}

if ! command -v python3 >/dev/null 2>&1; then
  fehler "python3 wurde nicht gefunden." "python3 was not found."
  installiere_abhaengigkeiten "$(familie)" || exit 1
fi

if ! pruefe_python; then
  printf '%s%s%s\n' "$gelb" \
    "$(sag "GTK 4 oder libadwaita fehlen für Python." \
           "GTK 4 or libadwaita are missing for Python.")" "$aus"
  installiere_abhaengigkeiten "$(familie)" || exit 1
  if ! pruefe_python; then
    fehler "Die GTK4-Anbindung lässt sich weiterhin nicht laden. Abbruch." \
           "The GTK4 bindings still cannot be loaded. Aborting."
    exit 1
  fi
fi

cd "$HIER" || exit 1
exec python3 -m silentinstaller "$@"
