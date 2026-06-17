import json 
from pathlib import Path 
from typing import Dict ,List 

from PySide6 .QtCore import QObject ,QThread ,Signal ,Slot 

from ..models import SearchResult 
from ..core .constants import (
QUERY_MODE_APPS ,QUERY_MODE_NORMAL ,KIND_LOCAL ,DEFAULT_MAX_RESULTS ,APP_ID 
)
from ..providers import LocalAppsProvider ,RegistryProvider 
from ..services import RegistryService ,CacheService 
from .search_worker import SearchWorker 


class SearchResultDispatcher (QObject ):
    results_ready =Signal (int ,list )

    @Slot (int ,list )
    def dispatch (self ,search_id :int ,results :list ):
        self .results_ready .emit (search_id ,results )


class Controller :
    def __init__ (self ,app_ref =None ):
        self .app_ref =app_ref 
        self .window =None 
        self .search_callback =None 
        self .cache_service =CacheService ()
        self .registry_service =RegistryService (self .cache_service )
        self .local_apps_provider =LocalAppsProvider ()
        self .config =self ._load_config ()
        self ._enabled_app_ids =None 
        self ._search_thread =None 
        self ._search_worker =None 
        self ._search_id =0 
        self ._search_mode =QUERY_MODE_NORMAL 
        self ._old_search_threads =[]
        self ._old_search_workers =[]

        self ._dispatcher =SearchResultDispatcher ()
        self ._dispatcher .results_ready .connect (self ._on_search_finished )

    def set_window (self ,window ):
        self .window =window 

    def set_search_callback (self ,callback ):
        self .search_callback =callback 

    def search (self ,query :str ,mode :str =QUERY_MODE_NORMAL )->List [SearchResult ]:
        query =str (query or "").strip ()


        if not query and mode !=QUERY_MODE_APPS :
            self ._search_id +=1 
            self ._cancel_current_search ()

            decorated_results =[]

            if self .window :
                self .window .update_results (decorated_results )

            if self .search_callback :
                self .search_callback (decorated_results )

            return decorated_results 

        return self ._start_async_search (query ,mode )

    def _cancel_current_search (self ):
        worker =self ._search_worker 
        thread =self ._search_thread 

        if worker is not None :
            try :
                worker .request_cancel ()
            except Exception :
                pass 

        if thread is not None :
            try :
                if thread .isRunning ():
                    if thread not in self ._old_search_threads :
                        self ._old_search_threads .append (thread )
                else :
                    try :
                        thread .deleteLater ()
                    except Exception :
                        pass 
            except Exception :
                pass 

        if worker is not None :
            try :
                if worker not in self ._old_search_workers :
                    self ._old_search_workers .append (worker )
            except Exception :
                pass 

        self ._search_thread =None 
        self ._search_worker =None 

    def _start_async_search (self ,query :str ,mode :str =QUERY_MODE_NORMAL ):
        self ._search_id +=1 
        sid =self ._search_id 
        self ._search_mode =mode 

        self ._cancel_current_search ()

        if mode ==QUERY_MODE_APPS :
            from .search_worker import AppsSearchWorker 
            worker =AppsSearchWorker (sid ,query )
        else :
            worker =SearchWorker (sid ,query ,app_ref =self .app_ref )

        thread =QThread ()
        self ._search_worker =worker 
        self ._search_thread =thread 

        worker .moveToThread (thread )

        thread .started .connect (worker .run )



        worker .finished .connect (self ._dispatcher .dispatch )

        worker .finished .connect (thread .quit )
        thread .finished .connect (thread .deleteLater )
        thread .finished .connect (worker .deleteLater )
        thread .finished .connect (
        lambda t =thread ,w =worker :self ._cleanup_finished_thread (t ,w )
        )

        thread .start ()

        return []

    def _cleanup_finished_thread (self ,thread ,worker ):
        try :
            if thread in self ._old_search_threads :
                self ._old_search_threads .remove (thread )
        except Exception :
            pass 

        try :
            if worker in self ._old_search_workers :
                self ._old_search_workers .remove (worker )
        except Exception :
            pass 

        if self ._search_thread is thread :
            self ._search_thread =None 

        if self ._search_worker is worker :
            self ._search_worker =None 

    @Slot (int ,list )
    def _on_search_finished (self ,search_id :int ,results_list :list ):
        try :
            if int (search_id )!=int (self ._search_id ):
                return 
        except Exception :
            return 

        mode =self ._search_mode 

        converted =[]
        for item in results_list or []:
            try :
                if isinstance (item ,SearchResult ):
                    converted .append (item )
                elif isinstance (item ,dict ):
                    sr =self .local_apps_provider ._dict_to_search_result (item )
                    converted .append (sr )
            except Exception :
                continue 


        if mode !=QUERY_MODE_APPS :
            try :
                converted =[r for r in converted if str (r .id or "").lower ()!=str (APP_ID ).lower ()]
            except Exception :
                pass 

        decorated =[self ._decorate_result (result ,mode )for result in converted ]

        if self .window :
            self .window .update_results (decorated )

        if self .search_callback :
            self .search_callback (decorated )

    def stop_search_thread (self ,wait_ms :int =2000 ):
        worker =self ._search_worker 
        thread =self ._search_thread 

        if worker is not None :
            try :
                worker .request_cancel ()
            except Exception :
                pass 

        self ._search_worker =None 
        self ._search_thread =None 

        if thread is not None :
            try :
                if thread .isRunning ():
                    if thread not in self ._old_search_threads :
                        self ._old_search_threads .append (thread )

                    if worker is not None and worker not in self ._old_search_workers :
                        self ._old_search_workers .append (worker )
                else :
                    try :
                        thread .deleteLater ()
                    except Exception :
                        pass 
            except Exception :
                pass 

    def _search_apps_mode (self ,query :str )->List [SearchResult ]:
        results_by_provider ={}
        installed_ids =self ._get_installed_app_ids ()

        local_results =self .local_apps_provider .search (query )
        results_by_provider ["local"]=local_results 

        registry_provider =RegistryProvider (self .registry_service ,installed_ids )
        registry_results =registry_provider .search (query )
        results_by_provider ["registry"]=registry_results 

        merged =self ._merge_apps_results (local_results ,registry_results )
        return merged 

    def _search_normal_mode (self ,query :str )->List [SearchResult ]:
        if not query :
            return []

        enabled =self ._get_enabled_app_ids ()

        try :
            all_results =self .local_apps_provider .search (query )
        except Exception :
            all_results =[]

        filtered =[]
        for res in all_results :
            try :
                kind =str (res .kind or "").lower ().strip ()
                if kind ==KIND_LOCAL :
                    app_id =str (res .id or "").lower ().strip ()
                    if enabled and app_id and app_id not in enabled :
                        continue 
                filtered .append (res )
            except Exception :
                continue 

        return filtered 

    def _get_enabled_app_ids (self )->set :
        if self ._enabled_app_ids is not None :
            return self ._enabled_app_ids 

        enabled =set ()

        try :
            from core .paths import get_user_config_path 

            path =get_user_config_path ()
            p =Path (path )

            if p .exists ():
                data =json .loads (p .read_text (encoding ="utf-8"))
                apps =data .get ("apps",{})if isinstance (data ,dict )else {}

                if isinstance (apps ,dict ):
                    for app_id ,entry in apps .items ():
                        try :
                            if bool (entry .get ("enabled",False )):
                                enabled .add (str (app_id ).strip ())
                        except Exception :
                            pass 
        except Exception :
            pass 

        self ._enabled_app_ids ={app_id .lower ()for app_id in enabled }
        return self ._enabled_app_ids 

    def _is_app_enabled (self ,app_id :str )->bool :
        if not app_id :
            return False 

        enabled =self ._get_enabled_app_ids ()
        return str (app_id ).lower ()in enabled 

    def _merge_apps_results (
    self ,
    local_results :List [SearchResult ],
    registry_results :List [SearchResult ]
    )->List [SearchResult ]:
        merged ={}

        for result in local_results :
            app_id =result .id .lower ()
            merged [app_id ]=result 

        for result in registry_results :
            app_id =result .id .lower ()
            if app_id not in merged :
                merged [app_id ]=result 

        sorted_results =sorted (
        merged .values (),
        key =lambda result :result .title .lower ()
        )

        return sorted_results [:DEFAULT_MAX_RESULTS ]

    def handle_result_action (self ,result_dict :Dict ):
        kind =str (result_dict .get ("kind","")).lower ().strip ()
        if kind ==KIND_LOCAL :


            if result_dict .get ("_from_history"):

                pass 
            else :

                if self ._search_mode ==QUERY_MODE_APPS :
                    self ._show_app_info (result_dict )
                    return 


            app_loader =None 
            runtime =None 
            try :
                app_ctx ={}
                if hasattr (self .app_ref ,"get_app_context")and callable (getattr (self .app_ref ,"get_app_context")):
                    try :
                        app_ctx =self .app_ref .get_app_context ()or {}
                    except Exception :
                        app_ctx ={}

                if isinstance (app_ctx ,dict ):
                    app_loader =app_ctx .get ("app_loader")or getattr (self .app_ref ,"app_loader",None )
                    runtime =app_ctx .get ("runtime_service")or app_ctx .get ("app_runtime_service")or getattr (self .app_ref ,"app_runtime_service",None )
                else :
                    app_loader =getattr (self .app_ref ,"app_loader",None )
                    runtime =getattr (self .app_ref ,"app_runtime_service",None )
            except Exception :
                app_loader =getattr (self .app_ref ,"app_loader",None )
                runtime =getattr (self .app_ref ,"app_runtime_service",None )

            if app_loader is not None :
                try :
                    app_id =result_dict .get ("app_id")or result_dict .get ("id")
                    app_dir =app_loader ._find_app_dir_by_id (app_id )
                    if app_dir is not None :
                        app_data =app_loader ._load_single_app (app_dir )
                        if app_data is not None :
                            if runtime is not None :
                                try :
                                    inst =runtime .launch (app_data )




                                    return 
                                except Exception :
                                    pass 
                            else :

                                try :

                                    runtime2 =getattr (self .app_ref ,"app_runtime_service",None )
                                    if runtime2 is not None :
                                        runtime2 .launch (app_data )
                                        return 
                                except Exception :
                                    pass 
                except Exception :
                    pass 


            if runtime is not None :
                try :
                    inst =runtime .launch (result_dict )
                    try :

                        pass 
                    except Exception :
                        pass 
                    return 
                except Exception :
                    pass 


            self ._show_app_info (result_dict )
        elif result_dict .get ("is_online"):
            self ._show_app_info (result_dict )
        elif kind in ("executable","shortcut"):
            self ._launch_item (result_dict )

    def _show_app_info (self ,app_data :Dict ):
        from ..ui .dialogs import AppInfoDialog 

        if not self .window :
            return 

        dialog =AppInfoDialog (app_data ,self .window )
        if dialog .exec ():
            print (f"Installing app: {app_data .get ('id')}")

    def _launch_item (self ,item_data :Dict ):
        import subprocess 

        command =item_data .get ("command")or item_data .get ("path")

        if command :
            try :
                subprocess .Popen (command ,shell =True )
            except Exception as e :
                print (f"Error launching {command }: {e }")

    def _get_installed_app_ids (self )->set :
        installed =set ()

        try :
            apps_dir =self .local_apps_provider .apps_dir 

            if apps_dir and apps_dir .exists ():
                for app_dir in apps_dir .iterdir ():
                    if app_dir .is_dir ():
                        installed .add (app_dir .name .lower ())
        except Exception :
            pass 

        return installed 

    def _decorate_result (self ,result :SearchResult ,mode :str )->Dict :
        decorated =result .to_dict ()
        kind =str (result .kind or "").lower ().strip ()

        if mode ==QUERY_MODE_APPS :
            if kind ==KIND_LOCAL :

                decorated ["_spotlight_status"]="enabled"
                decorated ["_spotlight_actionable"]=True 
                decorated ["_spotlight_action"]="showcase"
            elif result .metadata .get ("is_online")or result .metadata .get ("installed")is not None :
                installed =bool (result .metadata .get ("installed",False ))


                online_v =result .metadata .get ("online_version")
                local_v =result .metadata .get ("local_version")or result .metadata .get ("version")

                try :
                    from packaging .version import Version 
                    if online_v and local_v :
                        try :
                            if Version (str (online_v ))>Version (str (local_v )):
                                decorated ["_spotlight_status"]="update"
                                decorated ["_spotlight_actionable"]=True 
                                decorated ["_spotlight_action"]="update"
                                return decorated 
                        except Exception :
                            pass 
                except Exception :

                    if online_v and local_v and str (online_v )!=str (local_v ):
                        decorated ["_spotlight_status"]="update"
                        decorated ["_spotlight_actionable"]=True 
                        decorated ["_spotlight_action"]="update"
                        return decorated 

                decorated ["_spotlight_status"]="installed"if installed else "install"
                decorated ["_spotlight_actionable"]=not installed 
                decorated ["_spotlight_action"]="install"
        else :
            if kind ==KIND_LOCAL :

                if self ._is_app_enabled (result .id ):
                    decorated ["_spotlight_status"]="app"
                else :
                    decorated ["_spotlight_status"]=""

                decorated ["_spotlight_actionable"]=True 
                decorated ["_spotlight_action"]="launch"
            elif kind in ("executable","shortcut"):
                decorated ["_spotlight_status"]="win"
                decorated ["_spotlight_actionable"]=False 

        return decorated 

    def _load_config (self )->Dict :
        config_file =self ._get_config_file ()

        if config_file .exists ():
            try :
                with open (config_file ,"r",encoding ="utf-8")as f :
                    data =json .load (f )

                return data if isinstance (data ,dict )else {}
            except Exception as e :
                print (f"Error loading config: {e }")

        return {}

    def _save_config (self ,config :Dict ):
        config_file =self ._get_config_file ()

        try :
            config_file .parent .mkdir (parents =True ,exist_ok =True )

            with open (config_file ,"w",encoding ="utf-8")as f :
                json .dump (config ,f ,indent =2 ,ensure_ascii =False )

            self .config =config 
        except Exception as e :
            print (f"Error saving config: {e }")

    def _get_config_file (self )->Path :
        try :
            from core .paths import get_app_data_dir 
            return Path (get_app_data_dir ("emanf.spotlight"))/"config.json"
        except Exception :
            home =Path .home ()
            return home /".edock"/"apps"/"emanf.spotlight"/"config.json"
