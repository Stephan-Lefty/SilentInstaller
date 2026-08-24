#!/bin/sh
#
# Repariert widersprüchliche Paketquellen, die ältere Fassungen von
# SilentInstaller angelegt haben.
#
# Legte SilentInstaller eine Fremdquelle an, die die Distribution bereits
# mitbrachte, standen dieselbe Quelle zweimal mit verschiedenen
# Signaturschlüsseln in der Liste. apt verweigert dann jeden Dienst:
#
#   Fehler: Widersprüchliche Werte gesetzt für Option Signed-By ...
#   Fehler: Die Liste der Quellen konnte nicht gelesen werden.
#
# In diesem Zustand lässt sich auch das Paket mit der Fehlerbehebung nicht
# mehr installieren – deshalb kommt dieses Skript ohne apt aus.
#
#   sudo ./apt-quellen-reparieren.sh          zeigt nur an, was zu tun wäre
#   sudo ./apt-quellen-reparieren.sh --machen  entfernt die Widersprüche
#
set -u

MACHEN=0
[ "${1:-}" = "--machen" ] && MACHEN=1

QUELLEN_D=/etc/apt/sources.list.d
gefunden=0

if [ ! -d "$QUELLEN_D" ]; then
    echo "Kein Verzeichnis $QUELLEN_D – hier gibt es nichts zu reparieren."
    exit 0
fi

for datei in "$QUELLEN_D"/*.list; do
    [ -f "$datei" ] || continue

    # Nur von SilentInstaller angelegte Einträge betrachten. Sie erkennen sich
    # am Namen ihres Signaturschlüssels.
    grep -q 'silentinstaller-' "$datei" || continue

    url=$(grep -oE 'https?://[^ ]+' "$datei" | head -1)
    [ -n "$url" ] || continue
    url=${url%/}

    # Steht dieselbe Quelle noch in einer anderen Datei? Nur dann liegt ein
    # Widerspruch vor – eine allein stehende eigene Quelle ist in Ordnung.
    for andere in /etc/apt/sources.list "$QUELLEN_D"/*.list "$QUELLEN_D"/*.sources; do
        [ -f "$andere" ] || continue
        [ "$andere" = "$datei" ] && continue
        if grep -qsF "$url" "$andere"; then
            gefunden=$((gefunden + 1))
            echo "Widerspruch gefunden:"
            echo "  $datei"
            echo "  steht im Widerspruch zu $andere"
            echo "  gemeinsame Quelle: $url"
            if [ "$MACHEN" -eq 1 ]; then
                rm -f "$datei" && echo "  -> entfernt"
            else
                echo "  -> würde entfernt (mit --machen ausführen)"
            fi
            break
        fi
    done
done

echo
if [ "$gefunden" -eq 0 ]; then
    echo "Keine widersprüchlichen Paketquellen gefunden."
elif [ "$MACHEN" -eq 1 ]; then
    echo "$gefunden Widerspruch/Widersprüche behoben. Jetzt: sudo apt update"
else
    echo "$gefunden Widerspruch/Widersprüche gefunden."
    echo "Zum Beheben: sudo $0 --machen"
fi
