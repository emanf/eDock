from PySide6 .QtWidgets import QDialog 

from core .ui .base_ui import eD_UIBase 


class eD_Dialog (QDialog ,eD_UIBase ):
    def __init__ (self ,app =None ,context =None ,parent =None ):
        super ().__init__ (parent )
        self ._init_ui_base (app =app ,context =context )

    def show (self ):
        self .apply_theme ()
        super ().show ()
