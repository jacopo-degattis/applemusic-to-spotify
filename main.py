import json
import base64
import requests
import webbrowser
from os import path
from urllib import parse
from bs4 import BeautifulSoup

CLIENT_ID = "<CLIENT_ID>"
CLIENT_SECRET = "<CLIENT_SECRET>"

def fetch_apple_music_tracks(playlist_url: str) -> list[dict]:
    found_tracks = list()
    response = requests.get(playlist_url)

    if not response.status_code == 200:
        raise f"Request got an unexpected status code {response.status_code}"

    page_content = response.content
    souped_page = BeautifulSoup(page_content, "html.parser")

    parent_element = souped_page.find("div", { "class": "songs-list" })

    if not parent_element: raise "Cannot find parent element 'songs-list', quitting..."

    tracks = parent_element.find_all("div", { "class": "songs-list-row" })

    for track in tracks:
        track_name = track.find("div", { "class": "songs-list-row__song-name" }).text
        track_artist = track.find("a").text
        found_tracks.append({ "name": track_name, "artist": track_artist })

    return found_tracks

def fetch_spotify_token() -> dict:
    authorize_url = "https://accounts.spotify.com/authorize"

    params = {
        "response_type": "code",
        "client_id": "292eaeea04014559965b136528521a03",
        "scope": "user-read-private user-read-email playlist-modify-private playlist-modify-public",
        "redirect_uri": "https://www.google.it/",
    }

    authorize_url = f"{authorize_url}?{parse.urlencode(params)}"

    webbrowser.open(authorize_url)

    code_uri = input("Please input your code here ")
    code = code_uri.split("?code=")[1]
    encoded_auth = f"{CLIENT_ID}:{CLIENT_SECRET}".encode()
    basic_auth = base64.b64encode(encoded_auth).decode()

    response = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={
            "Authorization": f"Basic {basic_auth}",
            "Content-Type": "application/x-www-form-urlencoded"
        },
        data={
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": "https://www.google.it/",
        }
    )

    if not response.status_code == 200:
        raise f"Cannot fetch token, request sent a status code of {response.status_code}"

    return response.json()

def spotify_search(query_string: str, token: str) -> dict:
    response = requests.get(
        f"https://api.spotify.com/v1/search?{query_string}",
        headers={ "Authorization": f"Bearer {token}" }
    )

    if not response.status_code == 200:
        # TODO: improve for case not found
        print(f"Cannot fetch track or not found, request sent a status code of {response.status_code}")
        pass

    found_results = response.json()["tracks"]["items"]
    return found_results[0] if len(found_results) > 0 else None 

def parse_spotify_tracks(tracks: list[dict], token: str) -> None:
    parsed_tracks = list()

    for track in tracks:
        query_string = f"q=track:{track['name']}&artist:{track['artist']}&type=track"
        
        print(f"[!] Fetching track {track['name']} by {track['artist']}")
        response = spotify_search(query_string, token)
        
        if response:
            parsed_tracks.append(response["uri"])        

    return parsed_tracks

def move_to_spotify(playlist_url: str, tracks: list[dict]) -> None:
    auth_data = None

    if path.isfile("creds.json"):
        with open("creds.json", "r") as creds_file:
            auth_data = json.loads(creds_file.read())
    else:
        auth_data = fetch_spotify_token()
        
        with open("creds.json", "w") as creds_file:
            json.dump(auth_data, creds_file)

    parsed_tracks = parse_spotify_tracks(tracks, auth_data["access_token"])

    # TODO: add playlist url checking, skip for now
    # TODO: also extract playlist id using regex instead of shitty splits
    # TODO: Make sure token is not expired

    playlist_id = playlist_url.split("?si")[0].split("playlist/")[1]

    response = requests.post(
        f"https://api.spotify.com/v1/playlists/{playlist_id}/tracks",
        headers={
            "Authorization": f"Bearer {auth_data['access_token']}",
            "Content-Type": "application/json",
        },
        json={ "uris": parsed_tracks }
    )

    print(response)
    print(response.content)

if __name__ == "__main__":
    tracks = fetch_apple_music_tracks("<APPLE_MUSIC_PUBLIC_PLAYLIST_URL>")
    move_to_spotify("<SPOTIFY_PLAYLIST_URL>", tracks)

