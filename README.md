# Kodi Smart-Ish Playlist
---

A quick and dirty add-on for Kodi that builds a playlist based on the criteria provided for the script.

Configure it to your needs, then copy/zip the folder into an add-on and install.

The default addon.xml implements this as a script that can be run on demand.  The optional file will convert the add-on into a service that runs once at startup.

Suggestions for improvement/contributions are welcome.

#### Design
---

Make all of your changes to the default.py file.  In order to function correctly, ensure the titles are exact.

TV Shows
```bash
my_shows = {
  "Show Title": [
    10, # Number of episodes to select 
    True, # Random selection True/False, False will select episodes sequentially
    ["Episode to Exclude", "Another episode to exclude"] # Episodes to exclude from selection
    ],
  
  "Second Show": [
    5,
    True,
    [None] # Do not exclude any episodes
    
  ],
  ...
}
```

Movies

```bash
my_movies = [
  "Movie Title", # Exact title match needed
  "Second Movie",
  ...
]
```

Variables

```bash
number_of_movies_to_select = 5 # Number of movies to randomly select from my_movies
playlist = 1 # Default playlist id

clear_existing_playlist = True # Empty the selected playlist before adding to it, recommended if using the default playlist
autostart = True # Start playlist once built
shuffle = True # Shuffle the playlist once played, not applicable if autostart=False

cancel_dialog_visible = True # Display message to cancel the playlist build, helpful if configured as service that runs at start
cancel_dialog_title = "Building Playlist" 
cancel_dialog_message = "Initializing..."
```

Export

The easiest method is to copy the entire script.video.smartishplaylist folder, modify the default.py file, and zip the whole thing. 
Then it's ready to be installed.

#### Disclaimer
---
This add-on is not part of the official repository and is not responsible for any issues that you encounter with your Kodi installation.
Please review the code if you are concerned that it may conflict with your existing system. 
This project assumes that you legally own any and all media in your library.  When in doubt, please consult applicable copyright laws.
