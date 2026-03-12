# src/places_client.py
import os
import math
import requests
from typing import List, Dict, Any, Optional

GOOGLE_API_KEY = os.environ.get("GOOGLE_PLACES_API_KEY")  # set this in your environment if available

def _haversine_distance_km(lat1, lon1, lat2, lon2):
    # returns distance in kilometres
    R = 6371.0
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2.0)**2 + math.cos(phi1)*math.cos(phi2)*math.sin(dlambda/2.0)**2
    return 2*R*math.asin(math.sqrt(a))

# ---------------- Google Places ----------------
def _google_nearby_search(lat: float, lng: float, specialty: Optional[str] = None,
                          radius: int = 5000, max_results: int = 10) -> List[Dict[str, Any]]:
    if not GOOGLE_API_KEY:
        return []
    url = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "key": GOOGLE_API_KEY,
        "location": f"{lat},{lng}",
        "radius": radius,
        "type": "doctor"  # type doctor is generic; we also use keyword for speciality
    }
    if specialty:
        params["keyword"] = specialty
    res = requests.get(url, params=params, timeout=10)
    items = []
    if res.status_code != 200:
        return []
    data = res.json()
    for p in data.get("results", [])[:max_results]:
        loc = p.get("geometry", {}).get("location", {})
        d = _haversine_distance_km(lat, lng, loc.get("lat"), loc.get("lng")) if loc else None
        items.append({
            "name": p.get("name"),
            "address": p.get("vicinity") or p.get("formatted_address"),
            "lat": loc.get("lat"),
            "lng": loc.get("lng"),
            "rating": p.get("rating"),
            "open_now": p.get("opening_hours", {}).get("open_now") if p.get("opening_hours") else None,
            "place_id": p.get("place_id"),
            "distance_km": round(d, 2) if d is not None else None,
            "source": "google_places"
        })
    return items

# ---------------- OpenStreetMap / Overpass ----------------
def _overpass_search(lat: float, lng: float, specialty: Optional[str] = None,
                     radius: int = 5000, max_results: int = 15) -> List[Dict[str, Any]]:
    # generic Overpass query: search for amenity=clinic/doctor/hospital within radius
    # if specialty provided, include it in the name or healthcare:speciality tag search
    q_special = ""
    if specialty:
        # a pragmatic approach: search name and various tags for specialty keyword
        q_special = f'["name"~"{specialty}",i]'

    query = f"""
    [out:json][timeout:25];
    (
      node["amenity"~"clinic|hospital|doctors|healthcare"](around:{radius},{lat},{lng}){q_special};
      way["amenity"~"clinic|hospital|doctors|healthcare"](around:{radius},{lat},{lng}){q_special};
      relation["amenity"~"clinic|hospital|doctors|healthcare"](around:{radius},{lat},{lng}){q_special};
    );
    out center {max_results};
    """
    url = "https://overpass-api.de/api/interpreter"
    try:
        res = requests.post(url, data={"data": query}, timeout=30)
        if res.status_code != 200:
            return []
        data = res.json()
    except Exception:
        return []
    items = []
    for el in data.get("elements", [])[:max_results]:
        tags = el.get("tags", {})
        if el.get("type") == "node":
            lat2, lon2 = el.get("lat"), el.get("lon")
        else:
            center = el.get("center", {})
            lat2, lon2 = center.get("lat"), center.get("lon")
        d = _haversine_distance_km(lat, lng, lat2, lon2) if lat2 and lon2 else None
        items.append({
            "name": tags.get("name") or tags.get("operator") or "clinic",
            "address": ", ".join(filter(None, [tags.get("addr:street"), tags.get("addr:city"), tags.get("addr:postcode")])),
            "lat": lat2,
            "lng": lon2,
            "specialty_tags": tags.get("healthcare:speciality") or tags.get("specialty") or tags.get("clinic:speciality"),
            "distance_km": round(d, 2) if d is not None else None,
            "source": "overpass"
        })
    return items

# ---------------- Public API ----------------
def find_nearby_doctors(lat: float, lng: float, specialty: Optional[str] = None,
                        radius: int = 5000, max_results: int = 10) -> List[Dict[str, Any]]:
    """Try Google Places first (if key present), else Overpass fallback.
    Returns list of places sorted by distance."""
    places = []
    if GOOGLE_API_KEY:
        try:
            places = _google_nearby_search(lat, lng, specialty=specialty, radius=radius, max_results=max_results)
        except Exception:
            places = []
    if not places:
        try:
            places = _overpass_search(lat, lng, specialty=specialty, radius=radius, max_results=max_results)
        except Exception:
            places = []
    # sort by distance if available
    places_sorted = sorted([p for p in places if p.get("distance_km") is not None], key=lambda x: x["distance_km"]) + [p for p in places if p.get("distance_km") is None]
    return places_sorted[:max_results]
