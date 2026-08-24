# Tests

Ausführen:

```bash
python3 -m unittest discover -s tests        # kurz
python3 -m unittest discover -s tests -v     # mit Namen jedes Falls
```

Es braucht nichts außer Python und `bash` – bewusst kein `pytest`, damit die
Prüfungen auch auf einem frisch aufgesetzten Rechner sofort laufen.

## Was geprüft wird

| Datei | Inhalt |
| --- | --- |
| `test_katalog.py` | Aufbau des mitgelieferten Katalogs: doppelte Kennungen, unbekannte Kategorien, leere Quellen, unvollständige Fremdquellen, fehlende englische Fassungen |
| `test_aufloesung.py` | Welche Quelle auf welchem System gewählt wird – Debian, Ubuntu, Mint, Arch. Enthält den Nachweis, dass unter Ubuntu kein Paket genommen wird, das dort heimlich einen Snap nachzieht |
| `test_skript.py` | Die erzeugten Shell-Skripte: Syntax über `bash -n`, Reihenfolge der Schritte, Schutz vor durchschlagenden Paketnamen, Schutz vor doppelten Paketquellen |
| `test_bausteine.py` | Fassungsvergleich, Spracherkennung, Vollständigkeit der Übersetzungen, Kennungen, Pfad-Platzhalter, Profile und Auswahldateien |

## Warum gerade diese Fälle

Fast jeder Test steht für einen Fehler, der einmal wirklich aufgetreten ist:

- `1.10.0` galt als älter als `1.9.0`, weil Fassungen als Text verglichen wurden
- der Pfad-Platzhalter machte aus `/root/…` das unsinnige `/USER/…`
- unter Ubuntu fehlten sieben Paketnamen, und `apt install thunderbird` schob
  stillschweigend einen Snap unter
- eine doppelt eingetragene Paketquelle legte `apt` vollständig lahm

Wer einen Fehler behebt, sollte hier einen Fall ergänzen. Dann bleibt er behoben.

## Was hier nicht geprüft wird – und wo dann

Diese Tests prüfen Logik, nicht das Zusammenspiel mit einem echten System.
Zwei weitere Arbeitsabläufe schließen die wichtigsten Lücken:

| Wo | Was |
| --- | --- |
| `.github/workflows/tests.yml` | Baut das Debian-Paket, installiert es wirklich, startet es unter Xvfb und prüft alle Aufrufwege |
| `.github/workflows/paketname.yml` | Schlägt jeden Paketnamen in Containern von Arch, Debian 13 und Ubuntu 24.04 nach und fragt Flathub nach jeder Kennung |

Der zweite Ablauf hat beim ersten Lauf fünf Einträge gefunden, die nicht mehr
funktionierten – darunter einen, dessen einzige Quelle von Flathub verschwunden
war.

Weiterhin ungeprüft bleibt die Passwortabfrage über polkit: In Containern läuft
alles als root, `pkexec` kommt nie zum Zug. Das lässt sich nur an einem echten
Arbeitsplatzrechner feststellen.
