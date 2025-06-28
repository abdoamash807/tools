import argparse
import requests
import json

def fetch_movie_data(title: str, year: int):
    TMDB_API_BASE = "https://api.themoviedb.org/3"
    IMAGE_BASE_URL = "https://image.tmdb.org/t/p/original"

    headers = {
        "accept": "application/json",
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlZDA5NThkYmNlYmIzMzVmMGI2MjVkMGJkYmQxMjY0YyIsIm5iZiI6MTc0Njc1NTU3Mi45ODEsInN1YiI6IjY4MWQ1ZmY0OGZkM2NkYjFjZGMxZGU1NyIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.NRLLiARxx8WH5ZaQsqdxRWJdsx26uHZZatD2tXB8CyM"
    }

    # Step 1: Search
    search_url = (
        f"{TMDB_API_BASE}/search/movie"
        f"?query={requests.utils.quote(title)}"
        f"&include_adult=false"
        f"&language=en-US"
        f"&page=1"
        f"&year={year}"
    )
    resp = requests.get(search_url, headers=headers)
    movies = resp.json().get("results", [])

    # Strict filter by release year
    movies = [m for m in movies if m.get("release_date", "").startswith(str(year))]

    results = []
    for m in movies:
        movie_id = m["id"]

        # External IDs
        ext = requests.get(f"{TMDB_API_BASE}/movie/{movie_id}/external_ids", headers=headers).json()
        imdb_id = ext.get("imdb_id")

        # EN & AR details
        en = requests.get(f"{TMDB_API_BASE}/movie/{movie_id}?language=en-US", headers=headers).json()
        ar = requests.get(f"{TMDB_API_BASE}/movie/{movie_id}?language=ar", headers=headers).json()

        # Credits
        credits = requests.get(f"{TMDB_API_BASE}/movie/{movie_id}/credits", headers=headers).json()

        # Videos
        vids = requests.get(f"{TMDB_API_BASE}/movie/{movie_id}/videos", headers=headers).json().get("results", [])

        # Release dates → certification
        rels = requests.get(f"{TMDB_API_BASE}/movie/{movie_id}/release_dates", headers=headers).json().get("results", [])
        certification = None
        for country in rels:
            if country["iso_3166_1"] == "US":
                for d in country.get("release_dates", []):
                    if d.get("certification"):
                        certification = d["certification"]
                        break
            if certification:
                break

        # Images + English logo
        images = requests.get(f"{TMDB_API_BASE}/movie/{movie_id}/images", headers=headers).json()
        en_logos = [l for l in images.get("logos", []) if l.get("iso_639_1") == "en"]
        logo_url = IMAGE_BASE_URL + en_logos[0]["file_path"] if en_logos else None

        entry = {
            "title_en":            en.get("title"),
            "title_ar":            ar.get("title"),
            "overview_en":         en.get("overview"),
            "overview_ar":         ar.get("overview"),
            "runtime":             en.get("runtime"),
            "genres_en":           [g["name"] for g in en.get("genres", [])],
            "genres_ar":           [g["name"] for g in ar.get("genres", [])],
            "imdb_id":             imdb_id,
            "production_companies":[c["name"] for c in en.get("production_companies", [])],
            "production_countries":[c["iso_3166_1"] for c in en.get("production_countries", [])],
            "age_rating":          certification,
            "trailer":             next(
                                      (f"https://www.youtube.com/watch?v={v['key']}"
                                       for v in vids if v["site"] == "YouTube" and v["type"] == "Trailer"),
                                      None
                                   ),
            "directors":           [c["name"] for c in credits.get("crew", []) if c["job"] == "Director"],
            "writers":             [c["name"] for c in credits.get("crew", []) if c["job"] in ("Writer","Screenplay","Story")],
            "cast":                [c["name"] for c in credits.get("cast", [])[:10]],
            "backdrop":            IMAGE_BASE_URL + images["backdrops"][0]["file_path"] if images.get("backdrops") else None,
            "poster":              IMAGE_BASE_URL + images["posters"][0]["file_path"]   if images.get("posters")   else None,
            "logo":                logo_url
        }
        results.append(entry)

    # Output
    print(json.dumps(results, ensure_ascii=False, indent=2))
    with open(f"{title.replace(' ', '_').lower()}_{year}_full.json", "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch TMDB data for a given movie title and year")
    parser.add_argument("--title",  required=True, help="Movie title to search for (e.g. 'Dune')")
    parser.add_argument("--year",   type=int, required=True, help="Release year (e.g. 2024)")
    args = parser.parse_args()

    fetch_movie_data(args.title, args.year)