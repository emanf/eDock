import sys
from core.paths import setup_pycache_dir
setup_pycache_dir()

from PySide6.QtWidgets import QApplication
from core.config.config_manager import ConfigManager
from core.app.app_loader import AppLoader
from core.app.app_context import AppContext
from core.ui.dock.dock_window import DockWindow

def main():
    app = QApplication(sys.argv)
    app.setQuitOnLastWindowClosed(False)

    config_manager = ConfigManager()
    app_context = AppContext(config_manager=config_manager)
    app_loader = AppLoader(app_context=app_context, config_manager=config_manager)

    dock = DockWindow(config_manager=config_manager, app_loader=app_loader)
    dock.show()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
