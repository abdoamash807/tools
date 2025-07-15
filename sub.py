import requests
from bs4 import BeautifulSoup
import os


def fetch_arabic_subtitles(url):
    base_url = "https://yifysubtitles.ch"
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    arabic_links = []

    # Find all <tr> rows
    for row in soup.find_all("tr"):
        lang_cell = row.find("span", class_="sub-lang")
        if lang_cell and lang_cell.text.strip().lower() == "arabic":
            link_tag = row.find("a", href=True)
            if link_tag:
                href = link_tag["href"]
                if href.startswith("/subtitles/"):
                    # Convert /subtitles/... ➜ /subtitle/....zip
                    slug = href.replace("/subtitles/", "")
                    final_url = f"{base_url}/subtitle/{slug}.zip"
                    arabic_links.append(final_url)
    return arabic_links


def download_subtitle(url: str, save_path: str):
    headers = {
        "User-Agent": "Mozilla/5.0"
    }
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        filename = url.split("/")[-1]  # e.g. joker-2019-arabic-yify-2575.zip
        full_path = os.path.join(save_path, filename)
        with open(full_path, "wb") as f:
            f.write(response.content)
        print(f"✅ Downloaded: {full_path}")
    else:
        print(f"❌ Failed to download {url} (status {response.status_code})")


if __name__ == "__main__":
    url = "https://yifysubtitles.ch/movie-imdb/tt7286456"


    subtitle_links = fetch_arabic_subtitles(url)
    print("Arabic subtitles found:", subtitle_links)

