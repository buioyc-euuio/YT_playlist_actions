#改成用playlist!
import requests
import isodate
import json

# 設定 API 金鑰
YOUTUBE_API_KEY = "AIzaSyCxyedDY3lqvnO7gOI-8HphP0tntQch4Yw"
NOTION_API_KEY = "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"
NOTION_DATABASE_ID = "18bf87f8a8be800d80d8fcc3f8bfd16d"
PLAYLIST_ID = "PLCmy-BAXHkG972g0-BlRfWNIDPnV53f5X&si=l0rJvbkytHCAKeXD"


# 使用 YouTube Data API，每隔一定時間檢查「Watch Later」清單是否有新影片
def get_watch_later_videos():
    url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet,contentDetails&playlistId={PLAYLIST_ID}&maxResults=50&key={YOUTUBE_API_KEY}"
    response = requests.get(url).json()
    videos = [{"id": item["contentDetails"]["videoId"], "title": item["snippet"]["title"]} for item in response.get("items", [])]
    return videos

#新的，有分頁邏輯的
def get_playlist_videos():
    """
    使用 YouTube API 獲取播放清單中的所有影片，包括分頁邏輯。
    Returns:
        list: 包含影片 ID 和標題的列表。
    """
    videos = []
    url = f"https://www.googleapis.com/youtube/v3/playlistItems?part=snippet,contentDetails&playlistId={PLAYLIST_ID}&maxResults=50&key={YOUTUBE_API_KEY}"
    while url:
        response = requests.get(url).json()

        # 如果 API 返回錯誤
        if response.get("error"):
            print(f"❌ 無法獲取播放清單（錯誤代碼: {response['error']['code']}）：{response['error']['message']}")
            break

        # 將這頁的影片加入列表
        for item in response.get("items", []):
            video_id = item["contentDetails"]["videoId"]
            title = item["snippet"]["title"]
            videos.append({"id": video_id, "title": title})

        # 如果有下一頁，更新 URL；否則結束迴圈
        url = f"https://www.googleapis.com/youtube/v3/playlistItems?pageToken={response.get('nextPageToken')}&part=snippet,contentDetails&playlistId={PLAYLIST_ID}&maxResults=50&key={YOUTUBE_API_KEY}" if "nextPageToken" in response else None

    return videos

# 取得影片時長
def get_video_duration(video_id):
    url = f"https://www.googleapis.com/youtube/v3/videos?part=contentDetails&id={video_id}&key={YOUTUBE_API_KEY}"
    response = requests.get(url).json()
    duration = response["items"][0]["contentDetails"]["duration"]
    return duration  # ISO 8601 格式 (如 PT1H30M45S)

# 格式化時長
def parse_duration(duration):
    import isodate
    parsed_duration = isodate.parse_duration(duration)
    total_minutes = int(parsed_duration.total_seconds() / 60)
    return total_minutes

#查詢 Notion 資料庫，檢查影片是否已經存在。

def is_video_in_notion(video_title):
    """
    查詢 Notion 資料庫，檢查影片是否已經存在。
    Args:
        video_title (str): 影片標題。
    Returns:
        bool: 如果影片已存在，回傳 True，否則回傳 False。
    """
    url = f"https://api.notion.com/v1/databases/{NOTION_DATABASE_ID}/query"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }
    data = {
        "filter": {
            "property": "標題",
            "title": {"equals": video_title}
        }
    }

    response = requests.post(url, headers=headers, json=data)

    if response.status_code == 200:
        results = response.json().get("results", [])
        return len(results) > 0  # 如果 Notion 中已存在該標題，則回傳 True
    else:
        print(f"❌ 無法查詢 Notion（錯誤代碼: {response.status_code}）：{response.text}")
        return False

# 透過 YouTube API 抓取影片縮圖
def get_video_thumbnail(video_id):
    """
    取得 YouTube 影片的縮圖網址
    Args:
        video_id (str): 影片 ID
    Returns:
        str: 影片縮圖的網址
    """
    url = f"https://www.googleapis.com/youtube/v3/videos?part=snippet&id={video_id}&key={YOUTUBE_API_KEY}"
    response = requests.get(url).json()

    if "items" in response and len(response["items"]) > 0:
        thumbnails = response["items"][0]["snippet"]["thumbnails"]
        return thumbnails.get("high", {}).get("url", None)  # 取得高解析度縮圖
    return None

# 發送數據到 Notion
def add_to_notion(title, duration, video_url, thumbnail_url):
    url = "https://api.notion.com/v1/pages"
    headers = {
        "Authorization": f"Bearer {NOTION_API_KEY}",
        "Content-Type": "application/json",
        "Notion-Version": "2022-06-28"
    }

    data = {
        "parent": {"database_id": NOTION_DATABASE_ID},
        "properties": {
            "標題": {"title": [{"text": {"content": title}}]},
            "時長": {"number": duration},
            "連結": {"url": video_url},
            "狀態": {"select": {"name": "待觀看"}},
            "縮圖": {
                "files": [{"name": "縮圖", "external": {"url": thumbnail_url}}]  # 添加圖片欄位
            }
        },
        "cover": {  # 設定 Notion 封面圖片
            "external": {"url": thumbnail_url}
        }
    }
    response = requests.post(url, headers=headers, json=data)
    if response.status_code == 200:
        print(f"✅ 成功新增至 Notion：{title}")
    else:
        print(f"❌ 無法新增至 Notion（錯誤代碼: {response.status_code}）：{response.text}")


# 主邏輯：從播放清單中同步影片到 Notion，避免重複新增。
videos = get_playlist_videos()

for video in videos:
    video_id = video["id"]
    title = video["title"]
    video_url = f"https://www.youtube.com/watch?v={video_id}"

    # 先檢查 Notion 是否已存在該影片
    if is_video_in_notion(title):
        print(f"⚠️ 影片已存在，跳過：{title}")
        continue  # 跳過該影片，不新增

    # 取得影片時長
    duration_iso = get_video_duration(video_id)
    duration = parse_duration(duration_iso)

    # 取得影片縮圖
    thumbnail_url = get_video_thumbnail(video_id)

    # 將影片資訊新增到 Notion
    add_to_notion(title, duration, video_url, thumbnail_url)
    print(f"✅ 已新增：{title} - {duration} 分鐘")

print("✅ 全部影片已同步完成！")





