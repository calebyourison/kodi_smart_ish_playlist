import xbmc
import xbmcaddon

addon = xbmcaddon.Addon()

if addon.getSettingBool("build_at_startup"):

    monitor = xbmc.Monitor()

    while not monitor.waitForAbort(0.5):
        if xbmc.getCondVisibility("Window.IsVisible(10000)"):
            break

    if not monitor.abortRequested():
        xbmc.executebuiltin("RunScript(script.video.smartishplaylist)")
