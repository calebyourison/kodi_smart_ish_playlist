import xbmc
import xbmcaddon
import xbmcgui
import json
import random
from typing import Literal

from resources.lib.queries import list_of_all_tv_shows, list_all_movies, list_of_episodes_by_show_id, kodi_rpc
from resources.lib.logger import write_log


def clear_playlist(playlist_id:int=1) -> None:
    """Clear Playlist"""
    clear_playlist_payload = {
        "jsonrpc": "2.0",
        "method": "Playlist.Clear",
        "params": {"playlistid": playlist_id},
        "id": 1
    }

    kodi_rpc(clear_playlist_payload, return_result=False)
    write_log(f"Cleared playlist {playlist_id}")


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
    write_log(f"Added {content_type} id {item_id} to playlist {playlist_id}")


def gather_media_info() -> dict[str, dict]:
    """Select applicable number of movies, episodes, exclude were applicable"""
    addon = xbmcaddon.Addon()

    episodes = {}

    defined_show_criteria = json.loads(addon.getSetting("defined_show_criteria") or {})

    for show_id, show_info in defined_show_criteria.items():
        show_id = int(show_id)
        title = show_info.get("title")
        exclusions = {int(episode_id): title for episode_id, title in show_info.get("exclusions").items()}
        number_of_episodes = int(show_info.get("number_of_episodes"))

        write_log(f"Gathering {number_of_episodes} episodes from TV Show {title} id: {show_id}")
        write_log(f"Exclusions: {exclusions}")

        # Limit query to reduce load
        all_show_episodes = list_of_episodes_by_show_id(show_id=show_id, number=(number_of_episodes + len(exclusions) * 2) )
        non_excluded_episodes = [item for item in all_show_episodes if item.get("episodeid") not in exclusions.keys()]

        if number_of_episodes >= len(non_excluded_episodes):
            selection = non_excluded_episodes

        else:
            selection = random.sample(non_excluded_episodes, number_of_episodes)

        write_log(f"Selection: {selection}")

        for item in selection:
            episodes[item.get("episodeid")] = item.get("title")


    selected_movies = json.loads(addon.getSetting("selected_movie") or {})
    number_of_movies = json.loads(addon.getSetting("number_of_movies"))

    if number_of_movies >= len(selected_movies):
        final_movie_selection = selected_movies
    else:
        final_movie_selection = dict(random.sample(list(selected_movies.items()), number_of_movies))

    final_movie_selection = {int(movie_id): title for movie_id, title in final_movie_selection.items()}

    write_log(f"movie: {final_movie_selection}, episode: {episodes}")

    return {"movie": final_movie_selection, "episode": episodes}


def build_playlist(media_info:dict[str, dict], progress_dialog, clear_existing:bool=True, playlist_id:int=1) -> bool:
    """Add each media item to a given playlist"""
    if clear_existing:
        write_log(f"Clearing playlist {playlist_id}")
        clear_playlist(playlist_id=playlist_id)

    total_items = 0
    for item in media_info.values():
        total_items += len(item)
    write_log(f"Total items to add: {total_items}")

    items_completed = 0

    for media_type, media_items in media_info.items():
        for media_id, title in media_items.items():
            write_log(f"Adding {media_type} {title} id: {media_id}")

            if progress_dialog.iscanceled():
                xbmcgui.Dialog().notification("Cancelled", "Playlist building aborted", xbmcgui.NOTIFICATION_WARNING,3000)
                return False

            add_to_playlist(content_type=media_type, item_id=media_id, playlist_id=playlist_id)

            items_completed += 1
            percent = int(items_completed / total_items * 100)
            write_log(f"{percent}% complete")
            progress_dialog.update(percent, f"{title} added")
            xbmc.sleep(5)

    return True

def start_playlist(playlist_id: int = 1, shuffle: bool = True) -> None:
    """Open/Play the video playlist, shuffle if applicable."""
    write_log(f"Starting Playlist {playlist_id} shuffle={shuffle}")

    kodi_rpc({
        "jsonrpc": "2.0",
        "method": "Player.Open",
        "params": {"item": {"playlistid": playlist_id}},
        "id": 1
    }, return_result=False)

    if not shuffle:
        return

    # Max ~2 seconds
    player_id = None
    for _ in range(10):
        data = kodi_rpc({
            "jsonrpc": "2.0",
            "method": "Player.GetActivePlayers",
            "id": 2
        })

        if data and isinstance(data.get("result"), list):
            for player in data["result"]:
                if player.get("type") == "video":
                    player_id = player.get("playerid")
                    break

        if player_id is not None:
            break

        xbmc.sleep(200)

    if player_id is None:
        write_log("Video player not found for shuffle", xbmc.LOGERROR)
        return

    # Set Shuffle
    kodi_rpc({
        "jsonrpc": "2.0",
        "method": "Player.SetShuffle",
        "params": {
            "playerid": player_id,
            "shuffle": True
        },
        "id": 3
    }, return_result=False)


