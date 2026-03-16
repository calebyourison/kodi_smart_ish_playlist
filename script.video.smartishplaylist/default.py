import sys
import json
import threading
import xbmc
from queue import Queue
import xbmcaddon
import xbmcgui

from resources.lib.logger import write_log
from resources.lib.selections import (
    select_media,
    configure_shows,
    review_selections,
    select_smart_playlists,
    review_smart_playlist_selections
)
from resources.lib.playlist_functions import (
    gather_media_info,
    gather_all_smart_playlist_info,
    quit_kodi_after,
    playlist_builder,
    video_playlist_start,
)
from resources.lib.config import clear_config_section

all_args = sys.argv

write_log(f"all args: {all_args}")


def rpc_worker(progress_queue: Queue, cancel_event: threading.Event) -> None:
    write_log("Begin RPC worker")
    addon = xbmcaddon.Addon()

    chunk_by_size = True

    playlist_type = int(addon.getSetting("playlist_type"))
    chunk_type = int(addon.getSetting("batch_method"))
    if chunk_type == 1:
        chunk_by_size = False

    chunk_size = int(addon.getSetting("batch_size"))
    number_of_chunks = int(addon.getSetting("number_of_batches"))


    monitor = xbmc.Monitor()
    if playlist_type == 0:
        items = gather_media_info(monitor=monitor)
    elif playlist_type == 1:
        items = gather_all_smart_playlist_info(monitor=monitor)
    else:
        write_log(f"Playlist type undefined: {playlist_type}")
        return None

    playlist_progress = playlist_builder(
        media_info=items,
        monitor=monitor,
        progress_queue=progress_queue,
        cancel_event=cancel_event,
        chunk_by_size=chunk_by_size,
        chunk_size=chunk_size,
        number_of_chunks=number_of_chunks,

    )

    if playlist_progress:
        write_log("Playlist build complete")
        return None

    else:
        write_log("Playlist build interrupted")
        return None


def run() -> None:
    addon = xbmcaddon.Addon()
    progress = xbmcgui.DialogProgress()

    autoplay = addon.getSettingBool("auto_play")
    shuffle = addon.getSettingBool("shuffle")
    auto_quit = addon.getSettingBool("auto_quit")

    write_log(f"Building, Autoplay: {autoplay} Shuffle: {shuffle}")

    progress.create("Building Playlist", "Initializing...")

    progress_queue = Queue()
    cancel_event = threading.Event()

    background_worker = threading.Thread(
        target=rpc_worker, args=(progress_queue, cancel_event), daemon=True
    )

    background_worker.start()
    cancelled = False

    while True:
        if progress.iscanceled():
            cancel_event.set()
            cancelled = True
            break

        try:
            message = progress_queue.get_nowait()

            if message:
                if message[0] == "done":
                    break

                percent, text = message
                progress.update(percent, text)

        except Exception as e:
            write_log(f"Error: {e}")

        xbmc.sleep(50)

    progress.close()

    if cancelled:
        xbmcgui.Dialog().notification(
            "Stopped", "Playlist build incomplete", xbmcgui.NOTIFICATION_ERROR, 3000
        )
        write_log("Playlist build cancelled")

    else:
        xbmcgui.Dialog().notification(
            "Playlist Ready", "Build complete", xbmcgui.NOTIFICATION_INFO, 3000
        )
        if autoplay:
            video_playlist_start(shuffle=shuffle)
            write_log("Playback started")

            if auto_quit:
                auto_quit_minutes = json.loads(addon.getSetting("auto_quit_minutes"))
                quit_kodi_after(auto_quit_minutes)


def main():
    if len(all_args) > 1:
        action = all_args[1]

        if action == "select_shows":
            select_media(media_type="tvshow")

        if action == "select_movies":
            select_media(media_type="movie")

        if action == "configure_shows":
            configure_shows()

        if action == "clear_movies":
            clear_config_section("movie")

        if action == "clear_tvshows":
            clear_config_section("tvshow")

        if action == "review_selections":
            addon = xbmcaddon.Addon()
            playlist_type = int(addon.getSetting("playlist_type"))

            if playlist_type == 0:
                review_selections()
            elif playlist_type == 1:
                review_smart_playlist_selections()
            else:
                write_log(f"Playlist type undefined: {playlist_type}")


        if action == "select_smart":
            select_smart_playlists()

    else:
        run()


if __name__ == "__main__":
    main()
