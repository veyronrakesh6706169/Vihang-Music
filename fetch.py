import os, re, time, html, urllib.request
BASE = "https://opengameart.org"
UA = {"User-Agent": "Mozilla/5.0 (VihangMusicBot)"}
WANT = int(os.environ.get("COUNT") or "40")
KIND = (os.environ.get("KIND") or "music").strip().lower()
SFX = [
    ("Whoosh", ["whoosh", "swoosh", "swish", "woosh", "wind", "swing", "transition"]),
    ("Click", ["click", "button", "ui", "menu", "interface", "select", "beep", "blip", "notification"]),
    ("Impact", ["hit", "punch", "impact", "thud", "slam", "explosion", "boom", "crash", "smash", "kick"]),
    ("Funny", ["funny", "cartoon", "comedy", "silly", "boing", "laugh", "fart", "squeak"]),
    ("Nature", ["rain", "water", "bird", "birds", "forest", "fire", "nature", "thunder", "ocean", "river"]),
    ("Magic", ["magic", "spell", "sparkle", "power", "powerup", "fantasy", "heal", "shine"]),
    ("Game", ["coin", "jump", "pickup", "collect", "levelup", "win", "lose", "game", "retro", "8-bit"]),
]
MOODS = [
    ("Sad", ["sad", "melancholy", "melancholic", "sorrow", "emotional", "tragic", "lonely", "piano"]),
    ("LoFi", ["ambient", "calm", "relax", "relaxing", "chill", "lofi", "lo-fi", "peaceful", "soft", "dreamy", "meditation"]),
    ("Happy", ["happy", "cheerful", "fun", "cute", "joyful", "positive", "comedy", "funny", "bright"]),
    ("Upbeat", ["upbeat", "energetic", "electronic", "dance", "rock", "chiptune", "techno", "action", "fast", "8-bit", "8bit"]),
    ("Cinematic", ["epic", "orchestral", "cinematic", "battle", "adventure", "heroic", "dramatic", "boss", "fantasy", "theme"]),
]
def get(u):
    req = urllib.request.Request(u, headers=UA)
    return urllib.request.urlopen(req, timeout=60).read()
def text(u):
    return get(u).decode("utf-8", "ignore")
def field(page, name):
    i = page.find("field-name-" + name)
    if i < 0:
        return ""
    return page[i:i + 2500]
def clean(s):
    s = html.unescape(re.sub(r"<[^>]+>", "", s)).strip()
    s = re.sub(r"[^A-Za-z0-9 \-]+", "", s).strip()
    s = re.sub(r"\s+", "_", s)
    return s[:40] or "Track"
def mood_of(tags, title):
    words = (" ".join(tags) + " " + title).lower()
    for mood, keys in (SFX if KIND == "sfx" else MOODS):
        for k in keys:
            if re.search(r"\b" + re.escape(k) + r"\b", words):
                return mood
    return "Misc" if KIND == "sfx" else "Cinematic"
ROOT = "sfx" if KIND == "sfx" else "tracks"
TID = "12"
if KIND == "sfx":
    TID = "13"
    try:
        form = text(BASE + "/art-search-advanced")
        m = re.search(r'for="edit-field-art-type-tid-(\d+)"[^>]*>\s*Sound Effect', form)
        if m:
            TID = m.group(1)
    except Exception:
        pass
print("kind", KIND, "type id", TID)
have = set()
for root, dirs, files in os.walk(ROOT):
    for f in files:
        have.add(f.lower())
credits = open("CREDITS.md", "a", encoding="utf-8")
got = 0
seen = set()
for pg in range(0, 40):
    if got >= WANT:
        break
    url = BASE + "/art-search-advanced?field_art_type_tid%5B%5D=" + TID + "&sort_by=count&sort_order=DESC&page=" + str(pg)
    try:
        listing = text(url)
    except Exception as e:
        print("list fail", e)
        break
    links = []
    for l in re.findall(r'href="(/content/[^"#?]+)"', listing):
        if l not in seen:
            seen.add(l)
            links.append(l)
    if not links:
        break
    for l in links:
        if got >= WANT:
            break
        time.sleep(1)
        try:
            page = text(BASE + l)
        except Exception:
            continue
        lic = field(page, "field-art-licenses")
        if not re.search(r">\s*CC0\s*<", lic):
            continue
        files = re.findall(r'(https://opengameart\.org/sites/default/files/[^"\s<>]+?\.(?:mp3|ogg|wav))', page)
        if not files:
            continue
        mp3 = [f for f in files if f.lower().endswith(".mp3")]
        furl = (mp3 or files)[0]
        tm = re.search(r"<title>(.*?)\|", page, re.S)
        title = clean(tm.group(1) if tm else l.split("/")[-1])
        tags = [html.unescape(t).strip() for t in re.findall(r">([^<>]{2,30})</a>", field(page, "field-art-tags"))]
        mood = mood_of(tags, title)
        ext = furl.rsplit(".", 1)[1].lower()
        name = title + "." + ext
        if name.lower() in have:
            continue
        try:
            data = get(furl)
        except Exception:
            continue
        lo = 2000 if KIND == "sfx" else 30000
        hi = 3 * 1024 * 1024 if KIND == "sfx" else 12 * 1024 * 1024
        if len(data) < lo or len(data) > hi:
            continue
        os.makedirs(ROOT + "/" + mood, exist_ok=True)
        with open(ROOT + "/" + mood + "/" + name, "wb") as fo:
            fo.write(data)
        have.add(name.lower())
        am = re.search(r'field-name-author-submitter.*?<a[^>]*>([^<]+)</a>', page, re.S)
        author = html.unescape(am.group(1)).strip() if am else "Unknown"
        credits.write("- " + title.replace("_", " ") + " by " + author + " (CC0) " + BASE + l + "\n")
        got += 1
        print("added", mood, name, len(data))
credits.close()
print("total new:", got)
