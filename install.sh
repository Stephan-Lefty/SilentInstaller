#!/usr/bin/env bash
#
# Legt SilentInstaller unter ~/.local/share/silentinstaller ab, trägt einen
# Menüeintrag ein und meldet das Anwendungssymbol beim Icon-Theme an.
# Ohne Root-Rechte, nur für den aktuellen Benutzer.
#
set -euo pipefail

QUELLE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
DATEN="${XDG_DATA_HOME:-$HOME/.local/share}"
ZIEL="$DATEN/silentinstaller"
DESKTOP_DIR="$DATEN/applications"
ICON_DIR="$DATEN/icons/hicolor"
BIN_DIR="$HOME/.local/bin"
KENNUNG="de.stephanlefty.SilentInstaller"

aktualisiere_zwischenspeicher() {
  # Jeder Desktop führt seine eigene Buchhaltung über Menüeinträge und
  # Symbole. Fehlt einer dieser Anstöße, taucht der Eintrag erst nach einer
  # Neuanmeldung auf – oder bleibt ohne Symbol.
  if command -v update-desktop-database >/dev/null 2>&1; then
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
  fi
  if command -v gtk-update-icon-cache >/dev/null 2>&1; then
    gtk-update-icon-cache -qtf "$ICON_DIR" 2>/dev/null || true
  fi
  # Plasma liest sein Menü aus einer eigenen Datenbank (ksycoca) und merkt
  # eine neue .desktop-Datei sonst erst beim nächsten Anmelden.
  for werkzeug in kbuildsycoca6 kbuildsycoca5; do
    if command -v "$werkzeug" >/dev/null 2>&1; then
      "$werkzeug" --noincremental >/dev/null 2>&1 || true
      break
    fi
  done
  # XFCE, LXQt und Co. lesen die Menüs über xdg-desktop-menu neu ein.
  if command -v xdg-desktop-menu >/dev/null 2>&1; then
    xdg-desktop-menu forceupdate --mode user 2>/dev/null || true
  fi
}

pruefe_ergebnis() {
  local fehler=0
  [ -f "$DESKTOP_DIR/$KENNUNG.desktop" ] || {
    echo "  Menüeintrag fehlt: $DESKTOP_DIR/$KENNUNG.desktop" >&2
    fehler=1
  }
  [ -f "$ICON_DIR/48x48/apps/$KENNUNG.png" ] || {
    echo "  Symbol fehlt: $ICON_DIR/48x48/apps/$KENNUNG.png" >&2
    fehler=1
  }
  # Findet der Desktop das Symbol auch unter seinem Namen?
  if command -v kiconfinder6 >/dev/null 2>&1; then
    kiconfinder6 "$KENNUNG" >/dev/null 2>&1 ||
      echo "  Hinweis: KDE findet das Symbol »$KENNUNG« noch nicht." >&2
  fi
  return $fehler
}

case "${1:-install}" in
  uninstall|--uninstall|remove)
    rm -rf "$ZIEL"
    rm -f "$DESKTOP_DIR/$KENNUNG.desktop"
    rm -f "$BIN_DIR/silentinstaller"
    find "$ICON_DIR" \( -name "$KENNUNG.*" -o -name "silentinstaller-*" \) -delete 2>/dev/null || true
    aktualisiere_zwischenspeicher
    echo "SilentInstaller entfernt. Der eigene Katalog unter"
    echo "~/.config/silentinstaller/ bleibt erhalten."
    exit 0
    ;;
esac

mkdir -p "$ZIEL" "$DESKTOP_DIR" "$BIN_DIR"

cp -r "$QUELLE/silentinstaller" "$ZIEL/"
cp -r "$QUELLE/data" "$ZIEL/"
cp "$QUELLE/silentinstaller.sh" "$ZIEL/"
chmod +x "$ZIEL/silentinstaller.sh"

ln -sf "$ZIEL/silentinstaller.sh" "$BIN_DIR/silentinstaller"

# Symbol in allen mitgelieferten Größen beim Icon-Theme anmelden.
while IFS= read -r datei; do
  unterordner="${datei#"$QUELLE/data/icons/hicolor/"}"
  mkdir -p "$ICON_DIR/$(dirname "$unterordner")"
  cp "$datei" "$ICON_DIR/$unterordner"
done < <(find "$QUELLE/data/icons/hicolor" -type f \( -name "$KENNUNG.*" -o -name "silentinstaller-*" \))

sed "s|@EXEC@|$ZIEL/silentinstaller.sh|" \
  "$QUELLE/data/$KENNUNG.desktop" >"$DESKTOP_DIR/$KENNUNG.desktop"

aktualisiere_zwischenspeicher

if pruefe_ergebnis; then
  echo "Fertig. SilentInstaller steht im Anwendungsmenü."
else
  echo "Die Installation ist unvollständig – siehe die Meldungen oben." >&2
fi

case ":$PATH:" in
  *":$BIN_DIR:"*) echo "Im Terminal genügt: silentinstaller" ;;
  *) echo "Hinweis: $BIN_DIR liegt nicht im PATH – Start über $ZIEL/silentinstaller.sh" ;;
esac

echo "Erscheint der Eintrag nicht sofort, hilft ein Ab- und Anmelden."
