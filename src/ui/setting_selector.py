"""Reusable component for interactive setting selection and editing."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Callable, Union

from prompt_toolkit import HTML
from prompt_toolkit.application import Application
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.keys import Keys
from prompt_toolkit.layout import Layout, HSplit, Window
from prompt_toolkit.layout.dimension import D
from prompt_toolkit.layout.controls import FormattedTextControl

from ui.prompt_utils import TOOLBAR_STYLE


@dataclass
class SettingOption:
    """A single setting option with validation support."""
    key: str                          # Config key
    text: str                         # Display label
    value: Any                        # Current value
    options: List[Dict[str, Any]] = None  # For enum-style: {"value": x, "text": y}
    input_type: str = "select"        # "select", "text", "number", "boolean", "float"
    description: str = ""
    min_val: Union[int, float] = None
    max_val: Union[int, float] = None
    step: Union[int, float] = None
    validate_fn: Callable[[Any], bool] = None  # Custom validator

    def __post_init__(self):
        if self.options is None:
            self.options = []


@dataclass
class SettingCategory:
    """A category containing related settings."""
    title: str
    icon: str = ">"
    settings: List[SettingOption] = field(default_factory=list)


class SettingSelector:
    """Interactive setting selector with live value editing.

    Boolean settings display one per line with green ON / red OFF.
    Enter toggles booleans directly. A Save option sits at the bottom.
    Non-boolean types still support inline editing.
    """

    _CURSOR = "  "
    _ON_SAVE = False  # Sentinel: cursor is on the Save button

    def __init__(
        self,
        categories: List[SettingCategory],
        title: str = "Settings",
        on_change: Callable[[str, str, Any], None] = None  # Called on value change
    ):
        """Initialize the setting selector.

        Args:
            categories: List of SettingCategory objects with settings
            title: Panel title
            on_change: Callback(key, action, value) when setting changes
        """
        self.categories = categories
        self.title = title
        self.on_change = on_change

        self.current_cat_idx = 0
        self.current_setting_idx = 0
        self._on_save = self._ON_SAVE
        self.editing_value = False
        self.input_buffer = ""
        self._initial_values: Dict[str, Any] = {
            s.key: s.value
            for cat in categories
            for s in cat.settings
        }

    def _get_current_setting(self) -> Optional[SettingOption]:
        """Get the currently selected setting."""
        if 0 <= self.current_cat_idx < len(self.categories):
            cat = self.categories[self.current_cat_idx]
            if 0 <= self.current_setting_idx < len(cat.settings):
                return cat.settings[self.current_setting_idx]
        return None

    def _format_value(self, setting: SettingOption) -> str:
        """Format a setting value for display."""
        if setting.input_type == "boolean":
            return "ON" if setting.value else "OFF"
        elif setting.input_type == "select" and setting.options:
            for opt in setting.options:
                if opt.get("value") == setting.value:
                    return opt.get("text", str(setting.value))
        elif isinstance(setting.value, bool):
            return "Yes" if setting.value else "No"
        elif isinstance(setting.value, float) and setting.step and setting.step < 1:
            return f"{setting.value:.2f}"
        return str(setting.value)

    def _total_setting_rows(self) -> int:
        """Total navigable rows across all categories."""
        return sum(len(cat.settings) for cat in self.categories)

    def _is_boolean_setting(self, setting: Optional[SettingOption]) -> bool:
        """Check if a setting is a boolean toggle."""
        return setting is not None and setting.input_type == "boolean"

    def _get_display_text(self) -> HTML:
        """Build the display HTML with one-line boolean toggles."""
        lines = []

        # Title (only if provided)
        if self.title:
            lines.append(f"<b>{self.title}</b>")
            lines.append("")

        # Show category headers only when there are multiple categories
        show_headers = len(self.categories) > 1

        for c_idx, cat in enumerate(self.categories):
            is_active_cat = c_idx == self.current_cat_idx

            if show_headers:
                lines.append(f"  <b><style fg='cyan'>{cat.icon} {cat.title}</style></b>")

            for s_idx, setting in enumerate(cat.settings):
                is_selected = (is_active_cat
                               and s_idx == self.current_setting_idx
                               and not self._on_save)
                is_editing = is_selected and self.editing_value

                if setting.input_type == "boolean":
                    is_on = bool(setting.value)
                    tag = "ON" if is_on else "OFF"
                    label = setting.text

                    if is_selected:
                        color = "green" if is_on else "red"
                        lines.append(
                            f"> <style fg='{color}' bold='true'>{tag}</style>"
                            f"  <b>{label}</b>"
                        )
                    else:
                        lines.append(
                            f"  <style fg='gray'>{tag}</style>"
                            f"  {label}"
                        )

                elif is_editing and setting.input_type in ("number", "float"):
                    label = setting.text
                    lines.append(
                        f"> <b>{label}:</b>"
                        f"  <style fg='yellow'>{self.input_buffer}</style>"
                    )
                elif is_editing and setting.input_type == "text":
                    label = setting.text
                    lines.append(
                        f"> <b>{label}:</b>"
                        f"  <style fg='yellow'>{self.input_buffer}</style>"
                    )
                elif is_editing and setting.input_type == "select" and setting.options:
                    label = setting.text
                    lines.append(
                        f"> <b>{label}:</b>"
                        f"  <style fg='yellow'>{self._format_value(setting)}</style>"
                    )
                else:
                    label = setting.text
                    val = self._format_value(setting)
                    if is_selected:
                        lines.append(
                            f"> <b>{label}:</b>"
                            f"  <style fg='cyan'>{val}</style>"
                        )
                    else:
                        lines.append(
                            f"  {label}:  "
                            f"<style fg='gray'>{val}</style>"
                        )

        # Separator + Save button
        lines.append("")
        if self._on_save:
            lines.append("> <b>[ Save ]</b>")
        else:
            lines.append("  [ Save ]")

        # Help text
        lines.append("")
        setting = self._get_current_setting()
        if self._on_save:
            lines.append("<style fg='gray'>Enter to save changes, Esc to cancel</style>")
        elif self.editing_value:
            if setting and setting.input_type in ("number", "float", "text"):
                lines.append("<style fg='gray'>Type value, Enter to confirm, Esc to cancel</style>")
            elif setting and setting.input_type == "select":
                lines.append("<style fg='gray'>↑↓ Change, Enter to confirm, Esc to cancel</style>")
        else:
            if setting and self._is_boolean_setting(setting):
                lines.append("<style fg='gray'>↑↓ Navigate, Enter to toggle, Esc to cancel</style>")
            elif setting:
                lines.append("<style fg='gray'>↑↓ Navigate, Enter to edit, Esc to cancel</style>")
            else:
                lines.append("<style fg='gray'>↑↓ Navigate, Esc to cancel</style>")

        return HTML("\n".join(lines))

    def _validate_input(self, setting: SettingOption, value: str) -> bool:
        """Validate user input for a setting."""
        if setting.validate_fn:
            try:
                if setting.input_type == "number":
                    return setting.validate_fn(int(value))
                elif setting.input_type == "float":
                    return setting.validate_fn(float(value))
                return setting.validate_fn(value)
            except (ValueError, TypeError):
                return False

        # Built-in validation
        if setting.input_type == "number":
            try:
                int_val = int(value)
                if setting.min_val is not None and int_val < setting.min_val:
                    return False
                if setting.max_val is not None and int_val > setting.max_val:
                    return False
                if setting.step is not None and setting.step > 0:
                    if (int_val - setting.min_val if setting.min_val is not None else int_val) % setting.step != 0:
                        return False
                return True
            except ValueError:
                return False
        elif setting.input_type == "float":
            try:
                float_val = float(value)
                if setting.min_val is not None and float_val < setting.min_val:
                    return False
                if setting.max_val is not None and float_val > setting.max_val:
                    return False
                if setting.step is not None and setting.step > 0:
                    if (float_val - setting.min_val if setting.min_val is not None else float_val) % setting.step != 0:
                        return False
                return True
            except ValueError:
                return False

        return len(value) > 0

    def _apply_change(self, key: str, new_value: Any) -> None:
        """Apply a setting change."""
        # Find and update the setting
        for cat in self.categories:
            for setting in cat.settings:
                if setting.key == key:
                    old_value = setting.value
                    setting.value = new_value
                    if self.on_change and old_value != new_value:
                        self.on_change(key, "change", new_value)
                    return

    def _navigate_down(self):
        """Move selection down one row, wrapping into the Save button."""
        if self._on_save:
            return  # Already at bottom
        cat = self.categories[self.current_cat_idx]
        if self.current_setting_idx < len(cat.settings) - 1:
            self.current_setting_idx += 1
        elif self.current_cat_idx < len(self.categories) - 1:
            self.current_cat_idx += 1
            self.current_setting_idx = 0
        else:
            # Past last setting -> move to Save button
            self._on_save = True

    def _navigate_up(self):
        """Move selection up one row, off the Save button if needed."""
        if self._on_save:
            self._on_save = False
            return
        if self.current_setting_idx > 0:
            self.current_setting_idx -= 1
        elif self.current_cat_idx > 0:
            self.current_cat_idx -= 1
            self.current_setting_idx = len(self.categories[self.current_cat_idx].settings) - 1

    def _save(self, event):
        """Exit with changes (or empty dict if nothing changed)."""
        changes = {}
        for cat in self.categories:
            for setting in cat.settings:
                if setting.value != self._initial_values.get(setting.key):
                    changes[setting.key] = setting.value
        event.app.exit(result=changes if changes else {})

    def run(self) -> Optional[Dict[str, Any]]:
        """Display and run the setting selector.

        Returns:
            Dict of {key: new_value} for changed settings, or None if canceled
        """
        bindings = KeyBindings()

        def invalidate():
            if hasattr(invalidate, 'app'):
                invalidate.app.invalidate()

        @bindings.add(Keys.Up)
        def move_up(event):
            if self.editing_value:
                setting = self._get_current_setting()
                if setting and setting.input_type == "select" and setting.options:
                    current_idx = next((i for i, o in enumerate(setting.options) if o.get("value") == setting.value), 0)
                    new_idx = max(0, current_idx - 1)
                    self._apply_change(setting.key, setting.options[new_idx].get("value"))
                invalidate()
                return
            self._navigate_up()
            invalidate()

        @bindings.add(Keys.Down)
        def move_down(event):
            if self.editing_value:
                setting = self._get_current_setting()
                if setting and setting.input_type == "select" and setting.options:
                    current_idx = next((i for i, o in enumerate(setting.options) if o.get("value") == setting.value), 0)
                    new_idx = min(len(setting.options) - 1, current_idx + 1)
                    self._apply_change(setting.key, setting.options[new_idx].get("value"))
                invalidate()
                return
            self._navigate_down()
            invalidate()

        @bindings.add(Keys.Enter)
        def confirm(event):
            # On the Save button -> commit
            if self._on_save:
                self._save(event)
                return

            setting = self._get_current_setting()
            if not setting:
                return

            # Boolean: toggle directly
            if self._is_boolean_setting(setting):
                self._apply_change(setting.key, not setting.value)
                invalidate()
                return

            if self.editing_value:
                if setting.input_type in ("text", "number", "float"):
                    if self._validate_input(setting, self.input_buffer):
                        if setting.input_type == "number":
                            new_val = int(self.input_buffer)
                        elif setting.input_type == "float":
                            new_val = float(self.input_buffer)
                        else:
                            new_val = self.input_buffer
                        self._apply_change(setting.key, new_val)
                    self.editing_value = False
                    self.input_buffer = ""
                else:
                    self.editing_value = False
                invalidate()
            else:
                # Start editing for non-boolean types
                if setting.input_type not in ("boolean", "select"):
                    self.editing_value = True
                    self.input_buffer = str(setting.value)
                invalidate()

        @bindings.add(Keys.Escape)
        def close(event):
            event.app.exit(result=None)

        @bindings.add(Keys.Right)
        def enter_edit(event):
            setting = self._get_current_setting()
            if setting and not self.editing_value and setting.input_type not in ("boolean",):
                self.editing_value = True
                if setting.input_type in ("text", "number", "float"):
                    self.input_buffer = str(setting.value)
                invalidate()

        @bindings.add(Keys.Left)
        def exit_edit(event):
            if self.editing_value:
                self.editing_value = False
                self.input_buffer = ""
                invalidate()

        # Character input for text/number editing
        @bindings.add(Keys.Any)
        def handle_char(event):
            if not self.editing_value:
                return
            setting = self._get_current_setting()
            if setting and setting.input_type in ("text", "number", "float"):
                data = event.data
                if len(data) == 1 and ord(data) >= 32:
                    if setting.input_type == "number":
                        if data.isdigit() or (data == '-' and not self.input_buffer):
                            self.input_buffer += data
                    elif setting.input_type == "float":
                        if data.isdigit() or (data == '.' and '.' not in self.input_buffer) or (data == '-' and not self.input_buffer):
                            self.input_buffer += data
                    else:
                        self.input_buffer += data
                    invalidate()

        @bindings.add(Keys.Backspace)
        def handle_backspace(event):
            if self.editing_value and self.input_buffer:
                self.input_buffer = self.input_buffer[:-1]
                invalidate()

        @bindings.add(Keys.Delete)
        def handle_delete(event):
            if self.editing_value and self.input_buffer:
                self.input_buffer = self.input_buffer[:-1]
                invalidate()

        # Layout
        def get_content():
            return self._get_display_text()

        content = FormattedTextControl(get_content)
        container = HSplit([
            Window(content=content, height=D(min=1), width=D(min=1), wrap_lines=True),
        ])

        application = Application(
            layout=Layout(container),
            key_bindings=bindings,
            full_screen=False,
            mouse_support=False,
            cursor=None,
            style=TOOLBAR_STYLE,
        )

        invalidate.app = application
        result = application.run()

        # None = cancelled, {} = saved with no changes, {...} = saved with changes
        if result is None:
            return None
        return result if result else None


# Convenience function for quick usage
def select_setting(
    question: str,
    options: List[Dict[str, Any]],
    current_value: Any = None,
    on_change: Callable[[str, Any], None] = None
) -> Optional[Any]:
    """Quick single-setting selector.

    Args:
        question: Setting display name
        options: List of {value, text, description?}
        current_value: Currently selected value
        on_change: Callback(value) when value changes

    Returns:
        New selected value or None if canceled
    """
    setting = SettingOption(
        key="_single",
        text=question,
        value=current_value,
        input_type="select",
        options=[{"value": o.get("value"), "text": o.get("text"), "description": o.get("description")} for o in options]
    )

    def wrapped_on_change(key, action, value):
        if on_change:
            on_change(value)

    selector = SettingSelector(
        categories=[SettingCategory(title="Settings", settings=[setting])],
        title=question,
        on_change=wrapped_on_change
    )

    result = selector.run()
    if result and "_single" in result:
        return result["_single"]
    return None
