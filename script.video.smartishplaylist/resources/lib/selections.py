import xbmcgui
import json
import xbmcaddon
import xbmcvfs
import xml.etree.ElementTree as ET

from typing import Literal

from resources.lib.queries import (
    list_of_all_tv_shows,
    list_all_movies,
    list_of_episodes_by_show_id,
    single_smart_playlist_info
)
from resources.lib.playlist_functions import gather_single_smart_playlist_media
from resources.lib.logger import write_log
from resources.lib.config import open_config_file, write_to_config


def title_by_id_number(
    media_id: int, all_media_info: list[dict], media_type: Literal["movie", "tvshow"]
) -> str:
    """Search library based on media id number and return its string title"""
    titles: list[str] = [
        item.get("title")
        for item in all_media_info
        if item.get(f"{media_type}id") == media_id
    ]

    if len(titles) == 0:
        write_log(
            write_log(f"{media_type} id {media_id} returns zero titles: {titles}")
        )
        titles.append("Error no title")

    elif len(titles) > 1:
        write_log(
            f"{media_type} id {media_id} returns multiple titles: {titles}, selecting first entry"
        )

    title: str = titles[0]

    return title


def media_titles_with_preselection_idx(
    retrieved_info: list[dict],
    media_type: Literal["movie", "tvshow"],
    all_media_info: list[dict],
) -> tuple[list[str], list[int]]:
    """Return a tuple containing a list of sorted media titles and a list of preselection idx values determined by info retrieved from settings"""

    id_title_pairs: dict[int, str] = {
        media.get(f"{media_type}id"): media.get("title") for media in all_media_info
    }
    write_log(f"{media_type} title_id_pairs: {id_title_pairs}")

    media_titles: list[str] = sorted(id_title_pairs.values())
    write_log(f"{media_type} titles: {media_titles}")

    preselected_titles: list[str] = [item.get("title") for item in retrieved_info]
    write_log(f"Pre-selected {media_type} titles: {preselected_titles}")

    preselected_idx: list[int] = [
        media_titles.index(title) for title in preselected_titles
    ]
    write_log(f"Pre-selected {media_type} idx: {preselected_idx}")

    return media_titles, preselected_idx


def reconcile_titles(media_type:Literal["movie", "tvshow"], retrieved_info:list[dict], all_media_info:list[dict], selected_titles: list[str]) -> list[dict]:
    """Reconcile existing selections with newly selected titles, implemented to preserve existing TV Show configs"""

    selected_ids_titles: list[dict[str, str | int]] = [
        {"id": item.get(f"{media_type}id"), "title": item.get("title")}
        for item in all_media_info
        if item.get("title") in selected_titles
    ]

    write_log(f"Selected {media_type} ids: {selected_ids_titles}")

    existing_ids: list[int] = [item.get("id") for item in retrieved_info]
    new_ids: list[int] = [item.get("id") for item in selected_ids_titles]

    retained_items: list[dict] = [
        item for item in retrieved_info if item.get("id") in new_ids
    ]
    new_items: list[dict] = [
        item for item in selected_ids_titles if item.get("id") not in existing_ids
    ]

    updated_selections:list[dict] = retained_items + new_items

    return updated_selections


def select_media(media_type: Literal["movie", "tvshow"]) -> None:
    """Allow user to select titles from a window and save those selections to settings, check for previously select titles"""

    if media_type == "movie":
        all_media_info: list[dict] = list_all_movies()
        selection_text: str = "Select Movies"

    elif media_type == "tvshow":
        all_media_info: list[dict] = list_of_all_tv_shows()
        selection_text: str = "Select TV Shows"

    else:
        return None

    config_file: dict[str, list[dict]] = open_config_file()

    retrieved_info: list[dict] = config_file.get(media_type)

    titles: list[str]
    preselected_idx: list[int]
    titles, preselected_idx = media_titles_with_preselection_idx(
        retrieved_info=retrieved_info,
        media_type=media_type,
        all_media_info=all_media_info,
    )

    choices: list[int] = xbmcgui.Dialog().multiselect(
        selection_text, titles, preselect=preselected_idx
    )

    if choices:
        selected_titles: list[str] = [titles[index] for index in choices]
        write_log(f"Selected {media_type} titles: {selected_titles}")

        updated_selections = reconcile_titles(
            media_type=media_type,
            retrieved_info=retrieved_info,
            all_media_info=all_media_info,
            selected_titles=selected_titles
        )

        config_file[media_type] = updated_selections

        write_to_config(config_file)

    return None


