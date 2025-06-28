import requests
import urllib.parse

async def fetch_yts_movie(query: str):
    url = "https://yts.mx/api/v2/list_movies.json"
    params = {
        "query_term": query,
        "limit": 1
    }

    response = requests.get(url, params=params)
    if response.status_code != 200:
        return {"error": f"Request failed with status {response.status_code}"}

    data = response.json()
    if data["status"] != "ok" or data["data"]["movie_count"] == 0:
        return {"error": "Movie not found"}

    movie = data["data"]["movies"][0]
    result = {
        "title": movie['title_long'],
        "imdb_id": movie['imdb_code'],
        "year": movie['year'],
        "torrents": []
    }

    # common public trackers (you can add or remove as you like)
    trackers = [
        "udp://tracker.openbittorrent.com:80/announce",
        "udp://tracker.opentrackr.org:1337/announce",
        "udp://tracker.coppersurfer.tk:6969/announce",
        "udp://tracker.leechers-paradise.org:6969/announce",
    ]

    for torrent in movie['torrents']:
        infohash = torrent['hash']
        # Build a list of (key, value) pairs so that urlencode with doseq=True
        # will produce multiple &tr=... entries.
        qs = [
            ("xt", f"urn:btih:{infohash}"),
            ("dn", movie['title_long']),
        ]
        qs += [("tr", t) for t in trackers]

        magnet = "magnet:?" + urllib.parse.urlencode(qs, doseq=True)

        result["torrents"].append({
            "quality":   torrent['quality'],
            "type":      torrent['type'],
            "size":      torrent['size'],
            "codec":     torrent.get('video_codec', 'unknown'),
            "magnet":    magnet
        })

    return result