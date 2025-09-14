import xbmc

add_on = "Smart-ish Playlists"
default_log_level = xbmc.LOGDEBUG

def write_log(message:str, prefix:str = add_on, level=default_log_level):
    xbmc.log(f"{prefix} :: {message}", level=level)