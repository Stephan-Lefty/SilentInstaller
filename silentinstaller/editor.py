"""Dialog zum Anlegen und Bearbeiten eigener Programmeinträge."""

from __future__ import annotations

import re
from typing import Callable

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gtk  # noqa: E402

from .catalog import App, Catalog, Category, slugify  # noqa: E402
from .i18n import _, language  # noqa: E402
from .uihelpers import esc  # noqa: E402

#: Wert im Katalog -> Beschriftung. Übersetzt wird erst beim Aufbau des
#: Dialogs, weil die Sprache zum Zeitpunkt des Imports noch nicht feststeht.
PREFER_CHOICES = [
    ("", "Automatisch (nativ zuerst)"),
    ("apt", "APT bevorzugen"),
    ("pacman", "Pacman bevorzugen"),
    ("flatpak", "Flatpak bevorzugen"),
    ("deb", ".deb-Paket bevorzugen"),
]


def _split(value: str) -> list[str]:
    return [part for part in re.split(r"[\s,]+", value.strip()) if part]


class AppEditor(Adw.Window):
    """Formular für ein einzelnes Programm."""

    def __init__(
        self,
        parent: Gtk.Window,
        catalog: Catalog,
        app: App | None,
        on_save: Callable[[App, Category | None], None],
    ) -> None:
        super().__init__(
            transient_for=parent,
            modal=True,
            default_width=560,
            default_height=720,
            title=_("Programm bearbeiten") if app else _("Programm hinzufügen"),
        )
        self._catalog = catalog
        self._app = app
        self._on_save = on_save

        header = Adw.HeaderBar()
        cancel = Gtk.Button(label=_("Abbrechen"))
        cancel.connect("clicked", lambda *_a: self.close())
        header.pack_start(cancel)

        save_button = Gtk.Button(label=_("Speichern"))
        save_button.add_css_class("suggested-action")
        save_button.connect("clicked", self._on_save_clicked)
        header.pack_end(save_button)

        page = Adw.PreferencesPage(vexpand=True)
        page.add(self._build_general_group())
        page.add(self._build_sources_group())
        page.add(self._build_advanced_group())
        page.add(self._build_post_install_group())

        self._banner = Adw.Banner(revealed=False)

        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        body.append(self._banner)
        body.append(page)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.set_content(body)
        self.set_content(toolbar)

        self._fill(app)

    # -- Aufbau ------------------------------------------------------------

    def _build_general_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title=_("Allgemein"))

        self._name = Adw.EntryRow(title=_("Name"))
        self._name.connect("changed", self._on_name_changed)
        group.add(self._name)

        self._id = Adw.EntryRow(title=_("Kennung (eindeutig, klein geschrieben)"))
        group.add(self._id)

        self._description = Adw.EntryRow(title=_("Beschreibung"))
        group.add(self._description)

        self._categories = self._catalog.used_categories()
        names = [esc(c.display_name) for c in self._categories]
        names.append(_("Neue Kategorie …"))
        self._category = Adw.ComboRow(
            title=_("Kategorie"), model=Gtk.StringList.new(names)
        )
        self._category.connect("notify::selected", self._on_category_changed)
        group.add(self._category)

        self._new_category = Adw.EntryRow(
            title=_("Name der neuen Kategorie"), visible=False
        )
        group.add(self._new_category)
        return group

    def _build_sources_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(
            title=_("Installationsquellen"),
            description=_(
                "Mindestens eine Quelle ausfüllen. Mehrere Pakete durch "
                "Leerzeichen oder Komma trennen."
            ),
        )
        self._apt = Adw.EntryRow(title=esc(_("APT-Pakete (Debian & Co.)")))
        self._pacman = Adw.EntryRow(title=esc(_("Pacman-Pakete (Arch & Co.)")))
        self._flatpak = Adw.EntryRow(title=_("Flatpak-Kennung, z. B. org.gimp.GIMP"))
        self._deb = Adw.EntryRow(title=_(".deb-Download-Adresse"))
        for row in (self._apt, self._pacman, self._flatpak, self._deb):
            group.add(row)
        return group

    def _build_advanced_group(self) -> Adw.PreferencesGroup:
        group = Adw.PreferencesGroup(title=_("Feinheiten"))

        self._prefer = Adw.ComboRow(
            title=_("Bevorzugte Quelle"),
            model=Gtk.StringList.new([_(label) for _value, label in PREFER_CHOICES]),
        )
        group.add(self._prefer)

        self._icon = Adw.EntryRow(title=_("Symbolname (optional)"))
        group.add(self._icon)

        self._check = Adw.EntryRow(title=_("Prüfbefehl (optional, z. B. »code«)"))
        group.add(self._check)
        return group

    def _build_post_install_group(self) -> Adw.PreferencesGroup:
        self._post = Gtk.TextView(
            monospace=True, top_margin=8, bottom_margin=8, left_margin=8, right_margin=8
        )
        scroller = Gtk.ScrolledWindow(height_request=110, child=self._post)
        scroller.add_css_class("card")

        group = Adw.PreferencesGroup(
            title=_("Nacharbeiten"),
            description=_("Shell-Befehle, die nach der Installation als root laufen."),
        )
        group.add(scroller)
        return group

    # -- Befüllen und Auslesen --------------------------------------------

    def _fill(self, app: App | None) -> None:
        if app is None:
            self._category.set_selected(0)
            return
        self._name.set_text(app.display_name)
        self._id.set_text(app.id)
        self._description.set_text(app.display_description)
        self._icon.set_text(app.icon)
        self._check.set_text(app.check_command)

        for index, category in enumerate(self._categories):
            if category.id == app.category:
                self._category.set_selected(index)
                break

        self._apt.set_text(" ".join((app.sources.get("apt") or {}).get("packages", [])))
        self._pacman.set_text(
            " ".join((app.sources.get("pacman") or {}).get("packages", []))
        )
        self._flatpak.set_text((app.sources.get("flatpak") or {}).get("ref", ""))
        self._deb.set_text((app.sources.get("deb") or {}).get("url", ""))

        prefer = app.prefer[0] if app.prefer else ""
        for index, (value, _label) in enumerate(PREFER_CHOICES):
            if value == prefer:
                self._prefer.set_selected(index)
                break

        self._post.get_buffer().set_text(app.post_install)

    def _on_name_changed(self, entry: Adw.EntryRow) -> None:
        if self._app is None and not self._id.get_text().strip():
            self._id.set_text(slugify(entry.get_text()))

    def _on_category_changed(self, combo: Adw.ComboRow, _param) -> None:
        self._new_category.set_visible(
            combo.get_selected() == len(self._categories)
        )

    def _warn(self, message: str) -> None:
        self._banner.set_title(message)
        self._banner.set_revealed(True)

    def _on_save_clicked(self, _button: Gtk.Button) -> None:
        name = self._name.get_text().strip()
        app_id = self._id.get_text().strip().lower()

        if not name:
            self._warn(_("Bitte einen Namen eintragen."))
            return
        if not app_id:
            app_id = slugify(name)
            self._id.set_text(app_id)

        existing = self._catalog.by_id(app_id)
        if existing is not None and (self._app is None or self._app.id != app_id):
            self._warn(
                _("Die Kennung »{kennung}« ist bereits vergeben.").format(
                    kennung=app_id
                )
            )
            return

        sources: dict[str, dict] = {}
        if packages := _split(self._apt.get_text()):
            sources["apt"] = {"packages": packages}
        if packages := _split(self._pacman.get_text()):
            sources["pacman"] = {"packages": packages}
        if ref := self._flatpak.get_text().strip():
            sources["flatpak"] = {"ref": ref}
        if url := self._deb.get_text().strip():
            sources["deb"] = {"url": url}

        # Fremdquellen, Paketbereiche und Skripte aus der Mitlieferung bewahren.
        if self._app is not None:
            if "script" in self._app.sources:
                sources["script"] = self._app.sources["script"]
            for kind in ("apt", "deb"):
                old = self._app.sources.get(kind, {})
                if kind not in sources:
                    continue
                for key in ("repo", "components", "packages"):
                    if key in old and key not in sources[kind]:
                        sources[kind][key] = old[key]

        if not sources:
            self._warn(_("Mindestens eine Installationsquelle wird gebraucht."))
            return

        new_category: Category | None = None
        selected = self._category.get_selected()
        if selected == len(self._categories):
            label = self._new_category.get_text().strip()
            if not label:
                self._warn(_("Bitte die neue Kategorie benennen."))
                return
            new_category = Category(id=slugify(label), name=label)
            category_id = new_category.id
        else:
            category_id = self._categories[selected].id

        buffer = self._post.get_buffer()
        post = buffer.get_text(
            buffer.get_start_iter(), buffer.get_end_iter(), False
        ).strip()

        prefer_value = PREFER_CHOICES[self._prefer.get_selected()][0]
        description = self._description.get_text().strip()

        # Bearbeitet der Benutzer auf Englisch, gehört der Text ins englische
        # Feld – sonst wäre die deutsche Fassung überschrieben.
        if language() == "de" or self._app is None:
            german_name, english_name = name, self._app.name_en if self._app else ""
            german_desc = description
            english_desc = self._app.description_en if self._app else ""
        else:
            german_name = self._app.name or name
            english_name = name
            german_desc = self._app.description
            english_desc = description

        app = App(
            id=app_id,
            name=german_name,
            name_en=english_name,
            description=german_desc,
            description_en=english_desc,
            category=category_id,
            icon=self._icon.get_text().strip(),
            check_command=self._check.get_text().strip(),
            prefer=[prefer_value] if prefer_value else [],
            sources=sources,
            # Felder ohne eigene Eingabezeile dürfen nicht verloren gehen.
            homepage=self._app.homepage if self._app else "",
            pre_install=self._app.pre_install if self._app else "",
            post_install=post,
            builtin=False,
        )
        self._on_save(app, new_category)
        self.close()
