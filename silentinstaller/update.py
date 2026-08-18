"""Sieht bei GitHub nach, ob eine neuere Fassung vorliegt.

Bewusst zurückhaltend: Es wird nur gelesen und nur gemeldet. Heruntergeladen
oder gar installiert wird nichts – wer eine neue Fassung möchte, entscheidet
das selbst und holt sie über den üblichen Weg seines Systems.

Die Abfrage läuft in einem eigenen Faden und scheitert still: Ohne Netz, mit
Zeitüberschreitung oder bei unerwarteter Antwort bleibt es einfach beim
bisherigen Stand. Ein Werkzeug zum Installieren von Programmen soll nicht mit
Fehlermeldungen über sich selbst aufhalten.
"""

from __future__ import annotations

import json
import threading
import urllib.error
import urllib.request
from datetime import date
from typing import Callable

RELEASE_API = (
    "https://api.github.com/repos/Stephan-Lefty/SilentInstaller/releases/latest"
)
RELEASE_SEITE = "https://github.com/Stephan-Lefty/SilentInstaller/releases/latest"

#: Wie oft von selbst nachgesehen wird. Öfter als einmal am Tag wäre unhöflich
#: gegenüber dem Server und brächte nichts.
ABSTAND_TAGE = 1


def als_zahlen(fassung: str) -> tuple[int, ...]:
    """Macht aus »v1.2.1« die Zahlenfolge (1, 2, 1).

    Alles, was keine Zahl ist, wird verworfen – so stören weder das führende
    »v« noch Zusätze wie »-beta«.
    """
    teile: list[int] = []
    for stueck in fassung.strip().lstrip("vV").replace("-", ".").split("."):
        ziffern = "".join(c for c in stueck if c.isdigit())
        if not ziffern:
            break
        teile.append(int(ziffern))
    return tuple(teile) or (0,)


def ist_neuer(gefunden: str, laufend: str) -> bool:
    return als_zahlen(gefunden) > als_zahlen(laufend)


def hole_neueste(zeitgrenze: float = 6.0) -> str | None:
    """Fragt GitHub nach der neuesten Fassung. Gibt etwa »1.3.0« zurück."""
    anfrage = urllib.request.Request(
        RELEASE_API,
        headers={
            "Accept": "application/vnd.github+json",
            "User-Agent": "SilentInstaller",
        },
    )
    try:
        with urllib.request.urlopen(anfrage, timeout=zeitgrenze) as antwort:
            daten = json.loads(antwort.read().decode("utf-8"))
    except (urllib.error.URLError, TimeoutError, ValueError, OSError):
        return None

    marke = daten.get("tag_name") or daten.get("name") or ""
    return str(marke).lstrip("vV") or None


def pruefe_im_hintergrund(
    laufende_fassung: str,
    fertig: Callable[[str | None], None],
    zeitgrenze: float = 6.0,
) -> None:
    """Sucht nebenher nach einer neueren Fassung.

    ``fertig`` bekommt die gefundene Fassung – oder None, wenn es nichts Neues
    gibt oder die Abfrage nicht geklappt hat. Der Rückruf läuft im Arbeitsfaden;
    die Oberfläche muss ihn selbst auf ihren Hauptfaden umlenken.
    """

    def arbeit() -> None:
        neueste = hole_neueste(zeitgrenze)
        if neueste and ist_neuer(neueste, laufende_fassung):
            fertig(neueste)
        else:
            fertig(None)

    threading.Thread(target=arbeit, daemon=True).start()


def heute_schon_geprueft(letzter_lauf: str) -> bool:
    """Wurde innerhalb des Abstands bereits nachgesehen?"""
    if not letzter_lauf:
        return False
    try:
        vorher = date.fromisoformat(letzter_lauf)
    except ValueError:
        return False
    return (date.today() - vorher).days < ABSTAND_TAGE
