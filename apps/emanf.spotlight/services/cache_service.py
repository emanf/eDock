import json 
import os 
from pathlib import Path 
from typing import Any ,Optional ,Dict 
import time 


class CacheService :

    def __init__ (self ,cache_dir :Path =None ):
        self .cache_dir =cache_dir 
        if self .cache_dir is None :
            self ._discover_cache_dir ()

    def _discover_cache_dir (self ):
        try :
            from core .paths import get_cache_dir 
            cache_root =Path (get_cache_dir ())
            self .cache_dir =cache_root /"apps"/"emanf.spotlight"
        except Exception :
            home =Path .home ()
            self .cache_dir =home /".edock"/"cache"/"apps"/"emanf.spotlight"

    def read_cache (self ,key :str ,max_age_seconds :int =None )->Optional [Any ]:
        cache_file =self ._get_cache_file (key )

        if not cache_file .exists ():
            return None 


        if max_age_seconds is not None :
            age =time .time ()-cache_file .stat ().st_mtime 
            if age >max_age_seconds :
                return None 

        try :
            with open (cache_file ,"r",encoding ="utf-8")as f :
                data =json .load (f )
            return data 
        except Exception as e :
            print (f"Error reading cache {key }: {e }")
            return None 

    def write_cache (self ,key :str ,data :Any )->bool :
        cache_file =self ._get_cache_file (key )

        try :
            cache_file .parent .mkdir (parents =True ,exist_ok =True )
            with open (cache_file ,"w",encoding ="utf-8")as f :
                json .dump (data ,f ,indent =2 ,ensure_ascii =False )
            return True 
        except Exception as e :
            print (f"Error writing cache {key }: {e }")
            return False 

    def clear_cache (self ,key :str =None )->bool :
        try :
            if key is None :

                if self .cache_dir .exists ():
                    import shutil 
                    shutil .rmtree (str (self .cache_dir ))
            else :

                cache_file =self ._get_cache_file (key )
                if cache_file .exists ():
                    cache_file .unlink ()
            return True 
        except Exception as e :
            print (f"Error clearing cache: {e }")
            return False 

    def _get_cache_file (self ,key :str )->Path :
        os .makedirs (self .cache_dir ,exist_ok =True )
        return self .cache_dir /f"{key }.json"
