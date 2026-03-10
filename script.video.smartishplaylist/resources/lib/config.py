import os
import xbmcvfs
import json
import xbmcgui
from typing import Literal

addon_id = "script.video.smartishplaylist"

base_path = xbmcvfs.translatePath(f"special://profile/addon_data/{addon_id}/")

if not xbmcvfs.exists(base_path):
    xbmcvfs.mkdirs(base_path)

config_file_path = os.path.join(base_path, "config.json")


def default_config_file() -> None:
    """Write empty config file"""
    default_data: dict[str, list] = {
        "movie": [
            # {"id": 101, "title": "movie_title"}
        ],
        "tvshow": [
            # {"id": 10, "title": "example_title"},
            # {"id": 101, "title": "show_title", "number_of_episodes": 10, "exclusions": [{"id": 1001, "title": "episode_title"}]}
        ],
    }

    with xbmcvfs.File(config_file_path, "w") as file_path:
        file_path.write(json.dumps(default_data))


if not xbmcvfs.exists(config_file_path):
    default_config_file()


def open_config_file() -> dict[str, list]:
    """Return config file, dict of lists"""
    with xbmcvfs.File(config_file_path) as f:
        configuration: dict[str, list[dict]] = json.load(f)

    return configuration


def write_to_config(config: dict[str, list]) -> None:
    """Write new config"""
    with open(config_file_path, "w") as f:
        json.dump(config, f)


def clear_config_section(section: Literal["movie", "tvshow"]) -> None:
    """Read config, clear designated section, re-write"""
    window = xbmcgui.Dialog()

    confirmation = window.yesno(
        heading="Please confirm", message=f"This will erase all {section} selections"
    )

    if confirmation:
        config: dict[str, list] = open_config_file()
        config[section] = []
        write_to_config(config=config)

        window.notification(
            f"Reset complete",
            f"Cleared {section} selections",
            xbmcgui.NOTIFICATION_INFO,
            3000,
        )
