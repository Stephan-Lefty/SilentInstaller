# TODO – SilentInstaller

Offene Punkte und Ideen. Erledigtes wandert ins [Änderungsprotokoll](CHANGELOG.md).

## Als Nächstes

- [x] ~~**Auf echtem Debian 13 testen.**~~ Am 18.08.2026 in einem
      Debian-13-Container geprüft: Paketinstallation samt Abhängigkeiten,
      Freischalten von `contrib`, `non-free` und `non-free-firmware` in den
      deb822-Quellen, alle vier Fremdquellen mit Signaturschlüssel,
      `apt-get update` und eine Probeinstallation von Visual Studio Code –
      alle Schritte mit Rückgabe 0. Die Oberfläche startet unter Debian 13,
      erkennt das System und findet für alle 84 Einträge eine Quelle.
      **Offen bleibt:** ein Durchlauf auf einem echten Debian-Desktop mit
      polkit-Passwortabfrage; im Container läuft das Skript als root.
- [x] ~~**Screenshot fürs README.**~~ Zehn Aufnahmen unter `docs/screenshots/`,
      erzeugt in einem Debian-13-Container unter Xvfb. Neu erzeugen lassen sie
      sich mit dem Skript im Anhang des Änderungsprotokolls; unter Wayland
      liefert ein Bildschirmfoto des GTK4-Fensters keine brauchbare Datei.

## Ideen

- [ ] **AUR-Unterstützung** über `yay`/`paru`, falls vorhanden – bewusst
      zurückgestellt, weil auf Debian wirkungslos.
- [ ] **Weitere Sprachen.** Die Tabelle in `silentinstaller/i18n.py` ist auf
      Deutsch und Englisch ausgelegt, nimmt aber ohne Umbau weitere Sprachen
      auf: einen Schlüssel in `TRANSLATIONS` ergänzen und in `SUPPORTED`
      eintragen.
- [ ] **Auswahldatei mit Systemangabe.** Beim Import könnte angezeigt werden,
      auf welchem System die Datei entstanden ist und welche Einträge dort eine
      andere Quelle hatten.
- [ ] **Snap** als fünfte Quellenart für Ubuntu-Nutzer.
- [ ] **TUI-Modus** mit `whiptail` für Rechner ohne Desktop.
- [ ] **Katalog-Aktualisierung** aus dem Netz nachladen, statt nur mit dem
      Programm mitzuliefern.
- [ ] **Nach der Installation aufräumen:** `apt-get autoremove`, `pacman -Sc`
      und `flatpak uninstall --unused` als abschließender Schritt anbieten.
- [ ] **`pre_install` im Editor.** Steht bisher nur im JSON zur Verfügung; im
      Formular gibt es nur das Feld für Nacharbeiten.

## Bekannte Grenzen

- Programme, die nur auf einer der beiden Systemfamilien existieren – etwa
  Synaptic oder Déjà Dup –, werden beim Einlesen einer Auswahldatei auf dem
  anderen System übersprungen und beim Laden gemeldet.
- Das Katalogfeld `pre_install` hat derzeit keinen Nutzer mehr. Es bleibt als
  Ausweg für eigene Einträge erhalten, die vor der Installation etwas erledigen
  müssen – etwa `dpkg --add-architecture i386`.
- Abbrechen wirkt erst nach dem laufenden Schritt. Eine laufende
  Paketinstallation wird bewusst nicht abgeschossen.
- Flatpaks werden systemweit installiert (`--system`), nicht pro Benutzer.
- Ohne polkit (`pkexec`) startet nur der Weg über ein bereits gültiges
  `sudo`-Ticket.
- `firmware-linux` und die unfreien Firmware-Pakete gibt es nur unter Debian;
  Ubuntu bringt sie anders mit.
