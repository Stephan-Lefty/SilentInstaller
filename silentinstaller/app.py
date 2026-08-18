"""Einstiegspunkt der Anwendung."""

from __future__ import annotations

import sys
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, Gtk  # noqa: E402

from . import APP_ID, distro as distro_module  # noqa: E402
from .catalog import load_settings  # noqa: E402
from .i18n import set_language  # noqa: E402
from .uihelpers import apply_theme, install_css  # noqa: E402
from .window import MainWindow  # noqa: E402


class SilentInstallerApp(Adw.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id=APP_ID, flags=Gio.ApplicationFlags.DEFAULT_FLAGS
        )
        self._window: MainWindow | None = None

    def do_startup(self) -> None:
        Adw.Application.do_startup(self)

        settings = load_settings()
        set_language(settings.get("language", "auto"))
        apply_theme(settings.get("theme", "auto"))
        self._register_icons()
        install_css()

        self.set_accels_for_action("win.add-app", ["<Control>n"])
        self.set_accels_for_action("win.refresh", ["<Control>r"])
        self.set_accels_for_action("win.show-script", ["<Control>d"])
        self.set_accels_for_action("win.export-selection", ["<Control>s"])
        self.set_accels_for_action("win.import-selection", ["<Control>o"])
        self.set_accels_for_action("app.quit", ["<Control>q"])

        quit_action = Gio.SimpleAction.new("quit", None)
        quit_action.connect("activate", lambda *_a: self.quit())
        self.add_action(quit_action)

    @staticmethod
    def _register_icons() -> None:
        """Macht das mitgelieferte Anwendungssymbol auffindbar.

        Wer SilentInstaller direkt aus dem entpackten Verzeichnis startet, hat
        das Symbol nicht im Icon-Theme des Systems. Der zusätzliche Suchpfad
        sorgt dafür, dass es trotzdem im Fenster und im Über-Dialog erscheint.
        """
        icons = Path(__file__).resolve().parent.parent / "data" / "icons"
        display = Gdk.Display.get_default()
        if icons.is_dir() and display is not None:
            Gtk.IconTheme.get_for_display(display).add_search_path(str(icons))

    def do_activate(self) -> None:
        if self._window is None:
            self._window = MainWindow(self, distro_module.detect())
        self._window.present()

    def replace_window(self, window: MainWindow) -> None:
        """Übernimmt ein neu aufgebautes Fenster – etwa nach einem Sprachwechsel."""
        self._window = window


def main(argv: list[str] | None = None) -> int:
    system = distro_module.detect()
    if system.family == distro_module.FAMILY_UNKNOWN:
        print(
            "Warnung: Weder APT noch Pacman gefunden – SilentInstaller kann auf "
            "diesem System nichts installieren.\n"
            "Warning: neither APT nor Pacman found — SilentInstaller cannot "
            "install anything on this system.",
            file=sys.stderr,
        )
    return SilentInstallerApp().run(argv if argv is not None else sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
