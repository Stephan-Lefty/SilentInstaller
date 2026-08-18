<img src="data/logo.png" alt="SilentInstaller" width="420">

**[Deutsch](README.md) · [English](README.en.md) · [Changelog](CHANGELOG.md)**

After a fresh install of Debian 13, Ubuntu, Linux Mint, Arch, Manjaro or
EndeavourOS, the same twenty programs are always missing. SilentInstaller keeps
your favourites in a list, lets you tick them off in a GTK4 interface and
installs them in a single run — with exactly one password prompt.

The desktop does not matter: GNOME, KDE, XFCE, Cinnamon, Sway. The interface is
built on GTK 4 and libadwaita, so it runs everywhere — in English or German,
light or dark.

## What it does

- **One catalog, two worlds.** Every program knows its package names for APT
  *and* Pacman *and* Flathub. SilentInstaller picks the right source for the
  system it is running on.
- **Four kinds of sources.** Distribution packages (apt/pacman), Flatpak from
  Flathub, direct `.deb` downloads, and third-party repositories with signing
  keys (Visual Studio Code, Signal, Brave, Vivaldi).
- **Curate your own list.** Add, edit and remove entries right in the interface,
  no text editor needed. Your changes go to
  `~/.config/silentinstaller/catalog.json`; the bundled list stays untouched.
- **Take your selection with you.** Compose an "office PC" or "development
  machine" once and export it to a file. Load that file on the next computer and
  everything is ticked again — **whether that machine runs Debian or Arch**.
  Programs you added yourself travel along in full.
- **Profiles.** Named selections, one file each under
  `~/.config/silentinstaller/profile/`. On the very first start one is created
  automatically, holding every program already present on the machine — so what
  grew over the years is preserved.
- **English and German.** The language follows your system and can be pinned in
  the preferences. Switching takes effect immediately.
- **Light and dark.** Like the desktop — or fixed to your liking.
- **Look before you leap.** "Show script" reveals the complete shell run before
  anything happens.
- **Detects what is there.** Already installed programs are marked and skipped.
- **Removal too.** Selected programs can be uninstalled as well, optionally
  including their configuration.

## Installation

```bash
git clone https://github.com/Stephan-Lefty/SilentInstaller.git
cd SilentInstaller
./silentinstaller.sh
```

The launcher checks whether GTK 4 and libadwaita are available for Python and
offers to install the missing packages.

For a permanent menu entry:

```bash
./install.sh            # into ~/.local/share/silentinstaller
./install.sh uninstall  # remove again
```

### Requirements

| System            | Packages                                                        |
| ----------------- | --------------------------------------------------------------- |
| Debian, Ubuntu, … | `python3-gi python3-gi-cairo gir1.2-gtk-4.0 gir1.2-adw-1 pkexec` |
| Arch, Manjaro, …  | `python-gobject gtk4 libadwaita polkit`                          |

Python 3.10 or newer, GTK 4.6+, libadwaita 1.4+ and polkit for privilege
escalation.

## Usage

1. Pick a category on the left, or press `Ctrl+F` to search.
2. Tick the programs you want.
3. Click **Install** at the bottom, confirm, enter your password.
4. Progress and full output appear in the window.

Shortcuts: `Ctrl+N` new program, `Ctrl+F` search, `Ctrl+R` re-check what is
installed, `Ctrl+D` show script, `Ctrl+S` export selection, `Ctrl+O` import
selection, `Ctrl+Q` quit.

## Taking your selection to the next machine

This is what SilentInstaller is for: compose once, use everywhere.

1. Tick the programs you want.
2. Menu ▸ **Export selection to file …** — you get a `.json` file.
3. Carry that file to the new machine (USB stick, Nextcloud, a Git repository).
4. There, choose Menu ▸ **Import selection from file …** — everything is ticked
   again.
5. Press **Install**.

The file stores identifiers, not package names. That is why the same file works
on Debian and on Arch: one system installs `firefox-esr` via APT, the other
`firefox` via Pacman. Programs that do not exist on the target system — Arch has
no Synaptic, for instance — are skipped and reported on import.

Programs you added yourself are written to the file with their complete
definition. The new machine does not need to know them beforehand; it learns
them on import.

## Where things live

| What | Where |
| --- | --- |
| Profiles, one file each | `~/.config/silentinstaller/profile/` |
| Your own programs | `~/.config/silentinstaller/catalog.json` |
| Settings | `~/.config/silentinstaller/settings.json` |
| Exported selections | wherever you like |

A profile file and an exported selection use the same format. Copy a file you
created via "Export selection to file" into the profile directory and it shows
up under "Load profile" on the next start.

## Language and appearance

At startup SilentInstaller reads `LANGUAGE`, `LC_ALL`, `LC_MESSAGES` and `LANG`.
German means a German interface; anything else gets English. If you would rather
decide yourself, pin it under *Preferences ▸ Appearance* — which is also where
you switch between light, dark and "follow the system".

## How a run works

SilentInstaller turns your selection into a single shell script and runs it via
`pkexec`. Three reasons: one password prompt, batched package installation
instead of seventy separate calls — and you can read the script beforehand.

Steps run in a sensible order: third-party sources and package components
first, then `apt-get update`, then the installation. If a batch install fails,
packages are retried one by one so a single broken package does not sink the
whole run.

**Cancel** stops after the current step rather than killing a package operation
mid-flight, which would leave the package database half-finished.

## Adding your own programs

Easiest via **＋** in the header bar. If you prefer editing the file directly,
it lives at `~/.config/silentinstaller/catalog.json`:

```json
{
  "id": "mytool",
  "name": "Mein Werkzeug",
  "name_en": "My Tool",
  "description": "Kurze Beschreibung",
  "description_en": "Short description",
  "category": "system",
  "check_command": "mytool",
  "prefer": ["flatpak"],
  "sources": {
    "apt":     { "packages": ["mytool", "mytool-doc"] },
    "pacman":  { "packages": ["mytool"] },
    "flatpak": { "ref": "org.example.MyTool" },
    "deb":     { "url": "https://…/mytool.deb", "packages": ["mytool"] }
  },
  "pre_install":  "echo preparing",
  "post_install": "systemctl enable --now mytool.service"
}
```

A third-party APT repository:

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

`components` enables package components in the official Debian sources — needed
for non-free firmware or VirtualBox, for example.

## Security notes

- Everything requiring root lives in a script you can inspect before it starts.
  Nothing runs unseen.
- Third-party repositories are added with `signed-by` and their own keyring,
  never via the deprecated global keyring.
- `.deb` downloads and third-party sources come from the vendors. If you would
  rather avoid that, stick to entries with `apt`, `pacman` or `flatpak` sources.

## Bundled catalog

84 entries in eleven categories, each with a German and an English description:
internet, communication, office, multimedia, graphics, development, system
tools, security & backup, games, **fonts** and essentials (codecs, archive
formats, firmware).

The **fonts** category covers thirteen bundles — from Noto for every writing
system through colour emoji to coding fonts with ligatures. They install and
uninstall like anything else.

## License

MIT — see [LICENSE](LICENSE).
