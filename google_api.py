# google_api.py
import requests
import json
import os
import time

class GoogleAPI:
    """
    Wrapper para Google Distance Matrix con cache.
    - Primero intenta modo 'transit' (transporte público)
    - Si no existe ruta → prueba 'driving'
    - Cachea cualquier resultado en archivo JSON
    """

    def __init__(self, api_key, cache_file="cache_distancias.json", backoff=0.8):
        self.api_key = api_key
        self.cache_file = cache_file
        self.backoff = backoff
        self.cache = self._load_cache()

    # --------------------------------------
    # Cargar cache desde archivo
    # --------------------------------------
    def _load_cache(self):
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except:
                return {}
        return {}

    # --------------------------------------
    # Guardar cache en archivo
    # --------------------------------------
    def _save_cache(self):
        with open(self.cache_file, "w", encoding="utf-8") as f:
            json.dump(self.cache, f, ensure_ascii=False, indent=2)

    # --------------------------------------
    # Crear clave única para cache
    # --------------------------------------
    def _make_key(self, origen, destino):
        # clave no direccional
        k1 = f"{origen}|{destino}"
        k2 = f"{destino}|{origen}"
        return k1 if k1 <= k2 else k2

    # --------------------------------------
    # Hacer request a Google en un modo específico
    # --------------------------------------
    def _google_request(self, origen, destino, mode):
        url = "https://maps.googleapis.com/maps/api/distancematrix/json"
        params = {
            "origins": origen,
            "destinations": destino,
            "key": self.api_key,
            "mode": mode,
            "language": "es"
        }

        try:
            resp = requests.get(url, params=params, timeout=15)
            data = resp.json()
        except Exception as e:
            print("❌ Error al consultar Google API:", e)
            return None, None, "ERROR"

        # errores generales
        if data.get("status") != "OK":
            print("⚠️ Google API respondió:", data.get("status"))
            return None, None, data.get("status")

        elem = data["rows"][0]["elements"][0]

        # errores por modo ("ZERO_RESULTS", "NOT_FOUND", etc.)
        if elem.get("status") != "OK":
            return None, None, elem.get("status")

        # extraer datos
        dist = elem["distance"]["value"] / 1000.0  # km
        time_min = elem["duration"]["value"] / 60.0  # min
        return round(dist, 3), round(time_min, 2), "OK"

    # --------------------------------------
    # Consultar distancia real entre coordenadas
    # --------------------------------------
    def get_distance(self, origen_coord, destino_coord, allow_query=True):
        """
        origen_coord, destino_coord: "lat,lon" (strings)
        allow_query: True si se permite consultar Google
        Retorna: dist(km), tiempo(min) o None,None si falla
        """

        key = self._make_key(origen_coord, destino_coord)

        # 1) Ver si está en cache
        if key in self.cache:
            entry = self.cache[key]
            return float(entry["dist"]), float(entry["time_min"])

        if not allow_query:
            return None, None

        # 2) Intento modo TRANSIT
        dist, t, status = self._google_request(origen_coord, destino_coord, "transit")
        if status == "OK":
            self.cache[key] = {"dist": dist, "time_min": t}
            self._save_cache()
            time.sleep(self.backoff)
            return dist, t

        # 3) Fallback a DRIVING
        print(f"ℹ️ Transit falló ({status}). Probando 'driving'...")
        dist, t, status2 = self._google_request(origen_coord, destino_coord, "driving")
        if status2 == "OK":
            self.cache[key] = {"dist": dist, "time_min": t}
            self._save_cache()
            time.sleep(self.backoff)
            return dist, t

        # 4) Todo falla
        print("❌ No se pudo obtener distancia en ningún modo.")
        return None, None
    