def obtain_show_config(
    tv_show_id: int, tv_show_title: str, shows_config: list[dict], default_number_of_episodes: int
) -> tuple[int, list]:
    """Return a tuple of a show's current configuration or default values: number of episodes, excluded episodes"""

    possible_settings: list[dict] = [
        item for item in shows_config if item.get("id") == tv_show_id
    ]
    write_log(f"{tv_show_title} settings: {possible_settings}")

    if len(possible_settings) > 0:
        selected_show_settings: dict[str, str | int | list] = possible_settings[0]
    else:
        write_log(f"selected show settings are length {len(possible_settings)}")
        selected_show_settings = {}

    # Default number of episodes unless previously specified
    number_of_episodes: int = selected_show_settings.get(
        "number_of_episodes", default_number_of_episodes
    )
    write_log(f"Number of episodes: {number_of_episodes}")

    excluded_episodes: list[dict[str, str | int]] = selected_show_settings.get(
        "exclusions", []
    )
    write_log(f"Exclusions: {excluded_episodes}")

    return number_of_episodes, excluded_episodes


def select_number_of_episodes(window: xbmcgui.Dialog, tv_show_title: str) -> int | None:
    """User selection for number of episodes to select for a given show or None"""
    number_of_episodes: str = window.input(
        f"Select the number of episodes for {tv_show_title}", type=xbmcgui.INPUT_NUMERIC
    )

    if number_of_episodes:
        number_of_episodes_int: int = int(number_of_episodes)
        return number_of_episodes_int

    else:
        return None


def define_exclusions(
    window: xbmcgui.Dialog,
    tv_show_id: int,
    tv_show_title: str,
    excluded_episodes: list[dict],
) -> list[dict]:
    """Return of list of dictionaries containing id/title for episodes to be excluded, preselect if applicable"""
    selected_show_episodes: list[dict] = list_of_episodes_by_show_id(tv_show_id)
    episode_titles: list[str] = sorted(
        [episode.get("title") for episode in selected_show_episodes]
    )

    preselected_titles: list[str] = [item.get("title") for item in excluded_episodes]
    preselected_idx: list[int] = [
        episode_titles.index(title) for title in preselected_titles
    ]

    excluded_indexes: list[int] = window.multiselect(
        f"Select episodes to exclude from {tv_show_title}, press ok for None",
        episode_titles,
        preselect=preselected_idx,
    )

    if not excluded_indexes:
        excluded_indexes = []

    excluded_titles: list[str] = [episode_titles[index] for index in excluded_indexes]
    excluded_episodes: list[dict] = [
        {"id": episode.get("episodeid"), "title": episode.get("title")}
        for episode in selected_show_episodes
        if episode.get("title") in excluded_titles
    ]

    return excluded_episodes


def update_shows_config(
    config: dict[str, list[dict]],
    tv_shows_configurations: list[dict],
    tv_show_id: int,
    tv_show_title: str,
    number_of_episodes: int | None = None,
    excluded_episodes: list[dict] | None = None,
):
    """Overwrite config entry of a given show"""
    # Remove existing show config
    tv_shows_configurations: list[dict] = [
        item for item in tv_shows_configurations if item.get("id") != tv_show_id
    ]

    # Write updates to file, convert id to string for JSON key
    new_show_config: dict[str, str | int | list] = {
        "id": tv_show_id,
        "title": tv_show_title,
    }

    if number_of_episodes:
        new_show_config["number_of_episodes"] = number_of_episodes
    if excluded_episodes:
        new_show_config["exclusions"] = excluded_episodes

    tv_shows_configurations.append(new_show_config)

    write_log(f"Updated TV Shows configurations: {tv_shows_configurations}")

    config["tvshow"] = tv_shows_configurations

    write_to_config(config)


