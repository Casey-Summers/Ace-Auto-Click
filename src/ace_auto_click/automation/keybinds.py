from __future__ import annotations

from dataclasses import dataclass

from pynput import keyboard, mouse


MODIFIER_ORDER = {"ctrl": 0, "alt": 1, "shift": 2}

MODIFIER_ALIASES: dict[str, str] = {
    "ctrl": "ctrl",
    "key.ctrl": "ctrl",
    "key.ctrl_l": "ctrl",
    "key.ctrl_r": "ctrl",
    "shift": "shift",
    "key.shift": "shift",
    "key.shift_l": "shift",
    "key.shift_r": "shift",
    "alt": "alt",
    "key.alt": "alt",
    "key.alt_l": "alt",
    "key.alt_r": "alt",
    "key.alt_gr": "alt",
}

SIDE_BUTTON_ALIASES: dict[str, str] = {
    "btnm4": "x1",
    "mouse4": "x1",
    "button.x1": "x1",
    "x1": "x1",
    "btnm5": "x2",
    "mouse5": "x2",
    "button.x2": "x2",
    "x2": "x2",
}

SHIFTED_SYMBOL_BASES: dict[str, str] = {
    "!": "1",
    "@": "2",
    "#": "3",
    "$": "4",
    "%": "5",
    "^": "6",
    "&": "7",
    "*": "8",
    "(": "9",
    ")": "0",
    "_": "-",
    "+": "=",
    "{": "[",
    "}": "]",
    "|": "\\",
    ":": ";",
    '"': "'",
    "<": ",",
    ">": ".",
    "?": "/",
    "~": "`",
}


def normalize_modifier_key(value: str) -> str | None:
    return MODIFIER_ALIASES.get(value.lower())


def normalize_side_button(value: object) -> str | None:
    normalized = str(value).lower().replace(" ", "")
    return SIDE_BUTTON_ALIASES.get(normalized)


def control_char_to_key(char: str) -> str | None:
    if len(char) != 1:
        return None
    codepoint = ord(char)
    if 1 <= codepoint <= 26:
        return chr(codepoint + 96)
    return None


def canonical_key_name(key: keyboard.Key | keyboard.KeyCode) -> str | None:
    char = getattr(key, "char", None)
    if char:
        control_key = control_char_to_key(str(char))
        if control_key:
            return control_key
        printable = str(char)
        if printable in SHIFTED_SYMBOL_BASES:
            return SHIFTED_SYMBOL_BASES[printable]
        if printable.isprintable():
            return printable.lower()
        return None
    value = str(key).lower()
    if value.startswith("key."):
        return value.removeprefix("key.")
    return None


def normalize_keybind_components(
    key: keyboard.Key | keyboard.KeyCode,
    modifiers: set[str],
) -> tuple[set[str], str] | None:
    char = getattr(key, "char", None)
    if char:
        printable = str(char)
        if printable in SHIFTED_SYMBOL_BASES:
            return set(modifiers) | {"shift"}, SHIFTED_SYMBOL_BASES[printable]
        control_key = control_char_to_key(printable)
        if control_key:
            return set(modifiers) | {"ctrl"}, control_key
        if printable.isprintable():
            return set(modifiers), printable.lower()
        return None

    base = canonical_key_name(key)
    if not base:
        return None
    return set(modifiers), base


def parse_keybind_text(text: str) -> tuple[list[keyboard.Key], str | keyboard.Key]:
    parts = [part.strip().lower() for part in (text or "").split("+") if part.strip()]
    mods: list[keyboard.Key] = []
    base: str | keyboard.Key = "space"
    for part in parts:
        modifier = normalize_modifier_key(part)
        if modifier == "ctrl":
            mods.append(keyboard.Key.ctrl)
            continue
        if modifier == "shift":
            mods.append(keyboard.Key.shift)
            continue
        if modifier == "alt":
            mods.append(keyboard.Key.alt)
            continue
        if part.startswith("key."):
            base = getattr(keyboard.Key, part.split("key.", 1)[1], part)
            continue
        if part in SHIFTED_SYMBOL_BASES:
            base = SHIFTED_SYMBOL_BASES[part]
            if keyboard.Key.shift not in mods:
                mods.append(keyboard.Key.shift)
            continue
        base = part
    return mods, base


def format_keybind(modifiers: set[str], base: str) -> str:
    ordered_mods = sorted((modifier for modifier in modifiers if modifier), key=lambda item: MODIFIER_ORDER.get(item, 99))
    return "+".join([*ordered_mods, base]) if ordered_mods else base


def mouse_button_name(button: object) -> str | None:
    return normalize_side_button(button)


def resolve_mouse_button_attr(value: str) -> str | None:
    normalized = normalize_side_button(value)
    return normalized
