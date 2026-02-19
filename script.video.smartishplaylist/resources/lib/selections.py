import xbmcgui
import json
import xbmcaddon
from typing import Literal

from resources.lib.queries import list_of_all_tv_shows, list_all_movies, list_of_episodes_by_show_id
from resources.lib.logger import write_log

def title_by_id_number(media_id:int, all_media_info: list[dict], media_type:Literal["movie", "tvshow"]) -> str:
    """Search library based on media id number and return its string title"""
    possible_titles = [item.get("title") for item in all_media_info if item.get(f"{media_type}id") == media_id]

    if len(possible_titles) == 0:
        write_log(write_log(f"{media_type} id {media_id} returns zero titles: {possible_titles}"))
        possible_titles.append("Error no title")

    elif len(possible_titles) > 1:
        write_log(f"{media_type} id {media_id} returns multiple titles: {possible_titles}, selecting first entry")

    title = possible_titles[0]

    return title


def media_titles_with_preselection_idx(retrieved_info: dict[int, str], media_type:Literal["movie", "tvshow"], all_media_info: list[dict]) -> tuple[list[str], list[int]]:
    """Return a tuple containing a list of sorted media titles and a list of preselection idx values determined by info retrieved from settings"""

    id_title_pairs = {media.get(f"{media_type}id"): media.get("title") for media in all_media_info}
    write_log(f"{media_type} title_id_pairs: {id_title_pairs}")

    media_titles = sorted(id_title_pairs.values())
    write_log(f"{media_type} titles: {media_titles}")

    preselected_titles = retrieved_info.values()
    write_log(f"Pre-selected {media_type} titles: {preselected_titles}")

    preselected_idx = [media_titles.index(title) for title in preselected_titles]
    write_log(f"Pre-selected {media_type} idx: {preselected_idx}")

    return media_titles, preselected_idx


def select_media(media_type:Literal["movie", "tvshow"]) -> None:
    """Allow user to select titles from a window and save those selections to settings, check for previously select titles"""
    addon = xbmcaddon.Addon()

    all_media_info = []
    selection_text = "Select"

    if media_type == "movie":
        all_media_info = list_all_movies()
        selection_text = f"{selection_text} Movies"
    if media_type == "tvshow":
        all_media_info = list_of_all_tv_shows()
        selection_text = f"{selection_text} TV Shows"

    retrieved_info = json.loads(addon.getSetting(f"selected_{media_type}") or "{}")

    titles, preselected_idx = media_titles_with_preselection_idx(retrieved_info=retrieved_info, media_type=media_type, all_media_info=all_media_info)

    choices = xbmcgui.Dialog().multiselect(
        selection_text,
        titles,
        preselect=preselected_idx
    )

    if choices:
        selected_titles = [titles[index] for index in choices]
        write_log(f"Selected {media_type} titles: {selected_titles}")

        selected_ids_titles = {item.get(f"{media_type}id"): item.get("title") for item in all_media_info if item.get("title") in selected_titles}

        write_log(f"Selected {media_type} ids: {selected_ids_titles}")

        if media_type == "tvshow":
            show_criteria(addon=addon, selected_ids_shows=selected_ids_titles)

        # Save {id:title, ...} for playlist build
        saved = addon.setSetting(f"selected_{media_type}", json.dumps(selected_ids_titles))


def show_criteria(addon, selected_ids_shows:dict[int, str]) -> None:
    """Allow user to define criteria for each selected TV Show: number of episodes to select and excluded episodes"""

    show_criteria_info = {}

    for show_id, title in selected_ids_shows.items():
        window = xbmcgui.Dialog()
        number_of_episodes = window.input(f"Select the number of episodes for {title}", type=xbmcgui.INPUT_NUMERIC)

        while not number_of_episodes:
            number_of_episodes = window.input(f"Required: Select the number of episodes for {title}",
                                              type=xbmcgui.INPUT_NUMERIC)


        write_log(f"Selected {number_of_episodes} episodes for {title}")

        show_episodes_info = list_of_episodes_by_show_id(show_id=show_id)
        episode_titles = sorted([episode.get("title") for episode in show_episodes_info])

        excluded_indexes = window.multiselect(
            f"Select episodes to exclude from {title}, press ok for None",
            episode_titles
        )
        if not excluded_indexes:
            excluded_indexes = []

        excluded_episode_titles = [episode_titles[index] for index in excluded_indexes]

        write_log(f"Excluding {excluded_episode_titles} for {title}")

        exclusions = {episode.get("episodeid"): episode.get("title") for episode in show_episodes_info if episode.get("title") in excluded_episode_titles}

        write_log(f"Exclusions {exclusions} for {title}")


        show_criteria_info[show_id] = {"title": title, "number_of_episodes": number_of_episodes, "exclusions": exclusions}

    write_log(f"TV Show criteria: {show_criteria_info}")
    saved = addon.setSetting("defined_show_criteria", json.dumps(show_criteria_info))


def display_selections():
    """Rough display of JSON data based on Movie and TV Show selections"""
    addon = xbmcaddon.Addon()

    movie_selections = json.loads(addon.getSetting("selected_movie") or {})
    movie_info = [title for title in movie_selections.values()]
    tv_show_selections = json.loads(addon.getSetting("defined_show_criteria") or {})
    tv_show_info = {
        item.get("title"):
            {
                "number_of_episodes": item.get("number_of_episodes"),
                "exclusions": item.get("exclusions")
            }
        for item in tv_show_selections.values()
    }

    all_selections = {"movies": movie_info, "tv shows": tv_show_info}
    all_selections = json.dumps(all_selections, indent=4)

    dialog = xbmcgui.Dialog()
    dialog.textviewer('Selections', all_selections)

