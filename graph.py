# graph.py
import csv
import math
import matplotlib.pyplot as plt
import json
import os

# ---------------------------------------
# Haversine para distancias aproximadas
# ---------------------------------------
def haversine(lat1, lon1, lat2, lon2):
    R = 6371000  # metros
    phi1 = math.radians(lat1)
    phi2 = math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi/2)**2 + math.cos(phi1)*math.cos(phi2)*(math.sin(dlambda/2)**2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1-a))
    return R * c  # metros

# ============================================================
#                     CLASE GRAPH
# ============================================================
class Graph:

    def __init__(self):
        self.nodos = {}      # nombre → {lat, lon}
        self.coords = {}     # nombre → (lat, lon)
        self.aristas = {}    # nodo → { destino → {dist, time} }

    # ---------------------------------------------------------
    # Cargar estaciones desde CSV
    # ---------------------------------------------------------
    def cargar_estaciones(self, archivo):
        with open(archivo, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                nombre = row["Nombre parada"].strip()
                try:
                    lat = float(row["Coordenada Y"])
                    lon = float(row["Coordenada X"])
                except:
                    continue
                self.nodos[nombre] = {"lat": lat, "lon": lon}
                self.coords[nombre] = (lat, lon)
                self.aristas.setdefault(nombre, {})

    # ---------------------------------------------------------
    # Cargar rutas desde CSV (con secuencia)
    # ---------------------------------------------------------
    def cargar_rutas(self, archivo):
        rutas_por_nombre = {}
        with open(archivo, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ruta = row["Nombre ruta"].strip()
                parada = row["Nombre parada"].strip()
                seq = int(row["Secuencia parada"])
                if ruta not in rutas_por_nombre:
                    rutas_por_nombre[ruta] = []
                rutas_por_nombre[ruta].append((seq, parada))

        # Ordenar por secuencia y agregar aristas consecutivas
        for ruta, lista in rutas_por_nombre.items():
            lista.sort()
            for i in range(len(lista)-1):
                a = lista[i][1]
                b = lista[i+1][1]
                if a in self.coords and b in self.coords:
                    self.agregar_arista(a, b)

    # ---------------------------------------------------------
    # Agregar arista
    # ---------------------------------------------------------
    def agregar_arista(self, a, b):
        lat1, lon1 = self.coords[a]
        lat2, lon2 = self.coords[b]

        dist = haversine(lat1, lon1, lat2, lon2) / 1000  # km
        self.aristas[a][b] = {"dist": dist, "time": None}
        self.aristas[b][a] = {"dist": dist, "time": None}

    # ---------------------------------------------------------
    # Cargar distancias reales desde JSON cache
    # ---------------------------------------------------------
    def cargar_cache_aristas(self, archivo_json):
        """Carga distancias y tiempos de un JSON de coordenadas en el grafo."""
        if not os.path.exists(archivo_json):
            print("⚠️ JSON de cache no encontrado:", archivo_json)
            return

        with open(archivo_json, "r", encoding="utf-8") as f:
            cache = json.load(f)

        for a in self.aristas:
            for b in self.aristas[a]:
                lat1, lon1 = self.coords[a]
                lat2, lon2 = self.coords[b]

                k1 = f"{lat1},{lon1}|{lat2},{lon2}"
                k2 = f"{lat2},{lon2}|{lat1},{lon1}"

                if k1 in cache:
                    datos = cache[k1]
                elif k2 in cache:
                    datos = cache[k2]
                else:
                    continue

                self.aristas[a][b]["dist"] = datos.get("dist", self.aristas[a][b]["dist"])
                self.aristas[a][b]["time"] = datos.get("time_min", self.aristas[a][b]["time"])

        print("✔ Cache de distancias y tiempos cargada.")

    # ---------------------------------------------------------
    # Dijkstra para ruta más corta
    # ---------------------------------------------------------
    def ruta_mas_corta(self, origen, destino):
        import heapq

        dist = {n: float("inf") for n in self.aristas}
        dist[origen] = 0
        prev = {n: None for n in self.aristas}
        pq = [(0, origen)]

        while pq:
            d, u = heapq.heappop(pq)
            if u == destino:
                break
            if d != dist[u]:
                continue
            for v, datos in self.aristas[u].items():
                w = datos["dist"]
                if dist[u] + w < dist[v]:
                    dist[v] = dist[u] + w
                    prev[v] = u
                    heapq.heappush(pq, (dist[v], v))

        if dist[destino] == float("inf"):
            return None, None

        camino = []
        x = destino
        while x:
            camino.append(x)
            x = prev[x]
        camino.reverse()
        return camino, dist[destino]

    # ---------------------------------------------------------
    # Dibujar grafo completo
    # ---------------------------------------------------------
    def dibujar_grafo(self, ruta_destacada=None):
        plt.figure(figsize=(14, 12))
        pos = self.coords
        dibujadas = set()

        # Dibujar aristas
        for a in self.aristas:
            for b, datos in self.aristas[a].items():
                if (b, a) in dibujadas:
                    continue
                dibujadas.add((a, b))

                lat1, lon1 = pos[a]
                lat2, lon2 = pos[b]

                # si está en ruta destacada
                if ruta_destacada and a in ruta_destacada and b in ruta_destacada:
                    lw = 2.5
                    color = "orange"
                else:
                    lw = 1
                    color = "blue"

                plt.plot([lon1, lon2], [lat1, lat2], color=color, linewidth=lw)

                # Etiqueta con distancia y tiempo
                if datos.get("dist"):
                    xm, ym = (lon1 + lon2)/2, (lat1 + lat2)/2
                    etiqueta = f"{datos['dist']:.2f} km"
                    if datos.get("time"):
                        etiqueta += f" / {datos['time']:.1f} min"
                    plt.text(xm, ym, etiqueta, fontsize=6, color="red")

        # Dibujar nodos
        for n, (lat, lon) in pos.items():
            plt.scatter(lon, lat, s=20, color="black", zorder=3)
            plt.text(lon, lat, n, fontsize=6, zorder=4)

        plt.title("Mapa completo del sistema Transmetro")
        plt.xlabel("Longitud")
        plt.ylabel("Latitud")
        plt.tight_layout()
        plt.show()
