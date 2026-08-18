"""Zweisprachigkeit: Deutsch als Quellsprache, Englisch als Übersetzung.

Bewusst ohne gettext. Ein .mo-Übersetzungskatalog müsste vor dem Start mit
``msgfmt`` gebaut werden – auf einem frisch aufgesetzten Rechner, auf dem
SilentInstaller ja gerade laufen soll, ist das ein Werkzeug zu viel. Die
Tabelle hier braucht nichts außer Python.

Die Schlüssel sind die deutschen Zeichenketten aus dem Quelltext. Läuft das
Programm auf Deutsch, wird der Schlüssel unverändert zurückgegeben.
"""

from __future__ import annotations

import os

SUPPORTED = ("de", "en")
DEFAULT = "en"

_language = DEFAULT


def detect_language() -> str:
    """Ermittelt die Systemsprache aus den üblichen Umgebungsvariablen."""
    for variable in ("LANGUAGE", "LC_ALL", "LC_MESSAGES", "LANG"):
        value = os.environ.get(variable)
        if not value or value in ("C", "POSIX"):
            continue
        # LANGUAGE darf eine Liste sein: "de_DE:de:en_US:en"
        for part in value.split(":"):
            code = part.strip().split(".")[0].split("_")[0].lower()
            if code in SUPPORTED:
                return code
        return DEFAULT
    return DEFAULT


def set_language(code: str) -> str:
    """Setzt die Sprache. ``auto`` überlässt die Wahl dem System."""
    global _language
    if code == "auto" or code not in SUPPORTED:
        _language = detect_language()
    else:
        _language = code
    return _language


def language() -> str:
    return _language


def _(text: str) -> str:
    """Übersetzt eine deutsche Zeichenkette in die aktive Sprache."""
    if _language == "de":
        return text
    return TRANSLATIONS.get(_language, {}).get(text, text)


def translate_field(german: str, english: str) -> str:
    """Wählt zwischen zwei bereits vorhandenen Fassungen, etwa aus dem Katalog."""
    if _language != "de" and english:
        return english
    return german


