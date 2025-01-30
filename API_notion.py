import requests
import json

# 設定 API 金鑰
YOUTUBE_API_KEY = "AIzaSyCxyedDY3lqvnO7gOI-8HphP0tntQch4Yw"
NOTION_API_KEY = "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"
NOTION_DATABASE_ID = "18af87f8a8be80139bedc326d656341e"
PLAYLIST_ID = "PLj6E8qlqmkFs5e0vOwUC88cPLPtvpO57s"

# 取得播放清單影片
def get_playlist_videos(playlist_id):
    url = f"<https://www.googleapis.com/youtube/v3/playlistItems?part=snippet,contentDetails&playlistId={playlist_id}&maxResults=50&key={YOUTUBE_API_KEY}>"
    print("url=" + url)
    response = requests.get(url).json()
    videos = []

    for item in response.get("items", []):
        video_id = item["contentDetails"]["videoId"]
        title = item["snippet"]["title"]
        videos.append({"id": video_id, "title": title})

    return videos

# 取得影片時長
def get_video_duration(video_id):
    url = f"<https://www.googleapis.com/youtube/v3/videos?part=contentDetails&id={video_id}&key={YOUTUBE_API_KEY}>"
    response = requests.get(url).json()
    duration = response["items"][0]["contentDetails"]["duration"]
    return duration  # ISO 8601 格式 (如 PT1H30M45S)

# 格式化時長
def parse_duration(duration):
    import isodate
    parsed_duration = isodate.parse_duration(duration)
    total_minutes = int(parsed_duration.total_seconds() / 60)
    return f"{total_minutes} 分鐘"

# 發送數據到 Notion
def add_to_notion(title, duration, video_url):
    url = "<https://api.notion.com/v1/pages>"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "標題": {"title": [{"text": {"content": title}}]},
            "時長": {"rich_text": [{"text": {"content": duration}}]},
            "連結": {"url": video_url},
            "狀態": {"select": {"name": "待觀看"}}
        }
    }

    requests.post(url, headers=headers, json=data)

# 主流程
videos = get_playlist_videos(PLAYLIST_ID)
for video in videos:
    video_id = video["id"]
    title = video["title"]
    duration_iso = get_video_duration(video_id)
    duration = parse_duration(duration_iso)
    video_url = f"<https://www.youtube.com/watch?v={video_id}>"

    add_to_notion(title, duration, video_url)
    print(f"已新增：{title} - {duration}")

print("完成！")

