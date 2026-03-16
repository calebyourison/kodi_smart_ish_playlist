import xbmc
import xbmcaddon
import json
import random
from typing import Literal
import threading
from queue import Queue

from resources.lib.queries import (
    list_of_episodes_by_show_id,
    find_linked_movies_by_show_title,
    kodi_rpc,
    single_smart_playlist_info
)
from resources.lib.config import open_config_file
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
    content_type: Literal["movie", "episode"], item_id: int | list[int], playlist_id: int = 1
) -> None:
    """Add single or list of episode(s) or movie(s) to a given playlist using its content type and id numbers"""

    if isinstance(item_id, int):
        item_id = [item_id]

    item_key = f"{content_type}id"

    add_to_playlist_payload = {
        "jsonrpc": "2.0",
        "method": "Playlist.Add",
        "params": {"playlistid": playlist_id, "item": [{item_key: single_id} for single_id in item_id]},
        "id": 1,
    }

    write_log(f"add to playlist {add_to_playlist_payload}")

    kodi_rpc(add_to_playlist_payload, return_result=False)
    write_log(f"Added {content_type} ids {item_id} to playlist {playlist_id}")


def gather_single_show_info(show_id:int, title:str, exclusions:list[dict], number_of_episodes:int, all_show_episodes:list[dict]) -> list[dict]:
    """Return applicable episodes for a given show"""

    excluded_episodes: dict[int, str] = {
        item.get("id"): item.get("title") for item in exclusions
    }

    write_log(
        f"Gathering {number_of_episodes} episodes from TV Show {title} id: {show_id}"
    )
    write_log(f"Exclusions: {excluded_episodes}")

    non_excluded_episodes: list[dict] = [
        {"id": item.get("episodeid"), "title": item.get("title")}
        for item in all_show_episodes
        if item.get("episodeid") not in excluded_episodes.keys()
    ]

    if number_of_episodes >= len(non_excluded_episodes):
        selection: list[dict] = non_excluded_episodes

    else:
        selection: list[dict] = random.sample(
            non_excluded_episodes, number_of_episodes
        )

    write_log(f"Selection: {selection}")

    return selection


def gather_shows_info(
        defined_show_criteria: list[dict], default_number_of_episodes:int, monitor:xbmc.Monitor
) -> list[dict]:
    """Return applicable episodes for each show"""
    episodes = []

    for show in defined_show_criteria:
        show_id: int = show.get("id")
        title: str = show.get("title")
        exclusions:list[dict] = show.get("exclusions", [])

        number_of_episodes: int = show.get(
            "number_of_episodes", default_number_of_episodes
        )

        # Limit query to reduce load
        all_show_episodes: list[dict] = list_of_episodes_by_show_id(
            show_id=show_id, number=(number_of_episodes + len(exclusions) * 2)
        )

        selection = gather_single_show_info(
            show_id=show_id,
            title=title,
            exclusions=exclusions,
            number_of_episodes=number_of_episodes,
            all_show_episodes=all_show_episodes
        )

        episodes += selection

        if monitor.waitForAbort(0.01):
            break

    return episodes


def gather_movies_info(selected_movies:list[dict], number_of_movies:int) -> list[dict]:
    """Return a selection of movies"""
    if number_of_movies >= len(selected_movies):
        final_movie_selection: list[dict] = selected_movies
    else:
        final_movie_selection: list[dict] = random.sample(
            selected_movies, number_of_movies
        )

    return final_movie_selection


def gather_media_info(monitor: xbmc.Monitor) -> dict[str, list]:
    """Select applicable number of movies, episodes, exclude were applicable"""
    addon = xbmcaddon.Addon()

    config: dict[str, list] = open_config_file()

    defined_show_criteria: list[dict] = config.get("tvshow")
    default_number_of_episodes: int = json.loads(
        addon.getSetting("default_number_of_episodes")
    )

    episodes = gather_shows_info(
        defined_show_criteria=defined_show_criteria,
        default_number_of_episodes=default_number_of_episodes,
        monitor=monitor
    )

    selected_movies: list[dict] = config.get("movie")
    number_of_movies: int = json.loads(addon.getSetting("number_of_movies"))

    movies = gather_movies_info(selected_movies=selected_movies, number_of_movies=number_of_movies)

    write_log(f"movie: {movies}, episode: {episodes}")

    return {"movie": movies, "episode": episodes}


