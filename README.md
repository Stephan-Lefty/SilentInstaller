<img src="data/logo.png" alt="SilentInstaller" width="420">

**[Deutsch](README.md) · [English](README.en.md) · [Änderungsprotokoll](CHANGELOG.md)**

Nach einer Grundinstallation von Debian 13, Ubuntu, Linux Mint, Arch, Manjaro
oder EndeavourOS fehlen immer dieselben zwanzig Programme. SilentInstaller hält
deine Lieblingsprogramme in einer Liste vor, hakt sie in einer GTK4-Oberfläche
ab und installiert sie in einem einzigen Durchlauf – mit genau einer
Passwortabfrage.

Der Desktop ist dabei egal: GNOME, KDE, XFCE, Cinnamon, Sway. Die Oberfläche
baut auf GTK 4 und libadwaita, läuft also überall – auf Deutsch oder Englisch,
hell oder dunkel.

## Was es kann

- **Ein Katalog, zwei Welten.** Jedes Programm kennt seine Paketnamen für APT
  *und* Pacman *und* Flathub. SilentInstaller wählt auf dem laufenden System
  automatisch die passende Quelle.
- **Vier Quellenarten.** Distributionspakete (apt/pacman), Flatpak von Flathub,
  direkte `.deb`-Downloads und Fremd-Repositorys mit Signaturschlüssel
  (Visual Studio Code, Signal, Brave, Vivaldi).
- **Eigene Programme pflegen.** Hinzufügen, bearbeiten und wieder herausnehmen
  direkt in der Oberfläche – ohne Texteditor. Deine Änderungen landen in
  `~/.config/silentinstaller/catalog.json`, die Mitlieferung bleibt unberührt.
- **Auswahl mitnehmen.** Einmal „Büro-PC“ oder „Entwicklungsrechner“
  zusammenstellen und als Datei sichern. Auf dem nächsten Rechner die Datei
  laden – alles ist wieder angehakt, **egal ob dort Debian oder Arch läuft**.
  Selbst angelegte Programme wandern vollständig mit in die Datei.
- **Profile.** Benannte Auswahlen, je eine Datei unter
  `~/.config/silentinstaller/profile/`. Beim ersten Start entsteht automatisch
  eines mit allen Programmen, die schon auf dem Rechner liegen – der gewachsene
  Bestand ist damit gesichert.
- **Deutsch und Englisch.** Die Sprache richtet sich nach dem System und lässt
  sich in den Einstellungen fest wählen. Der Wechsel greift sofort.
- **Hell und dunkel.** Wie der Desktop – oder fest eingestellt.
- **Erst schauen, dann installieren.** Über „Skript anzeigen“ siehst du den
  vollständigen Shell-Ablauf, bevor irgendetwas passiert.
- **Erkennt Vorhandenes.** Bereits installierte Programme werden markiert und
  bei der Installation übersprungen.
- **Auch wieder runter.** Ausgewählte Programme lassen sich ebenso entfernen,
  auf Wunsch samt Konfiguration.

## Installation

### Debian, Ubuntu, Linux Mint … – als Paket

```bash
sudo apt install ./silentinstaller_1.2.0_all.deb
```

Das Paket bringt alle Abhängigkeiten mit, legt den Menüeintrag an und meldet
das Symbol beim System an. Danach genügt `silentinstaller` im Terminal oder der
Eintrag im Anwendungsmenü. Entfernen mit `sudo apt remove silentinstaller`.

Das Paket lässt sich aus dem Quelltext selbst bauen – auch auf einem
Arch-System, solange `dpkg-deb` vorhanden ist:

```bash
./build-deb.sh              # ergibt dist/silentinstaller_<version>_all.deb
./build-deb.sh --pruefen    # baut und zeigt Steuerdatei und Inhalt
```

### Aus dem Quelltext – alle Systeme

```bash
git clone https://github.com/Stephan-Lefty/SilentInstaller.git
cd SilentInstaller
./silentinstaller.sh
```

Der Starter prüft, ob GTK 4 und libadwaita für Python bereitstehen, und bietet
die fehlenden Pakete zur Nachinstallation an.

Für einen dauerhaften Menüeintrag:

```bash
./install.sh            # nach ~/.local/share/silentinstaller
./install.sh uninstall  # wieder entfernen
```

### Voraussetzungen

| System            | Pakete                                                                    |
| ----------------- | ------------------------------------------------------------------------- |
| Debian, Ubuntu, … | `python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 pkexec`           |
| Arch, Manjaro, …  | `python-gobject gtk4 libadwaita polkit`                                    |

Vorausgesetzt werden Python 3.10 oder neuer, GTK 4.6+, libadwaita 1.4+ und
polkit für die Rechteanfrage.

## Bedienung

1. Links eine Kategorie wählen oder mit `Strg+F` nach einem Programm suchen.
2. Rechts die gewünschten Programme ankreuzen.
3. Unten auf **Installieren** klicken, das Vorhaben bestätigen, Passwort eingeben.
4. Der Fortschritt läuft mit vollständiger Ausgabe im Fenster mit.

Tastenkürzel: `Strg+N` neues Programm, `Strg+F` suchen, `Strg+R`
Installationsstand neu prüfen, `Strg+D` Skript anzeigen, `Strg+S` Auswahl
sichern, `Strg+O` Auswahl laden, `Strg+Q` beenden.

## Die Auswahl auf den nächsten Rechner mitnehmen

Genau dafür ist SilentInstaller gedacht: einmal zusammenstellen, überall
verwenden.

