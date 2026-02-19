import xbmc
import time
import json
import traceback
from typing import Any

from resources.lib.logger import write_log


def kodi_rpc(params:dict, return_result:bool=True) -> Any|None:
    """Return a JSON object from rpc call"""
    method = params.get("method", "UNKNOWN")
    start = time.time()

    try:
        response = xbmc.executeJSONRPC(json.dumps(params))
        elapsed = time.time() - start

        write_log(f"RPC {method} took {elapsed:.3f}s")

        if not return_result:
            return None

        data = json.loads(response)

        if "error" in data:
            write_log(f"RPC ERROR in {method}: {data['error']}", level=xbmc.LOGERROR)

        return data

    except Exception as e:
        write_log(f"Exception in RPC {method}: {e}", level=xbmc.LOGERROR)
        write_log(traceback.format_exc(), level=xbmc.LOGERROR)
        return None


def list_all_movies() -> list[dict]:
    """Return a list of all movies with their various attributes"""
    write_log(message="Querying all Movies")

    movies_payload = {
        "jsonrpc": "2.0",
        "method": "VideoLibrary.GetMovies",
        "params": {
            "properties": ["title"]
        },
        "id": 1
    }

    movies_list = kodi_rpc(movies_payload, return_result=True).get('result', {}).get('movies', [])

    write_log(f"All Movies info: {movies_list}")

    return movies_list


def list_of_all_tv_shows() -> list[dict]:
    """Return a list of all TV shows with their various attributes"""
    write_log("Querying all TV Shows")

    tv_shows_payload = {
        "jsonrpc": "2.0",
        "method": "VideoLibrary.GetTVShows",
        "id": 1,
        "params": {
            "properties": [
                "title",
            ]
        },
    }

    tv_show_list = kodi_rpc(tv_shows_payload).get('result', {}).get('tvshows', [])

    write_log(f"TV Shows info: {tv_show_list}")

    return tv_show_list



def list_of_episodes_by_show_id(show_id: int, number:int|None=None) -> list[dict]:
    """Return a list of episodes for a given show id and various episode attributes"""
    write_log(f"Querying all episodes for show_id: {show_id}")

    episodes_payload = {
        "jsonrpc": "2.0",
        "method": "VideoLibrary.GetEpisodes",
        "id": 1,
        "params": {
            "tvshowid": show_id,
            "properties": [
                "title",
            ],
        },
    }

    if number:
        episodes_payload["params"]["sort"] = {"method": "random"}
        episodes_payload["params"]["limits"] = {"start": 0, "end": number}

    episodes_list = kodi_rpc(episodes_payload).get('result', {}).get('episodes', [])
    write_log(f"Episodes list: {episodes_list}")

    return episodes_list