import sys
import json

import xbmcaddon
import xbmcgui

from resources.lib.logger import write_log
from resources.lib.selections import select_media, display_selections
from resources.lib.playlist_functions import build_playlist, gather_media_info, start_playlist, quit_kodi_after

all_args = sys.argv

write_log(f"all args: {all_args}")


def build():
    addon = xbmcaddon.Addon()

    autoplay = addon.getSettingBool("auto_play")
    shuffle = addon.getSettingBool("shuffle")
    auto_quit = addon.getSettingBool("auto_quit")

    write_log(f"Building, Autoplay: {autoplay} Shuffle: {shuffle}")

    progress = xbmcgui.DialogProgress()
    progress.create("Building Playlist", "Initializing...")
    items = gather_media_info()
    playlist_progress = build_playlist(media_info=items, progress_dialog=progress)
    progress.close()

    if playlist_progress:
        xbmcgui.Dialog().notification("Playlist Ready", "Build complete", xbmcgui.NOTIFICATION_INFO, 3000)
        write_log("Playlist build complete")

        if autoplay:
            start_playlist(playlist_id=1, shuffle=shuffle)
            write_log("Playback started")

            if auto_quit:
                auto_quit_minutes = json.loads(addon.getSetting("auto_quit_minutes"))
                quit_kodi_after(auto_quit_minutes)

    else:
        xbmcgui.Dialog().notification("Stopped", "Playlist build incomplete", xbmcgui.NOTIFICATION_ERROR, 3000)
        write_log("Playlist build cancelled")


def main():
    if len(all_args) > 1:
        action = all_args[1]

        if action == "select_shows":
            select_media(media_type="tvshow")

        if action == "select_movies":
            select_media(media_type="movie")

        if action == "selection_info":
            display_selections()

    else:
        build()


if __name__ == "__main__":
    main()








