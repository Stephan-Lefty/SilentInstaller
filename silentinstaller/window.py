"""Hauptfenster von SilentInstaller."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import gi

gi.require_version("Gtk", "4.0")
gi.require_version("Adw", "1")

from gi.repository import Adw, Gdk, Gio, GLib, GObject, Gtk  # noqa: E402

from . import APP_ID, __version__  # noqa: E402
from . import backends, catalog as catalog_module, runner  # noqa: E402
from .catalog import App, Catalog, CatalogError  # noqa: E402
from .distro import FAMILY_UNKNOWN, Distro  # noqa: E402
from .editor import AppEditor  # noqa: E402
from .i18n import _, language  # noqa: E402
from .uihelpers import (  # noqa: E402
    anzeige_pfad,
    apply_theme,
    choose_file,
    esc,
    info_button,
)

FILTER_ALL = "__alle__"
FILTER_SELECTED = "__auswahl__"
FILTER_INSTALLED = "__installiert__"
FILTER_MISSING = "__fehlend__"

MODE_INSTALL = "install"
MODE_REMOVE = "remove"

LANGUAGE_CHOICES = ("auto", "de", "en")
THEME_CHOICES = ("auto", "light", "dark")

EXPORT_FILENAME = "silentinstaller-auswahl.json"


class MainWindow(Adw.ApplicationWindow):
    def __init__(self, application: Adw.Application, distro: Distro) -> None:
        super().__init__(
            application=application,
            title="SilentInstaller",
            default_width=1080,
            default_height=760,
            icon_name=APP_ID,
        )
        self.distro = distro
        self.settings = catalog_module.load_settings()
        self.catalog: Catalog = catalog_module.load()
        self.index = backends.InstalledIndex.collect(distro)

        self.selected: set[str] = set()
        self.filter: str = FILTER_ALL
        self.search_text: str = ""
        self.mode: str = MODE_INSTALL
        self._runner: runner.ScriptRunner | None = None

        self._build_actions()
        self._build_ui()
        self.rebuild_list()
        self._create_initial_profile()

    def _create_initial_profile(self) -> None:
        """Sichert beim allerersten Start den vorgefundenen Bestand als Profil.

        Wer SilentInstaller auf einem eingerichteten Rechner öffnet, hat dort
        über Monate eine Programmauswahl zusammengetragen. Dieses Profil hält
        sie fest, bevor irgendetwas verändert wird – und lässt sich auf dem
        nächsten Rechner mit einem Klick wieder herstellen.
        """
        # Profile aus älteren Fassungen liegen noch in der Einstellungsdatei.
        umgezogen = catalog_module.migrate_profiles(self.settings, self.catalog)
        if umgezogen:
            GLib.timeout_add(
                900,
                self._announce,
                _("{anzahl} Profile in eigene Dateien überführt").format(
                    anzahl=len(umgezogen)
                ),
            )

        if self.settings.get("initial_profile_done"):
            return

        self.settings["initial_profile_done"] = True
        vorhanden = {
            app.id for app in self.catalog.apps if self.index.app_state(app)[0]
        }
        name = ""
        if vorhanden:
            name = _("Dieses System ({datum})").format(datum=date.today().isoformat())
            try:
                catalog_module.save_profile(name, self.catalog, vorhanden)
            except OSError:
                name = ""
        catalog_module.save_settings(self.settings)

        if name:
            # Der Hinweis kommt verzögert, damit er nicht im Fensteraufbau untergeht.
            GLib.timeout_add(
                900,
                self._announce,
                _("Profil »{name}« mit {anzahl} vorgefundenen Programmen angelegt")
                .format(name=name, anzahl=len(vorhanden)),
            )

    def _announce(self, message: str) -> bool:
        """Einblendung aus einem Zeitgeber heraus – meldet sich einmalig."""
        self._toast(message)
        return False

    # -- Aufbau ------------------------------------------------------------

    def _build_actions(self) -> None:
        for name, handler in (
            ("add-app", self._on_add_app),
            ("refresh", lambda *_a: self.refresh_installed()),
            ("select-none", lambda *_a: self._set_selection(set())),
            ("select-visible", lambda *_a: self._select_visible()),
            ("save-profile", self._on_save_profile),
            ("load-profile", self._on_load_profile),
            ("export-selection", self._on_export_selection),
            ("import-selection", self._on_import_selection),
            ("show-script", lambda *_a: self._show_script_preview()),
            ("preferences", self._on_preferences),
            ("about", self._on_about),
        ):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", handler)
            self.add_action(action)

    def _build_ui(self) -> None:
        self.stack = Gtk.Stack(transition_type=Gtk.StackTransitionType.CROSSFADE)
        self.stack.add_named(self._build_browse_page(), "browse")
        self.stack.add_named(self._build_progress_page(), "progress")

        self.toasts = Adw.ToastOverlay(child=self.stack)

        self.split = Adw.NavigationSplitView(
            sidebar=self._build_sidebar(),
            content=Adw.NavigationPage(title=_("Programme"), child=self.toasts),
        )
        self.split.set_min_sidebar_width(220)
        self.split.set_max_sidebar_width(290)
        self.set_content(self.split)

    def _build_sidebar(self) -> Adw.NavigationPage:
        self.sidebar_list = Gtk.ListBox()
        self.sidebar_list.add_css_class("navigation-sidebar")
        self.sidebar_list.connect("row-selected", self._on_sidebar_selected)

        scroller = Gtk.ScrolledWindow(vexpand=True, child=self.sidebar_list)

        subtitle = self.distro.pretty
        if self.distro.family == FAMILY_UNKNOWN:
            subtitle += " – " + _("nicht unterstützt")
        header = Adw.HeaderBar()
        header.set_title_widget(
            Adw.WindowTitle(title="SilentInstaller", subtitle=esc(subtitle))
        )

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.set_content(scroller)

        self._fill_sidebar()
        return Adw.NavigationPage(title=_("Kategorien"), child=toolbar)

    def _fill_sidebar(self) -> None:
        while child := self.sidebar_list.get_first_child():
            self.sidebar_list.remove(child)

        entries: list[tuple[str, str, str]] = [
            (FILTER_ALL, _("Alle Programme"), "view-list-symbolic"),
            (FILTER_SELECTED, _("Ausgewählt"), "object-select-symbolic"),
            (FILTER_INSTALLED, _("Installiert"), "emblem-ok-symbolic"),
            (FILTER_MISSING, _("Noch nicht installiert"), "list-add-symbolic"),
        ]
        entries.extend(
            (c.id, c.display_name, c.icon) for c in self.catalog.used_categories()
        )

        target_row = None
        for key, label, icon in entries:
            row = Gtk.ListBoxRow()
            row.filter_key = key  # type: ignore[attr-defined]
            box = Gtk.Box(
                orientation=Gtk.Orientation.HORIZONTAL,
                spacing=12,
                margin_top=8,
                margin_bottom=8,
                margin_start=6,
                margin_end=6,
            )
            box.append(Gtk.Image.new_from_icon_name(icon))
            box.append(Gtk.Label(label=label, xalign=0.0, hexpand=True))
            row.set_child(box)
            self.sidebar_list.append(row)
            if key == self.filter:
                target_row = row
            if key == FILTER_MISSING:
                self.sidebar_list.append(
                    Gtk.ListBoxRow(
                        selectable=False, activatable=False, child=Gtk.Separator()
                    )
                )

        self.sidebar_list.select_row(target_row)

    def _build_browse_page(self) -> Gtk.Widget:
        header = Adw.HeaderBar()

        self.search_button = Gtk.ToggleButton(
            icon_name="system-search-symbolic", tooltip_text=_("Suchen (Strg+F)")
        )
        header.pack_start(self.search_button)
        header.pack_start(
            Gtk.Button(
                icon_name="list-add-symbolic",
                tooltip_text=_("Eigenes Programm hinzufügen"),
                action_name="win.add-app",
            )
        )

        header.pack_end(self._build_main_menu())

        self.search_entry = Gtk.SearchEntry(
            placeholder_text=_("Programm, Paketname oder Stichwort …"), hexpand=True
        )
        self.search_entry.connect("search-changed", self._on_search_changed)
        self.search_bar = Gtk.SearchBar(child=self.search_entry)
        self.search_bar.set_key_capture_widget(self)
        self.search_button.bind_property(
            "active",
            self.search_bar,
            "search-mode-enabled",
            GObject.BindingFlags.BIDIRECTIONAL,
        )

        self.list_box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=24,
            margin_top=24,
            margin_bottom=24,
            margin_start=12,
            margin_end=12,
        )
        scroller = Gtk.ScrolledWindow(
            vexpand=True, child=Adw.Clamp(maximum_size=860, child=self.list_box)
        )

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.add_top_bar(self.search_bar)
        toolbar.set_content(scroller)
        toolbar.add_bottom_bar(self._build_action_bar())
        return toolbar

    def _build_main_menu(self) -> Gtk.Widget:
        """Das Hauptmenü als eigenes Popover.

        Ein Menü aus ``Gio.Menu`` wäre kürzer, kennt aber keine Erklärtexte:
        ``Gio.MenuItem`` hat nur Beschriftung, Aktion und Symbol. Gerade der
        Unterschied zwischen einem Profil (bleibt hier) und einer ausgelagerten
        Auswahl (geht mit auf den nächsten Rechner) braucht aber einen Satz
        Erklärung – deshalb Knöpfe mit Hinweistext.
        """
        box = Gtk.Box(
            orientation=Gtk.Orientation.VERTICAL,
            spacing=2,
            margin_top=6,
            margin_bottom=6,
            margin_start=6,
            margin_end=6,
        )

        gruppen: list[tuple[str, list[tuple[str, str, str]]]] = [
            (
                "",
                [
                    (_("Alle sichtbaren auswählen"), "win.select-visible",
                     _("Setzt bei allen gerade angezeigten Programmen einen Haken")),
                    (_("Auswahl aufheben"), "win.select-none",
                     _("Entfernt alle Haken")),
                ],
            ),
            (
                _("Auf diesem Rechner"),
                [
                    (_("Auswahl als Profil speichern …"), "win.save-profile",
                     _("Sichert die aktuelle Auswahl unter einem Namen – als Datei "
                       "in ~/.config/silentinstaller/profile/. Gedacht zum schnellen "
                       "Umschalten auf diesem Rechner.")),
                    (_("Profil laden …"), "win.load-profile",
                     _("Stellt eine gespeicherte Auswahl wieder her. Ersetzt die "
                       "aktuellen Haken.")),
                ],
            ),
            (
                _("Auf einen anderen Rechner mitnehmen"),
                [
                    (_("Auswahl in Datei sichern …"), "win.export-selection",
                     _("Legt die Auswahl als Datei ab, die du weitergeben kannst – "
                       "USB-Stick, Nextcloud, Git. Gespeichert werden Kennungen, "
                       "keine Paketnamen: Dieselbe Datei funktioniert auf Debian "
                       "wie auf Arch. Selbst angelegte Programme wandern mit.")),
                    (_("Auswahl aus Datei laden …"), "win.import-selection",
                     _("Liest eine mitgebrachte Datei ein, auch von einem anderen "
                       "System. Was es hier nicht gibt, wird übersprungen und "
                       "gemeldet.")),
                ],
            ),
            (
                "",
                [
                    (_("Skript anzeigen …"), "win.show-script",
                     _("Zeigt den vollständigen Shell-Ablauf, der bei „Installieren“ "
                       "mit Root-Rechten laufen würde – bevor etwas passiert")),
                    (_("Installationsstand neu prüfen"), "win.refresh",
                     _("Fragt apt, pacman und flatpak erneut, was installiert ist")),
                ],
            ),
            (
                "",
                [
                    (_("Einstellungen"), "win.preferences",
                     _("Sprache, Erscheinungsbild, Flatpak-Vorrang und Speicherorte")),
                    (_("Über SilentInstaller"), "win.about", ""),
                ],
            ),
        ]

        self._menu_popover = Gtk.Popover(has_arrow=True)

        erste = True
        for titel, eintraege in gruppen:
            if not erste:
                trenner = Gtk.Separator(margin_top=4, margin_bottom=4)
                box.append(trenner)
            erste = False
            if titel:
                label = Gtk.Label(
                    label=titel, xalign=0.0, hexpand=True, margin_start=10
                )
                label.add_css_class("caption")
                label.add_css_class("dim-label")

                info = info_button(_("Was ist der Unterschied?"))
                info.connect("clicked", self._on_storage_info)

                kopfzeile = Gtk.Box(
                    orientation=Gtk.Orientation.HORIZONTAL,
                    margin_top=4,
                    margin_bottom=2,
                    margin_end=4,
                )
                kopfzeile.append(label)
                kopfzeile.append(info)
                box.append(kopfzeile)
            for beschriftung, aktion, hinweis in eintraege:
                box.append(self._menu_entry(beschriftung, aktion, hinweis))

        self._menu_popover.set_child(box)
        return Gtk.MenuButton(
            icon_name="open-menu-symbolic",
            popover=self._menu_popover,
            tooltip_text=_("Hauptmenü"),
        )

    def _on_storage_info(self, _button: Gtk.Button) -> None:
        """Erklärt in Ruhe, was ein Profil von einer Auswahldatei unterscheidet."""
        self._menu_popover.popdown()

        page = Adw.PreferencesPage()

        profile = Adw.PreferencesGroup(
            title=_("Profil – bleibt auf diesem Rechner"),
            description=_(
                "Eine benannte Auswahl zum schnellen Umschalten. Praktisch, wenn "
                "du je nach Aufgabe andere Programme brauchst – etwa ein Profil "
                "fürs Büro und eines zum Entwickeln. Jedes Profil ist eine eigene "
                "Datei; gelöscht wird es über den Lade-Dialog."
            ),
        )
        profile.add(
            Adw.ActionRow(
                title=_("Liegt unter"),
                subtitle=esc(anzeige_pfad(catalog_module.profile_dir())),
                subtitle_selectable=True,
            )
        )
        page.add(profile)

        datei = Adw.PreferencesGroup(
            title=_("Auswahl als Datei – geht mit auf andere Rechner"),
            description=_(
                "Dieselbe Auswahl, aber an einem Ort deiner Wahl: USB-Stick, "
                "Nextcloud, Git-Ablage. Gespeichert werden Kennungen, keine "
                "Paketnamen – deshalb funktioniert dieselbe Datei auf Debian wie "
                "auf Arch. Auf dem einen System wird »firefox-esr« über APT "
                "geholt, auf dem anderen »firefox« über Pacman. Programme, die "
                "du selbst angelegt hast, wandern vollständig mit; der neue "
                "Rechner muss sie nicht kennen."
            ),
        )
        page.add(datei)

        gemeinsam = Adw.PreferencesGroup(
            title=_("Beides ist dasselbe Dateiformat"),
            description=_(
                "Eine Profildatei und eine ausgelagerte Auswahl sind identisch "
                "aufgebaut. Kopierst du eine mitgebrachte Datei in das "
                "Profilverzeichnis, steht sie beim nächsten Start unter »Profil "
                "laden«. Umgekehrt kannst du eine Profildatei direkt weitergeben."
            ),
        )
        page.add(gemeinsam)

        window = Adw.Window(
            transient_for=self,
            modal=True,
            title=_("Profile und Auswahldateien"),
            default_width=580,
            default_height=620,
        )
        header = Adw.HeaderBar()
        schliessen = Gtk.Button(label=_("Schließen"))
        schliessen.connect("clicked", lambda *_a: window.close())
        header.pack_start(schliessen)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.set_content(page)
        window.set_content(toolbar)
        window.present()

    def _menu_entry(self, label: str, action: str, tooltip: str) -> Gtk.Button:
        button = Gtk.Button(action_name=action, has_frame=False)
        inhalt = Gtk.Label(label=label, xalign=0.0, margin_start=4, margin_end=4)
        button.set_child(inhalt)
        if tooltip:
            button.set_tooltip_text(tooltip)
        # Ein Knopf schließt das Popover nicht von selbst, anders als ein Menüeintrag.
        button.connect("clicked", lambda *_a: self._menu_popover.popdown())
        return button

    def _build_action_bar(self) -> Gtk.Widget:
        self.selection_label = Gtk.Label(label=_("Nichts ausgewählt"), xalign=0.0)
        self.selection_label.add_css_class("dim-label")

        self.install_button = Gtk.Button(label=_("Installieren"))
        self.install_button.add_css_class("suggested-action")
        self.install_button.connect("clicked", lambda *_a: self._start(MODE_INSTALL))

        self.remove_button = Gtk.Button(label=_("Entfernen"))
        self.remove_button.add_css_class("destructive-action")
        self.remove_button.connect("clicked", lambda *_a: self._start(MODE_REMOVE))

        bar = Gtk.ActionBar()
        bar.pack_start(self.selection_label)
        bar.pack_end(self.install_button)
        bar.pack_end(self.remove_button)
        return bar

    def _build_progress_page(self) -> Gtk.Widget:
        self.progress_title = Gtk.Label(
            label="", xalign=0.0, wrap=True, margin_start=12, margin_end=12
        )
        self.progress_title.add_css_class("title-4")

        self.progress_bar = Gtk.ProgressBar(
            show_text=True, margin_start=12, margin_end=12
        )

        self.log_view = Gtk.TextView(
            editable=False,
            monospace=True,
            cursor_visible=False,
            wrap_mode=Gtk.WrapMode.WORD_CHAR,
            top_margin=8,
            bottom_margin=8,
            left_margin=8,
            right_margin=8,
        )
        self.log_scroller = Gtk.ScrolledWindow(
            vexpand=True,
            child=self.log_view,
            margin_start=12,
            margin_end=12,
            margin_bottom=12,
        )
        self.log_scroller.add_css_class("card")

        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12, margin_top=18)
        box.append(self.progress_title)
        box.append(self.progress_bar)
        box.append(self.log_scroller)

        self.cancel_button = Gtk.Button(label=_("Abbrechen"))
        self.cancel_button.connect("clicked", self._on_cancel)
        self.close_progress_button = Gtk.Button(label=_("Fertig"), sensitive=False)
        self.close_progress_button.add_css_class("suggested-action")
        self.close_progress_button.connect("clicked", self._on_progress_done)

        bar = Gtk.ActionBar()
        bar.pack_end(self.close_progress_button)
        bar.pack_end(self.cancel_button)

        header = Adw.HeaderBar(show_start_title_buttons=False)
        header.set_title_widget(Adw.WindowTitle(title=_("Wird ausgeführt"), subtitle=""))

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.set_content(box)
        toolbar.add_bottom_bar(bar)
        return toolbar

    # -- Liste -------------------------------------------------------------

    def _visible_apps(self) -> list[App]:
        needle = self.search_text.strip().lower()
        result = []
        special = (FILTER_ALL, FILTER_SELECTED, FILTER_INSTALLED, FILTER_MISSING)
        for app in self.catalog.apps:
            installed, _via = self.index.app_state(app)
            if self.filter == FILTER_SELECTED and app.id not in self.selected:
                continue
            if self.filter == FILTER_INSTALLED and not installed:
                continue
            if self.filter == FILTER_MISSING and installed:
                continue
            if self.filter not in special and app.category != self.filter:
                continue
            if needle and needle not in app.search_text():
                continue
            result.append(app)
        return result

    def rebuild_list(self) -> None:
        while child := self.list_box.get_first_child():
            self.list_box.remove(child)

        apps = self._visible_apps()
        if not apps:
            self.list_box.append(
                Adw.StatusPage(
                    icon_name="system-search-symbolic",
                    title=_("Nichts gefunden"),
                    description=_(
                        "Andere Kategorie wählen oder Suchbegriff anpassen."
                    ),
                    vexpand=True,
                )
            )
            self._update_selection_label()
            return

        by_category: dict[str, list[App]] = {}
        for app in apps:
            by_category.setdefault(app.category, []).append(app)

        order = [c.id for c in self.catalog.used_categories()]
        for category_id in sorted(
            by_category, key=lambda c: order.index(c) if c in order else 999
        ):
            group = Adw.PreferencesGroup(
                title=esc(self.catalog.category_name(category_id))
            )
            for app in by_category[category_id]:
                group.add(self._build_row(app))
            self.list_box.append(group)

        self._update_selection_label()

    def _build_row(self, app: App) -> Gtk.Widget:
        installed, via = self.index.app_state(app)
        resolved = backends.resolve(
            app, self.distro, self.settings.get("prefer_flatpak", False)
        )

        row = Adw.ActionRow(
            title=esc(app.display_name), subtitle=esc(app.display_description) or " "
        )
        row.add_prefix(self._icon_for(app))

        if resolved is None:
            tag = Gtk.Label(label=_("nicht verfügbar"))
            tag.add_css_class("dim-label")
            tag.add_css_class("caption")
            row.add_suffix(tag)
            row.set_sensitive(False)
            return row

        source_label = Gtk.Label(label=resolved.label)
        source_label.add_css_class("dim-label")
        source_label.add_css_class("caption")
        row.add_suffix(source_label)

        if installed:
            badge = Gtk.Label(label=_("installiert"))
            badge.add_css_class("caption")
            badge.add_css_class("accent")
            badge.set_tooltip_text(
                _("Bereits vorhanden über {quelle}").format(
                    quelle=via or _("einen Prüfbefehl")
                )
            )
            row.add_suffix(badge)

        check = Gtk.CheckButton(active=app.id in self.selected, valign=Gtk.Align.CENTER)
        check.connect("toggled", self._on_row_toggled, app.id)
        row.add_suffix(check)
        row.set_activatable_widget(check)
        row.add_suffix(self._row_menu(app))
        return row

    def _row_menu(self, app: App) -> Gtk.Widget:
        menu = Gio.Menu()
        menu.append(_("Bearbeiten …"), f"win.edit-{app.id}")
        menu.append(
            _("Ausblenden") if app.builtin else _("Aus der Liste nehmen"),
            f"win.delete-{app.id}",
        )
        if app.homepage:
            menu.append(_("Webseite öffnen"), f"win.web-{app.id}")

        for suffix, handler in (
            ("edit", lambda *_a, a=app: self._open_editor(a)),
            ("delete", lambda *_a, a=app: self._confirm_delete(a)),
            ("web", lambda *_a, a=app: self._open_homepage(a)),
        ):
            name = f"{suffix}-{app.id}"
            if self.lookup_action(name) is None:
                action = Gio.SimpleAction.new(name, None)
                action.connect("activate", handler)
                self.add_action(action)

        button = Gtk.MenuButton(
            icon_name="view-more-symbolic", menu_model=menu, valign=Gtk.Align.CENTER
        )
        button.add_css_class("flat")
        return button

    def _open_homepage(self, app: App) -> None:
        if hasattr(Gtk, "UriLauncher"):
            launcher = Gtk.UriLauncher(uri=app.homepage)
            launcher.launch(self, None, None)
        else:
            Gio.AppInfo.launch_default_for_uri(app.homepage, None)

    def _icon_for(self, app: App) -> Gtk.Image:
        theme = Gtk.IconTheme.get_for_display(Gdk.Display.get_default())
        for name in (app.icon, app.id, f"{app.id}-symbolic"):
            if name and theme.has_icon(name):
                return Gtk.Image.new_from_icon_name(name)
        category = self.catalog.category(app.category)
        return Gtk.Image.new_from_icon_name(
            category.icon if category else "application-x-executable-symbolic"
        )

    # -- Auswahl -----------------------------------------------------------

    def _on_row_toggled(self, check: Gtk.CheckButton, app_id: str) -> None:
        if check.get_active():
            self.selected.add(app_id)
        else:
            self.selected.discard(app_id)
        self._update_selection_label()

    def _set_selection(self, ids: set[str]) -> None:
        self.selected = {i for i in ids if self.catalog.by_id(i)}
        self.rebuild_list()

    def _select_visible(self) -> None:
        prefer_flatpak = self.settings.get("prefer_flatpak", False)
        for app in self._visible_apps():
            if backends.resolve(app, self.distro, prefer_flatpak):
                self.selected.add(app.id)
        self.rebuild_list()

    def _update_selection_label(self) -> None:
        count = len(self.selected)
        installed = sum(
            1
            for app_id in self.selected
            if (app := self.catalog.by_id(app_id)) and self.index.app_state(app)[0]
        )
        if count == 0:
            self.selection_label.set_label(_("Nichts ausgewählt"))
        elif installed:
            self.selection_label.set_label(
                _("{anzahl} ausgewählt · {vorhanden} davon bereits installiert").format(
                    anzahl=count, vorhanden=installed
                )
            )
        else:
            self.selection_label.set_label(
                _("{anzahl} ausgewählt").format(anzahl=count)
            )

        self.install_button.set_sensitive(count > 0)
        self.remove_button.set_sensitive(installed > 0)

    def _on_search_changed(self, entry: Gtk.SearchEntry) -> None:
        self.search_text = entry.get_text()
        self.rebuild_list()

    def _on_sidebar_selected(self, _box, row: Gtk.ListBoxRow | None) -> None:
        if row is None:
            return
        self.filter = getattr(row, "filter_key", FILTER_ALL)
        self.rebuild_list()

    def _toast(self, message: str) -> None:
        self.toasts.add_toast(Adw.Toast(title=message, timeout=4))

    # -- Katalog pflegen ---------------------------------------------------

    def _on_add_app(self, *_args) -> None:
        self._open_editor(None)

    def _open_editor(self, app: App | None) -> None:
        AppEditor(self, self.catalog, app, self._save_app).present()

    def _save_app(self, app: App, new_category) -> None:
        if new_category is not None and self.catalog.category(new_category.id) is None:
            self.catalog.categories.append(new_category)
        self.catalog.upsert(app)
        catalog_module.save(self.catalog)
        self.refresh_installed()
        self._fill_sidebar()
        self._toast(_("»{name}« gespeichert").format(name=app.display_name))

    def _confirm_delete(self, app: App) -> None:
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading=_("»{name}« aus der Liste nehmen?").format(name=app.display_name),
            body=_(
                "Der Eintrag verschwindet nur aus SilentInstaller. Ein bereits "
                "installiertes Programm bleibt auf dem Rechner."
            ),
        )
        dialog.add_response("cancel", _("Abbrechen"))
        dialog.add_response("delete", _("Entfernen"))
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("cancel")
        dialog.connect("response", self._on_delete_response, app)
        dialog.present()

    def _on_delete_response(self, _dialog, response: str, app: App) -> None:
        if response != "delete":
            return
        name = app.display_name
        self.catalog.remove(app.id)
        self.selected.discard(app.id)
        catalog_module.save(self.catalog)
        self._fill_sidebar()
        self.rebuild_list()
        self._toast(_("»{name}« entfernt").format(name=name))

    # -- Profile im Programm -----------------------------------------------

    def _on_save_profile(self, *_args) -> None:
        if not self.selected:
            self._toast(_("Erst Programme auswählen"))
            return
        entry = Gtk.Entry(placeholder_text=_("Name des Profils"))
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading=_("Auswahl als Profil speichern"),
            body=_("{anzahl} Programme werden gesichert.").format(
                anzahl=len(self.selected)
            ),
            extra_child=entry,
        )
        dialog.add_response("cancel", _("Abbrechen"))
        dialog.add_response("save", _("Speichern"))
        dialog.set_response_appearance("save", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_default_response("save")

        def on_response(_d, response: str) -> None:
            name = entry.get_text().strip()
            if response != "save" or not name:
                return
            try:
                pfad = catalog_module.save_profile(name, self.catalog, self.selected)
            except OSError as exc:
                self._toast(_("Sichern fehlgeschlagen: {fehler}").format(fehler=exc))
                return
            self._toast(
                _("Profil »{name}« in {datei} gespeichert").format(
                    name=name, datei=pfad.name
                )
            )

        dialog.connect("response", on_response)
        dialog.present()

    def _on_load_profile(self, *_args) -> None:
        profile = catalog_module.list_profiles()
        if not profile:
            self._toast(_("Noch keine Profile gespeichert"))
            return

        combo = Gtk.DropDown.new_from_strings(
            [
                _("{name} – {anzahl} Programme").format(name=p.name, anzahl=p.count)
                for p in profile
            ]
        )
        dialog = Adw.MessageDialog(
            transient_for=self,
            heading=_("Profil laden"),
            body=_("Die gespeicherte Auswahl ersetzt die aktuelle.")
            + "\n"
            + anzeige_pfad(catalog_module.profile_dir()),
            extra_child=combo,
        )
        dialog.add_response("cancel", _("Abbrechen"))
        dialog.add_response("delete", _("Löschen"))
        dialog.add_response("load", _("Laden"))
        dialog.set_response_appearance("load", Adw.ResponseAppearance.SUGGESTED)
        dialog.set_response_appearance("delete", Adw.ResponseAppearance.DESTRUCTIVE)
        dialog.set_default_response("load")

        def on_response(_d, response: str) -> None:
            gewaehlt = profile[combo.get_selected()]
            if response == "load":
                # Über den Einlese-Weg, damit auch eigene Programme
                # nachgetragen werden, die dem Katalog inzwischen fehlen.
                self._read_selection(gewaehlt.path, profil=gewaehlt.name)
            elif response == "delete":
                if catalog_module.delete_profile(gewaehlt):
                    self._toast(
                        _("Profil »{name}« gelöscht").format(name=gewaehlt.name)
                    )

        dialog.connect("response", on_response)
        dialog.present()

    # -- Auswahl als eigenständige Datei -----------------------------------

    def _on_export_selection(self, *_args) -> None:
        if not self.selected:
            self._toast(_("Erst Programme auswählen"))
            return
        choose_file(
            self,
            save=True,
            title=_("Auswahl sichern"),
            initial_name=EXPORT_FILENAME,
            on_chosen=self._write_selection,
        )

    def _write_selection(self, path: Path) -> None:
        try:
            written = catalog_module.export_selection(
                path, self.catalog, self.selected, name=path.stem
            )
        except OSError as exc:
            self._toast(_("Sichern fehlgeschlagen: {fehler}").format(fehler=exc))
            return
        self._toast(_("Auswahl in {datei} gesichert").format(datei=written.name))

    def _on_import_selection(self, *_args) -> None:
        choose_file(
            self,
            save=False,
            title=_("Auswahl laden"),
            on_chosen=self._read_selection,
        )

    def _read_selection(self, path: Path, profil: str = "") -> None:
        """Liest eine Auswahldatei ein.

        ``profil`` benennt das geladene Profil, damit die Meldung sagen kann,
        woher die Auswahl stammt.
        """
        try:
            result = catalog_module.import_selection(path, self.catalog)
        except CatalogError as exc:
            self._toast(_(str(exc)))
            return
        except OSError as exc:
            self._toast(_("Laden fehlgeschlagen: {fehler}").format(fehler=exc))
            return

        if result.added_apps:
            catalog_module.save(self.catalog)
        self._set_selection(result.selected)
        self._fill_sidebar()

        if profil:
            message = _("Profil »{name}« geladen: {anzahl} Programme").format(
                name=profil, anzahl=len(result.selected)
            )
        elif result.added_apps:
            message = _(
                "{anzahl} Programme geladen, {eigene} eigene Einträge übernommen"
            ).format(anzahl=len(result.selected), eigene=len(result.added_apps))
        else:
            message = _("{anzahl} Programme geladen").format(
                anzahl=len(result.selected)
            )
        if result.unknown:
            message += " – " + _(
                "{anzahl} Einträge waren unbekannt und wurden übersprungen"
            ).format(anzahl=len(result.unknown))
        self._toast(message)

    # -- Einstellungen -----------------------------------------------------

    def _on_preferences(self, *_args) -> None:
        window = Adw.PreferencesWindow(
            transient_for=self, modal=True, title=_("Einstellungen")
        )
        page = Adw.PreferencesPage(
            title=_("Allgemein"), icon_name="preferences-system-symbolic"
        )

        look = Adw.PreferencesGroup(title=_("Darstellung"))

        automatic = _("Automatisch ({sprache})").format(
            sprache=_("Deutsch") if language() == "de" else _("Englisch")
        )
        language_row = Adw.ComboRow(
            title=_("Sprache"),
            subtitle=_("Der Systemsprache folgen"),
            model=Gtk.StringList.new([automatic, "Deutsch", "English"]),
        )
        language_row.set_selected(
            LANGUAGE_CHOICES.index(self.settings.get("language", "auto"))
            if self.settings.get("language", "auto") in LANGUAGE_CHOICES
            else 0
        )
        language_row.connect("notify::selected", self._on_language_changed)
        look.add(language_row)

        theme_row = Adw.ComboRow(
            title=_("Erscheinungsbild"),
            subtitle=_("Hell oder dunkel – oder dem Desktop überlassen"),
            model=Gtk.StringList.new([_("Wie das System"), _("Hell"), _("Dunkel")]),
        )
        theme_row.set_selected(
            THEME_CHOICES.index(self.settings.get("theme", "auto"))
            if self.settings.get("theme", "auto") in THEME_CHOICES
            else 0
        )
        theme_row.connect("notify::selected", self._on_theme_changed)
        look.add(theme_row)
        page.add(look)

        group = Adw.PreferencesGroup(title=_("Installation"))
        flatpak_row = Adw.SwitchRow(
            title=_("Flatpak bevorzugen"),
            subtitle=_("Wo möglich Flathub statt der Distributionspakete verwenden"),
            active=bool(self.settings.get("prefer_flatpak")),
        )
        flatpak_row.connect("notify::active", self._on_prefer_flatpak)
        group.add(flatpak_row)

        purge_row = Adw.SwitchRow(
            title=_("Beim Entfernen auch Einstellungen löschen"),
            subtitle=_("apt purge bzw. pacman -Rns statt eines einfachen Entfernens"),
            active=bool(self.settings.get("purge_on_remove")),
        )
        purge_row.connect("notify::active", self._on_purge_toggle)
        group.add(purge_row)
        page.add(group)

        paths = Adw.PreferencesGroup(title=_("Dateien"))
        paths.add(
            Adw.ActionRow(
                title=_("Eigener Katalog"),
                subtitle=esc(anzeige_pfad(catalog_module.user_catalog_path())),
            )
        )
        # Beim mitgelieferten Katalog hilft der volle Pfad niemandem – er hängt
        # davon ab, wohin das Programm entpackt wurde, und lässt sich ohnehin
        # nicht sinnvoll bearbeiten. Der Ort innerhalb des Programms genügt.
        mitgeliefert = sum(1 for app in self.catalog.apps if app.builtin)
        paths.add(
            Adw.ActionRow(
                title=_("Mitgelieferter Katalog"),
                subtitle=_(
                    "{anzahl} Einträge in silentinstaller/data/catalog.json – "
                    "wird bei Aktualisierungen ersetzt"
                ).format(anzahl=mitgeliefert),
            )
        )
        page.add(paths)

        window.add(page)
        self._preferences_window = window
        window.present()

    def _on_language_changed(self, row: Adw.ComboRow, _param) -> None:
        choice = LANGUAGE_CHOICES[row.get_selected()]
        if choice == self.settings.get("language", "auto"):
            return
        self.settings["language"] = choice
        catalog_module.save_settings(self.settings)
        if window := getattr(self, "_preferences_window", None):
            window.close()
        self._reload_for_language()

    def _reload_for_language(self) -> None:
        """Baut das Fenster in der neuen Sprache neu auf.

        Ein Neustart wäre dem Benutzer gegenüber unhöflich, und die Beschriftungen
        einzeln nachzuziehen wäre eine endlose Fehlerquelle. Ein frisches Fenster
        mit übernommener Auswahl ist der ehrlichste Weg.
        """
        from .i18n import set_language

        set_language(self.settings.get("language", "auto"))

        application = self.get_application()
        fresh = MainWindow(application, self.distro)
        fresh.selected = set(self.selected)
        fresh.filter = self.filter
        fresh._fill_sidebar()
        fresh.rebuild_list()
        if hasattr(application, "replace_window"):
            application.replace_window(fresh)
        fresh.present()
        self.close()

    def _on_theme_changed(self, row: Adw.ComboRow, _param) -> None:
        choice = THEME_CHOICES[row.get_selected()]
        self.settings["theme"] = choice
        catalog_module.save_settings(self.settings)
        apply_theme(choice)

    def _on_prefer_flatpak(self, row: Adw.SwitchRow, _param) -> None:
        self.settings["prefer_flatpak"] = row.get_active()
        catalog_module.save_settings(self.settings)
        self.rebuild_list()

    def _on_purge_toggle(self, row: Adw.SwitchRow, _param) -> None:
        self.settings["purge_on_remove"] = row.get_active()
        catalog_module.save_settings(self.settings)

    def _on_about(self, *_args) -> None:
        Adw.AboutWindow(
            transient_for=self,
            application_name="SilentInstaller",
            application_icon=APP_ID,
            version=__version__,
            developer_name="Stephan Rösner",
            comments=_(
                "Lieblingsprogramme nach einer Grundinstallation in einem Rutsch "
                "nachinstallieren – für Debian- und Arch-basierte Systeme."
            ),
            license_type=Gtk.License.MIT_X11,
            website="https://github.com/Stephan-Lefty/SilentInstaller",
        ).present()

    # -- Ausführung --------------------------------------------------------

    def _resolved_selection(self, mode: str) -> list[backends.Resolved]:
        prefer_flatpak = self.settings.get("prefer_flatpak", False)
        items = []
        for app_id in sorted(self.selected):
            app = self.catalog.by_id(app_id)
            if app is None:
                continue
            installed, via = self.index.app_state(app)
            if mode == MODE_INSTALL and installed:
                continue
            if mode == MODE_REMOVE:
                if not installed:
                    continue
                # Entfernt wird über die Quelle, aus der es tatsächlich stammt.
                if via and app.sources.get(via):
                    items.append(backends.Resolved(app, via, dict(app.sources[via])))
                    continue
            if resolved := backends.resolve(app, self.distro, prefer_flatpak):
                items.append(resolved)
        return items

    def _build_plan(self, mode: str) -> runner.Plan:
        items = self._resolved_selection(mode)
        if mode == MODE_REMOVE:
            return runner.build_remove_plan(
                items, self.distro, bool(self.settings.get("purge_on_remove"))
            )
        return runner.build_install_plan(items, self.distro)

    def _show_script_preview(self) -> None:
        plan = self._build_plan(self.mode)
        if not plan:
            self._toast(_("Für die aktuelle Auswahl gibt es nichts zu tun"))
            return
        script = runner.render_script(plan)

        view = Gtk.TextView(editable=False, monospace=True, top_margin=8, left_margin=8)
        view.get_buffer().set_text(script)

        window = Adw.Window(
            transient_for=self,
            modal=True,
            title=_("Erzeugtes Skript"),
            default_width=820,
            default_height=640,
        )
        header = Adw.HeaderBar()
        copy = Gtk.Button(label=_("Kopieren"))
        copy.connect(
            "clicked",
            lambda *_a: Gdk.Display.get_default().get_clipboard().set_text(script),
        )
        header.pack_end(copy)
        close = Gtk.Button(label=_("Schließen"))
        close.connect("clicked", lambda *_a: window.close())
        header.pack_start(close)

        toolbar = Adw.ToolbarView()
        toolbar.add_top_bar(header)
        toolbar.set_content(Gtk.ScrolledWindow(vexpand=True, child=view))
        window.set_content(toolbar)
        window.present()

    def _start(self, mode: str) -> None:
        self.mode = mode
        plan = self._build_plan(mode)
        if not plan:
            self._toast(
                _("Alles schon installiert")
                if mode == MODE_INSTALL
                else _("Nichts zu entfernen")
            )
            return

        count = len({app_id for step in plan.steps for app_id in step.apps})
        heading = (
            _("{anzahl} Programm(e) werden installiert")
            if mode == MODE_INSTALL
            else _("{anzahl} Programm(e) werden entfernt")
        ).format(anzahl=count)

        dialog = Adw.MessageDialog(
            transient_for=self,
            heading=heading,
            body=_(
                "Dafür laufen {schritte} Arbeitsschritte mit Root-Rechten. Das "
                "Passwort wird einmal abgefragt."
            ).format(schritte=len(plan.steps)),
        )
        dialog.add_response("cancel", _("Abbrechen"))
        dialog.add_response("script", _("Skript ansehen"))
        dialog.add_response(
            "go", _("Installieren") if mode == MODE_INSTALL else _("Entfernen")
        )
        dialog.set_response_appearance(
            "go",
            Adw.ResponseAppearance.SUGGESTED
            if mode == MODE_INSTALL
            else Adw.ResponseAppearance.DESTRUCTIVE,
        )
        dialog.set_default_response("go")
        dialog.connect("response", self._on_start_response, plan)
        dialog.present()

    def _on_start_response(self, _dialog, response: str, plan: runner.Plan) -> None:
        if response == "script":
            self._show_script_preview()
        elif response == "go":
            self._execute(plan)

    def _execute(self, plan: runner.Plan) -> None:
        self._plan = plan
        self._total_steps = len(plan.steps)
        self._failed_steps: list[str] = []

        self.log_view.get_buffer().set_text("")
        self.progress_bar.set_fraction(0.0)
        self.progress_bar.set_text(_("Warte auf die Rechtefreigabe …"))
        self.progress_title.set_label(_("Vorbereitung"))
        self.cancel_button.set_sensitive(True)
        self.close_progress_button.set_sensitive(False)
        self.split.set_collapsed(True)
        self.stack.set_visible_child_name("progress")

        self._runner = runner.ScriptRunner()
        cancel_file = self._runner.prepare()
        script = runner.render_script(plan, str(cancel_file))
        self._runner.start(
            script,
            lambda line: GLib.idle_add(self._on_output, line),
            lambda code, error: GLib.idle_add(self._on_finished, code, error),
        )

    def _on_output(self, line: str) -> bool:
        if line.startswith(runner.MARK_STEP):
            parts = line.split("@@")
            index, total, title = parts[2], parts[3], "@@".join(parts[4:])
            self.progress_title.set_label(title)
            self.progress_bar.set_fraction((int(index) - 1) / max(int(total), 1))
            self.progress_bar.set_text(
                _("Schritt {nummer} von {gesamt}").format(nummer=index, gesamt=total)
            )
            self._append_log(f"\n▶ {title}\n")
        elif line.startswith(runner.MARK_RESULT):
            parts = line.split("@@")
            index, code = int(parts[2]), int(parts[3])
            self.progress_bar.set_fraction(index / max(self._total_steps, 1))
            if code != 0:
                self._failed_steps.append(self._plan.steps[index - 1].title)
                self._append_log(
                    "✗ " + _("fehlgeschlagen (Code {code})").format(code=code) + "\n"
                )
            else:
                self._append_log("✓ " + _("erledigt") + "\n")
        elif line.startswith(runner.MARK_CANCELLED):
            self._append_log("\n" + _("Abgebrochen auf Wunsch.") + "\n")
        elif not line.startswith(runner.MARK_DONE):
            self._append_log(line + "\n")
        return False

    def _append_log(self, text: str) -> None:
        buffer = self.log_view.get_buffer()
        buffer.insert(buffer.get_end_iter(), text)
        adjustment = self.log_scroller.get_vadjustment()
        GLib.idle_add(
            lambda: adjustment.set_value(
                adjustment.get_upper() - adjustment.get_page_size()
            )
        )

    def _on_finished(self, code: int, error: str | None) -> bool:
        self.cancel_button.set_sensitive(False)
        self.close_progress_button.set_sensitive(True)
        self.progress_bar.set_fraction(1.0)

        if error:
            self.progress_title.set_label(error)
            self.progress_bar.set_text(_("Abgebrochen"))
            self._append_log(f"\n{error}\n")
        elif self._failed_steps:
            self.progress_title.set_label(
                _("{anzahl} Schritt(e) fehlgeschlagen").format(
                    anzahl=len(self._failed_steps)
                )
            )
            self.progress_bar.set_text(_("Mit Fehlern beendet"))
            self._append_log(
                "\n"
                + _("Fehlgeschlagen: {schritte}").format(
                    schritte=", ".join(self._failed_steps)
                )
                + "\n"
            )
        else:
            self.progress_title.set_label(_("Alles erledigt"))
            self.progress_bar.set_text(_("Fertig"))

        if self._runner:
            self._runner.cleanup()
        return False

    def _on_cancel(self, _button: Gtk.Button) -> None:
        if self._runner:
            self._runner.cancel()
        self.cancel_button.set_sensitive(False)
        self._append_log(
            "\n"
            + _("Abbruch angefordert – der laufende Schritt wird noch zu Ende geführt.")
            + "\n"
        )

    def _on_progress_done(self, _button: Gtk.Button) -> None:
        self.refresh_installed()
        self.split.set_collapsed(False)
        self.stack.set_visible_child_name("browse")

    def refresh_installed(self) -> None:
        self.index = backends.InstalledIndex.collect(self.distro)
        self.rebuild_list()
