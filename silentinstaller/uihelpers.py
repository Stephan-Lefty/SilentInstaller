"""Kleine Helfer für die Oberfläche."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, GLib, Gtk  # noqa: E402

from .i18n import _  # noqa: E402


def anzeige_pfad(pfad) -> str:
    """Ersetzt das Benutzerverzeichnis durch einen neutralen Platzhalter.

    Aus ``/home/anna/.config/…`` wird ``/home/USER/.config/…``. So lässt sich
    ein Fenster zeigen, abfotografieren oder in eine Anleitung übernehmen, ohne
    den eigenen Benutzernamen mit zu veröffentlichen. Gespeichert und geladen
    wird selbstverständlich weiterhin am echten Ort.
    """
    text = str(pfad)
    heim = str(Path.home())
    if text != heim and not text.startswith(heim + os.sep):
        return text

    eltern = Path(heim).parent
    if eltern == Path(os.sep):
        # Liegt das Benutzerverzeichnis direkt unter der Wurzel – etwa /root –,
        # ergäbe »/USER« ein falsches Bild. Dann ist die Tilde ehrlicher.
        return "~" + text[len(heim):]
    return str(eltern / "USER") + text[len(heim):]


def esc(text: str) -> str:
    """Macht Text für Pango-Markup sicher.

    Titel und Untertitel in libadwaita werden als Markup gelesen. Ein »&« in
    einem Kategorie- oder Programmnamen – etwa »Grafik & Foto« – lässt das
    Label sonst leer.
    """
    return GLib.markup_escape_text(text or "")


# -- Eigenes Aussehen ------------------------------------------------------

#: Dieselben Blautöne wie im Anwendungssymbol.
BLAU_HELL = "#1eadf4"
BLAU_DUNKEL = "#0072b5"

CSS = f"""
.si-info {{
  background-image: linear-gradient(135deg, {BLAU_HELL}, {BLAU_DUNKEL});
  background-color: {BLAU_DUNKEL};
  color: #ffffff;
  border: none;
  border-radius: 9999px;
  min-width: 22px;
  min-height: 22px;
  padding: 0;
  -gtk-icon-size: 14px;
  margin: 0 4px;
  box-shadow: none;
}}

.si-info:hover {{
  background-image: linear-gradient(135deg, {BLAU_DUNKEL}, {BLAU_DUNKEL});
}}
"""


def install_css() -> None:
    """Meldet das eigene Stylesheet einmalig beim Bildschirm an."""
    display = Gdk.Display.get_default()
    if display is None:
        return
    provider = Gtk.CssProvider()
    try:
        provider.load_from_data(CSS, -1)
    except TypeError:
        # Ältere PyGObject-Fassungen erwarten Bytes ohne Längenangabe.
        provider.load_from_data(CSS.encode("utf-8"))
    Gtk.StyleContext.add_provider_for_display(
        display, provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
    )


def info_button(tooltip: str = "") -> Gtk.Button:
    """Rundes »i« in den Farben des Anwendungssymbols."""
    button = Gtk.Button(
        icon_name="silentinstaller-info-symbolic",
        valign=Gtk.Align.CENTER,
        halign=Gtk.Align.CENTER,
        has_frame=False,
    )
    button.add_css_class("si-info")
    if tooltip:
        button.set_tooltip_text(tooltip)
    return button


# -- Hell und Dunkel -------------------------------------------------------

THEMES = ("auto", "light", "dark")


def apply_theme(name: str) -> None:
    """Stellt das Farbschema ein. ``auto`` folgt der Vorgabe des Desktops."""
    scheme = {
        "light": Adw.ColorScheme.FORCE_LIGHT,
        "dark": Adw.ColorScheme.FORCE_DARK,
    }.get(name, Adw.ColorScheme.DEFAULT)
    Adw.StyleManager.get_default().set_color_scheme(scheme)


# -- Dateiauswahl ----------------------------------------------------------


def _json_filters() -> Gio.ListStore:
    store = Gio.ListStore.new(Gtk.FileFilter)
    json_filter = Gtk.FileFilter()
    json_filter.set_name(_("SilentInstaller-Auswahl"))
    json_filter.add_pattern("*.json")
    store.append(json_filter)
    return store


def choose_file(
    parent: Gtk.Window,
    save: bool,
    title: str,
    on_chosen: Callable[[Path], None],
    initial_name: str = "",
) -> None:
    """Öffnet einen Datei-Dialog zum Sichern oder Laden.

    GTK 4.10 hat ``Gtk.FileDialog`` eingeführt; auf älteren Fassungen – etwa
    unter Ubuntu 22.04 – gibt es nur ``Gtk.FileChooserNative``. Beide Wege sind
    hier abgedeckt, damit das Programm nicht an der GTK-Version scheitert.
    """
    if hasattr(Gtk, "FileDialog"):
        dialog = Gtk.FileDialog(title=title, modal=True)
        dialog.set_filters(_json_filters())
        if initial_name:
            dialog.set_initial_name(initial_name)

        def finished(source, result) -> None:
            try:
                gfile = source.save_finish(result) if save else source.open_finish(result)
            except GLib.Error:
                return  # Vom Benutzer abgebrochen – kein Fehlerfall.
            if gfile is not None and (path := gfile.get_path()):
                on_chosen(Path(path))

        if save:
            dialog.save(parent, None, finished)
        else:
            dialog.open(parent, None, finished)
        return

    action = Gtk.FileChooserAction.SAVE if save else Gtk.FileChooserAction.OPEN
    chooser = Gtk.FileChooserNative.new(title, parent, action, None, None)
    chooser.set_modal(True)
    chooser.set_filter(_json_filters().get_item(0))
    if initial_name:
        chooser.set_current_name(initial_name)

    def responded(source, response: int) -> None:
        if response == Gtk.ResponseType.ACCEPT:
            gfile = source.get_file()
            if gfile is not None and (path := gfile.get_path()):
                on_chosen(Path(path))
        source.destroy()

    chooser.connect("response", responded)
    # Ohne eigene Referenz räumt Python den Dialog weg, bevor er antwortet.
    chooser._am_leben = chooser  # type: ignore[attr-defined]
    chooser.show()
