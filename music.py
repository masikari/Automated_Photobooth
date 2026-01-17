# music.py
import os
import shutil
import subprocess
import yt_dlp
import pygame
import tkinter as tk
from tkinter import simpledialog, messagebox

pygame.mixer.init()

# File paths
PREVIEW_FILE = "preview_temp.mp3"
SELECTED_FILE = "selected_song.mp3"

# Logging will be handled via main.py
log_callback = print  # default fallback

def set_log_callback(callback):
    """Set log function from main.py"""
    global log_callback
    log_callback = callback

def log(msg):
    if log_callback:
        log_callback(msg)
    print(msg)

# --- YouTube search ---
def search_youtube(query, max_results=5):
    ydl_opts = {
        'quiet': True,
        'skip_download': True,
        'format': 'bestaudio/best',
        'default_search': f'ytsearch{max_results}'
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)
    results = []
    if 'entries' in info:
        for entry in info['entries']:
            results.append({'title': entry.get('title'), 'url': entry.get('webpage_url')})
    return results

# --- Preview song ---
def preview_song(youtube_url):
    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": PREVIEW_FILE,
        "quiet": True,
        "noplaylist": True,
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "128"
        }]
    }
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])
    try:
        subprocess.Popen(["vlc", "--play-and-exit", PREVIEW_FILE])
        log("Previewing song...")
    except Exception as e:
        log(f"Failed to play preview: {e}")

# --- Select song ---
def select_song(youtube_url):
    if os.path.exists(PREVIEW_FILE):
        shutil.copy(PREVIEW_FILE, SELECTED_FILE)
        try: os.remove(PREVIEW_FILE)
        except: pass
        log("Song selected from preview!")
    else:
        ydl_opts = {
            "format": "bestaudio/best",
            "outtmpl": SELECTED_FILE,
            "quiet": True,
            "noplaylist": True,
            "postprocessors": [{
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192"
            }]
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
        log("Song downloaded directly as selection.")

# --- Tkinter music search ---
def search_music():
    root = tk.Tk()
    root.withdraw()  # hide root window for simpledialog
    query = simpledialog.askstring("Search Music", "Enter song or artist:")
    if not query:
        return

    win = tk.Toplevel()
    win.title("Music Results")

    try:
        videos = search_youtube(query, max_results=6)
        for i, v in enumerate(videos):
            title = v['title']
            link = v['url']
            tk.Label(win, text=title, wraplength=500, justify='left').grid(row=i, column=0, sticky='w')
            tk.Button(win, text="Preview", command=lambda u=link: preview_song(u)).grid(row=i, column=1)
            tk.Button(win, text="Select", command=lambda u=link: select_song(u)).grid(row=i, column=2)
    except Exception as e:
        messagebox.showerror("Search Error", str(e))

# --- Play/Stop selected song ---
def play_selected_song():
    if os.path.exists(SELECTED_FILE):
        pygame.mixer.music.load(SELECTED_FILE)
        pygame.mixer.music.play()
        log("Playing selected song...")
    else:
        log("[ERR] No selected song available!")

def stop_music():
    pygame.mixer.music.stop()
