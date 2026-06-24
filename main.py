import sys
from core.paths import setup_pycache_dir

setup_pycache_dir()

from PySide6.QtWidgets import QApplication
from core.config.config_manager import ConfigManager
from core.app.app_loader import AppLoader
from core.app.app_context import AppContext
from core.ui.dock.dock_window import DockWindow
from core.ui.tray_manager import TrayManager

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)
    
    config_manager = ConfigManager()
    app_context = AppContext(config_manager=config_manager)
    app_loader = AppLoader(app_context=app_context, config_manager=config_manager)

    dock = DockWindow(config_manager=config_manager, app_loader=app_loader)
    dock.show()

    tray = TrayManager(app, dock)

    def toggle_dock(action, tray_manager):
        if dock.isVisible():
            dock.hide()
            tray_manager.update_label(action, "Show Dock")
        else:
            dock.show()
            dock.raise_()
            dock.activateWindow()
            tray_manager.update_label(action, "Hide Dock")

    tray.build_menu({
        "Hide Dock": toggle_dock,
        "-": None,
        "Quit": app.quit,
    })

    tray.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
