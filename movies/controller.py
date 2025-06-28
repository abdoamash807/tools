# At the very top of movies/controller.py, after shebang if any
import sys
import os
import requests
# Get the absolute path of the directory containing this script
script_dir = os.path.dirname(os.path.abspath(__file__))
# Get the path to the 'uploader' directory (assuming it's the parent of 'movies')
uploader_dir = os.path.dirname(script_dir)
# Add the 'uploader' directory to sys.path
if uploader_dir not in sys.path:
    sys.path.insert(0, uploader_dir)

# Now your imports
from yts import fetch_yts_movie
from movie_info import fetch_movie_data_by_imdb
from download.download import download_aria2c
from babelfish import Language
import subliminal
import subtitles
import subprocess
import asyncio

csv_file = "/home/kda/uploader/movies/fasel.csv"

async def main():
    api = "http://localhost:5000"
    res = requests.get(f"{api}/movie")
    title =""
    if res.status_code == 200:
        data = res.json()
        title = data["title"]
    data = await fetch_yts_movie(title) 
    folder_name=''
    for torrent in data.get('torrents', []):
        if torrent['codec'] == 'x264' and torrent['type'] =='web': 
            download_path = os.path.join("downloads", data['imdb_id']) 
            folder_name = f"{torrent['quality']}_{data['title'].replace(' ', '_')}"  
            download_path = await download_aria2c(download_path, torrent['magnet'], folder_name)
            if os.path.exists(download_path):
                subliminal.region.configure('dogpile.cache.memory')
                videos = subliminal.scan_videos(download_path, recursive=True)
                if videos:
                    langs = {Language('en'), Language('ar')}
                    downloaded = subliminal.download_best_subtitles(videos, langs)
                    subliminal.save_subtitles(videos, downloaded)
    requests.post(f"{api}/movie/{title}")
if __name__ == "__main__":
    asyncio.run(main())