def gather_single_smart_playlist_media(files: list[dict]) -> tuple[list[dict], list[dict]]:
    """Extract applicable media info from a smart playlist files selection"""
    episodes = []
    movies = []

    for item in files:
        item_id = item.get("id")

        if item.get("type") == "episode":
            episodes.append({"id": item_id, "title": item.get("label")})

        elif item.get("type") == "movie":
            movies.append({"id": item_id, "title": item.get("label")})

        elif item.get("type") == "tvshow":
            title = item.get("label")
            show_episodes = list_of_episodes_by_show_id(item_id)
            show_movies = find_linked_movies_by_show_title(title)

            for episode in show_episodes:
                episodes.append({"id": episode.get("episodeid"), "title": episode.get("title")})

            for movie in show_movies:
                movies.append({"id": movie.get("movieid"), "title": movie.get("title")})

    return episodes, movies


def gather_all_smart_playlist_info(monitor: xbmc.Monitor) -> dict[str, list[dict]]:
    """Return media items from smart playlists"""

    config:dict[str, list] = open_config_file()
    playlists:list[dict] = config.get("smart")

    episodes = []
    movies = []

    for playlist in playlists:
        title:str = playlist.get("title")
        path:str = playlist.get("path")

        write_log(f"Gathering media items for {title}: {path}")

        items = single_smart_playlist_info(path)
        files = items.get("result", {}).get("files", [])

        playlist_episodes, playlist_movies = gather_single_smart_playlist_media(files)

        episodes += playlist_episodes
        movies += playlist_movies

        if monitor.waitForAbort(0.01):
            break

    write_log(f"movie: {movies}, episode: {episodes}")

    return {"movie": movies, "episode": episodes}


def define_chunks(media_info:dict[str,list[dict]], chunk_by_size:bool, number_of_chunks:int, chunk_size:int) -> tuple[bool, int, dict]:
    """Split media into chunks for adding to playlist based upon provided criteria"""
    super_slow = False

    total_items = 0

    media_chunks: dict = {}

    # Split into chunks by number or size
    for media_type, media_items in media_info.items():
        if chunk_by_size:
            chunks:list[list[dict]] = [media_items[i:i + chunk_size] for i in range(0, len(media_items), chunk_size)]
            if chunk_size == 1:
                super_slow = True
        else:
            k, m = divmod(len(media_items), number_of_chunks)
            chunks: list[list[dict]] = [media_items[i*k + min(i, m):(i+1)*k + min(i+1, m)]for i in range(number_of_chunks)]

        for chunk in chunks:
            total_items += len(chunk)
        media_chunks[media_type] = chunks

    return super_slow, total_items, media_chunks


def playlist_builder(
    media_info: dict[str,list[dict]],
    monitor: xbmc.Monitor,
    progress_queue: Queue,
    cancel_event: threading.Event,
    clear_existing: bool = True,
    playlist_id: int = 1,
    chunk_by_size:bool = True,
    number_of_chunks:int = 10,
    chunk_size:int = 25,
) -> bool:
    """Add each media item to a given playlist"""
    if clear_existing:
        write_log(f"Clearing playlist {playlist_id}")
        clear_playlist(playlist_id=playlist_id)

    super_slow, total_items, media_chunks = define_chunks(
        media_info=media_info,
        chunk_by_size=chunk_by_size,
        number_of_chunks=number_of_chunks,
        chunk_size=chunk_size
    )

    write_log(f"Total chunks to add: {len(media_chunks)}")
    write_log(f"Chunks: {media_chunks}")

    items_completed = 0
    remaining_items = total_items

    media_type:Literal["movie", "episode"]

    for media_type, chunks in media_chunks.items():
        for chunk in chunks:
            if cancel_event.is_set():
                return False
            write_log(f"Adding {media_type} chunk {chunk}")

            ids = [item.get("id") for item in chunk]

            add_to_playlist(content_type=media_type, item_id=ids, playlist_id=playlist_id)

            items_completed += len(chunk)
            remaining_items -= len(chunk)
            percent = int(items_completed / total_items * 100)
            write_log(f"{percent}% complete")
            if super_slow:
                item:dict = chunk[0]
                media_title = item.get("title")
                progress_queue.put((percent, f"Added {media_type}: {media_title} ({remaining_items}) items remaining"))
            else:
                progress_queue.put((percent, f"{len(chunk)} {media_type}s added ({remaining_items}) items remaining"))
            if monitor.waitForAbort(0.0001):
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
