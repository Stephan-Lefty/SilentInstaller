# Blockierte Paketverwaltung wieder in Ordnung bringen

Diese Anleitung ist für Sie, wenn `apt` seit einem Durchlauf von SilentInstaller
diese Meldung bringt:

```
Fehler: Widersprüchliche Werte gesetzt für Option Signed-By betreffend die
Quelle https://brave-browser-apt-release.s3.brave.com/ stable:
/usr/share/keyrings/brave-browser-archive-keyring.gpg !=
/usr/share/keyrings/silentinstaller-brave.gpg
Fehler: Die Liste der Quellen konnte nicht gelesen werden.
```

## Was passiert ist

Ihr System hatte Brave bereits eingerichtet. SilentInstaller hat in einer
älteren Fassung nicht nachgesehen und die Paketquelle ein zweites Mal
eingetragen – mit einem anderen Signaturschlüssel. Zwei Einträge derselben
Quelle mit verschiedenen Schlüsseln lehnt `apt` grundsätzlich ab, und zwar
für **alle** Vorgänge, nicht nur für den auslösenden.

Deshalb geht im Moment gar nichts mehr: kein Installieren, kein
Aktualisieren – auch nicht die Fassung, die den Fehler behebt.

**Ihre Programme sind davon nicht betroffen.** Brave und alles andere bleibt
installiert und läuft weiter. Es ist nur die Liste der Paketquellen, die
geradegerückt werden muss.

## Schritt 1 – Nachsehen, was da ist

Öffnen Sie ein Terminal und geben Sie ein:

```
grep -rl brave /etc/apt/sources.list.d/
```

Es werden zwei Dateien angezeigt, zum Beispiel:

```
/etc/apt/sources.list.d/brave-browser-release.list
/etc/apt/sources.list.d/brave-browser.list
```

Die zweite stammt von SilentInstaller, die erste von Ihrem System. Welche
welche ist, klärt der nächste Befehl:

```
grep -rl silentinstaller- /etc/apt/sources.list.d/
```

Was hier erscheint, hat SilentInstaller angelegt – und nur das wird entfernt.

## Schritt 2 – Aufräumen

```
sudo rm $(grep -rl silentinstaller- /etc/apt/sources.list.d/)
```

Sie werden nach Ihrem Passwort gefragt. Der Befehl entfernt ausschließlich die
Dateien, die SilentInstaller angelegt hat. Die Paketquelle Ihres Systems bleibt
unangetastet.

## Schritt 3 – Prüfen, ob es wieder geht

```
sudo apt update
```

Jetzt sollte die Liste ohne die Fehlermeldung durchlaufen. Sehen Sie am Ende
etwas wie „Alle Pakete sind aktuell", ist alles in Ordnung.

Zur Sicherheit noch einmal:

```
grep -rl brave /etc/apt/sources.list.d/
```

Es darf nur noch **eine** Datei erscheinen.

## Schritt 4 – SilentInstaller aktualisieren

Erst jetzt lässt sich die neue Fassung installieren – vorher hätte `apt` ja
abgelehnt:

```
wget https://github.com/Stephan-Lefty/SilentInstaller/releases/download/v1.4.2/silentinstaller_1.4.2_all.deb
sudo apt install ./silentinstaller_1.4.2_all.deb
```

Prüfen, ob es geklappt hat:

```
dpkg-query -W -f='${Version}\n' silentinstaller
```

Es muss `1.4.2` erscheinen.

## Schritt 5 – Ausprobieren

Starten Sie SilentInstaller und wählen Sie ein Programm aus. Wenn Sie auf
**Installieren** klicken, kommt die Passwortabfrage, und danach sehen Sie ein
Fenster mit dem Fortschritt und den einzelnen Arbeitsschritten.

Kreuzen Sie testweise Brave an, sollte im Protokoll diese Zeile auftauchen:

```
Paketquelle https://brave-browser-apt-release.s3.brave.com/ ist bereits
eingerichtet – wird nicht doppelt angelegt
```

Das ist der Beweis, dass der Fehler nicht wiederkommt.

## Falls doch etwas klemmt

Sollte `apt` nach Schritt 2 immer noch meckern, sehen Sie sich alle Quellen an:

```
ls -la /etc/apt/sources.list.d/
```

Und schauen Sie in die genannten Dateien hinein:

```
cat /etc/apt/sources.list.d/brave-browser-release.list
```

Falls Sie unsicher sind, schicken Sie einfach die Ausgaben dieser beiden
Befehle – daraus lässt sich erkennen, was noch im Weg steht.

## Was sich geändert hat

Ab Fassung **1.4.1** sieht SilentInstaller vor dem Anlegen einer Paketquelle
nach, ob sie schon vorhanden ist, und lässt sie dann in Ruhe. Ein bereits
entstandener Widerspruch löst sich beim nächsten Durchlauf von selbst auf.

Fassung **1.4.2** behebt zusätzlich, dass die Fortschrittsanzeige während der
Installation nicht zu sehen war – nach der Passwortabfrage erschien nur die
Kategorienliste.
