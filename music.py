import os
import subprocess
import yt_dlp
import pygame

from config import MUSIC_FILE, PREVIEW_FILE
from logger import log

pygame.mixer.init()

_vlc_process = None

# === YOUTUBE SEARCH / PREVIEW ===
def search_youtube(query, max_results=5):
    ydl_opts = {'quiet': True, 'skip_download': True, 'format': 'bestaudio/best', 'default_search': f'ytsearch{max_results}'}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        info = ydl.extract_info(query, download=False)
    results = []
    if 'entries' in info:
        for entry in info['entries']:
            results.append({'title': entry.get('title'), 'url': entry.get('webpage_url')})
    return results

def preview_song(youtube_url):
    ydl_opts = {"format": "bestaudio/best", "outtmpl": "preview_temp.%(ext)s",
                "quiet": True, "noplaylist": True,
                "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "128"}]}
    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])
    subprocess.Popen(["vlc", "--play-and-exit", PREVIEW_FILE])

def select_song(youtube_url):
    if os.path.exists(PREVIEW_FILE):
        shutil.copy(PREVIEW_FILE, SELECTED_FILE)
        try:
            os.remove(PREVIEW_FILE)
        except: pass
        log("Song selected from preview!")
    else:
        ydl_opts = {"format": "bestaudio/best", "outtmpl": "selected_song.%(ext)s",
                    "quiet": True, "noplaylist": True,
                    "postprocessors": [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3", "preferredquality": "192"}]}
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([youtube_url])
        log("Song downloaded directly as selection.")

def search_music(auto_start=False):
    query = simpledialog.askstring("Search Music", "Enter song or artist:")
    if not query: return
    win = tk.Toplevel(root)
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

# SESSION
pygame.mixer.init()
def play_selected_song():
    if os.path.exists(SELECTED_FILE):
        pygame.mixer.music.load(SELECTED_FILE)
        pygame.mixer.music.play()
        log(" Playing selected song...")
    else:
        log("[ERR] No selected song available!")