def configure_single_show(tv_show_id: int, tv_show_title: str) -> None:
    """Configuration for a given show"""

    addon = xbmcaddon.Addon()
    window: xbmcgui.Dialog = xbmcgui.Dialog()

    while True:
        config: dict[str, list[dict]] = open_config_file()
        tv_shows_configurations: list[dict] = config.get("tvshow")
        default_number_of_episodes: int = json.loads(addon.getSetting("default_number_of_episodes"))

        write_log(f"Retrieved all tv show settings: {tv_shows_configurations}")

        number_of_episodes: int
        excluded_episodes: list[dict]

        number_of_episodes, excluded_episodes = obtain_show_config(
            tv_show_id=tv_show_id,
            tv_show_title=tv_show_title,
            shows_config=tv_shows_configurations,
            default_number_of_episodes=default_number_of_episodes
        )

        options = [
            f"Number of Episodes: {number_of_episodes}",
            f"Exclude Episodes ({len(excluded_episodes)})",
            "Clear Configuration",
        ]

        choice = window.select(f"Configure {tv_show_title}", options)

        if choice == -1 or choice > len(options):
            write_log(f"Done configuring show: {tv_show_title}")
            break

        # Number of episodes
        elif choice == 0:
            number_of_episodes: int = select_number_of_episodes(
                window=window, tv_show_title=tv_show_title
            )
            if number_of_episodes:
                update_shows_config(
                    config,
                    tv_shows_configurations,
                    tv_show_id,
                    tv_show_title,
                    number_of_episodes,
                    excluded_episodes,
                )

        # Exclusions
        elif choice == 1:
            excluded_episodes: list[dict] = define_exclusions(
                window=window,
                tv_show_title=tv_show_title,
                tv_show_id=tv_show_id,
                excluded_episodes=excluded_episodes,
            )
            update_shows_config(
                config,
                tv_shows_configurations,
                tv_show_id,
                tv_show_title,
                number_of_episodes,
                excluded_episodes,
            )

        elif choice == 2:
            update_shows_config(
                config, tv_shows_configurations, tv_show_id, tv_show_title
            )
            xbmcgui.Dialog().notification(
                f"Cleared {tv_show_title} configuration",
                f"Using default values",
                xbmcgui.NOTIFICATION_INFO,
                3000,
            )


def configure_shows() -> None:
    """Selection window to configure individual shows"""
    window = xbmcgui.Dialog()

    while True:
        config: dict[str, list[dict]] = open_config_file()

        tv_show_selections: list[dict] = config.get("tvshow")

        write_log(f"Selected TV Shows: {tv_show_selections}")

        titles: list[str] = sorted([item.get("title") for item in tv_show_selections])

        choice: int = window.select(
            "Select TV Show for additional configuration", list=titles
        )

        if choice == -1 or choice > len(titles):
            write_log("Show configuration exited")
            break

        elif choice != -1:
            title: str = titles[choice]
            tv_show_id: int = [
                show.get("id")
                for show in tv_show_selections
                if show.get("title") == title
            ][0]
            configure_single_show(tv_show_id=int(tv_show_id), tv_show_title=title)


def list_smart_playlists() -> list[dict[str, str]]:
    """Return a list of smart playlist dictionaries, name, path keys """
    smart_playlists = []
    paths = ["special://profile/playlists/video/", "special://xbmc/system/playlists/video/"]

    for path in paths:
        dirs, files = xbmcvfs.listdir(path)
        playlists = [f for f in files if f.endswith(".xsp")]
        for playlist in playlists:
            filepath = path + playlist

            file = xbmcvfs.File(filepath)
            xml_data = file.read()
            file.close()

            root = ET.fromstring(xml_data)
            title = root.findtext("name")

            smart_playlists.append({"title": title, "path": filepath})

    write_log(f"Smart Playlists: {smart_playlists}")

    return smart_playlists


def select_smart_playlists() -> None:
    """Selection window for smart playlists"""
    config: dict[str, list] = open_config_file()

    preselected_smart_playlists: list[dict[str,str]] = config.get("smart", [])
    preselected_titles:list[str] = [playlist.get("title") for playlist in preselected_smart_playlists]

    playlists:list[dict[str,str]] = list_smart_playlists()

    available_titles:list[str] = sorted([playlist.get("title") for playlist in playlists])

    preselected_idx:list[int] = [available_titles.index(title) for title in preselected_titles if title in available_titles]

    choices: list[int] = xbmcgui.Dialog().multiselect(
        "Select Smart Playlists", available_titles, preselect=preselected_idx
    )

    if choices:
        selected_titles: list[str] = [available_titles[index] for index in choices]
        latest_playlist_selection: list[dict[str,str]] = [playlist for playlist in playlists if playlist.get("title") in selected_titles]
        write_log(f"Latest smart playlist selection: {latest_playlist_selection}")
        config["smart"] = latest_playlist_selection
        write_to_config(config)


