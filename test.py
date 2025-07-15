import argparse
import requests
import json

TMDB_API_BASE = "https://api.themoviedb.org/3"
IMAGE_BASE_URL = "https://image.tmdb.org/t/p/original"
HEADERS = {
    "accept": "application/json",
    "Authorization": "Bearer eyJhbGciOiJIUzI1NiJ9.eyJhdWQiOiJlZDA5NThkYmNlYmIzMzVmMGI2MjVkMGJkYmQxMjY0YyIsIm5iZiI6MTc0Njc1NTU3Mi45ODEsInN1YiI6IjY4MWQ1ZmY0OGZkM2NkYjFjZGMxZGU1NyIsInNjb3BlcyI6WyJhcGlfcmVhZCJdLCJ2ZXJzaW9uIjoxfQ.NRLLiARxx8WH5ZaQsqdxRWJdsx26uHZZatD2tXB8CyM"
}
def get_json(url, params=None):
    resp = requests.get(url, headers=HEADERS, params=params)
    return resp.json() if resp.ok else {}

def get_tv_id_by_title_and_year(title, year=None):
    params = {"query": title}
    if year:
        params["first_air_date_year"] = year
    res = get_json(f"{TMDB_API_BASE}/search/tv", params)
    results = res.get("results", [])
    return results[0]["id"] if results else None
def fetch_tv_data_by_id(tv_id: int):
    ext = get_json(f"{TMDB_API_BASE}/tv/{tv_id}/external_ids")
    imdb_id = ext.get("imdb_id")
    en = get_json(f"{TMDB_API_BASE}/tv/{tv_id}?language=en-US")
    ar = get_json(f"{TMDB_API_BASE}/tv/{tv_id}?language=ar")
    credits = get_json(f"{TMDB_API_BASE}/tv/{tv_id}/credits")
    vids = get_json(f"{TMDB_API_BASE}/tv/{tv_id}/videos").get("results", [])
    images = get_json(f"{TMDB_API_BASE}/tv/{tv_id}/images")

    en_logos = [l for l in images.get("logos", []) if l.get("iso_639_1") == "en"]
    logo_url = IMAGE_BASE_URL + en_logos[0]["file_path"] if en_logos else None

    # Fetch episodes per season
    seasons = en.get("seasons", [])
    episodes_per_season = []
    for season in seasons:
        season_number = season.get("season_number")
        if season_number is not None and season_number != 0:
            season_details = get_json(f"{TMDB_API_BASE}/tv/{tv_id}/season/{season_number}")
            episodes_per_season.append({
                "season": season_number,
                "episode_count": len(season_details.get("episodes", []))
            })

    entry = {
        "title_en":            en.get("name"),
        "title_ar":            ar.get("name"),
        "overview_en":         en.get("overview"),
        "overview_ar":         ar.get("overview"),
        "number_of_seasons":   en.get("number_of_seasons"),
        "number_of_episodes":  en.get("number_of_episodes"),
        "episodes_per_season": episodes_per_season,
        "genres_en":           [g["name"] for g in en.get("genres", [])],
        "genres_ar":           [g["name"] for g in ar.get("genres", [])],
        "imdb_id":             imdb_id,
        "first_air_date":      en.get("first_air_date", "").split("-")[0],
        "original_language":   en.get("original_language"),
        "production_companies":[c["name"] for c in en.get("production_companies", [])],
        "origin_countries":    en.get("origin_country", []),
        "trailer":             next(
                                    (f"https://www.youtube.com/watch?v={v['key']}"
                                     for v in vids if v["site"] == "YouTube" and v["type"] == "Trailer"),
                                    None
                                ),
        "directors":           [c["name"] for c in credits.get("crew", []) if c["job"] == "Director"],
        "cast":                [c["name"] for c in credits.get("cast", [])[:10]],
        "backdrop":            IMAGE_BASE_URL + images["backdrops"][0]["file_path"] if images.get("backdrops") else None,
        "poster":              IMAGE_BASE_URL + images["posters"][0]["file_path"]   if images.get("posters")   else None,
        "logo":                logo_url
    }

    return entry

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Fetch TMDB TV show data using title/year or IMDb ID")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--imdb", help="IMDb ID to search for (e.g. 'tt1160419')")
    group.add_argument("--title", help="TV show title to search for (e.g. 'Breaking Bad')")
    parser.add_argument("--year", help="First air year (optional)", type=int)
    args = parser.parse_args()

    if args.imdb:
        find_url = f"{TMDB_API_BASE}/find/{args.imdb}?external_source=imdb_id"
        find_result = get_json(find_url)
        tv_results = find_result.get("tv_results", [])
        if not tv_results:
            print(json.dumps({"error": "No TV show found with this IMDb ID."}, ensure_ascii=False, indent=2))
        else:
            tv_id = tv_results[0]["id"]
            result = fetch_tv_data_by_id(tv_id)
            print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        tv_id = get_tv_id_by_title_and_year(args.title, args.year)
        if not tv_id:
            print(json.dumps({"error": "No TV show found with this title/year."}, ensure_ascii=False, indent=2))
        else:
            result = fetch_tv_data_by_id(tv_id)
            print(json.dumps(result, ensure_ascii=False, indent=2))