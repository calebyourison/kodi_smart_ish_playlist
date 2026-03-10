import xbmc
import xbmcaddon
import json
import random
from typing import Literal
import threading
from queue import Queue

from resources.lib.queries import (
    list_of_all_tv_shows,
    list_all_movies,
    list_of_episodes_by_show_id,
    kodi_rpc,
)
from resources.lib.selections import open_config_file
from resources.lib.logger import write_log


def clear_playlist(playlist_id: int = 1) -> None:
    """Clear Playlist"""
    clear_playlist_payload = {
        "jsonrpc": "2.0",
        "method": "Playlist.Clear",
        "params": {"playlistid": playlist_id},
        "id": 1,
    }

    kodi_rpc(clear_playlist_payload, return_result=False)
    write_log(f"Cleared playlist {playlist_id}")


def add_to_playlist(
    content_type: Literal["movie", "episode"], item_id: int, playlist_id: int = 1
) -> None:
    """Add an episode or a movie to a given playlist using its content type and id numbers"""

    item_key = f"{content_type}id"

    add_to_playlist_payload = {
        "jsonrpc": "2.0",
        "method": "Playlist.Add",
        "params": {"playlistid": playlist_id, "item": {item_key: item_id}},
        "id": 1,
    }

    kodi_rpc(add_to_playlist_payload, return_result=False)
    write_log(f"Added {content_type} id {item_id} to playlist {playlist_id}")


def gather_media_info(monitor: xbmc.Monitor) -> dict[str, dict]:
    """Select applicable number of movies, episodes, exclude were applicable"""
    addon = xbmcaddon.Addon()

    config: dict[str, list] = open_config_file()

    episodes: dict[int, str] = {}

    defined_show_criteria: list[dict] = config.get("tvshow")
    default_number_of_episodes: int = json.loads(
        addon.getSetting("default_number_of_episodes")
    )

    for show in defined_show_criteria:
        show_id: int = show.get("id")
        title: str = show.get("title")
        exclusions: dict[int, str] = {
            item.get("id"): item.get("title") for item in show.get("exclusions", [])
        }
        number_of_episodes: int = show.get(
            "number_of_episodes", default_number_of_episodes
        )

        write_log(
            f"Gathering {number_of_episodes} episodes from TV Show {title} id: {show_id}"
        )
        write_log(f"Exclusions: {exclusions}")

        # Limit query to reduce load
        all_show_episodes: list[dict] = list_of_episodes_by_show_id(
            show_id=show_id, number=(number_of_episodes + len(exclusions) * 2)
        )
        non_excluded_episodes: list[dict] = [
            item
            for item in all_show_episodes
            if item.get("episodeid") not in exclusions.keys()
        ]

        if number_of_episodes >= len(non_excluded_episodes):
            selection: list[dict] = non_excluded_episodes

        else:
            selection: list[dict] = random.sample(
                non_excluded_episodes, number_of_episodes
            )

        write_log(f"Selection: {selection}")

        for item in selection:
            episodes[item.get("episodeid")] = item.get("title")

        if monitor.waitForAbort(0.01):
            break

    selected_movies: list[dict] = config.get("movie")
    number_of_movies: int = json.loads(addon.getSetting("number_of_movies"))

    if number_of_movies >= len(selected_movies):
        final_movie_selection: list[dict] = selected_movies
    else:
        final_movie_selection: list[dict] = random.sample(
            selected_movies, number_of_movies
        )

    movies_dict: dict[int, str] = {
        item.get("id"): item.get("title") for item in final_movie_selection
    }

    write_log(f"movie: {movies_dict}, episode: {episodes}")

    return {"movie": movies_dict, "episode": episodes}


def playlist_builder(
    media_info: dict[str, dict],
    monitor: xbmc.Monitor,
    progress_queue: Queue,
    cancel_event: threading.Event,
    clear_existing: bool = True,
    playlist_id: int = 1,
) -> bool:
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
            if cancel_event.is_set():
                return False
            write_log(f"Adding {media_type} {title} id: {media_id}")

            add_to_playlist(
                content_type=media_type, item_id=media_id, playlist_id=playlist_id
            )

            items_completed += 1
            percent = int(items_completed / total_items * 100)
            write_log(f"{percent}% complete")
            progress_queue.put((percent, f"{title} added"))
            if monitor.waitForAbort(0.01):
                break

    progress_queue.put(("done", None))
    return True


def video_playlist_start(shuffle: bool) -> None:
    """Open/Play the video playlist, shuffle if applicable."""
    write_log(f"Starting Video Playlist, shuffle={shuffle}")

    playlist = xbmc.PlayList(xbmc.PLAYLIST_VIDEO)

    if shuffle:
        playlist.shuffle()

    xbmc.Player().play(playlist)


def quit_kodi_after(minutes: int) -> None:
    """Stop playback if applicable and quit kodi after specified number of minutes"""

    def _worker():
        write_log(f"Kodi will quit in {minutes} minutes")

        total_ms = minutes * 60 * 1000
        elapsed = 0
        step = 500

        while elapsed < total_ms and not xbmc.Monitor().abortRequested():
            # Sleep every half second
            xbmc.sleep(step)
            elapsed += step

        if xbmc.Monitor().abortRequested():
            return

        data = kodi_rpc(
            {"jsonrpc": "2.0", "method": "Player.GetActivePlayers", "id": 10}
        )

        player_id = None
        if data and isinstance(data.get("result"), list):
            for player in data["result"]:
                if player.get("type") == "video":
                    player_id = player.get("playerid")
                    break

        # Stop playback if applicable
        if player_id is not None:
            write_log("Stopping video playback before quit")
            kodi_rpc(
                {
                    "jsonrpc": "2.0",
                    "method": "Player.Stop",
                    "params": {"playerid": player_id},
                    "id": 11,
                },
                return_result=False,
            )

            xbmc.sleep(1000)

        write_log("Quitting Kodi")
        kodi_rpc(
            {"jsonrpc": "2.0", "method": "Application.Quit", "id": 12},
            return_result=False,
        )

    threading.Thread(target=_worker, daemon=True).start()
