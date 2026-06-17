from PySide6 .QtCore import Qt 
from PySide6 .QtGui import QPainter ,QPen ,QFontMetrics ,QColor 
from PySide6 .QtWidgets import QApplication 

from core .theming .theme_manager import Theme 
from core .ui .widget import eD_Widget 


class eD_Tooltip (eD_Widget ):
    def __init__ (self ,app =None ,context =None ,parent =None ):
        super ().__init__ (app =app ,context =context ,parent =parent )

        self .uic =Theme .to_ui_color 
        self .toolTip_theme =Theme .get_tooltip ()

        self .text =""
        self .padding_x =10 
        self .padding_y =6 
        self .radius =18 
        self .border_width =1 
        self .bg_color ="#333333"
        self .border_color ="#1A1A1A"
        self .text_color ="#E0E0E0"

        self .apply_theme ()

        self .setWindowFlags (
        Qt .ToolTip |
        Qt .FramelessWindowHint |
        Qt .WindowStaysOnTopHint 
        )
        self .setAttribute (Qt .WA_TranslucentBackground ,True )
        self .setAttribute (Qt .WA_ShowWithoutActivating ,True )
        self .setAttribute (Qt .WA_TransparentForMouseEvents ,True )
        self .hide ()

    def apply_theme (self ,update =False ):
        self .uic =Theme .to_ui_color 
        self .toolTip_theme =Theme .get_tooltip ()

        self .radius =self .toolTip_theme .get ("border_radius")
        self .border_width =self .toolTip_theme .get ("border_width")
        self .bg_color =self .uic (self .toolTip_theme .get ("background_color"))
        self .border_color =self .uic (self .toolTip_theme .get ("border_color"))
        self .text_color =self .uic (self .toolTip_theme .get ("text_color"))

        if update :
            self .update ()

    def set_text (self ,text ):
        self .text =str (text or "")
        metrics =QFontMetrics (self .font ())
        text_width =metrics .horizontalAdvance (self .text )
        text_height =metrics .height ()

        width =text_width +self .padding_x *2 
        height =text_height +self .padding_y *2 
        self .resize (width ,height )
        self .update ()

    def show_text (self ,text ,pos =None ):
        self .set_text (text )
        self .apply_theme ()

        if pos is not None :
            self .move (pos )

        self .show ()
        self .raise_ ()

    def move_near_point (self ,global_x ,global_y ):
        self .move (global_x ,global_y )

    def clamp_to_screen (self ,margin =8 ):
        screen =QApplication .screenAt (self .pos ())
        if screen is None :
            screen =QApplication .primaryScreen ()
        if screen is None :
            return 

        geom =screen .availableGeometry ()
        x =self .x ()
        y =self .y ()

        if x +self .width ()>geom .right ()-margin :
            x =geom .right ()-margin -self .width ()
        if x <geom .left ()+margin :
            x =geom .left ()+margin 

        if y +self .height ()>geom .bottom ()-margin :
            y =geom .bottom ()-margin -self .height ()
        if y <geom .top ()+margin :
            y =geom .top ()+margin 

        self .move (x ,y )

    def paintEvent (self ,event ):
        if not self .text :
            return 

        painter =QPainter (self )
        painter .setRenderHint (QPainter .Antialiasing )

        rect =self .rect ().adjusted (0 ,0 ,-1 ,-1 )

        painter .setPen (QPen (QColor (self .border_color ),self .border_width ))
        painter .setBrush (QColor (self .bg_color ))
        painter .drawRoundedRect (rect ,self .radius ,self .radius )

        painter .setPen (QColor (self .text_color ))
        text_rect =self .rect ().adjusted (
        self .padding_x ,
        self .padding_y ,
        -self .padding_x ,
        -self .padding_y 
        )
        painter .drawText (text_rect ,Qt .AlignCenter ,self .text )
