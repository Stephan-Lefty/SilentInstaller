# Änderungsprotokoll

Alle nennenswerten Änderungen an SilentInstaller. Das Format folgt
[Keep a Changelog](https://keepachangelog.com/de/1.1.0/), die Versionierung
[Semantic Versioning](https://semver.org/lang/de/).

## [1.2.1] – 2026-08-18

### Behoben

- **`install.sh` stieß Plasmas Menü-Datenbank nie an.** Unter KDE erschien der
  Menüeintrag deshalb erst nach einer Neuanmeldung. Der Installer ruft jetzt
  `kbuildsycoca6` beziehungsweise `kbuildsycoca5` auf, dazu
  `xdg-desktop-menu forceupdate` für XFCE und LXQt. Das Debian-Paket braucht
  das nicht: Es installiert systemweit, und dort liest KDE neue Einträge selbst
  ein – ein Aufruf als root ginge ohnehin an der Sitzung des Benutzers vorbei.
- **`install.sh` meldete auch dann Erfolg, wenn nichts ankam.** Am Ende wird
  jetzt geprüft, ob Menüeintrag und Symbol wirklich liegen, und unter KDE, ob
  das Symbol über seinen Namen auffindbar ist. Fehlt etwas, sagt das Skript es.
- Das Einstellungsfenster trug den englischen Titel „Preferences“, auch bei
  deutscher Oberfläche – `Adw.PreferencesWindow` bekam keinen eigenen Titel.
- Lag das Benutzerverzeichnis unmittelbar unter der Wurzel, etwa `/root`,
  entstand aus dem Platzhalter für den Benutzernamen der unsinnige Pfad
  `/USER/…`. In diesem Fall wird jetzt die Tilde verwendet.

### Neu

- **Bildschirmfotos im README.** Zehn Aufnahmen unter `docs/screenshots/`,
  entstanden in einem Debian-13-Container unter Xvfb.
- **Auf Debian 13 geprüft.** Paketinstallation, das Freischalten der
  `contrib`-, `non-free`- und `non-free-firmware`-Bereiche in den
  deb822-Quellen, alle vier Fremdquellen mit eigenem Signaturschlüssel sowie
  eine Probeinstallation aus einer Fremdquelle laufen durch. Die Oberfläche
  startet unter Debian 13 und findet für alle 84 Einträge eine Quelle.

## [1.2.0] – 2026-08-18

### Neu

- **Debian-Paket.** `./build-deb.sh` baut ein installierbares
  `silentinstaller_<version>_all.deb` mit Menüeintrag, Symbolen im
  hicolor-Thema und allen Abhängigkeiten. Das Skript läuft auch auf einem
  Arch-System, solange `dpkg-deb` vorhanden ist.
- **Benutzername in angezeigten Pfaden ersetzt.** Wo die Oberfläche einen Pfad
  im eigenen Verzeichnis nennt, steht jetzt `/home/USER/…` statt des echten
  Namens. So lässt sich ein Fenster zeigen oder abfotografieren, ohne ihn
  mitzuveröffentlichen. Gespeichert und geladen wird weiterhin am echten Ort.
- **Infofenster zu Profilen und Auswahldateien.** Neben beiden Überschriften im
  Hauptmenü sitzt ein rundes »i« in den Blautönen des Anwendungssymbols. Ein
  Klick öffnet ein Fenster, das den Unterschied in Ruhe erklärt: was auf dem
  Rechner bleibt, was mitgeht, wo es liegt – und dass beides dasselbe
  Dateiformat ist. Das »i« ist ein eigenes Icon: `dialog-information-symbolic`
  ist unter Adwaita eine Glühbirne und je nach Systemthema etwas anderes.
- **Erklärungen im Hauptmenü.** Jeder Eintrag zeigt beim Darüberfahren einen
  Hinweis, was er tut. Zwei Überschriften trennen außerdem, was auf dem Rechner
  bleibt („Auf diesem Rechner“ – Profile) von dem, was mitgeht („Auf einen
  anderen Rechner mitnehmen“ – Auswahl als Datei). Dafür ist das Menü von einem
  Menümodell auf ein eigenes Popover umgestellt: `Gio.MenuItem` kennt kein
  Feld für Hinweistexte.
- **Profile liegen jetzt als einzelne Dateien** unter
  `~/.config/silentinstaller/profile/`, eine Datei je Profil. Damit lässt sich
  ein einzelnes Profil kopieren, sichern oder in eine Ablage legen, ohne die
  Einstellungen mitzuschleppen. Eine Profildatei hat dasselbe Format wie eine
  ausgelagerte Auswahl – wer eine exportierte Datei in dieses Verzeichnis legt,
  findet sie beim nächsten Start als Profil wieder. Vorhandene Profile aus der
  Einstellungsdatei werden beim ersten Start automatisch überführt.
- **Erstprofil beim ersten Start.** SilentInstaller legt einmalig ein Profil
  „Dieses System (Datum)“ an, das alle bereits vorhandenen Programme aus dem
  Katalog enthält. Damit ist der gewachsene Bestand eines eingerichteten
  Rechners festgehalten, bevor irgendetwas verändert wird – über „Profil laden“
  und „Auswahl in Datei sichern“ lässt er sich auf den nächsten Rechner
  übertragen, gleich welcher Systemfamilie.
- **Eigenes Logo.** Weißes Motiv – ein in drei Stufen zerlegter Pfeil, der auf
  eine Festplatte zuläuft – auf blauem Verlauf aus `#1eadf4` und `#0072b5`,
  abgedunkelt mit `#3c2a42`. Die Aussparungen im Laufwerk entstehen über
  `fill-rule="evenodd"`, sodass der Verlauf hindurchscheint, statt mit einer
  festen Farbe nachgebildet zu werden. Als skalierbares SVG und in acht PNG-Größen von 16 bis 512 Pixeln
  unter `data/icons/hicolor/`. Dazu zwei Wortmarken: `data/logo.svg` für dunkle,
  `data/logo-hell.svg` für helle Untergründe. Der Schriftzug steht in einer
  Arial-metrischen Schrift (Liberation Sans / Arial / Helvetica), damit die
  Wortmarke auf Linux, Windows und macOS gleich aussieht. In den READMEs ist
  bewusst die gerenderte PNG-Fassung eingebunden: Bei einem SVG mit echtem Text
  entscheidet der Browser des Betrachters über die Schrift.
- Das Symbol erscheint im Anwendungsmenü, in der Fensterleiste und im
  Über-Dialog. Wird SilentInstaller direkt aus dem entpackten Verzeichnis
  gestartet, meldet es seinen Symbolordner selbst beim Icon-Theme an – eine
  Installation ist dafür nicht nötig.
- **Kategorie „Schriften“** mit dreizehn Einträgen: Noto für alle Schriftsysteme,
  Noto CJK, farbige Emoji, DejaVu, GNU FreeFont, Linux Libertine, moderne
  Oberflächenschriften (Inter, Roboto, Open Sans, Lato), die Ubuntu-Familie,
  Programmierschriften mit Ligaturen (Fira Code, JetBrains Mono, Cascadia, Hack,
  Inconsolata, Anonymous Pro, Source Code Pro), Terminus fürs Terminal und
  Symbolschriften für die Eingabeaufforderung. Alle Paketnamen wurden gegen die
  offiziellen Quellen von Debian 13 und Arch geprüft.
- Schriften lassen sich wie jedes andere Programm auch wieder **entfernen** –
  dafür war keine Sonderbehandlung nötig, der vorhandene Weg trägt sie mit.
- Der Eintrag „Schriften für Office-Dokumente“ ist von der Grundausstattung in
  die neue Kategorie umgezogen.

## [1.1.0] – 2026-08-18

### Neu

- **Zweisprachig, Deutsch und Englisch.** Die Sprache wird aus `LANGUAGE`,
  `LC_ALL`, `LC_MESSAGES` und `LANG` erkannt: Ein deutsches System bekommt eine
  deutsche Oberfläche, jedes andere eine englische. In den Einstellungen lässt
  sich die Sprache fest wählen; der Wechsel greift sofort, ohne Neustart.
  Übersetzt sind auch die Kategorie- und Programmbeschreibungen im Katalog
  sowie die Meldungen des Starters.
- **Hell und dunkel.** Erscheinungsbild in den Einstellungen umschaltbar:
  „Wie das System“, „Hell“ oder „Dunkel“.
- **Auswahl als eigenständige Datei sichern und laden.** Über das Menü oder
  `Strg+S` / `Strg+O`. Die Datei enthält neben den Kennungen auch die
  vollständige Definition aller selbst angelegten Programme – dadurch lässt sie
  sich auf einem frischen Rechner einlesen, der diese Einträge noch nie gesehen
  hat. Da alle Paketnamen erhalten bleiben, funktioniert dieselbe Datei auf
  Debian- **und** Arch-Systemen.
- Meldungen erscheinen jetzt als Einblendung (Toast) statt in der Statuszeile.

### Geändert

- **Schriften: Microsoft-Original ersetzt durch freien Ersatz.** Der Eintrag
  `ttf-mscorefonts-installer` ist entfallen – er lief nur auf Debian, brauchte
  contrib, eine EULA-Zusage per debconf und lud die Schriften beim Installieren
  erst von SourceForge nach. An seine Stelle tritt „Schriften für
  Office-Dokumente“ mit Liberation, Carlito und Caladea: metrisch identisch zu
  Arial, Times New Roman, Calibri und Cambria – Zeilen- und Seitenumbrüche
  bleiben also gleich –, dafür auf Debian **und** Arch in den offiziellen
  Paketquellen.
- Der Programmeditor schreibt Änderungen in das Feld der gerade aktiven Sprache,
  statt die andere Fassung zu überschreiben.
- Der Starter `silentinstaller.sh` meldet sich in der Systemsprache.

### Behoben

- Beim Bearbeiten eines mitgelieferten Eintrags gingen `homepage` und
  `pre_install` verloren, weil der Editor keine Felder dafür hat.

## [1.0.0] – 2026-08-18

### Neu

- Erste Fassung: GTK4-/libadwaita-Oberfläche zum Nachinstallieren von
  Lieblingsprogrammen nach einer Grundinstallation.
- Unterstützung für Debian- und Arch-basierte Systeme mit automatischer
  Erkennung über `/etc/os-release`.
- Vier Quellenarten: `apt`, `pacman`, `flatpak` (Flathub) und `deb` samt
  Fremd-Repositorys mit eigenem Keyring (`signed-by`).
- Mitgelieferter Katalog mit 72 Programmen in zehn Kategorien.
- Katalog-Editor in der Oberfläche: Programme hinzufügen, bearbeiten und wieder
  herausnehmen. Eigene Einträge liegen in
  `~/.config/silentinstaller/catalog.json`, die Mitlieferung bleibt unverändert.
- Profile: Auswahl unter einem Namen speichern und später wieder laden.
- Erkennung bereits installierter Programme über `dpkg-query`, `pacman -Qq`,
  `flatpak list` und optionale Prüfbefehle.
- Vorschau des erzeugten Shell-Skripts vor dem Start.
- Gebündelte Installation mit Einzelfallback: Scheitert die Sammelinstallation,
  werden die Pakete einzeln nachgereicht.
- Entfernen ausgewählter Programme, wahlweise samt Konfiguration
  (`apt purge` bzw. `pacman -Rns`).
- Fortschrittsanzeige mit vollständiger Ausgabe und schonendem Abbruch nach
  dem laufenden Schritt.
- Starter `silentinstaller.sh`, der fehlende GTK4-Abhängigkeiten nachrüstet,
  sowie `install.sh` für den Menüeintrag.

[1.2.1]: https://github.com/Stephan-Lefty/SilentInstaller/releases/tag/v1.2.1
[1.2.0]: https://github.com/Stephan-Lefty/SilentInstaller/releases/tag/v1.2.0
[1.1.0]: https://github.com/Stephan-Lefty/SilentInstaller/releases/tag/v1.1.0
[1.0.0]: https://github.com/Stephan-Lefty/SilentInstaller/releases/tag/v1.0.0
