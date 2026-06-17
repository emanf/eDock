import os 
import sys 
import shutil 
import importlib ._bootstrap_external as bootstrap_external 
from pathlib import Path 

ROOT_DIR =Path (__file__ ).resolve ().parent .parent 
CORE_DIR =ROOT_DIR /"core"
APPS_DIR =ROOT_DIR /"apps"
USER_DIR =ROOT_DIR /"user"
ASSETS_DIR =ROOT_DIR /"assets"
THEMES_DIR =CORE_DIR /"theming"/"builtin"
CORE_THEMES_DIR =CORE_DIR /"theming"/"builtin"
USER_THEMES_DIR =USER_DIR /"themes"

USER_CONFIG_PATH =USER_DIR /"config.json"

USER_DATA_DIR =USER_DIR /"data"

USER_CACHE_DIR =USER_DIR /"cache"
USER_CACHE_MAIN_DIR =USER_CACHE_DIR /"main"
USER_CACHE_CORE_DIR =USER_CACHE_DIR /"core"
USER_CACHE_APPS_DIR =USER_CACHE_DIR /"apps"

_ORIGINAL_CACHE_FROM_SOURCE =bootstrap_external .cache_from_source 
_PYCACHE_IS_SETUP =False 


def get_root_dir ():
    return ROOT_DIR 


def get_core_dir ():
    return CORE_DIR 


def get_apps_dir ():
    return APPS_DIR 


def get_user_dir ():
    return USER_DIR 


def get_assets_dir ():
    return ASSETS_DIR 


def get_themes_dir ():
    return THEMES_DIR 


def get_core_themes_dir ():
    return CORE_THEMES_DIR 


def get_user_themes_dir ():
    return USER_THEMES_DIR 


def get_app_dir (app_id ):
    if not app_id :
        return APPS_DIR 
    return APPS_DIR /str (app_id )


def get_app_themes_dir (app_id ):
    return get_app_dir (app_id )/"themes"


def get_all_app_themes_dirs ():
    result =[]
    if not APPS_DIR .exists ()or not APPS_DIR .is_dir ():
        return result 
    for app_dir in sorted (APPS_DIR .iterdir (),key =lambda p :p .name .lower ()):
        if app_dir .is_dir ():
            result .append (app_dir /"themes")
    return result 


def get_user_config_path ():
    return USER_CONFIG_PATH 


def get_user_data_dir ():
    return USER_DATA_DIR 


def get_app_data_dir (app_id ):
    if not app_id :
        return USER_DATA_DIR 
    return USER_DATA_DIR /str (app_id )


def get_cache_dir ():
    return USER_CACHE_DIR 


def get_core_cache_dir ():
    return USER_CACHE_CORE_DIR 


def get_main_cache_dir ():
    return USER_CACHE_MAIN_DIR 


def get_apps_cache_dir ():
    return USER_CACHE_APPS_DIR 


def get_app_cache_dir (app_id ):
    if not app_id :
        return USER_CACHE_APPS_DIR 
    return USER_CACHE_APPS_DIR /str (app_id )


def ensure_dir (path ):
    path =Path (path )
    path .mkdir (parents =True ,exist_ok =True )
    return path 


def ensure_user_dirs ():
    ensure_dir (USER_DIR )
    ensure_dir (USER_THEMES_DIR )
    ensure_dir (USER_DATA_DIR )
    ensure_dir (USER_CACHE_DIR )
    ensure_dir (USER_CACHE_MAIN_DIR )
    ensure_dir (USER_CACHE_CORE_DIR )
    ensure_dir (USER_CACHE_APPS_DIR )


def ensure_app_cache_dir (app_id ):
    return ensure_dir (get_app_cache_dir (app_id ))


def ensure_app_data_dir (app_id ):
    return ensure_dir (get_app_data_dir (app_id ))


def _pyc_filename (source_path ,optimization =None ):
    tag =sys .implementation .cache_tag or "cpython"
    name =Path (source_path ).stem 

    if optimization is None :
        optimization =sys .flags .optimize 

    if optimization :
        return f"{name }.{tag }.opt-{optimization }.pyc"

    return f"{name }.{tag }.pyc"


def _safe_original_cache_from_source (path ,debug_override =None ,optimization =None ):
    try :
        if debug_override is not None :
            optimization =""if debug_override else 1 
        return _ORIGINAL_CACHE_FROM_SOURCE (path ,optimization =optimization )
    except TypeError :
        return _ORIGINAL_CACHE_FROM_SOURCE (path )


def _project_cache_from_source (path ,debug_override =None ,*,optimization =None ):
    source =Path (path ).resolve ()

    try :
        relative_path =source .relative_to (ROOT_DIR )
    except ValueError :
        return _safe_original_cache_from_source (path ,debug_override ,optimization )

    parts =relative_path .parts 

    if not parts :
        return _safe_original_cache_from_source (path ,debug_override ,optimization )

    if parts [0 ]=="user":
        return _safe_original_cache_from_source (path ,debug_override ,optimization )

    pyc_name =_pyc_filename (source ,optimization )

    if parts [0 ]=="apps"and len (parts )>=2 :
        app_name =parts [1 ]
        inside_app =Path (*parts [2 :]).parent if len (parts )>2 else Path ()
        cache_dir =ensure_dir (USER_CACHE_APPS_DIR /app_name /"__pycache__"/inside_app )
        return str (cache_dir /pyc_name )

    if parts [0 ]=="core":
        inside_core =Path (*parts [1 :]).parent if len (parts )>1 else Path ()
        cache_dir =ensure_dir (USER_CACHE_CORE_DIR /inside_core )
        return str (cache_dir /pyc_name )

    cache_dir =ensure_dir (USER_CACHE_MAIN_DIR /relative_path .parent )
    return str (cache_dir /pyc_name )


def _remove_dir (path ):
    path =Path (path )
    if path .exists ()and path .is_dir ():
        shutil .rmtree (path ,ignore_errors =True )


def cleanup_project_pycache_dirs ():
    for pycache_dir in ROOT_DIR .rglob ("__pycache__"):
        _remove_dir (pycache_dir )


def cleanup_bad_mirrored_cache_dirs ():
    bad_core_user =CORE_DIR /"user"
    if bad_core_user .exists ()and bad_core_user .is_dir ():
        _remove_dir (bad_core_user )


def setup_pycache_dir ():
    global _PYCACHE_IS_SETUP 

    if _PYCACHE_IS_SETUP :
        return 

    ensure_user_dirs ()
    cleanup_project_pycache_dirs ()
    cleanup_bad_mirrored_cache_dirs ()

    bootstrap_external .cache_from_source =_project_cache_from_source 
    _PYCACHE_IS_SETUP =True 
