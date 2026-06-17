class eD_UIBase :
    def _init_ui_base (self ,app =None ,context =None ):
        self .app =app 
        self .context =context or getattr (app ,"context",{})or {}

        self .config_manager =self .context .get ("config_manager")
        self .dock =self .context .get ("dock")

    def apply_theme (self ):
        pass 

    def show_and_activate (self ):
        self .show ()
        self .raise_ ()
        self .activateWindow ()
