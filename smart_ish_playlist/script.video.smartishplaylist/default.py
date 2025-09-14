import xbmc
import xbmcgui

import random

from resources.lib.utils import (
    find_id_number_by_title,
    list_of_episodes_by_show_id,
    add_to_playlist,
    start_playlist,
    clear_playlist
)

from resources.lib.logging import write_log

my_shows = {
    # Show Title
    "Show One": [
        # Number of episodes to select
        5,
        # Randomly Select True/False
        True,
        # Episodes to exclude
        [
            "Boring Episode",
        ]
    ],
    "Show Two": [5, True, [None]], # Do not exclude any episodes
}

my_movies = [
    # Movie Titles
    "Movie One",
    "Movie Two",
    "Movie Three",
    "Movie Four",
    "Movie Five",

]

number_of_movies_to_select = 2 # Number of movies to randomly select from my_movies
playlist = 1 # Default playlist id

clear_existing_playlist = True # Empty the selected playlist before adding to it, recommended if using the default playlist
autostart = False # Start playlist once built
shuffle = True # Shuffle the playlist once played, not applicable if autostart=False

cancel_dialog_title = "Building Playlist"
cancel_dialog_message = "Initializing..."


def build_playlist(progress_dialog, clear_existing:bool=True, playlist_id:int=1) -> bool:
    """Build a playlist based on criteria from TV shows and Movies, automatically clears the default playlist id (1) unless specified otherwise"""
    if clear_existing:
        write_log(f"Clearing playlist with id: {playlist_id}")
        clear_playlist(playlist_id=playlist_id)

    total_episodes = sum([show[0] for show in my_shows.values()])
    write_log(f"Total episodes to add: {total_episodes}")

    total_number_of_items = number_of_movies_to_select + total_episodes
    write_log(f"Total movies to add: {number_of_movies_to_select}")
    write_log(f"Total items to add: {total_number_of_items}")

    items_completed = 0

    # Shows
    for show, (number_of_episodes, random_selection, exclude_episodes) in my_shows.items():
        write_log(f"Adding {number_of_episodes} episodes from show: {show}; random={random_selection}, excluding episodes: {exclude_episodes}")

        if progress_dialog.iscanceled():
            xbmcgui.Dialog().notification("Cancelled", "Playlist building aborted", xbmcgui.NOTIFICATION_WARNING, 3000)
            return False

        exclude_episodes_lower = [item.lower() for item in exclude_episodes if item is not None]
        show_id = find_id_number_by_title(content_type="tvshow", title=show)
        episodes = [episode for episode in list_of_episodes_by_show_id(show_id) if episode.get("title").lower() not in exclude_episodes_lower]

        # Reduce the number of selected episodes if the real-life value is less
        if number_of_episodes >= len(episodes):
            number_of_episodes = len(episodes)

        if random_selection:
            final_selection = random.sample(episodes, number_of_episodes)

        # Else select the first n episodes
        else:
            final_selection = episodes[:number_of_episodes-1]

        write_log(f"Final selection of {len(final_selection)} episodes: {final_selection}")

        for episode in final_selection:
            write_log(f"Adding episode: {episode}")
            id_number = episode.get('episodeid', None)
            if id_number:
                add_to_playlist(content_type='episode', item_id=id_number, playlist_id=playlist_id)

        items_completed += len(final_selection)
        percent = int(items_completed / total_number_of_items * 100)
        write_log(f"{percent}% complete")
        progress_dialog.update(percent, f"{show} added")


    # Movies
    if number_of_movies_to_select >= len(my_movies):
        movie_selection = my_movies

    else:
        movie_selection = random.sample(my_movies, number_of_movies_to_select)

    for movie in movie_selection:
        write_log(f"Adding movie: {movie}")

        if progress_dialog.iscanceled():
            xbmcgui.Dialog().notification("Cancelled", "Playlist building aborted", xbmcgui.NOTIFICATION_WARNING, 3000)
            return False

        movie_id = find_id_number_by_title(content_type="movie", title=movie)
        add_to_playlist(content_type="movie", item_id=movie_id, playlist_id=playlist_id)

        items_completed += 1
        percent = int(items_completed / total_number_of_items * 100)
        write_log(f"{percent}% complete")
        progress_dialog.update(percent, f"{movie} added")

    return True


def run():
    write_log(f"Autoplay: {autostart}")

    if autostart:
        write_log(f"Shuffle: {shuffle}")

    progress = xbmcgui.DialogProgress()
    progress.create(cancel_dialog_title, cancel_dialog_message)

    playlist_progress = build_playlist(
        progress_dialog=progress,
        clear_existing=clear_existing_playlist,
        playlist_id=playlist,
    )

    progress.close()

    if playlist_progress:
        xbmcgui.Dialog().notification("Playlist Ready", "Build complete", xbmcgui.NOTIFICATION_INFO, 3000)
        write_log("Playlist build complete")

        if autostart:
            start_playlist(playlist_id=playlist, shuffle=shuffle)
            write_log("Playback started")
    else:
        xbmcgui.Dialog().notification("Stopped", "Playlist build incomplete", xbmcgui.NOTIFICATION_ERROR, 3000)
        write_log("Playlist build cancelled")



if __name__ == '__main__':
    run()
