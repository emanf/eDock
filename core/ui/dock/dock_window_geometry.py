from PySide6.QtCore import QPoint, QPropertyAnimation
from PySide6.QtWidgets import QApplication


def current_screen_geometry(window):
    screen = window.screen()
    if screen is None:
        screen = QApplication.screenAt(window.pos())
    if screen is None:
        screen = QApplication.primaryScreen()
    if screen is None:
        return None
    return screen.geometry()


def max_dock_length(window):
    geom = window.current_screen_geometry()
    if not geom:
        return None
    if window.dock_position in ("top", "bottom"):
        return geom.width()
    return geom.height()


def dock_button_count(window):
    buttons = getattr(window, "buttons", [])

    if buttons:
        visible_buttons = [
            button for button in buttons if button is not None and not button.isHidden()
        ]
        return max(1, len(visible_buttons))

    loaded_apps = getattr(window, "loaded_apps", [])
    return max(1, len(loaded_apps))


def dock_size_for_icon_size(window, icon_size):
    count = dock_button_count(window)

    if window.dock_position in ("top", "bottom"):
        width = (
            window.inner_padding * 2
            + count * (icon_size + 8)
            + max(0, count - 1) * window.spacing
        )
        height = window.inner_padding * 2 + icon_size + 8
    else:
        width = window.inner_padding * 2 + icon_size + 8
        height = (
            window.inner_padding * 2
            + count * (icon_size + 8)
            + max(0, count - 1) * window.spacing
        )

    return width, height


def update_effective_icon_size(window):
    count = dock_button_count(window)
    window.effective_icon_size = window.icon_size
    window.scroll_enabled = False

    max_length = window.max_dock_length()
    if not max_length:
        return

    natural_width, natural_height = window.dock_size_for_icon_size(window.icon_size)
    natural_length = (
        natural_width if window.dock_position in ("top", "bottom") else natural_height
    )

    if natural_length <= max_length:
        return

    if window.resize_mode == "scroll-able":
        window.scroll_enabled = True
        return

    available_for_buttons = (
        max_length - window.inner_padding * 2 - max(0, count - 1) * window.spacing
    )
    fitted_size = int(available_for_buttons / count) - 8

    fitted_size = min(fitted_size, window.button_max_size)
    fitted_size = max(fitted_size, window.button_min_size)

    window.effective_icon_size = fitted_size

    fitted_width, fitted_height = window.dock_size_for_icon_size(
        window.effective_icon_size
    )
    fitted_length = (
        fitted_width if window.dock_position in ("top", "bottom") else fitted_height
    )

    if fitted_length > max_length:
        window.scroll_enabled = True


def apply_button_sizes(window):
    for button in window.buttons:
        button.base_size = int(window.effective_icon_size)
        button.hover_size = button.base_size + 4
        button.widget_size = button.hover_size + 8
        button.setFixedSize(button.widget_size, button.widget_size)
        button.update()


def update_dock_geometry(window):
    window.update_effective_icon_size()
    window.apply_button_sizes()

    content_width, content_height = window.dock_size_for_icon_size(
        window.effective_icon_size
    )
    width = content_width
    height = content_height

    geom = window.current_screen_geometry()

    if geom:
        if window.dock_position in ("top", "bottom"):
            if width > geom.width():
                width = geom.width()
                window.scroll_enabled = True
        else:
            if height > geom.height():
                height = geom.height()
                window.scroll_enabled = True

    width = max(width, window.min_dock_width)
    height = max(height, window.min_dock_height)

    if window.dock_position in ("top", "bottom"):
        window.content_widget.setFixedSize(max(content_width, width), height)
    else:
        window.content_widget.setFixedSize(width, max(content_height, height))

    window.scroll_area.setFixedSize(width, height)
    window.scroll_area.setEnabled(True)
    window.setFixedSize(width, height)

    window.reposition_dock()


def reposition_dock(window):
    geom = window.current_screen_geometry()
    if not geom:
        return

    edge_guard = int(getattr(window, "edge_guard", 4))

    if window.dock_position == "left":
        y = geom.y() + (geom.height() - window.height()) // 2

        window.shown_pos = QPoint(geom.x() - edge_guard, y)

        window.hidden_pos = QPoint(geom.x() - window.width() + window.peek_width, y)

    elif window.dock_position == "right":
        y = geom.y() + (geom.height() - window.height()) // 2

        window.shown_pos = QPoint(
            geom.x() + geom.width() - window.width() + edge_guard, y
        )

        window.hidden_pos = QPoint(geom.x() + geom.width() - window.peek_width, y)

    elif window.dock_position == "top":
        x = geom.x() + (geom.width() - window.width()) // 2

        window.shown_pos = QPoint(x, geom.y() - edge_guard)

        window.hidden_pos = QPoint(x, geom.y() - window.height() + window.peek_width)

    elif window.dock_position == "bottom":
        x = geom.x() + (geom.width() - window.width()) // 2

        window.shown_pos = QPoint(
            x, geom.y() + geom.height() - window.height() + edge_guard
        )

        window.hidden_pos = QPoint(x, geom.y() + geom.height() - window.peek_width)

    else:
        y = geom.y() + (geom.height() - window.height()) // 2

        window.shown_pos = QPoint(
            geom.x() + geom.width() - window.width() + edge_guard, y
        )

        window.hidden_pos = QPoint(geom.x() + geom.width() - window.peek_width, y)

    if window.slide_anim.state() != QPropertyAnimation.Running:
        window.move(window.shown_pos if window.hover_visible else window.hidden_pos)