1. Programme ankreuzen.
2. Menü ▸ **Auswahl in Datei sichern …** – heraus kommt eine `.json`-Datei.
3. Diese Datei auf den neuen Rechner bringen (USB-Stick, Nextcloud, Git-Ablage).
4. Dort Menü ▸ **Auswahl aus Datei laden …** – alles ist wieder angehakt.
5. **Installieren** drücken.

Die Datei speichert Kennungen, keine Paketnamen. Deshalb funktioniert dieselbe
Datei auf Debian wie auf Arch: Auf dem einen System wird `firefox-esr` per APT
installiert, auf dem anderen `firefox` per Pacman. Programme, die es auf dem
Zielsystem nicht gibt – Synaptic etwa kennt Arch nicht – werden übersprungen
und beim Laden gemeldet.

Selbst angelegte Programme werden mit ihrer vollständigen Definition in die
Datei geschrieben. Der neue Rechner muss sie also nicht kennen; er lernt sie
beim Laden dazu.

## Wo liegt was

| Was | Wo |
| --- | --- |
| Profile, je eine Datei | `~/.config/silentinstaller/profile/` |
| Eigene Programme | `~/.config/silentinstaller/catalog.json` |
| Einstellungen | `~/.config/silentinstaller/settings.json` |
| Ausgelagerte Auswahl | wohin du möchtest |

Profildatei und ausgelagerte Auswahl sind dasselbe Format. Eine Datei, die du
über „Auswahl in Datei sichern“ erzeugt hast, kannst du also einfach ins
Profilverzeichnis kopieren – beim nächsten Start steht sie unter „Profil laden“.

## Sprache und Erscheinungsbild

Beim Start liest SilentInstaller `LANGUAGE`, `LC_ALL`, `LC_MESSAGES` und `LANG`
aus. Steht dort Deutsch, wird die Oberfläche deutsch; bei allem anderen
englisch. Wer das nicht möchte, stellt unter *Einstellungen ▸ Darstellung* fest
ein, was er will – dort sitzt auch die Umschaltung zwischen hell, dunkel und
„wie das System“.

## Wie ein Durchlauf abläuft

SilentInstaller schreibt aus deiner Auswahl ein einziges Shell-Skript und
startet es über `pkexec`. Das hat drei Gründe: nur eine Passwortabfrage,
gebündelte Paketinstallation statt siebzig Einzelaufrufe – und du kannst das
Skript vorher lesen.

Die Schritte laufen in sinnvoller Reihenfolge: erst Fremdquellen und
Paketbereiche einrichten, dann `apt-get update`, dann die Installation. Scheitert
eine Sammelinstallation, werden die Pakete einzeln nachgereicht, damit ein
einziges kaputtes Paket nicht den ganzen Durchlauf kippt.

**Abbrechen** hält nach dem laufenden Schritt an, statt mitten in einer
Paketoperation abzuschießen – das hinterlässt keine halbfertige Paketdatenbank.

## Eigene Programme eintragen

Am bequemsten über **＋** in der Kopfleiste. Wer die Datei lieber direkt
bearbeitet, findet sie unter `~/.config/silentinstaller/catalog.json`:

```json
{
  "id": "meintool",
  "name": "Mein Werkzeug",
  "name_en": "My Tool",
  "description": "Kurze Beschreibung",
  "description_en": "Short description",
  "category": "system",
  "check_command": "meintool",
  "prefer": ["flatpak"],
  "sources": {
    "apt":     { "packages": ["meintool", "meintool-doc"] },
    "pacman":  { "packages": ["meintool"] },
    "flatpak": { "ref": "org.beispiel.MeinTool" },
    "deb":     { "url": "https://…/meintool.deb", "packages": ["meintool"] }
  },
  "pre_install":  "echo Vorbereitung",
  "post_install": "systemctl enable --now meintool.service"
}
```

Ein Fremd-Repository für APT:

```json
"apt": {
  "packages": ["code"],
  "repo": {
    "id": "vscode",
    "key_url": "https://packages.microsoft.com/keys/microsoft.asc",
    "keyring": "/usr/share/keyrings/silentinstaller-microsoft.gpg",
    "line": "deb [arch=amd64 signed-by=/usr/share/keyrings/silentinstaller-microsoft.gpg] https://packages.microsoft.com/repos/code stable main"
  },
  "components": ["contrib", "non-free"]
}
```

`components` schaltet Paketbereiche in den offiziellen Debian-Quellen frei –
nötig etwa für unfreie Firmware oder VirtualBox.

## Sicherheitshinweise

- Alles, was Root-Rechte braucht, steht in einem Skript, das du vor dem Start
  ansehen kannst. Nichts läuft unbemerkt im Hintergrund.
- Fremd-Repositorys werden mit `signed-by` und eigenem Keyring eingebunden, nie
  über den veralteten globalen Schlüsselbund.
- `.deb`-Downloads und Fremdquellen kommen von den Herstellern. Wer das nicht
  möchte, bleibt bei den Einträgen mit `apt`-, `pacman`- oder `flatpak`-Quelle.

## Mitgelieferter Katalog

84 Einträge in elf Kategorien, jeweils mit deutscher und englischer
Beschreibung: Internet, Kommunikation, Büro & Dokumente, Multimedia,
Grafik & Foto, Entwicklung, System & Werkzeuge, Sicherheit & Backup, Spiele,
**Schriften** und Grundausstattung (Codecs, Archivformate, Firmware).

Die Kategorie **Schriften** deckt dreizehn Bündel ab – von Noto für alle
Schriftsysteme über farbige Emoji bis zu Programmierschriften mit Ligaturen.
Sie lassen sich genauso installieren wie entfernen.

## Lizenz

MIT – siehe [LICENSE](LICENSE).
