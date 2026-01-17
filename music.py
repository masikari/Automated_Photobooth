# Handles music search, preview, selection, and playback

import os
import subprocess
import yt_dlp
import pygame

from config import MUSIC_FILE, PREVIEW_FILE
from logger import log

pygame.mixer.init()

_vlc_process = None


# Search YouTube
def search_music(query: str, limit: int = 5) -> list:
    """
    Returns a list of {title, url}
    """
    opts = {
        "quiet": True,
        "skip_download": True,
        "default_search": f"ytsearch{limit}",
        "format": "bestaudio/best",
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(query, download=False)

    results = []
    for entry in info.get("entries", []):
        results.append({
            "title": entry.get("title"),
            "url": entry.get("webpage_url")
        })

    return results


# Preview Song
def preview_song(youtube_url: str):
    """
    Downloads short preview and plays via VLC
    """
    global _vlc_process

    # Stop previous preview
    if _vlc_process and _vlc_process.poll() is None:
        _vlc_process.kill()

    opts = {
        "format": "bestaudio/best",
        "outtmpl": PREVIEW_FILE,
        "quiet": True,
        "noplaylist": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "128",
        }],
    }

    with yt_dlp.YoutubeDL(opts) as ydl:
        ydl.download([youtube_url])

    _vlc_process = subprocess.Popen(
        ["vlc", "--play-and-exit", PREVIEW_FILE],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

    log("Music preview playing")

# Select Song
def select_song():
    """
    Moves preview to selected song (overwrite)
    """
    if not os.path.exists(PREVIEW_FILE):
        log("No preview file to select")
        return False

    os.replace(PREVIEW_FILE, MUSIC_FILE)
    log("Song selected successfully")
    return True


# Play Selected Song
def play_selected_song():
    """
    Plays selected song using pygame
    """
    if not os.path.exists(MUSIC_FILE):
        log("No selected song found")
        return False

    pygame.mixer.music.load(MUSIC_FILE)
    pygame.mixer.music.play()
    log("Selected song playing")
    return True


# Stop Music
def stop_music():
    pygame.mixer.music.stop()
