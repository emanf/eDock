from pathlib import Path
from typing import Optional
from PySide6.QtGui import QPixmap
from PySide6.QtSvg import QSvgRenderer
from core.rendering.material_icons import MaterialIcons

class IconLoader:
    @staticmethod
    def resolve_path(value: str, app_dir: Optional[Path]) -> Optional[Path]:
        text = str(value or "").strip()
        if not text:
            if app_dir:
                for name in ["app.svg", "app.png", "icon.svg", "icon.png"]:
                    p = app_dir / name
                    if p.exists(): return p
            return None
        
        path = Path(text)
        if path.is_absolute() and path.exists(): return path
        if path.exists(): return path
        
        if app_dir:
            for sub in [app_dir, app_dir / "icons", app_dir / "assets"]:
                p = sub / text
                if p.exists(): return p
        return None

    @staticmethod
    def load(icon_value: str, app_dir: Optional[Path]):
        value = str(icon_value or "").strip()
        if value.startswith("m:"):
            return None, None, MaterialIcons.glyph(value, "")
        
        path = IconLoader.resolve_path(value, app_dir)
        if not path:
            return None, None, ""
            
        if path.suffix.lower() == ".svg":
            renderer = QSvgRenderer(str(path))
            if renderer.isValid():
                return None, renderer, ""
        else:
            pixmap = QPixmap(str(path))
            if not pixmap.isNull():
                return pixmap, None, ""
        
        return None, None, ""
