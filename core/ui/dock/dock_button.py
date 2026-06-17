from pathlib import Path 

from PySide6 .QtCore import Qt ,QRectF ,QSize ,QTimer 
from PySide6 .QtGui import QPainter ,QPainterPath ,QPen ,QPixmap ,QFont 
from PySide6 .QtSvg import QSvgRenderer 
from PySide6 .QtWidgets import QPushButton 

from core .rendering .material_icons import MaterialIcons 
from core .theming .theme_manager import Theme 
from core .rendering .icon_loader import IconLoader 
from core import paths 
from core .utils import functions 
from core .ui .dialogs .app_info_dialog import AppInfoDialog 
from core .ui .dialogs .shortcut_capture_dialog import ShortcutCaptureDialog 


class DockButton (QPushButton ):
    def __init__ (self ,icon_value ="",app_dir =None ,icon_size =56 ,icon_padding =20 ,on_click =None ,parent =None ):
        super ().__init__ (parent )

        self .icon_value =str (icon_value or "").strip ()
        self .app_dir =Path (app_dir )if app_dir else None 
        self .base_size =int (icon_size )
        self .icon_padding =int (icon_padding )
        self .on_click =on_click 

        self .loaded_app =None 
        self .app_instance =None 
        self .dock_window =None 
        self .shortcut_value =""
        self .shortcut =""

        self .hovered =False 
        self .pressed =False 
        self ._context_menu_open =False 

        self ._pixmap =None 
        self ._svg_renderer =None 
        self ._material_glyph =""

        self .hover_size =self .base_size +4 
        self .widget_size =self .hover_size +8 

        self .setFixedSize (QSize (self .widget_size ,self .widget_size ))
        self .setCursor (Qt .PointingHandCursor )
        self .setFlat (True )
        self .setAutoFillBackground (False )
        self .setAttribute (Qt .WA_StyledBackground ,False )
        self .setStyleSheet ("QPushButton { background: transparent; border: none; }")

        self .load_icon ()

        if callable (self .on_click ):
            self .clicked .connect (self ._handle_click )

    def _handle_click (self ,checked =False ):
        if self ._context_menu_open :
            return 
        self .on_click ()

    def set_loaded_app (self ,app_data ):
        self .loaded_app =app_data 

    def set_app_instance (self ,app_instance ):
        self .app_instance =app_instance 

    def set_dock_window (self ,dock_window ):
        self .dock_window =dock_window 
        self .update ()

    def set_shortcut (self ,shortcut_value ):
        self .shortcut_value =str (shortcut_value or "")
        self .shortcut =self .shortcut_value 

    def enterEvent (self ,event ):
        self .hovered =True 
        self .update ()
        super ().enterEvent (event )

    def leaveEvent (self ,event ):
        self .hovered =False 
        self .pressed =False 
        self .update ()
        super ().leaveEvent (event )

    def mousePressEvent (self ,event ):
        self .pressed =True 
        self .update ()
        super ().mousePressEvent (event )

    def mouseReleaseEvent (self ,event ):
        self .pressed =False 
        self .update ()
        super ().mouseReleaseEvent (event )

    def contextMenuEvent (self ,event ):
        self ._context_menu_open =True 
        from core .ui .menus .dock_button_menu import DockButtonMenu 
        DockButtonMenu .execute (self ,event .globalPos ())
        QTimer .singleShot (0 ,self ._clear_context_menu_flag )

    def _clear_context_menu_flag (self ):
        self ._context_menu_open =False 

    def _app_id (self ):
        app =self .loaded_app or {}
        if isinstance (app ,dict ):
            return str (app .get ("id")).strip ()

        return ""

    def _app_name (self ):
        app =self .loaded_app or {}
        if isinstance (app ,dict ):
            return str (app .get ("title")).strip ()

        return "{NO NAME}"

    def _app_cache_name (self ):
        app =self .loaded_app or {}
        if isinstance (app ,dict ):
            return str (app .get ("name")or app .get ("title")or app .get ("id")or "App").strip ()

        return "App"

    def _app_path_names (self ):
        names =[]
        app =self .loaded_app or {}

        if isinstance (app ,dict ):
            for key in ("name","title","id","app_id"):
                value =str (app .get (key )or "").strip ()
                if value and value not in names :
                    names .append (value )

        if self .app_dir :
            value =self .app_dir .name .strip ()
            if value and value not in names :
                names .append (value )

        return names 

    def _project_root (self ):
        return Path (paths .get_root_dir ())

    def _path_from_core_paths (self ,*parts ):
        try :
            if not parts :
                return Path (paths .get_user_dir ())

            p0 =str (parts [0 ]).lower ()

            if p0 =="cache":
                if len (parts )>=3 and str (parts [1 ]).lower ()=="apps":
                    return Path (paths .get_app_cache_dir (parts [2 ]))
                return Path (paths .get_cache_dir ())

            if p0 =="data":
                if len (parts )>=2 :
                    return Path (paths .get_app_data_dir (parts [1 ]))
                return Path (paths .get_user_data_dir ())

            return Path (paths .get_user_dir ()).joinpath (*parts )
        except Exception :
            return self ._project_root ().joinpath ("user",*parts )

    def _config_manager (self ):
        if self .dock_window is None :
            return None 
        return getattr (self .dock_window ,"config_manager",None )

    def show_app_info (self ):
        try :
            AppInfoDialog .show (self ,app_instance =self .app_instance )
        except Exception :
            try :
                AppInfoDialog .show (self )
            except Exception :
                pass 

    def open_shortcut_dialog (self ):

        app_id =self ._app_id ()
        if not app_id :
            return 

        dialog =ShortcutCaptureDialog (
        current_shortcut =self .shortcut_value ,
        parent =self 
        )

        try :
            app_id =self ._app_id ()
            dialog .set_app_id (app_id )
            cfg =self ._config_manager ()
            if cfg is not None :
                dialog .set_config_manager (cfg )
                dialog .load_shortcut (app_id ,cfg )
            else :
                dialog .load_shortcut (app_id ,None )
        except Exception :
            pass 

        if not dialog .exec ():
            return 

        new_shortcut =str (dialog .get_value ()or "")

        self .set_shortcut (new_shortcut )

        config_manager =self ._config_manager ()
        if config_manager and hasattr (config_manager ,"set_shortcut"):
            config_manager .set_shortcut (app_id ,new_shortcut )

        try :
            if isinstance (self .loaded_app ,dict ):
                self .loaded_app ["shortcut"]=new_shortcut 
        except Exception :
            pass 

        if self .dock_window is not None :
            try :
                if new_shortcut :
                    if hasattr (self .dock_window ,"register_shortcut"):
                        self .dock_window .register_shortcut (app_id ,new_shortcut ,getattr (self ,"loaded_app",None ))
                else :
                    if hasattr (self .dock_window ,"unregister_shortcut"):
                        self .dock_window .unregister_shortcut (app_id )
            except Exception :
                pass 

    def clear_shortcut (self ):
        app_id =self ._app_id ()
        if not app_id :
            return 

        self .set_shortcut ("")

        config_manager =self ._config_manager ()
        if config_manager and hasattr (config_manager ,"set_shortcut"):
            config_manager .set_shortcut (app_id ,"")


        try :
            if isinstance (self .loaded_app ,dict ):
                self .loaded_app ["shortcut"]=""
        except Exception :
            pass 


        if self .dock_window and hasattr (self .dock_window ,"unregister_shortcut"):
            try :
                self .dock_window .unregister_shortcut (app_id )
            except Exception :
                pass 

    def remove_button (self ):
        app_id =self ._app_id ()

        if not app_id :
            return 

        config_manager =self ._config_manager ()
        if config_manager is None :
            return 

        data =None 

        if hasattr (config_manager ,"config")and isinstance (config_manager .config ,dict ):
            data =config_manager .config 
        elif hasattr (config_manager ,"data")and isinstance (config_manager .data ,dict ):
            data =config_manager .data 

        if not isinstance (data ,dict ):
            return 

        if "apps"not in data or not isinstance (data .get ("apps"),dict ):
            data ["apps"]={}

        if app_id not in data ["apps"]or not isinstance (data ["apps"].get (app_id ),dict ):
            data ["apps"][app_id ]={}

        data ["apps"][app_id ]["enabled"]=False 

        if hasattr (config_manager ,"save"):
            config_manager .save ()

        if self .dock_window and hasattr (self .dock_window ,"remove_app_button"):
            self .dock_window .remove_app_button (self ,app_id )

    def clear_app_cache (self ):
        if self .app_instance and hasattr (self .app_instance ,"clear_cache"):
            try :
                self .app_instance .clear_cache ()
            except Exception :
                pass 

        for cache_dir in self .get_app_cache_dirs ():
            if cache_dir .exists ()and cache_dir .is_dir ():
                functions .clear_directory_contents (cache_dir )

    def clear_app_data (self ):
        if self .app_instance and hasattr (self .app_instance ,"clear_data"):
            try :
                self .app_instance .clear_data ()
            except Exception :
                pass 

        for data_dir in self .get_app_data_dirs ():
            if data_dir .exists ()and data_dir .is_dir ():
                functions .clear_directory_contents (data_dir )

    def _remove_readonly (self ,func ,path ,exc_info ):
        return functions .remove_readonly (func ,path ,exc_info )

    def _clear_directory_contents (self ,directory ):
        return functions .clear_directory_contents (directory )

    def open_app_data_folder (self ):
        data_dir =self .get_app_data_dir ()
        data_dir .mkdir (parents =True ,exist_ok =True )
        functions .open_folder (data_dir )

    def get_app_cache_dirs (self ):
        dirs =[]

        if self .app_instance and hasattr (self .app_instance ,"get_cache_dir"):
            try :
                path =Path (self .app_instance .get_cache_dir ())
                if path not in dirs :
                    dirs .append (path )
            except Exception :
                pass 

        for name in self ._app_path_names ():
            try :
                path =Path (paths .get_app_cache_dir (name ))
            except Exception :
                path =self ._path_from_core_paths ("cache","apps",name )
            if path not in dirs :
                dirs .append (path )

        return dirs 

    def get_app_data_dirs (self ):
        dirs =[]

        if self .app_instance and hasattr (self .app_instance ,"get_data_dir"):
            try :
                path =Path (self .app_instance .get_data_dir ())
                if path not in dirs :
                    dirs .append (path )
            except Exception :
                pass 

        for name in self ._app_path_names ():
            try :
                path =Path (paths .get_app_data_dir (name ))
            except Exception :
                path =self ._path_from_core_paths ("data",name )
            if path not in dirs :
                dirs .append (path )

        return dirs 

    def get_app_cache_dir (self ):
        app_id =self ._app_id ()
        if not app_id :
            return 

        return paths .get_app_cache_dir (app_id )

    def get_app_data_dir (self ):
        app_id =self ._app_id ()
        if not app_id :
            return 

        return paths .get_app_data_dir (app_id )

    @staticmethod 
    def _open_folder (path ):
        return functions .open_folder (path )

    def _resolve_icon_path (self ):
        try :
            return IconLoader .resolve_path (self .icon_value ,self .app_dir )
        except Exception :
            return None 

    def load_icon (self ):
        self ._pixmap =None 
        self ._svg_renderer =None 
        self ._material_glyph =""

        if not self .icon_value :
            return 

        try :
            pixmap ,renderer ,glyph =IconLoader .load (self .icon_value ,self .app_dir )
            self ._pixmap =pixmap 
            self ._svg_renderer =renderer 
            self ._material_glyph =glyph or ""
            if self ._material_glyph :
                try :
                    MaterialIcons .ensure_font ()
                except Exception :
                    pass 
        except Exception :
            self ._pixmap =None 
            self ._svg_renderer =None 
            self ._material_glyph =""

    def _button_rect (self ):
        size =self .hover_size if self .hovered else self .base_size 
        x =(self .width ()-size )/2 
        y =(self .height ()-size )/2 
        return QRectF (x ,y ,size ,size )

    def _button_colors (self ):
        button_theme =Theme .get_button (Theme .BUTTON_NORMAL )

        if self .pressed :
            bg =Theme .to_ui_qcolor (button_theme .get (Theme .Components .Button .PRESSED_COLOR ))
        elif self .hovered :
            bg =Theme .to_ui_qcolor (button_theme .get (Theme .Components .Button .HOVER_COLOR ))
        else :
            bg =Theme .to_ui_qcolor (button_theme .get (Theme .Components .Button .BACKGROUND_COLOR ))

        border =Theme .to_ui_qcolor (button_theme .get (Theme .Components .Button .BORDER_COLOR ))

        border_width =float (button_theme .get (Theme .Components .Button .BORDER_WIDTH ,1.0 ))
        border_radius =float (button_theme .get (Theme .Components .Button .BORDER_RADIUS ,18 ))

        return bg ,border ,border_width ,border_radius 

    def _icon_color (self ):
        try :
            color =Theme .get_icon_color ()
            return Theme .to_ui_qcolor (color )
        except Exception :
            return Theme .to_ui_qcolor ("#FFFFFF")

    def _draw_svg_icon (self ,painter ,target_rect ):
        if not self ._svg_renderer :
            return False 

        self ._svg_renderer .render (painter ,target_rect )
        painter .save ()
        painter .setCompositionMode (QPainter .CompositionMode_SourceIn )
        painter .fillRect (target_rect ,self ._icon_color ())
        painter .restore ()
        return True 

    def _draw_pixmap_icon (self ,painter ,target_rect ):
        if self ._pixmap is None or self ._pixmap .isNull ():
            return False 

        scaled =self ._pixmap .scaled (
        int (target_rect .width ()),
        int (target_rect .height ()),
        Qt .KeepAspectRatio ,
        Qt .SmoothTransformation 
        )

        x =target_rect .x ()+(target_rect .width ()-scaled .width ())/2 
        y =target_rect .y ()+(target_rect .height ()-scaled .height ())/2 
        painter .drawPixmap (int (x ),int (y ),scaled )
        return True 

    def _draw_material_icon (self ,painter ,target_rect ):
        if not self ._material_glyph :
            return False 

        painter .save ()
        try :
            MaterialIcons .ensure_font ()
        except Exception :
            pass 
        font =QFont (MaterialIcons .font_family ())
        font .setPixelSize (max (14 ,int (target_rect .height ()*0.9 )))
        painter .setFont (font )
        painter .setPen (self ._icon_color ())
        painter .drawText (target_rect ,Qt .AlignCenter ,self ._material_glyph )
        painter .restore ()
        return True 

    def _draw_fallback (self ,painter ,target_rect ):
        painter .save ()
        font =QFont ()
        font .setBold (True )
        font .setPixelSize (max (12 ,int (target_rect .height ()*0.5 )))
        painter .setFont (font )
        painter .setPen (self ._icon_color ())
        painter .drawText (target_rect ,Qt .AlignCenter ,"?")
        painter .restore ()

    def paintEvent (self ,event ):
        painter =QPainter (self )
        painter .setRenderHint (QPainter .Antialiasing )

        btn_rect =self ._button_rect ()
        bg ,border ,border_width ,border_radius =self ._button_colors ()

        path =QPainterPath ()
        path .addRoundedRect (btn_rect ,border_radius ,border_radius )

        painter .fillPath (path ,bg )
        painter .setPen (QPen (border ,border_width ))
        painter .drawPath (path )

        padding =int (self .icon_padding )
        icon_size =max (16 ,int (btn_rect .width ())-padding )

        icon_rect =QRectF (
        btn_rect .x ()+(btn_rect .width ()-icon_size )/2 ,
        btn_rect .y ()+(btn_rect .height ()-icon_size )/2 ,
        icon_size ,
        icon_size 
        )

        drawn =False 
        if self ._svg_renderer is not None :
            drawn =self ._draw_svg_icon (painter ,icon_rect )
        elif self ._pixmap is not None :
            drawn =self ._draw_pixmap_icon (painter ,icon_rect )
        elif self ._material_glyph :
            drawn =self ._draw_material_icon (painter ,icon_rect )

        if not drawn :
            self ._draw_fallback (painter ,icon_rect )
