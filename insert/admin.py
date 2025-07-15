import requests



def upload_movie(
    title,
    duration,
    release_year,
    poster_url,
    backdrop_url,
    mobile_url,
    trailer_url,
    logo_url='',
    hot_video_url='',
    status='',
    age_rating='',
    subtitles=None,
    directors=None,
    actors=None,
    authors=None,
    companies=None,
    countries=None,
    genres=None,
    languages=None,
    categories=None,
    dubbed=False,
    free_video_sources=None,
    free_download_links=None,
    free_third_party_links=None,
    paid_video_sources=None,
    paid_download_links=None,
    paid_third_party_links=None
):
    subtitles = subtitles or []
    directors = directors or []
    actors = actors or []
    authors = authors or []
    companies = companies or []
    countries = countries or []
    genres = genres or []
    languages = languages or []
    categories = categories or []

    free_video_sources = free_video_sources or [{
        'url_360p': '', 'url_480p': '', 'url_720p': '', 'url_1080p': ''
    }]
    free_download_links = free_download_links or [{
        'url_360p': '', 'url_480p': '', 'url_720p': '', 'url_1080p': ''
    }]
    free_third_party_links = free_third_party_links or ['']

    paid_video_sources = paid_video_sources or [{
        'url_360p': '', 'url_480p': '', 'url_720p': '', 'url_1080p': '', 'url_2160p': '', 'url_4320p': ''
    }]
    paid_download_links = paid_download_links or [{
        'url_360p': '', 'url_480p': '', 'url_720p': '', 'url_1080p': ''
    }]
    paid_third_party_links = paid_third_party_links or ['']

    json_data = {
        'title': title,
        'description': '',
        'duration': duration,
        'release_year': release_year,
        'poster_url': poster_url,
        'backdrop_url': backdrop_url,
        'mobile': mobile_url,
        'trailer_url': trailer_url,
        'logo_url': logo_url,
        'hot_video_url': hot_video_url,
        'status': status,
        'age_rating': age_rating,
        'subtitles': subtitles,
        'directors': directors,
        'actors': actors,
        'authors': authors,
        'companies': companies,
        'countries': countries,
        'genres': genres,
        'languages': languages,
        'categories': categories,
        'dubbed': dubbed,
        'free': {
            'video_sources': free_video_sources,
            'download_links': free_download_links,
            'third_party_video_links': free_third_party_links,
            'pixel_videos': {
                'url_360p': ['undefined'],
                'url_480p': ['undefined'],
                'url_720p': ['undefined'],
                'url_1080p': ['undefined'],
            },
        },
        'paid': {
            'video_sources': paid_video_sources,
            'download_links': paid_download_links,
            'third_party_video_links': paid_third_party_links,
            'pixel_videos': {
                'url_360p': ['undefined'],
                'url_480p': ['undefined'],
                'url_720p': ['undefined'],
                'url_1080p': ['undefined'],
                'url_2160p': ['undefined'],
                'url_4320p': ['undefined'],
            },
        },
    }

    headers = {
        'Accept': '*/*',
        'Accept-Language': 'en-US,en;q=0.9',
        'Access': 'yatki',
        'Cache-Control': 'no-cache',
        'Connection': 'keep-alive',
        'Content-Type': 'application/json',
        'Origin': 'https://ddtank.halashow.com',
        'Pragma': 'no-cache',
        'Referer': 'https://ddtank.halashow.com/',
        'Sec-Fetch-Dest': 'empty',
        'Sec-Fetch-Mode': 'cors',
        'Sec-Fetch-Site': 'same-site',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Not.A/Brand";v="99", "Chromium";v="136"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
    }

    cookies = {
        'auth_token': '63ec82b2b552c566e8bc5fad64e6c65e50254e0f84bc872fe98d45444d30ef88',
    }

    response = requests.post(
        'https://swag.halashow.com/ddtank/admin/movie',
        cookies=cookies,
        headers=headers,
        json=json_data
    )

    return response.json()



def upload_subtitle(file_path: str, language: str = "ar") -> str:
    url = 'https://swag.halashow.com/ddtank/admin/subs'

    cookies = {
        'cf_clearance': 'Uz5L8hl0QFKE4QhuewgQMzTYJuHAFFCV6iqaR6LYnCA-1745825383-1.2.1.1-oEHxCiNRVVq6nPRn562cksbV37_kTzRWpvKN6M.IUrH3meh0Wlbm.gbOVeA9_GR5_eBEuUusWCSvq3kCfyWhQVOM0fBBnxE2rIGrjeW8HNYpmO7LeGF9o78_Of68AT2JStoBYe229pGYeBw2BX2CGkdlbr5LnOt76YAa8qMCL8WmNyJSeFxVrRbgsxiYxergZm4yhKVkamKZjV2h.2y.Bdxzew5RfqLLk763pM7XN2QrdnbHSA6uIK6QZwyznFN0ydWQt0EOU416xG7UWoJmqG4FFAGhef8SkYj4ic9U8Icd3Th4uBIRD4l5jw7Y2FtJUAEhMAmsuCZgSHf7YFI.114izx8CrtDl4iimna1J_bo',
        'auth_token': '962dbcd64bb2a956b7b329a6fb104c4bb24622b3acc735b0a6fcbd0936e36728',
    }
    headers = {
        'Accept': '*/*',
        'Access': 'yatki',
        'Origin': 'https://ddtank.halashow.com',
        'Referer': 'https://ddtank.halashow.com/',
        'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36',
        'sec-ch-ua': '"Not.A/Brand";v="99", "Chromium";v="136"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Linux"',
    }

    files = {
        'file': ('w.srt', open(file_path, 'rb'), 'application/x-subrip'),
    }

    data = {
        'language': language,
    }

    response = requests.post(url, headers=headers, cookies=cookies, data=data, files=files)

    if response.ok:
        result = response.json()
        return result.get("data") 
    else:
        print("Failed:", response.status_code, response.text)
        return None