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
  command -v update-desktop-database >/dev/null 2>&1 &&
    update-desktop-database "$DESKTOP_DIR" 2>/dev/null || true
  command -v gtk-update-icon-cache >/dev/null 2>&1 &&
    gtk-update-icon-cache -qtf "$ICON_DIR" 2>/dev/null || true
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

echo "Fertig. SilentInstaller steht im Anwendungsmenü."
case ":$PATH:" in
  *":$BIN_DIR:"*) echo "Im Terminal genügt: silentinstaller" ;;
  *) echo "Hinweis: $BIN_DIR liegt nicht im PATH – Start über $ZIEL/silentinstaller.sh" ;;
esac