def review_manual_tv_show_selections(tv_show_config:list, default_number_of_episodes:int) -> tuple[int, str]:
    """Calculate total number of expected episodes and produce user-friendly text for display"""
    total_number_of_episodes = 0
    shows_text = []
    # {"id": 101, "title": "show_title", "number_of_episodes": 10, "exclusions": [{"id": 1001, "title": "episode_title"}]}
    for show in tv_show_config:
        show_id:int = show.get("id")
        title:str = show.get("title")
        number_of_episodes:int = show.get("number_of_episodes", default_number_of_episodes)
        exclusions:list[dict] = show.get("exclusions", [])

        # Account for shows with fewer number of episodes than the user defined/default selection number
        excluded_ids:list[int] = [episode.get("id") for episode in exclusions]
        total_episodes:list[dict] = list_of_episodes_by_show_id(show_id)
        eligible_episodes = [episode for episode in total_episodes if episode.get("episodeid") not in excluded_ids]

        if number_of_episodes > len(eligible_episodes):
            number_of_episodes = len(eligible_episodes)

        total_number_of_episodes += number_of_episodes

        text = f"[{title}] [{number_of_episodes} episodes]\n"

        if len(exclusions) > 0:
            exclusion_text = "\n".join(f"        {episode.get('title')}" for episode in exclusions)
            exclusion_text = f"    excluding:\n{exclusion_text}\n"
            text = text + exclusion_text

        shows_text.append(text)

    shows_text = sorted(shows_text)

    final_text = "\n".join(shows_text)

    message = final_text if final_text else " "

    return total_number_of_episodes, message


def review_selections() -> None:
    """Provide a user-friendly display for all the media selections and defined criteria"""
    window = xbmcgui.Dialog()
    addon = xbmcaddon.Addon()

    while True:
        selections: dict[str, list] = open_config_file()

        number_of_movies: int = json.loads(addon.getSetting("number_of_movies"))
        default_number_of_episodes: int = json.loads(
            addon.getSetting("default_number_of_episodes")
        )

        tv_shows:list = selections.get("tvshow")
        movies:list = selections.get("movie")

        if number_of_movies >= len(movies):
            number_of_movies = len(movies)

        total_episodes:int
        shows_text:str
        total_episodes, shows_text = review_manual_tv_show_selections(tv_shows, default_number_of_episodes)

        choices = [f"Movies ({number_of_movies})", f"TV Shows ({total_episodes})"]

        choice: int = window.select(
            f"Current Selections ({total_episodes + number_of_movies} items total)",
            list=choices,
        )

        if choice == -1 or choice > len(choices):
            break

        # Movies
        elif choice == 0:
            movie_selection = sorted([movie.get("title") for movie in movies])
            movie_text = "\n".join(movie_selection)

            message = movie_text if movie_text else " "

            heading = f"Movie selections ({number_of_movies} title(s) to be randomly selected from this list)"
            if number_of_movies == len(movie_selection):
                heading = f"Movie selections (all {number_of_movies} title(s) to be selected from this list)"

            window.textviewer(
                heading=heading,
                text=message,
            )

        # TV Shows
        elif choice == 1:

            window.textviewer(
                heading=f"TV Show selections ({total_episodes} items in total)",
                text=shows_text,
            )


def review_smart_playlist_selections() -> None:
    """Provide a user-friendly display for media selections defined in smart playlists"""
    window = xbmcgui.Dialog()

    total_episodes = 0
    total_movies = 0

    playlist_text = []

    selections: dict[str, list] = open_config_file()
    playlists = selections.get("smart", [])
    for playlist in playlists:
        playlist_counts:dict[str,int] = {}
        title = playlist.get("title")
        path = playlist.get("path")

        files = single_smart_playlist_info(path).get("result", {}).get("files", {})
        playlist_episodes, playlist_movies = gather_single_smart_playlist_media(files)

        playlist_counts["episodes"] = len(playlist_episodes)
        playlist_counts["movies"] = len(playlist_movies)

        total_movies += playlist_counts.get("movies")
        total_episodes += playlist_counts.get("episodes")

        text = f"[{title}] [{playlist_counts.get('movies')} movies {playlist_counts.get('episodes')} episodes]\n"

        playlist_text.append(text)

    playlist_text = sorted(playlist_text)

    final_text = "\n".join(playlist_text)

    message = final_text if final_text else " "

    window.textviewer(heading=f"Smart Playlist selections ({total_episodes + total_movies}) items total", text=message)
