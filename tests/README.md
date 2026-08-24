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

## Was diese Tests *nicht* leisten

Sie prüfen Logik, nicht das Zusammenspiel mit einem echten System. Nicht
abgedeckt sind:

- ob ein Paketname in der jeweiligen Distribution tatsächlich existiert
  (dafür braucht es Container mit Debian, Ubuntu und Arch)
- die Passwortabfrage über polkit
- das Aussehen der Oberfläche

Diese drei Lücken haben in der Vergangenheit Fehler durchgelassen. Der
Paketbau-Auftrag in `.github/workflows/tests.yml` deckt inzwischen einen Teil
davon ab: Er installiert das gebaute Paket wirklich und startet es unter Xvfb.
