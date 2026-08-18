# TODO – SilentInstaller

Offene Punkte und Ideen. Erledigtes wandert ins [Änderungsprotokoll](CHANGELOG.md).

## Als Nächstes

- [ ] **Auf echtem Debian 13 testen.** Bisher nur auf Manjaro (Arch) gelaufen.
      Besonders prüfen: `si_enable_components` gegen die deb822-Quellen unter
      `/etc/apt/sources.list.d/debian.sources`, Fremdquellen für VS Code,
      Signal, Brave und Vivaldi sowie der `.deb`-Weg für Google Chrome.
- [ ] **Screenshot fürs README.** Der Versuch über XWayland ist gescheitert;
      auf einem X11-Rechner oder mit Spectacle von Hand nachholen.

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
