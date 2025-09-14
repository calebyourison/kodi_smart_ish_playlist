import xbmc
import json
from typing import Any, Literal


def kodi_rpc(params:dict, return_result:bool=True) -> Any|None:
    """Return a json object from rpc call"""
    response = xbmc.executeJSONRPC(json.dumps(params))

    if return_result:
        return json.loads(response)
    else:
        return None


def list_all_movies() -> list[dict]:
    """Return a list of all movies with their various attributes"""
    movies_payload = {
        "jsonrpc": "2.0",
        "method": "VideoLibrary.GetMovies",
        "params": {
            "properties": ["title"]
        },
        "id": 1
    }

    movies_list = kodi_rpc(movies_payload, return_result=True).get('result', {}).get('movies', [])

    return movies_list


def find_id_number_by_title(content_type:Literal["movie", "tvshow"], title:str) -> int|None:
    """Return int id number for a movie or tvshow, title requires exact match apart from capitalization"""
    if content_type == 'movie':
        items = list_all_movies()
    elif content_type == "tvshow":
        items = list_of_all_tv_shows()

    else:
        xbmc.log("No content selected")
        return None

    items_matching_title = [item for item in items if item['title'].lower() == title.lower()]

    if len(items_matching_title) == 0:
        xbmc.log(f"No {content_type} matching title: {title}")

    elif len(items_matching_title) > 1:
        xbmc.log(f"Multiple {content_type} matching title: {title}")

    item_id = items_matching_title[0].get(f"{content_type}id", None)

    return item_id

def list_of_all_tv_shows() -> list[dict]:
    """Return a list of all tv shows with their various attributes"""

    tv_shows_payload = {
        "jsonrpc": "2.0",
        "method": "VideoLibrary.GetTVShows",
        "id": 1,
        "params": {
            "properties": [
                "title",
                "genre",
                "year",
                "rating",
                "playcount",
                "episode",
                "watchedepisodes",
                "thumbnail",
            ]
        },
    }

    tv_show_list = kodi_rpc(tv_shows_payload).get('result', {}).get('tvshows', [])
    return tv_show_list


def list_of_episodes_by_show_id(show_id: int) -> list[dict]:
    """Return a list of episodes for a given show id and various episode attributes"""

    episodes_payload = {
        "jsonrpc": "2.0",
        "method": "VideoLibrary.GetEpisodes",
        "id": 1,
        "params": {
            "tvshowid": show_id,
            "properties": [
                "title",
                "season",
                "episode",
                "firstaired",
                "playcount",
                "runtime",
            ],
        },
    }

    episodes_list = kodi_rpc(episodes_payload).get('result', {}).get('episodes', [])

    return episodes_list


def clear_playlist(playlist_id:int=1) -> None:
    """Clear Playlist"""
    clear_playlist_payload = {
        "jsonrpc": "2.0",
        "method": "Playlist.Clear",
        "params": {"playlistid": playlist_id},
        "id": 1
    }

    kodi_rpc(clear_playlist_payload, return_result=False)


def add_to_playlist(content_type:Literal["movie", "episode"], item_id:int, playlist_id:int=1) -> None:
    """Add an episode or a movie to a given playlist using their content type and id numbers"""

    item_key = f"{content_type}id"

    add_to_playlist_payload = {
        "jsonrpc": "2.0",
        "method": "Playlist.Add",
        "params": {
            "playlistid": playlist_id,
            "item": {
                item_key: item_id
            }
        },
        "id": 1
    }

    kodi_rpc(add_to_playlist_payload, return_result=False)


def start_playlist(playlist_id:int=1, shuffle=True) -> None:
    """Open/Play the playlist, shuffle if applicable"""
    # Start the playlist
    open_payload = {
        "jsonrpc": "2.0",
        "method": "Player.Open",
        "params": {
            "item": {
                "playlistid": playlist_id
            }
        },
        "id": 1
    }

    kodi_rpc(open_payload, return_result=False)


    if shuffle:
        # Give Kodi a moment to open the player
        xbmc.sleep(1000)  # One-second delay

        # Get active player ID
        get_player_payload = {
            "jsonrpc": "2.0",
            "method": "Player.GetActivePlayers",
            "id": 2
        }

        data = kodi_rpc(get_player_payload)

        if data and isinstance(data.get("result"), list) and data["result"]:
            player_id = data["result"][0]["playerid"]

            # Enable shuffle
            set_shuffle_payload = {
                "jsonrpc": "2.0",
                "method": "Player.SetShuffle",
                "params": {
                    "playerid": player_id,
                    "shuffle": True
                },
                "id": 3
            }
            kodi_rpc(set_shuffle_payload, return_result=False)
