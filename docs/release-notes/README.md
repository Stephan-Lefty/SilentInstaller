# Anmerkungen zu den Fassungen

Der Text, der jeweils auf der Release-Seite steht – hier mitversioniert, damit
er auch ohne Netzzugang und unabhängig von GitHub nachlesbar ist.

Eine knappe Übersicht aller Änderungen steht im
[Änderungsprotokoll](../../CHANGELOG.md). Die Dateien hier sind ausführlicher
und richten sich an Leute, die eine bestimmte Fassung installieren.

| Fassung | Kern |
| --- | --- |
| [1.4.2](v1.4.2.md) | Fortschritt war während der Installation unsichtbar |
| [1.4.1](v1.4.1.md) | Doppelte Paketquelle machte apt unbrauchbar |
| [1.4.0](v1.4.0.md) | Snap als fünfte Quellenart, Paketnamen je Distribution |
| [1.3.1](v1.3.1.md) | Terminal-Befehl über den Verweis repariert |
| [1.3.0](v1.3.0.md) | Hinweis auf neue Fassungen |
| [1.2.1](v1.2.1.md) | Menüeintrag unter KDE, Bildschirmfotos |
| [1.2.0](v1.2.0.md) | Debian-Paket, Logo, Profile als Dateien, Schriften |

Neue Anmerkungen kommen beim Veröffentlichen dazu:

```bash
gh release create vX.Y.Z \
  dist/silentinstaller_X.Y.Z_all.deb \
  dist/silentinstaller_X.Y.Z_all.deb.sha256 \
  --title "SilentInstaller X.Y.Z" \
  --notes-file docs/release-notes/vX.Y.Z.md
```
