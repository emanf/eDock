from PySide6 .QtCore import Qt ,QAbstractListModel ,QModelIndex ,QSize ,QRect 
from PySide6 .QtGui import QColor ,QPainter ,QPen 
from PySide6 .QtWidgets import QStyledItemDelegate ,QStyle 

from core .theming .theme_manager import Theme 


class ResultsListModel (QAbstractListModel ):
    ItemRole =Qt .UserRole +1 

    def __init__ (self ,parent =None ):
        super ().__init__ (parent )
        self .results =[]
        self .row_height =46 

    def rowCount (self ,parent =QModelIndex ())->int :
        if parent .isValid ():
            return 0 
        return len (self .results )

    def data (self ,index :QModelIndex ,role =Qt .DisplayRole ):
        if not index .isValid ():
            return None 

        row =index .row ()
        if row <0 or row >=len (self .results ):
            return None 

        result =self .results [row ]

        if role ==Qt .DisplayRole :
            if isinstance (result ,dict ):
                return result .get ("title","")
            else :
                return result .title 

        if role ==self .ItemRole :
            if isinstance (result ,dict ):
                return result 
            else :
                return result .to_dict ()

        if role ==Qt .SizeHintRole :
            return QSize (0 ,self .row_height )

        return None 

    def set_results (self ,results ):
        self .beginResetModel ()
        self .results =list (results or [])
        self .endResetModel ()


class ResultItemDelegate (QStyledItemDelegate ):
    def __init__ (self ,parent =None ):
        super ().__init__ (parent )
        self .row_height =46 
        self .button_width =86 
        self .button_height =26 
        self .right_margin =12 

    def sizeHint (self ,option ,index )->QSize :
        return QSize (option .rect .width (),self .row_height )

    def paint (self ,painter ,option ,index ):
        item =index .data (ResultsListModel .ItemRole )or {}
        title =str (item .get ("title","")).strip ()
        subtitle =str (item .get ("subtitle","")).strip ()
        status =str (item .get ("_spotlight_status","")).strip ()
        actionable =bool (item .get ("_spotlight_actionable",False ))

        uiqc =Theme .to_ui_qcolor 


        colors =Theme .get_colors ()


        text_color =uiqc (colors .get (Theme .Colors .TEXT ))
        muted_color =uiqc (colors .get (Theme .Colors .MUTED_TEXT ))


        selected_bg =uiqc (colors .get (Theme .Colors .SURFACE_PRESSED ))
        hover_bg =uiqc (colors .get (Theme .Colors .SURFACE_HOVER ))

        painter .save ()
        painter .setRenderHint (QPainter .Antialiasing ,True )

        rect =option .rect .adjusted (0 ,0 ,-1 ,-1 )


        if option .state &QStyle .State_Selected :
            painter .setBrush (selected_bg )
            painter .setPen (Qt .NoPen )
            painter .drawRoundedRect (rect ,10 ,10 )
            text_color =QColor ("white")
            muted_color =QColor (235 ,235 ,235 )
        elif option .state &QStyle .State_MouseOver :
            painter .setBrush (hover_bg )
            painter .setPen (Qt .NoPen )
            painter .drawRoundedRect (rect ,10 ,10 )


        right_reserved =112 if status else 0 
        text_rect =rect .adjusted (12 ,5 ,-right_reserved -12 ,-5 )


        painter .setPen (text_color )
        title_font =painter .font ()
        title_font .setPointSize (10 )
        title_font .setBold (True )
        painter .setFont (title_font )

        if subtitle :
            painter .drawText (text_rect .adjusted (0 ,1 ,0 ,-18 ),Qt .AlignLeft |Qt .AlignVCenter ,title )

            subtitle_font =painter .font ()
            subtitle_font .setPointSize (8 )
            subtitle_font .setBold (False )
            painter .setFont (subtitle_font )
            painter .setPen (muted_color )
            painter .drawText (text_rect .adjusted (0 ,20 ,0 ,0 ),Qt .AlignLeft |Qt .AlignVCenter ,subtitle )
        else :
            painter .drawText (text_rect ,Qt .AlignLeft |Qt .AlignVCenter ,title )


        if status :
            badge_text =""
            badge_bg =None 
            badge_text_color =text_color 

            try :

                if status =="win":
                    badge_text =""
                    badge_bg =None 
                    badge_text_color =muted_color 
                elif status =="installed":
                    badge_text ="Installed"
                    badge_bg =uiqc (colors .get (Theme .Colors .INFO ))
                    badge_text_color =uiqc (colors .get (Theme .Colors .INFO_TEXT ))
                elif status =="enabled":
                    badge_text ="Enabled"
                    badge_bg =uiqc (colors .get (Theme .Colors .POSITIVE ))
                    badge_text_color =uiqc (colors .get (Theme .Colors .POSITIVE_TEXT ))
                elif status =="app":
                    badge_text ="App"
                    badge_bg =uiqc (colors .get (Theme .Colors .POSITIVE ))
                    badge_text_color =uiqc (colors .get (Theme .Colors .POSITIVE_TEXT ))
                elif status in ("install","not_installed","not installed"):
                    badge_text ="Not installed"
                    badge_bg =None 
                    badge_text_color =muted_color 
                else :
                    badge_text =str (status ).capitalize ()
                    badge_bg =None 
                    badge_text_color =muted_color 
            except Exception :
                badge_text =str (status ).capitalize ()
                badge_bg =None 
                badge_text_color =muted_color 

            if badge_text :
                badge_w =min (self .button_width ,rect .width ()//3 )
                badge_h =min (self .button_height ,rect .height ()-10 )
                badge_x =rect .right ()-badge_w -self .right_margin 
                badge_y =rect .center ().y ()-badge_h //2 
                badge_rect =QRect (badge_x ,badge_y ,badge_w ,badge_h )

                painter .save ()
                if badge_bg is not None :
                    painter .setBrush (badge_bg )
                    painter .setPen (Qt .NoPen )
                    painter .drawRoundedRect (badge_rect ,8 ,8 )
                else :

                    pen =QPen (muted_color )
                    pen .setWidth (1 )
                    painter .setPen (pen )
                    painter .setBrush (Qt .NoBrush )
                    painter .drawRoundedRect (badge_rect ,8 ,8 )


                painter .setPen (badge_text_color )
                font =painter .font ()
                font .setPointSize (8 )
                font .setBold (True )
                painter .setFont (font )
                painter .drawText (badge_rect ,Qt .AlignCenter ,badge_text )
                painter .restore ()

        painter .restore ()
