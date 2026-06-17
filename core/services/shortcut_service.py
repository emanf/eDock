try :
    import keyboard 
except Exception :
    keyboard =None 


class ShortcutService :
    def __init__ (self ,launch_callback ):
        self .launch_callback =launch_callback 
        self .handles ={}
        self .shortcuts ={}

    def normalize (self ,shortcut ):
        value =str (shortcut or "").strip ()
        if not value :
            return ""

        replacements ={
        "Ctrl":"ctrl",
        "Control":"ctrl",
        "Alt":"alt",
        "Shift":"shift",
        "Meta":"windows",
        "Win":"windows",
        "Windows":"windows",
        "Cmd":"command",
        "Command":"command",
        "PgUp":"page up",
        "PgDown":"page down",
        "Del":"delete",
        "Ins":"insert",
        "Esc":"esc",
        "Return":"enter",
        }

        parts =[
        part .strip ()
        for part in value .replace (" ","").split ("+")
        if part .strip ()
        ]

        normalized =[]

        for part in parts :
            normalized .append (replacements .get (part ,part .lower ()))

        return "+".join (normalized )

    def register (self ,app_id ,shortcut ,app_data ):
        if not keyboard :
            return 

        app_id =str (app_id or "").strip ()
        shortcut =self .normalize (shortcut )

        if not app_id or not shortcut :
            return 


        self .unregister (app_id )

        try :
            self .handles [app_id ]=keyboard .add_hotkey (
            shortcut ,
            lambda data =dict (app_data ):self .launch_callback (data ),
            )

            self .shortcuts [app_id ]=shortcut 
        except Exception :
            pass 

    def register_apps (self ,apps ):
        self .unregister_all ()

        for app in apps :
            app_id =str (app .get ("id","")or "").strip ()
            shortcut =str (app .get ("shortcut","")or "").strip ()

            if app_id and shortcut :
                self .register (app_id ,shortcut ,app )

    def unregister (self ,app_id ):
        if not keyboard :
            return 

        if app_id not in self .handles :

            try :
                sc =self .shortcuts .pop (app_id ,None )
                if sc :
                    keyboard .remove_hotkey (sc )
            except Exception :
                pass 
            return 

        try :
            handle =self .handles .pop (app_id )

            try :
                keyboard .remove_hotkey (handle )
            except Exception :

                try :
                    sc =self .shortcuts .pop (app_id ,None )
                    if sc :
                        keyboard .remove_hotkey (sc )
                except Exception :
                    pass 
        except Exception :

            try :
                sc =self .shortcuts .pop (app_id ,None )
                if sc :
                    keyboard .remove_hotkey (sc )
            except Exception :
                pass 

    def unregister_all (self ):
        for app_id in list (set (list (self .handles .keys ())+list (self .shortcuts .keys ()))):
            self .unregister (app_id )