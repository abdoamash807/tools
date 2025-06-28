import argparse
import requests
import json

async def fetch_movie_data_by_imdb(imdb_id: str):
    TMDB_API_BASE = "https://api.themoviedb.org/3"
    IMAGE_BASE_URL = "https://image.tmdb.org/t/p/original"

    headers = {
        "accept": "application/json",
        "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlZDA5NThkYmNlYmIzMzVmMGI2MjVkMGJkYmQxMjY0YyIsIm5iZiI6MTc0Njc1NTU3Mi45ODEsInN1YiI6IjY4MWQ1ZmY0OGZkM2NkYjFjZGMxZGU1NyIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.NRLLiARxx8WH5ZaQsqdxRWJdsx26uHZZatD2tXB8CyM"
    }

    def get_json(url):
        resp = requests.get(url, headers=headers)
        return resp.json() if resp.ok else {}

    find_url = f"{TMDB_API_BASE}/find/{imdb_id}?external_source=imdb_id"
    resp = get_json(find_url)
    movie_results = resp.get("movie_results", [])
    if not movie_results:
        return {"error": "No movie found with this IMDb ID."}

    movie_id = movie_results[0]["id"]
    ext = get_json(f"{TMDB_API_BASE}/movie/{movie_id}/external_ids")
    en = get_json(f"{TMDB_API_BASE}/movie/{movie_id}?language=en-US")
    ar = get_json(f"{TMDB_API_BASE}/movie/{movie_id}?language=ar")
    credits = get_json(f"{TMDB_API_BASE}/movie/{movie_id}/credits")
    vids = get_json(f"{TMDB_API_BASE}/movie/{movie_id}/videos").get("results", [])
    rels = get_json(f"{TMDB_API_BASE}/movie/{movie_id}/release_dates").get("results", [])
    images = get_json(f"{TMDB_API_BASE}/movie/{movie_id}/images")

    # Age Rating / Certification
    certification = None
    for country in rels:
        if country["iso_3166_1"] == "US":
            for d in country.get("release_dates", []):
                if d.get("certification"):
                    certification = d["certification"]
                    break
        if certification:
            break

    # Logo
    en_logos = [l for l in images.get("logos", []) if l.get("iso_639_1") == "en"]
    logo_url = IMAGE_BASE_URL + en_logos[0]["file_path"] if en_logos else None

    # Final result dict
    entry = {
        "title_en":            en.get("title"),
        "title_ar":            ar.get("title"),
        "overview_en":         en.get("overview"),
        "overview_ar":         ar.get("overview"),
        "runtime":             en.get("runtime"),
        "genres_en":           [g["name"] for g in en.get("genres", [])],
        "genres_ar":           [g["name"] for g in ar.get("genres", [])],
        "imdb_id":             imdb_id,
        "release_date":        en.get("release_date", "").split("-")[0],
        "status":              en.get("status"),
        "original_language":   en.get("original_language"),
        "production_companies":[c["name"] for c in en.get("production_companies", [])],
        "production_countries":[c["iso_3166_1"] for c in en.get("production_countries", [])],
        "age_rating":          certification,
        "trailer":             next(
                                    (f"https://www.youtube.com/watch?v={v['key']}"
                                     for v in vids if v["site"] == "YouTube" and v["type"] == "Trailer"),
                                    None
                                ),
        "directors":           [c["name"] for c in credits.get("crew", []) if c["job"] == "Director"],
        "writers":             [c["name"] for c in credits.get("crew", []) if c["job"] in ("Writer", "Screenplay", "Story")],
        "cast":                [c["name"] for c in credits.get("cast", [])[:10]],
        "backdrop":            IMAGE_BASE_URL + images["backdrops"][0]["file_path"] if images.get("backdrops") else None,
        "poster":              IMAGE_BASE_URL + images["posters"][0]["file_path"]   if images.get("posters")   else None,
        "logo":                logo_url
    }

    return entry


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch TMDB data using IMDb ID")
    parser.add_argument("--imdb", required=True, help="IMDb ID to search for (e.g. 'tt1160419')")
    args = parser.parse_args()

    result = fetch_movie_data_by_imdb(args.imdb)
    print(json.dumps(result, ensure_ascii=False, indent=2))