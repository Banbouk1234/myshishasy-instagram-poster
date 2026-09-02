#!/usr/bin/env python3
import os, sys, json, time, requests
from pathlib import Path
from datetime import datetime, timezone

ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN", "")
APP_ID       = os.environ.get("APP_ID",       "1064773792747496")
APP_SECRET   = os.environ.get("APP_SECRET",   "")
IG_USER_ID   = os.environ.get("IG_USER_ID",   "17841441637970223")
GITHUB_REPO  = os.environ.get("GITHUB_REPOSITORY", "Banbouk1234/myshishasy-instagram-poster")
IMAGE_REPO   = "Banbouk1234/myshisha-instagram-poster"  # shared image source
API_VER      = "v25.0"
BASE_URL     = f"https://graph.facebook.com/{API_VER}"

STORIES_DIR  = Path(__file__).parent
POSTED_FILE  = STORIES_DIR / ".posted.json"
LOG_FILE     = STORIES_DIR / "post.log"

def log(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def load_posted():
    if POSTED_FILE.exists():
        try:
            return json.loads(POSTED_FILE.read_text())
        except:
            pass
    return []

def save_posted(posted):
    POSTED_FILE.write_text(json.dumps(posted, indent=2))

def get_images_from_repo():
    """Fetch list of images from the shared image repo via GitHub API."""
    url = f"https://api.github.com/repos/{IMAGE_REPO}/contents/"
    resp = requests.get(url, timeout=15)
    files = resp.json()
    exts = {".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".JPEG"}
    return sorted([f["name"] for f in files if isinstance(f, dict) and Path(f["name"]).suffix in exts])

def get_next_image(posted):
    images = get_images_from_repo()
    remaining = [f for f in images if f not in posted]
    if not remaining:
        log("All images posted. Resetting cycle.")
        posted.clear()
        remaining = images
    return remaining[0] if remaining else None

def get_public_url(image_name):
    return f"https://raw.githubusercontent.com/{IMAGE_REPO}/main/{image_name}"

def create_container(image_url):
    resp = requests.post(f"{BASE_URL}/{IG_USER_ID}/media",
        data={"image_url": image_url, "media_type": "STORIES", "access_token": ACCESS_TOKEN},
        timeout=30)
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Container creation error: {data['error']}")
    return data["id"]

def wait_ready(container_id, max_wait=120):
    deadline = time.time() + max_wait
    while time.time() < deadline:
        resp = requests.get(f"{BASE_URL}/{container_id}",
            params={"fields": "status_code", "access_token": ACCESS_TOKEN}, timeout=15)
        status = resp.json().get("status_code", "")
        log(f"  status: {status}")
        if status == "FINISHED": return True
        if status == "ERROR": raise RuntimeError("Container processing failed")
        time.sleep(5)
    raise RuntimeError("Timeout waiting for FINISHED")

def publish(container_id):
    resp = requests.post(f"{BASE_URL}/{IG_USER_ID}/media_publish",
        data={"creation_id": container_id, "access_token": ACCESS_TOKEN}, timeout=30)
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Publish error: {data['error']}")
    return data.get("id")

def main():
    log("=== Instagram Story Poster started ===")
    if not ACCESS_TOKEN:
        log("ERROR: ACCESS_TOKEN is not set.")
        sys.exit(1)
    posted = load_posted()
    image_name = get_next_image(posted)
    if not image_name:
        log("No images found in source repo.")
        sys.exit(0)
    log(f"Next image: {image_name}")
    try:
        image_url = get_public_url(image_name)
        container = create_container(image_url)
        wait_ready(container)
        media_id = publish(container)
        posted.append(image_name)
        save_posted(posted)
        log(f"Success! Posted {image_name} (media_id={media_id})")
    except Exception as e:
        log(f"ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()#!/usr/bin/env python3
import os, sys, json, time, requests
from pathlib import Path
from datetime import datetime, timezone

ACCESS_TOKEN = os.environ.get("ACCESS_TOKEN", "")
APP_ID       = os.environ.get("APP_ID",       "1064773792747496")
APP_SECRET   = os.environ.get("APP_SECRET",   "")
IG_USER_ID   = os.environ.get("IG_USER_ID",   "17841441637970223")
GITHUB_REPO  = os.environ.get("GITHUB_REPOSITORY", "Banbouk1234/myshishasy-instagram-poster")
API_VER      = "v25.0"
BASE_URL     = f"https://graph.facebook.com/{API_VER}"

STORIES_DIR  = Path(__file__).parent
POSTED_FILE  = STORIES_DIR / ".posted.json"
LOG_FILE     = STORIES_DIR / "post.log"

def log(msg):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{ts}] {msg}"
    print(line, flush=True)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")

def load_posted():
    if POSTED_FILE.exists():
        try:
            return json.loads(POSTED_FILE.read_text())
        except:
            pass
    return []

def save_posted(posted):
    POSTED_FILE.write_text(json.dumps(posted, indent=2))

def get_next_image(posted):
    exts = {".png", ".jpg", ".jpeg", ".PNG", ".JPG", ".JPEG"}
    images = sorted([f for f in STORIES_DIR.iterdir() if f.suffix in exts and f.name not in posted])
    if not images:
        log("All images posted. Resetting cycle.")
        images = sorted([f for f in STORIES_DIR.iterdir() if f.suffix in exts])
    return images[0] if images else None

def get_public_url(image_path):
    return f"https://raw.githubusercontent.com/{GITHUB_REPO}/main/{image_path.name}"

def create_container(image_url):
    resp = requests.post(f"{BASE_URL}/{IG_USER_ID}/media",
        data={"image_url": image_url, "media_type": "STORIES", "access_token": ACCESS_TOKEN},
        timeout=30)
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Container creation error: {data['error']}")
    return data["id"]

def wait_ready(container_id, max_wait=120):
    deadline = time.time() + max_wait
    while time.time() < deadline:
        resp = requests.get(f"{BASE_URL}/{container_id}",
            params={"fields": "status_code", "access_token": ACCESS_TOKEN}, timeout=15)
        status = resp.json().get("status_code", "")
        log(f"  status: {status}")
        if status == "FINISHED": return True
        if status == "ERROR": raise RuntimeError("Container processing failed")
        time.sleep(5)
    raise RuntimeError("Timeout waiting for FINISHED")

def publish(container_id):
    resp = requests.post(f"{BASE_URL}/{IG_USER_ID}/media_publish",
        data={"creation_id": container_id, "access_token": ACCESS_TOKEN}, timeout=30)
    data = resp.json()
    if "error" in data:
        raise RuntimeError(f"Publish error: {data['error']}")
    return data.get("id")

def main():
    log("=== Instagram Story Poster started ===")
    if not ACCESS_TOKEN:
        log("ERROR: ACCESS_TOKEN is not set.")
        sys.exit(1)
    posted = load_posted()
    image = get_next_image(posted)
    if not image:
        log("No images found.")
        sys.exit(0)
    log(f"Next image: {image.name}")
    try:
        image_url = get_public_url(image)
        container = create_container(image_url)
        wait_ready(container)
        media_id = publish(container)
        posted.append(image.name)
        save_posted(posted)
        log(f"Success! Posted {image.name} (media_id={media_id})")
    except Exception as e:
        log(f"ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
