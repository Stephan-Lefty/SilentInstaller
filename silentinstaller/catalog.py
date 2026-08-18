"""Laden, Zusammenführen und Speichern des Programmkatalogs.

Der Katalog besteht aus zwei Ebenen:

* die mitgelieferte Liste in ``silentinstaller/data/catalog.json``
* die persönliche Liste in ``~/.config/silentinstaller/catalog.json``

Beim Start werden beide zusammengeführt. Die persönliche Datei kann eigene
Programme ergänzen, mitgelieferte überschreiben (gleiche ``id``) oder über
``hidden`` ausblenden. Gespeichert wird immer nur die persönliche Datei –
die Mitlieferung bleibt unberührt und kann jederzeit per Update ersetzt werden.
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from .i18n import translate_field

CATALOG_VERSION = 1

#: Kennung im Kopf einer ausgelagerten Auswahldatei.
SELECTION_FORMAT = "silentinstaller-auswahl"
SELECTION_VERSION = 1

BUILTIN_CATALOG = Path(__file__).resolve().parent / "data" / "catalog.json"

SOURCE_KINDS = ("apt", "pacman", "flatpak", "deb", "script")


def config_dir() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")
    return Path(base) / "silentinstaller"


def user_catalog_path() -> Path:
    return config_dir() / "catalog.json"


def settings_path() -> Path:
    return config_dir() / "settings.json"


def profile_dir() -> Path:
    """Verzeichnis, in dem jedes Profil als eigene Datei liegt."""
    return config_dir() / "profile"


def slugify(text: str) -> str:
    """Macht aus einem Anzeigenamen einen brauchbaren Datei- oder Kennungsnamen."""
    text = text.lower().strip()
    for source, target in (("ä", "ae"), ("ö", "oe"), ("ü", "ue"), ("ß", "ss")):
        text = text.replace(source, target)
    text = re.sub(r"[^a-z0-9]+", "-", text)
    return text.strip("-") or "eintrag"


@dataclass
class Category:
    id: str
    name: str
    #: Englische Fassung; fehlt sie, wird der deutsche Name genommen.
    name_en: str = ""
    icon: str = "application-x-executable-symbolic"

    @classmethod
    def from_dict(cls, raw: dict) -> "Category":
        return cls(
            id=str(raw["id"]),
            name=str(raw.get("name", raw["id"])),
            name_en=str(raw.get("name_en", "")),
            icon=str(raw.get("icon", "application-x-executable-symbolic")),
        )

    def to_dict(self) -> dict:
        data = {"id": self.id, "name": self.name, "icon": self.icon}
        if self.name_en:
            data["name_en"] = self.name_en
        return data

    @property
    def display_name(self) -> str:
        return translate_field(self.name, self.name_en)


@dataclass
class App:
    """Ein Programm mit einer oder mehreren Installationsquellen."""

    id: str
    name: str
    description: str = ""
    #: Englische Fassungen; fehlen sie, wird der deutsche Text genommen.
    name_en: str = ""
    description_en: str = ""
    category: str = "sonstiges"
    icon: str = ""
    homepage: str = ""
    #: Prüfbefehl – liegt dieses Programm im PATH, gilt die App als installiert.
    check_command: str = ""
    #: Reihenfolge der bevorzugten Quellen, z. B. ["flatpak", "apt"].
    prefer: list[str] = field(default_factory=list)
    #: Quellen nach Art: {"apt": {...}, "flatpak": {...}}
    sources: dict[str, dict] = field(default_factory=dict)
    #: Shell-Schnipsel, das vor der Installation als root läuft (z. B. debconf).
    pre_install: str = ""
    #: Shell-Schnipsel, das nach erfolgreicher Installation als root läuft.
    post_install: str = ""
    #: Stammt aus der mitgelieferten Liste (nicht löschbar, nur ausblendbar).
    builtin: bool = True

    @classmethod
    def from_dict(cls, raw: dict, builtin: bool = True) -> "App":
        sources = {
            kind: dict(value)
            for kind, value in (raw.get("sources") or {}).items()
            if kind in SOURCE_KINDS and isinstance(value, dict)
        }
        return cls(
            id=str(raw["id"]),
            name=str(raw.get("name", raw["id"])),
            description=str(raw.get("description", "")),
            name_en=str(raw.get("name_en", "")),
            description_en=str(raw.get("description_en", "")),
            category=str(raw.get("category", "sonstiges")),
            icon=str(raw.get("icon", "")),
            homepage=str(raw.get("homepage", "")),
            check_command=str(raw.get("check_command", "")),
            prefer=[str(p) for p in raw.get("prefer", []) if p in SOURCE_KINDS],
            sources=sources,
            pre_install=str(raw.get("pre_install", "")),
            post_install=str(raw.get("post_install", "")),
            builtin=builtin,
        )

    def to_dict(self) -> dict:
        data: dict = {"id": self.id, "name": self.name, "category": self.category}
        for key in (
            "description",
            "name_en",
            "description_en",
            "icon",
            "homepage",
            "check_command",
            "pre_install",
            "post_install",
        ):
            value = getattr(self, key)
            if value:
                data[key] = value
        if self.prefer:
            data["prefer"] = list(self.prefer)
        data["sources"] = {k: v for k, v in self.sources.items() if v}
        return data

    @property
    def display_name(self) -> str:
        return translate_field(self.name, self.name_en)

    @property
    def display_description(self) -> str:
        return translate_field(self.description, self.description_en)

    def source_kinds(self) -> list[str]:
        return [kind for kind in SOURCE_KINDS if self.sources.get(kind)]

    def search_text(self) -> str:
        """Durchsucht wird immer beides – wer »Sicherheit« tippt, findet auch
        einen Eintrag, dessen englische Beschreibung gerade angezeigt wird."""
        packages = " ".join(
            " ".join(str(v) for v in src.values() if isinstance(v, str))
            for src in self.sources.values()
        )
        return " ".join(
            (
                self.name,
                self.name_en,
                self.id,
                self.description,
                self.description_en,
                packages,
            )
        ).lower()


@dataclass
class Catalog:
    categories: list[Category] = field(default_factory=list)
    apps: list[App] = field(default_factory=list)
    hidden: set[str] = field(default_factory=set)

    def by_id(self, app_id: str) -> App | None:
        return next((a for a in self.apps if a.id == app_id), None)

    def category(self, cat_id: str) -> Category | None:
        return next((c for c in self.categories if c.id == cat_id), None)

    def category_name(self, cat_id: str) -> str:
        cat = self.category(cat_id)
        return cat.display_name if cat else cat_id.capitalize()

    def apps_in(self, cat_id: str) -> list[App]:
        return [a for a in self.apps if a.category == cat_id]

    def used_categories(self) -> list[Category]:
        """Kategorien in Katalogreihenfolge, aber nur solche mit Programmen."""
        used = {a.category for a in self.apps}
        known = [c for c in self.categories if c.id in used]
        extra = sorted(used - {c.id for c in self.categories})
        return known + [Category(id=c, name=c.capitalize()) for c in extra]

    # -- Bearbeiten -------------------------------------------------------

    def upsert(self, app: App) -> None:
        """Fügt ein Programm hinzu oder ersetzt das gleichnamige."""
        self.hidden.discard(app.id)
        for index, existing in enumerate(self.apps):
            if existing.id == app.id:
                self.apps[index] = app
                return
        self.apps.append(app)

    def remove(self, app_id: str) -> None:
        """Entfernt ein Programm aus der Liste (mitgelieferte werden versteckt)."""
        app = self.by_id(app_id)
        if app is None:
            return
        self.apps = [a for a in self.apps if a.id != app_id]
        if app.builtin:
            self.hidden.add(app_id)


def _read_json(path: Path) -> dict:
    try:
        with path.open(encoding="utf-8") as handle:
            data = json.load(handle)
    except FileNotFoundError:
        return {}
    except (OSError, json.JSONDecodeError) as exc:
        raise CatalogError(f"{path} konnte nicht gelesen werden: {exc}") from exc
    return data if isinstance(data, dict) else {}


class CatalogError(RuntimeError):
    """Der Katalog ist unlesbar oder fehlerhaft aufgebaut."""


def load(user_path: Path | None = None) -> Catalog:
    """Führt mitgelieferten und persönlichen Katalog zusammen."""
    user_path = user_path or user_catalog_path()

    builtin = _read_json(BUILTIN_CATALOG)
    personal = _read_json(user_path)

    categories = [Category.from_dict(c) for c in builtin.get("categories", [])]
    known_cats = {c.id for c in categories}
    for raw in personal.get("categories", []):
        cat = Category.from_dict(raw)
        if cat.id in known_cats:
            categories = [cat if c.id == cat.id else c for c in categories]
        else:
            categories.append(cat)
            known_cats.add(cat.id)

    hidden = {str(h) for h in personal.get("hidden", [])}

    catalog = Catalog(categories=categories, hidden=hidden)
    for raw in builtin.get("apps", []):
        app = App.from_dict(raw, builtin=True)
        if app.id not in hidden:
            catalog.apps.append(app)
    for raw in personal.get("apps", []):
        app = App.from_dict(raw, builtin=False)
        catalog.upsert(app)

    return catalog


def save(catalog: Catalog, user_path: Path | None = None) -> Path:
    """Schreibt ausschließlich die persönlichen Abweichungen."""
    user_path = user_path or user_catalog_path()
    user_path.parent.mkdir(parents=True, exist_ok=True)

    builtin = _read_json(BUILTIN_CATALOG)
    builtin_apps = {str(a.get("id")): a for a in builtin.get("apps", [])}
    builtin_cats = {str(c.get("id")): c for c in builtin.get("categories", [])}

    apps = []
    for app in catalog.apps:
        data = app.to_dict()
        # Unveränderte Mitlieferungen müssen nicht dupliziert werden.
        if app.builtin and builtin_apps.get(app.id) == data:
            continue
        apps.append(data)

    categories = [
        c.to_dict() for c in catalog.categories if builtin_cats.get(c.id) != c.to_dict()
    ]

    payload = {
        "version": CATALOG_VERSION,
        "categories": categories,
        "hidden": sorted(catalog.hidden),
        "apps": apps,
    }

    tmp = user_path.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    tmp.replace(user_path)
    return user_path


# -- Auswahl als eigenständige Datei ---------------------------------------


@dataclass
class ImportResult:
    """Was beim Einlesen einer Auswahldatei herauskam."""

    selected: set[str] = field(default_factory=set)
    #: Eigene Programmdefinitionen, die der Katalog noch nicht kannte.
    added_apps: list[str] = field(default_factory=list)
    #: Kennungen ohne Definition – weder im Katalog noch in der Datei.
    unknown: list[str] = field(default_factory=list)
    name: str = ""


def export_selection(
    path: Path, catalog: Catalog, selected: set[str], name: str = ""
) -> Path:
    """Schreibt eine Auswahl in eine eigenständige, weitergebbare Datei.

    Mitgeschrieben werden nicht nur die Kennungen, sondern auch die vollständige
    Definition aller selbst angelegten Programme. Nur so lässt sich die Datei auf
    einem frischen Rechner einlesen, der diese Einträge noch nie gesehen hat.
    Die Paketnamen bleiben dabei für alle Systeme erhalten, weshalb dieselbe
    Datei auf Debian wie auf Arch funktioniert.
    """
    apps = [catalog.by_id(app_id) for app_id in sorted(selected)]
    apps = [app for app in apps if app is not None]

    custom = [app for app in apps if not app.builtin]
    needed_categories = {app.category for app in custom}
    categories = [
        c.to_dict() for c in catalog.categories if c.id in needed_categories
    ]

    payload = {
        "format": SELECTION_FORMAT,
        "version": SELECTION_VERSION,
        "created": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "name": name,
        "apps": [app.id for app in apps],
        "custom_apps": [app.to_dict() for app in custom],
        "categories": categories,
    }

    path = Path(path)
    if path.suffix.lower() != ".json":
        path = path.with_suffix(".json")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    return path


def import_selection(path: Path, catalog: Catalog) -> ImportResult:
    """Liest eine Auswahldatei ein und ergänzt fehlende eigene Programme.

    Der Katalog wird dabei verändert; das Speichern bleibt dem Aufrufer
    überlassen.
    """
    data = _read_json(Path(path))
    if data.get("format") != SELECTION_FORMAT:
        raise CatalogError(
            "Diese Datei enthält keine SilentInstaller-Auswahl."
        )

    result = ImportResult(name=str(data.get("name", "")))

    for raw in data.get("categories", []):
        category = Category.from_dict(raw)
        if catalog.category(category.id) is None:
            catalog.categories.append(category)

    for raw in data.get("custom_apps", []):
        try:
            app = App.from_dict(raw, builtin=False)
        except (KeyError, TypeError):
            continue
        if catalog.by_id(app.id) is None:
            catalog.upsert(app)
            result.added_apps.append(app.id)

    builtin_apps = {
        str(raw.get("id")): raw for raw in _read_json(BUILTIN_CATALOG).get("apps", [])
    }

    for app_id in data.get("apps", []):
        app_id = str(app_id)
        if catalog.by_id(app_id) is not None:
            result.selected.add(app_id)
        elif app_id in catalog.hidden and app_id in builtin_apps:
            # Auf diesem Rechner ausgeblendet, in der Auswahl aber gewünscht.
            catalog.upsert(App.from_dict(builtin_apps[app_id], builtin=True))
            result.selected.add(app_id)
            result.added_apps.append(app_id)
        else:
            result.unknown.append(app_id)

    return result


# -- Profile als einzelne Dateien -----------------------------------------


@dataclass
class Profile:
    """Eine gespeicherte Auswahl im Profilverzeichnis."""

    name: str
    path: Path
    apps: list[str] = field(default_factory=list)
    created: str = ""

    @property
    def count(self) -> int:
        return len(self.apps)


def list_profiles() -> list[Profile]:
    """Liest alle Profildateien. Unlesbare Dateien werden übergangen.

    Da eine Profildatei dasselbe Format hat wie eine ausgelagerte Auswahl,
    genügt es, eine exportierte Datei hierher zu kopieren – sie erscheint
    beim nächsten Start als Profil.
    """
    verzeichnis = profile_dir()
    if not verzeichnis.is_dir():
        return []

    profile: list[Profile] = []
    for datei in sorted(verzeichnis.glob("*.json")):
        try:
            data = _read_json(datei)
        except CatalogError:
            continue
        if data.get("format") != SELECTION_FORMAT:
            continue
        profile.append(
            Profile(
                name=str(data.get("name") or datei.stem),
                path=datei,
                apps=[str(a) for a in data.get("apps", [])],
                created=str(data.get("created", "")),
            )
        )
    return sorted(profile, key=lambda p: p.name.lower())


def save_profile(name: str, catalog: Catalog, selected: set[str]) -> Path:
    """Legt ein Profil als eigene Datei ab.

    Ein vorhandenes Profil gleichen Namens wird ersetzt. Ergeben zwei
    verschiedene Namen denselben Dateinamen, bekommt der zweite eine Ziffer.
    """
    verzeichnis = profile_dir()
    verzeichnis.mkdir(parents=True, exist_ok=True)

    grundname = slugify(name)
    ziel = verzeichnis / f"{grundname}.json"
    zaehler = 2
    while ziel.exists():
        vorhanden = _read_json(ziel)
        if vorhanden.get("name", ziel.stem) == name:
            break  # dasselbe Profil – wird überschrieben
        ziel = verzeichnis / f"{grundname}-{zaehler}.json"
        zaehler += 1

    return export_selection(ziel, catalog, selected, name=name)


def delete_profile(profile: Profile) -> bool:
    try:
        profile.path.unlink()
    except OSError:
        return False
    return True


def migrate_profiles(settings: dict, catalog: Catalog) -> list[str]:
    """Holt Profile aus einer älteren settings.json in das Profilverzeichnis.

    Bis Fassung 1.2.0 steckten alle Profile im Schlüssel ``profiles`` der
    Einstellungsdatei. Sie werden einmalig in eigene Dateien überführt.
    """
    alt = settings.pop("profiles", None)
    if not isinstance(alt, dict) or not alt:
        return []

    umgezogen = []
    for name, ids in alt.items():
        if not isinstance(ids, list):
            continue
        try:
            save_profile(str(name), catalog, {str(i) for i in ids})
        except OSError:
            continue
        umgezogen.append(str(name))

    save_settings(settings)
    return umgezogen


# -- Einstellungen ---------------------------------------------------------

DEFAULT_SETTINGS = {
    "prefer_flatpak": False,
    "purge_on_remove": False,
    "language": "auto",
    "theme": "auto",
}


def load_settings() -> dict:
    data = dict(DEFAULT_SETTINGS)
    try:
        data.update(_read_json(settings_path()))
    except CatalogError:
        pass
    return data


def save_settings(settings: dict) -> None:
    path = settings_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".json.tmp")
    with tmp.open("w", encoding="utf-8") as handle:
        json.dump(settings, handle, indent=2, ensure_ascii=False)
        handle.write("\n")
    tmp.replace(path)
