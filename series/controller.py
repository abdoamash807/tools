import requests


def main():
    api = "http://localhost:8080"  # Adjust the URL as needed
    res = requests.get(f"{api}/series")
    
    if res.status_code == 200:
        data = res.json()
        print(data)
    else:
        print("Failed to retrieve data")


if __name__ == "__main__":
    main()