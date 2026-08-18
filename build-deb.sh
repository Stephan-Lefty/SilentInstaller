#!/usr/bin/env bash
#
# Baut ein installierbares Debian-Paket aus dem Projektverzeichnis.
#
# Läuft auch auf einem Arch-System, solange dpkg-deb vorhanden ist – gebaut
# wird ein reines Architektur-unabhängiges Paket ohne Übersetzungsschritt.
#
#   ./build-deb.sh              baut dist/silentinstaller_<version>_all.deb
#   ./build-deb.sh --pruefen    baut und prüft das Ergebnis zusätzlich
#
set -euo pipefail

QUELLE="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
PAKET="silentinstaller"
KENNUNG="de.stephanlefty.SilentInstaller"

VERSION="$(sed -n 's/^__version__ = "\(.*\)"/\1/p' "$QUELLE/silentinstaller/__init__.py")"
[ -n "$VERSION" ] || { echo "Version nicht gefunden" >&2; exit 1; }

BETREUER="${DEBFULLNAME:-Stephan-Lefty} <${DEBEMAIL:-204562172+Stephan-Lefty@users.noreply.github.com}>"

BAU="$QUELLE/build/${PAKET}_${VERSION}"
ZIEL="$QUELLE/dist"

command -v dpkg-deb >/dev/null || { echo "dpkg-deb fehlt" >&2; exit 1; }

rm -rf "$BAU"
mkdir -p "$BAU/DEBIAN" \
         "$BAU/usr/bin" \
         "$BAU/usr/share/$PAKET" \
         "$BAU/usr/share/applications" \
         "$BAU/usr/share/icons/hicolor" \
         "$BAU/usr/share/doc/$PAKET"

# -- Programm ---------------------------------------------------------------
cp -r "$QUELLE/silentinstaller" "$BAU/usr/share/$PAKET/"
find "$BAU/usr/share/$PAKET" -name '__pycache__' -type d -exec rm -rf {} + 2>/dev/null || true

# Das Programm sucht seine Symbole neben dem Paketverzeichnis.
mkdir -p "$BAU/usr/share/$PAKET/data"
cp -r "$QUELLE/data/icons" "$BAU/usr/share/$PAKET/data/"

# -- Symbole ins System-Thema ----------------------------------------------
cp -r "$QUELLE/data/icons/hicolor/." "$BAU/usr/share/icons/hicolor/"

# -- Startskript ------------------------------------------------------------
cat >"$BAU/usr/bin/$PAKET" <<'START'
#!/usr/bin/python3
"""SilentInstaller starten."""

import sys

sys.path.insert(0, "/usr/share/silentinstaller")

from silentinstaller.app import main  # noqa: E402

sys.exit(main())
START
chmod 0755 "$BAU/usr/bin/$PAKET"

# -- Menüeintrag ------------------------------------------------------------
sed "s|@EXEC@|/usr/bin/$PAKET|" "$QUELLE/data/$KENNUNG.desktop" \
  >"$BAU/usr/share/applications/$KENNUNG.desktop"

# -- Unterlagen -------------------------------------------------------------
cp "$QUELLE/README.md" "$QUELLE/README.en.md" "$BAU/usr/share/doc/$PAKET/"
gzip -9n -c "$QUELLE/CHANGELOG.md" >"$BAU/usr/share/doc/$PAKET/changelog.gz"

cat >"$BAU/usr/share/doc/$PAKET/copyright" <<COPY
Format: https://www.debian.org/doc/packaging-manuals/copyright-format/1.0/
Upstream-Name: SilentInstaller
Source: https://github.com/Stephan-Lefty/SilentInstaller

Files: *
Copyright: 2026 Stephan-Lefty
License: MIT

License: MIT
 Permission is hereby granted, free of charge, to any person obtaining a copy
 of this software and associated documentation files (the "Software"), to deal
 in the Software without restriction, including without limitation the rights
 to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
 copies of the Software, and to permit persons to whom the Software is
 furnished to do so, subject to the following conditions:
 .
 The above copyright notice and this permission notice shall be included in
 all copies or substantial portions of the Software.
 .
 THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
 IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
 FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
 AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
 LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
 OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
 THE SOFTWARE.
COPY

