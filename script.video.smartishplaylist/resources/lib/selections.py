import xbmcgui
import json
import xbmcaddon

from typing import Literal

from resources.lib.queries import list_of_all_tv_shows, list_all_movies, list_of_episodes_by_show_id
from resources.lib.logger import write_log
from resources.lib.config import open_config_file, write_to_config


def title_by_id_number(media_id:int, all_media_info: list[dict], media_type:Literal["movie", "tvshow"]) -> str:
    """Search library based on media id number and return its string title"""
    titles:list[str] = [item.get("title") for item in all_media_info if item.get(f"{media_type}id") == media_id]

    if len(titles) == 0:
        write_log(write_log(f"{media_type} id {media_id} returns zero titles: {titles}"))
        titles.append("Error no title")

    elif len(titles) > 1:
        write_log(f"{media_type} id {media_id} returns multiple titles: {titles}, selecting first entry")

    title:str = titles[0]

    return title


def media_titles_with_preselection_idx(retrieved_info: list[dict], media_type:Literal["movie", "tvshow"], all_media_info: list[dict]) -> tuple[list[str], list[int]]:
    """Return a tuple containing a list of sorted media titles and a list of preselection idx values determined by info retrieved from settings"""

    id_title_pairs:dict[int, str] = {media.get(f"{media_type}id"): media.get("title") for media in all_media_info}
    write_log(f"{media_type} title_id_pairs: {id_title_pairs}")

    media_titles:list[str] = sorted(id_title_pairs.values())
    write_log(f"{media_type} titles: {media_titles}")

    preselected_titles:list[str] = [item.get("title") for item in retrieved_info]
    write_log(f"Pre-selected {media_type} titles: {preselected_titles}")

    preselected_idx:list[int] = [media_titles.index(title) for title in preselected_titles]
    write_log(f"Pre-selected {media_type} idx: {preselected_idx}")

    return media_titles, preselected_idx


def select_media(media_type:Literal["movie", "tvshow"]) -> None:
    """Allow user to select titles from a window and save those selections to settings, check for previously select titles"""

    if media_type == "movie":
        all_media_info:list[dict] = list_all_movies()
        selection_text:str = "Select Movies"

    elif media_type == "tvshow":
        all_media_info:list[dict] = list_of_all_tv_shows()
        selection_text:str = "Select TV Shows"

    else:
        return None

    config_file:dict[str,list[dict]] = open_config_file()

    retrieved_info:list[dict] = config_file.get(media_type)

    titles:list[str]
    preselected_idx: list[int]
    titles, preselected_idx = media_titles_with_preselection_idx(retrieved_info=retrieved_info, media_type=media_type, all_media_info=all_media_info)

    choices:list[int] = xbmcgui.Dialog().multiselect(
        selection_text,
        titles,
        preselect=preselected_idx
    )

    if choices:
        selected_titles:list[str] = [titles[index] for index in choices]
        write_log(f"Selected {media_type} titles: {selected_titles}")

        selected_ids_titles:list[dict[str,str|int]] = [{"id": item.get(f"{media_type}id"), "title": item.get("title")} for item in all_media_info if item.get("title") in selected_titles]

        write_log(f"Selected {media_type} ids: {selected_ids_titles}")

        # Reconcile old/new titles to retain other settings
        existing_ids:list[int] = [item.get("id") for item in retrieved_info]
        new_ids:list[int] = [item.get("id") for item in selected_ids_titles]

        retained_items:list[dict] = [item for item in retrieved_info if item.get("id") in new_ids]
        new_items:list[dict] = [item for item in selected_ids_titles if item.get("id") not in existing_ids]

        updated_selections = retained_items + new_items

        config_file[media_type] = updated_selections

        write_to_config(config_file)

    return None


def obtain_show_config(tv_show_id:int, tv_show_title:str, shows_config:list[dict]) -> tuple[int,list]:
    """Return a tuple of a shows current configuration or default values: number of episodes, excluded episodes"""
    addon = xbmcaddon.Addon()
    possible_settings:list[dict] = [item for item in shows_config if item.get("id") == tv_show_id]
    write_log(f"{tv_show_title} settings: {possible_settings}")

    if len(possible_settings) > 0:
        selected_show_settings:dict[str,str|int|list] = possible_settings[0]
    else:
        write_log(f"selected show settings are length {len(possible_settings)}")
        selected_show_settings = {}

    default_number_of_episodes:int = json.loads(addon.getSetting("default_number_of_episodes"))
    # Default number of episodes unless previously specified
    number_of_episodes:int = selected_show_settings.get("number_of_episodes", default_number_of_episodes)
    write_log(f"Number of episodes: {number_of_episodes}")

    excluded_episodes:list[dict[str, str|int]] = selected_show_settings.get("exclusions", [])
    write_log(f"Exclusions: {excluded_episodes}")

    return default_number_of_episodes, excluded_episodes


