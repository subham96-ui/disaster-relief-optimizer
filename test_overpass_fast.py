import urllib.request
import urllib.parse
import json
import time

lat = 22.6064
lon = 88.3648
radius_m = 2500

query = f"""[out:json][timeout:6];
(
  way["building"](around:{radius_m}, {lat}, {lon});
  relation["building"](around:{radius_m}, {lat}, {lon});
  way["natural"="water"](around:{radius_m}, {lat}, {lon});
  way["waterway"="riverbank"](around:{radius_m}, {lat}, {lon});
);
out center 500;
"""

servers = [
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter"
]

for s in servers:
    t0 = time.time()
    try:
        data = urllib.parse.urlencode({"data": query}).encode()
        req = urllib.request.Request(s, data=data, headers={"User-Agent": "DisasterReliefApp/1.0"})
        with urllib.request.urlopen(req, timeout=6) as resp:
            res = json.loads(resp.read().decode())
            elements = res.get("elements", [])
            print(f"Success from {s}! Fetched {len(elements)} elements in {time.time()-t0:.2f}s")
            
            bldgs = [e for e in elements if e.get("tags", {}).get("building")]
            water = [e for e in elements if e.get("tags", {}).get("natural") == "water" or e.get("tags", {}).get("waterway")]
            print(f"  -> Buildings: {len(bldgs)}, Water elements: {len(water)}")
            if bldgs:
                c0 = bldgs[0].get("center") or {"lat": bldgs[0].get("lat"), "lon": bldgs[0].get("lon")}
                print(f"  -> Sample building on mainland: lat={c0.get('lat')}, lon={c0.get('lon')}")
            break
    except Exception as e:
        print(f"Server {s} failed ({time.time()-t0:.2f}s): {e}")
