from PySide6 .QtGui import QColor 
from pathlib import Path 
import os 
import shutil 
import subprocess 
import sys 


def rgba_to_argb_hex (color_value ):
    value =str (color_value or "").strip ()
    if not value .startswith ("#"):
        return value 

    hex_value =value [1 :]

    if len (hex_value )==8 :
        r =hex_value [0 :2 ]
        g =hex_value [2 :4 ]
        b =hex_value [4 :6 ]
        a =hex_value [6 :8 ]
        return f"#{a }{r }{g }{b }"

    return value 


def qcolor_from_theme (color_value ,fallback ="#000000"):
    value =str (color_value or "").strip ()
    fallback_value =str (fallback or "#000000").strip ()

    converted =rgba_to_argb_hex (value )
    color =QColor (converted )

    if color .isValid ():
        return color 

    fallback_converted =rgba_to_argb_hex (fallback_value )
    fallback_color =QColor (fallback_converted )

    if fallback_color .isValid ():
        return fallback_color 

    return QColor ("#000000")


def remove_readonly (func ,path ,exc_info ):
    try :
        os .chmod (path ,0o777 )
        func (path )
    except Exception :
        pass 


def clear_directory_contents (directory ):
    directory =Path (directory )

    if not directory .exists ()or not directory .is_dir ():
        return 

    children =list (directory .iterdir ())

    for child in children :
        try :
            if child .is_file ()or child .is_symlink ():
                try :
                    os .chmod (child ,0o777 )
                except Exception :
                    pass 
                child .unlink (missing_ok =True )
            elif child .is_dir ():
                shutil .rmtree (child ,onerror =remove_readonly )
        except Exception :
            pass 

    for child in list (directory .iterdir ()):
        try :
            if child .is_file ()or child .is_symlink ():
                try :
                    os .chmod (child ,0o777 )
                except Exception :
                    pass 
                try :
                    os .remove (str (child ))
                except Exception :
                    pass 
            elif child .is_dir ():
                try :
                    shutil .rmtree (str (child ),ignore_errors =True )
                except Exception :
                    pass 
        except Exception :
            pass 


def open_folder (path ):
    path =Path (path )

    if not path .exists ():
        return 

    if sys .platform .startswith ("win"):
        os .startfile (str (path ))
    elif sys .platform =="darwin":
        subprocess .Popen (["open",str (path )])
    else :
        subprocess .Popen (["xdg-open",str (path )])