def select_number_of_episodes(window:xbmcgui.Dialog, tv_show_title:str) -> int:
    number_of_episodes: int | None = int(window.input(f"Select the number of episodes for {tv_show_title}",
                                                      type=xbmcgui.INPUT_NUMERIC))

    while not number_of_episodes:
        number_of_episodes: int | None = int(
            window.input(f"Required: Select the number of episodes for {tv_show_title}",
                         type=xbmcgui.INPUT_NUMERIC))

    return number_of_episodes


def define_exclusions(window:xbmcgui.Dialog, tv_show_id:int, tv_show_title:str, excluded_episodes:list[dict]) -> list[dict]:
    """Return of list of dictionaries containing id/title for episodes to be excluded, preselect if applicable"""
    selected_show_episodes: list[dict] = list_of_episodes_by_show_id(tv_show_id)
    episode_titles:list[str] = sorted([episode.get("title") for episode in selected_show_episodes])

    preselected_titles:list[str] = [item.get("title") for item in excluded_episodes]
    preselected_idx:list[int] = [episode_titles.index(title) for title in preselected_titles]

    excluded_indexes:list[int] = window.multiselect(
        f"Select episodes to exclude from {tv_show_title}, press ok for None",
        episode_titles, preselect=preselected_idx
    )

    if not excluded_indexes:
        excluded_indexes = []

    excluded_titles:list[str] = [episode_titles[index] for index in excluded_indexes]
    excluded_episodes:list[dict] = [{"id": episode.get("episodeid"), "title": episode.get("title")} for episode in
                         selected_show_episodes if episode.get("title") in excluded_titles]

    return excluded_episodes


def update_shows_config(config:dict[str,list[dict]],tv_shows_configurations: list[dict], tv_show_id:int, tv_show_title:str, number_of_episodes:int, excluded_episodes: list[dict]):
        """Save to file"""
        # Remove existing show config
        tv_shows_configurations:list[dict] = [item for item in tv_shows_configurations if item.get("id") != tv_show_id]

        # Write updates to file, convert id to string for JSON key
        new_show_config:dict[str,str|int|list] = {
            "id": tv_show_id,
            "title": tv_show_title,
            "number_of_episodes": number_of_episodes,
            "exclusions": excluded_episodes
        }

        tv_shows_configurations.append(new_show_config)

        write_log(f"Updated TV Shows configurations: {tv_shows_configurations}")

        config["tvshow"] = tv_shows_configurations

        write_to_config(config)


def configure_single_show(tv_show_id:int, tv_show_title:str) -> None:
    """Configuration for a given show"""

    window:xbmcgui.Dialog = xbmcgui.Dialog()

    config:dict[str,list[dict]] = open_config_file()
    tv_shows_configurations: list[dict] = config.get("tvshow")
    write_log(f"Retrieved all tv show settings: {tv_shows_configurations}")

    number_of_episodes:int
    excluded_episodes: list[dict]

    number_of_episodes, excluded_episodes = obtain_show_config(tv_show_id=tv_show_id, tv_show_title=tv_show_title, shows_config=tv_shows_configurations)

    while True:
        options = [f"Number of Episodes: {number_of_episodes}", f"Exclude Episodes ({len(excluded_episodes)})"]

        choice = window.select(f"Configure {tv_show_title}", options)

        if choice == -1 or choice > len(options):
            break

        # Number of episodes
        elif choice == 0:
            number_of_episodes:int = select_number_of_episodes(window=window, tv_show_title=tv_show_title)
            update_shows_config(config, tv_shows_configurations, tv_show_id, tv_show_title, number_of_episodes, excluded_episodes)

        # Exclusions
        elif choice == 1:
            excluded_episodes:list[dict] = define_exclusions(window=window, tv_show_title=tv_show_title, tv_show_id=tv_show_id, excluded_episodes=excluded_episodes)
            update_shows_config(config, tv_shows_configurations, tv_show_id, tv_show_title, number_of_episodes, excluded_episodes)


def configure_shows() -> None:
    window = xbmcgui.Dialog()

    config:dict[str,list[dict]] = open_config_file()

    tv_show_selections:list[dict] = config.get("tvshow")

    write_log(f"Selected TV Shows: {tv_show_selections}")

    titles:list[str] = sorted([item.get("title") for item in tv_show_selections])

    choice:int = window.select("Select TV Show for additional configuration", list=titles)

    if choice != -1:
        title:str = titles[choice]
        tv_show_id:int = [show.get("id") for show in tv_show_selections if show.get('title') == title][0]
        configure_single_show(tv_show_id=int(tv_show_id), tv_show_title=title)