# -- Steuerdatei ------------------------------------------------------------
GROESSE=$(du -ks "$BAU" | cut -f1)

cat >"$BAU/DEBIAN/control" <<CONTROL
Package: $PAKET
Version: $VERSION
Section: admin
Priority: optional
Architecture: all
Depends: python3 (>= 3.10),
         python3-gi,
         python3-gi-cairo,
         gir1.2-gtk-4.0,
         gir1.2-adw-1,
         policykit-1 | pkexec
Recommends: flatpak
Suggests: gnome-software-plugin-flatpak
Installed-Size: $GROESSE
Maintainer: $BETREUER
Homepage: https://github.com/Stephan-Lefty/SilentInstaller
Description: Lieblingsprogramme nach der Grundinstallation nachrüsten
 SilentInstaller hält die eigenen Lieblingsprogramme in einer Liste vor und
 installiert sie nach einer Grundinstallation in einem einzigen Durchlauf –
 mit genau einer Passwortabfrage.
 .
 Jeder Eintrag kennt seine Paketnamen für APT, Pacman und Flathub; auf dem
 laufenden System wird automatisch die passende Quelle gewählt. Neben
 Distributionspaketen und Flatpak werden direkte .deb-Downloads und
 Fremd-Repositorys mit eigenem Signaturschlüssel unterstützt.
 .
 Aus der Auswahl entsteht ein einziges Shell-Skript, das sich vor dem Start
 ansehen lässt. Eigene Programme lassen sich in der Oberfläche pflegen, die
 Auswahl als Datei sichern und auf einem anderen Rechner wieder einlesen –
 gleich ob dieser auf Debian oder Arch beruht.
 .
 Die Oberfläche spricht Deutsch und Englisch und richtet sich nach der
 Systemsprache.
CONTROL

# -- Nach der Installation --------------------------------------------------
cat >"$BAU/DEBIAN/postinst" <<'POSTINST'
#!/bin/sh
set -e
if [ "$1" = "configure" ]; then
    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
        gtk-update-icon-cache -qtf /usr/share/icons/hicolor || true
    fi
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database -q /usr/share/applications || true
    fi
fi
exit 0
POSTINST

cat >"$BAU/DEBIAN/postrm" <<'POSTRM'
#!/bin/sh
set -e
if [ "$1" = "remove" ] || [ "$1" = "purge" ]; then
    if command -v gtk-update-icon-cache >/dev/null 2>&1; then
        gtk-update-icon-cache -qtf /usr/share/icons/hicolor || true
    fi
    if command -v update-desktop-database >/dev/null 2>&1; then
        update-desktop-database -q /usr/share/applications || true
    fi
fi
exit 0
POSTRM

chmod 0755 "$BAU/DEBIAN/postinst" "$BAU/DEBIAN/postrm"

# Rechte geraderücken – Debian erwartet root:root und keine Schreibrechte
# für die Gruppe.
find "$BAU" -type d -exec chmod 0755 {} +
find "$BAU" -type f -exec chmod 0644 {} +
chmod 0755 "$BAU/usr/bin/$PAKET" "$BAU/DEBIAN/postinst" "$BAU/DEBIAN/postrm"
chmod 0755 "$BAU/usr/share/$PAKET/silentinstaller.sh" 2>/dev/null || true

# -- Bauen ------------------------------------------------------------------
mkdir -p "$ZIEL"
DATEI="$ZIEL/${PAKET}_${VERSION}_all.deb"

if command -v fakeroot >/dev/null 2>&1; then
    fakeroot dpkg-deb --build --root-owner-group "$BAU" "$DATEI" >/dev/null
else
    dpkg-deb --build --root-owner-group "$BAU" "$DATEI" >/dev/null
fi

echo "Gebaut: $DATEI"
echo "Größe:  $(du -h "$DATEI" | cut -f1)"

if [ "${1:-}" = "--pruefen" ]; then
    echo
    echo "--- Steuerdatei ---"
    dpkg-deb --info "$DATEI"
    echo "--- Inhalt ---"
    dpkg-deb --contents "$DATEI" | awk '{print $6, $7, $8}'
    command -v lintian >/dev/null 2>&1 && { echo "--- lintian ---"; lintian "$DATEI" || true; }
fi