#: Deutscher Quelltext -> englische Fassung.
TRANSLATIONS: dict[str, dict[str, str]] = {
    "en": {
        # -- Fenster, Navigation ------------------------------------------
        "Programme": "Programs",
        "Kategorien": "Categories",
        "Alle Programme": "All programs",
        "Ausgewählt": "Selected",
        "Installiert": "Installed",
        "Noch nicht installiert": "Not installed yet",
        "nicht unterstützt": "not supported",
        "Suchen (Strg+F)": "Search (Ctrl+F)",
        "Eigenes Programm hinzufügen": "Add your own program",
        "Programm, Paketname oder Stichwort …": "Program, package name or keyword …",
        "Nichts gefunden": "Nothing found",
        "Andere Kategorie wählen oder Suchbegriff anpassen.":
            "Pick another category or adjust your search.",
        # -- Menü ----------------------------------------------------------
        "Alle sichtbaren auswählen": "Select all visible",
        "Auswahl aufheben": "Clear selection",
        "Auswahl als Profil speichern …": "Save selection as profile …",
        "Profil laden …": "Load profile …",
        "Auswahl in Datei sichern …": "Export selection to file …",
        "Auswahl aus Datei laden …": "Import selection from file …",
        "Skript anzeigen …": "Show script …",
        "Installationsstand neu prüfen": "Re-check what is installed",
        "Einstellungen": "Preferences",
        "Über SilentInstaller": "About SilentInstaller",
        # -- Zeile und Auswahl ---------------------------------------------
        "nicht verfügbar": "not available",
        "installiert": "installed",
        "Bereits vorhanden über {quelle}": "Already present via {quelle}",
        "einen Prüfbefehl": "a check command",
        "Bearbeiten …": "Edit …",
        "Aus der Liste nehmen": "Remove from list",
        "Ausblenden": "Hide",
        "Webseite öffnen": "Open website",
        "Nichts ausgewählt": "Nothing selected",
        "{anzahl} ausgewählt": "{anzahl} selected",
        "{anzahl} ausgewählt · {vorhanden} davon bereits installiert":
            "{anzahl} selected · {vorhanden} already installed",
        "Installieren": "Install",
        "Entfernen": "Remove",
        "Abbrechen": "Cancel",
        "Speichern": "Save",
        "Laden": "Load",
        "Löschen": "Delete",
        "Schließen": "Close",
        "Kopieren": "Copy",
        "Fertig": "Done",
        # -- Katalog pflegen ------------------------------------------------
        "»{name}« gespeichert": "“{name}” saved",
        "»{name}« entfernt": "“{name}” removed",
        "»{name}« aus der Liste nehmen?": "Remove “{name}” from the list?",
        "Der Eintrag verschwindet nur aus SilentInstaller. Ein bereits "
        "installiertes Programm bleibt auf dem Rechner.":
            "The entry only disappears from SilentInstaller. An already "
            "installed program stays on your computer.",
        # -- Profile ---------------------------------------------------------
        "Erst Programme auswählen": "Select some programs first",
        "Name des Profils": "Profile name",
        "Auswahl als Profil speichern": "Save selection as profile",
        "{anzahl} Programme werden gesichert.": "{anzahl} programs will be saved.",
        "Profil »{name}« in {datei} gespeichert": "Profile “{name}” saved to {datei}",
        "{name} – {anzahl} Programme": "{name} — {anzahl} programs",
        "{anzahl} Profile in eigene Dateien überführt":
            "{anzahl} profiles moved into separate files",
        "Noch keine Profile gespeichert": "No profiles saved yet",
        "Profil laden": "Load profile",
        "Die gespeicherte Auswahl ersetzt die aktuelle.":
            "The saved selection replaces the current one.",
        "Profil »{name}« geladen: {anzahl} Programme":
            "Profile “{name}” loaded: {anzahl} programs",
        "Profil »{name}« gelöscht": "Profile “{name}” deleted",
        "Dieses System ({datum})": "This system ({datum})",
        "Profil »{name}« mit {anzahl} vorgefundenen Programmen angelegt":
            "Profile “{name}” created with the {anzahl} programs found here",
        # -- Sichern und Laden als Datei -------------------------------------
        "Auswahl sichern": "Export selection",
        "Auswahl laden": "Import selection",
        "SilentInstaller-Auswahl": "SilentInstaller selection",
        "Auswahl in {datei} gesichert": "Selection exported to {datei}",
        "Sichern fehlgeschlagen: {fehler}": "Export failed: {fehler}",
        "Laden fehlgeschlagen: {fehler}": "Import failed: {fehler}",
        "{anzahl} Programme geladen": "{anzahl} programs loaded",
        "{anzahl} Programme geladen, {eigene} eigene Einträge übernommen":
            "{anzahl} programs loaded, {eigene} custom entries added",
        "Diese Datei enthält keine SilentInstaller-Auswahl.":
            "This file does not contain a SilentInstaller selection.",
        "{anzahl} Einträge waren unbekannt und wurden übersprungen":
            "{anzahl} entries were unknown and got skipped",
        # -- Hauptmenü -------------------------------------------------------
        'Hauptmenü':
            'Main menu',
        'Auf diesem Rechner':
            'On this computer',
        'Auf einen anderen Rechner mitnehmen':
            'Take to another computer',
        'Setzt bei allen gerade angezeigten Programmen einen Haken':
            'Ticks every program currently shown',
        'Entfernt alle Haken':
            'Removes every tick',
        'Sichert die aktuelle Auswahl unter einem Namen – als Datei in ~/.config/silentinstaller/profile/. Gedacht zum schnellen Umschalten auf diesem Rechner.':
            'Saves the current selection under a name — one file in ~/.config/silentinstaller/profile/. Meant for switching quickly on this computer.',
        'Stellt eine gespeicherte Auswahl wieder her. Ersetzt die aktuellen Haken.':
            'Restores a saved selection. Replaces the current ticks.',
        'Legt die Auswahl als Datei ab, die du weitergeben kannst – USB-Stick, Nextcloud, Git. Gespeichert werden Kennungen, keine Paketnamen: Dieselbe Datei funktioniert auf Debian wie auf Arch. Selbst angelegte Programme wandern mit.':
            'Writes the selection to a file you can pass on — USB stick, Nextcloud, Git. It stores identifiers, not package names: the same file works on Debian and on Arch. Programs you added travel along.',
        'Liest eine mitgebrachte Datei ein, auch von einem anderen System. Was es hier nicht gibt, wird übersprungen und gemeldet.':
            'Reads a file you brought along, even from a different system. Anything unavailable here is skipped and reported.',
        'Zeigt den vollständigen Shell-Ablauf, der bei „Installieren“ mit Root-Rechten laufen würde – bevor etwas passiert':
            'Shows the complete shell run that “Install” would execute with root privileges — before anything happens',
        'Fragt apt, pacman und flatpak erneut, was installiert ist':
            'Asks apt, pacman and flatpak again what is installed',
        'Sprache, Erscheinungsbild, Flatpak-Vorrang und Speicherorte':
            'Language, colour scheme, Flatpak preference and file locations',

        # -- Infofenster -----------------------------------------------------
        'Was ist der Unterschied?':
            'What is the difference?',
        'Profile und Auswahldateien':
            'Profiles and selection files',
        'Profil – bleibt auf diesem Rechner':
            'Profile — stays on this computer',
        'Eine benannte Auswahl zum schnellen Umschalten. Praktisch, wenn du je nach Aufgabe andere Programme brauchst – etwa ein Profil fürs Büro und eines zum Entwickeln. Jedes Profil ist eine eigene Datei; gelöscht wird es über den Lade-Dialog.':
            'A named selection for switching quickly. Handy when different tasks need different programs — one profile for the office, another for development. Each profile is its own file; delete it from the load dialog.',
        'Liegt unter':
            'Stored in',
        'Auswahl als Datei – geht mit auf andere Rechner':
            'Selection as a file — travels to other computers',
        'Dieselbe Auswahl, aber an einem Ort deiner Wahl: USB-Stick, Nextcloud, Git-Ablage. Gespeichert werden Kennungen, keine Paketnamen – deshalb funktioniert dieselbe Datei auf Debian wie auf Arch. Auf dem einen System wird »firefox-esr« über APT geholt, auf dem anderen »firefox« über Pacman. Programme, die du selbst angelegt hast, wandern vollständig mit; der neue Rechner muss sie nicht kennen.':
            'The same selection, but wherever you like: USB stick, Nextcloud, a Git repository. It stores identifiers, not package names — which is why the same file works on Debian and on Arch. One system fetches “firefox-esr” via APT, the other “firefox” via Pacman. Programs you added yourself travel along in full; the new machine need not know them beforehand.',
        'Beides ist dasselbe Dateiformat':
            'Both use the same file format',
        'Eine Profildatei und eine ausgelagerte Auswahl sind identisch aufgebaut. Kopierst du eine mitgebrachte Datei in das Profilverzeichnis, steht sie beim nächsten Start unter »Profil laden«. Umgekehrt kannst du eine Profildatei direkt weitergeben.':
            'A profile file and an exported selection are built identically. Copy a file you brought along into the profile directory and it appears under “Load profile” on the next start. Conversely, you can pass a profile file straight on.',

        # -- Einstellungen ---------------------------------------------------
        "Allgemein": "General",
        "Darstellung": "Appearance",
        "Sprache": "Language",
        "Der Systemsprache folgen": "Follow the system language",
        "Automatisch ({sprache})": "Automatic ({sprache})",
        "Deutsch": "German",
        "Englisch": "English",
        "Erscheinungsbild": "Colour scheme",
        "Hell oder dunkel – oder dem Desktop überlassen":
            "Light or dark — or leave it to the desktop",
        "Wie das System": "Follow the system",
        "Hell": "Light",
        "Dunkel": "Dark",
        "Installation": "Installation",
        "Flatpak bevorzugen": "Prefer Flatpak",
        "Wo möglich Flathub statt der Distributionspakete verwenden":
            "Use Flathub instead of distribution packages where possible",
        "Beim Entfernen auch Einstellungen löschen":
            "Delete configuration when removing",
        "apt purge bzw. pacman -Rns statt eines einfachen Entfernens":
            "apt purge or pacman -Rns instead of a plain removal",
        "Dateien": "Files",
        "Eigener Katalog": "Your catalog",
        "Mitgelieferter Katalog": "Bundled catalog",
        "{anzahl} Einträge in silentinstaller/data/catalog.json – "
        "wird bei Aktualisierungen ersetzt":
            "{anzahl} entries in silentinstaller/data/catalog.json — "
            "replaced on updates",
        # -- Über ------------------------------------------------------------
        "Lieblingsprogramme nach einer Grundinstallation in einem Rutsch "
        "nachinstallieren – für Debian- und Arch-basierte Systeme.":
            "Install your favourite programs in one go after a fresh setup — "
            "for Debian- and Arch-based systems.",
        # -- Ausführung -------------------------------------------------------
        "Für die aktuelle Auswahl gibt es nichts zu tun":
            "Nothing to do for the current selection",
        "Alles schon installiert": "Everything is installed already",
        "Nichts zu entfernen": "Nothing to remove",
        "Erzeugtes Skript": "Generated script",
        "{anzahl} Programm(e) werden installiert":
            "{anzahl} program(s) will be installed",
        "{anzahl} Programm(e) werden entfernt": "{anzahl} program(s) will be removed",
        "Dafür laufen {schritte} Arbeitsschritte mit Root-Rechten. Das Passwort "
        "wird einmal abgefragt.":
            "That takes {schritte} steps with root privileges. You will be asked "
            "for your password once.",
        "Skript ansehen": "Show script",
        "Wird ausgeführt": "Running",
        "Vorbereitung": "Preparing",
        "Warte auf die Rechtefreigabe …": "Waiting for authorisation …",
        "Schritt {nummer} von {gesamt}": "Step {nummer} of {gesamt}",
        "erledigt": "done",
        "fehlgeschlagen (Code {code})": "failed (code {code})",
        "Abgebrochen auf Wunsch.": "Cancelled on request.",
        "Abbruch angefordert – der laufende Schritt wird noch zu Ende geführt.":
            "Cancellation requested — the current step will still finish.",
        "Alles erledigt": "All done",
        "Abgebrochen": "Cancelled",
        "Mit Fehlern beendet": "Finished with errors",
        "{anzahl} Schritt(e) fehlgeschlagen": "{anzahl} step(s) failed",
        "Fehlgeschlagen: {schritte}": "Failed: {schritte}",
        # -- Editor -------------------------------------------------------------
        "Programm bearbeiten": "Edit program",
        "Programm hinzufügen": "Add program",
        "Name": "Name",
        "Kennung (eindeutig, klein geschrieben)": "Identifier (unique, lower case)",
        "Beschreibung": "Description",
        "Kategorie": "Category",
        "Neue Kategorie …": "New category …",
        "Name der neuen Kategorie": "Name of the new category",
        "Installationsquellen": "Installation sources",
        "Mindestens eine Quelle ausfüllen. Mehrere Pakete durch Leerzeichen "
        "oder Komma trennen.":
            "Fill in at least one source. Separate multiple packages with "
            "spaces or commas.",
        "APT-Pakete (Debian & Co.)": "APT packages (Debian and friends)",
        "Pacman-Pakete (Arch & Co.)": "Pacman packages (Arch and friends)",
        "Flatpak-Kennung, z. B. org.gimp.GIMP": "Flatpak ID, e.g. org.gimp.GIMP",
        ".deb-Download-Adresse": ".deb download address",
        "Feinheiten": "Details",
        "Bevorzugte Quelle": "Preferred source",
        "Automatisch (nativ zuerst)": "Automatic (native first)",
        "APT bevorzugen": "Prefer APT",
        "Pacman bevorzugen": "Prefer Pacman",
        ".deb-Paket bevorzugen": "Prefer .deb package",
        "Symbolname (optional)": "Icon name (optional)",
        "Prüfbefehl (optional, z. B. »code«)": "Check command (optional, e.g. “code”)",
        "Nacharbeiten": "Follow-up commands",
        "Shell-Befehle, die nach der Installation als root laufen.":
            "Shell commands that run as root after the installation.",
        "Bitte einen Namen eintragen.": "Please enter a name.",
        "Die Kennung »{kennung}« ist bereits vergeben.":
            "The identifier “{kennung}” is already taken.",
        "Mindestens eine Installationsquelle wird gebraucht.":
            "At least one installation source is required.",
        "Bitte die neue Kategorie benennen.": "Please name the new category.",
    }
}
