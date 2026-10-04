import urllib.request
import urllib.parse
import json
import time

lat = 22.6064
lon = 88.3648
min_lat, min_lon = 22.58, 88.34
max_lat, max_lon = 22.63, 88.39

query = f"""[out:json][timeout:5];
(
  way["waterway"]({min_lat},{min_lon},{max_lat},{max_lon});
  way["natural"="water"]({min_lat},{min_lon},{max_lat},{max_lon});
  relation["natural"="water"]({min_lat},{min_lon},{max_lat},{max_lon});
);
out geom 50;
"""

servers = [
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass-api.de/api/interpreter",
    "https://overpass.private.coffee/api/interpreter"
]

for url in servers:
    t0 = time.time()
    try:
        data = urllib.parse.urlencode({"data": query}).encode("utf-8")
        req = urllib.request.Request(url, data=data, headers={"User-Agent": "DisasterReliefApp/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            res = json.loads(resp.read().decode("utf-8"))
            elems = res.get("elements", [])
            print(f"Success from {url}! Fetched {len(elems)} water features in {time.time()-t0:.2f}s")
            for e in elems[:6]:
                tags = e.get("tags", {})
                name = tags.get("name") or tags.get("waterway") or tags.get("natural")
                print(f"  * {name} ({tags.get('waterway') or tags.get('natural')}): {len(e.get('geometry', []))} pts")
            break
    except Exception as e:
        print(f"Failed on {url}: {e}")
