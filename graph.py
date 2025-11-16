import csv
import math
import json
import os
import plotly.graph_objects as go

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
    # Cargar rutas desde CSV
    # ---------------------------------------------------------
    def cargar_rutas(self, archivo):
        rutas_por_nombre = {}
        with open(archivo, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                ruta = row["Nombre ruta"].strip()
                parada = row["Nombre parada"].strip()
                seq = int(row["Secuencia parada"])
                rutas_por_nombre.setdefault(ruta, []).append((seq, parada))

        for ruta, lista in rutas_por_nombre.items():
            lista.sort()
            for i in range(len(lista)-1):
                a = lista[i][1]
                b = lista[i+1][1]
                if a in self.coords and b in self.coords:
                    self.agregar_arista(a, b)

    # ---------------------------------------------------------
    # Agregar arista con Haversine como base
    # ---------------------------------------------------------
    def agregar_arista(self, a, b):
        lat1, lon1 = self.coords[a]
        lat2, lon2 = self.coords[b]

        dist = haversine(lat1, lon1, lat2, lon2) / 1000  # km
        self.aristas[a][b] = {"dist": dist, "time": None}
        self.aristas[b][a] = {"dist": dist, "time": None}

    # ---------------------------------------------------------
    # Cargar distancias y tiempos reales desde JSON
    # ---------------------------------------------------------
    def cargar_cache_aristas(self, archivo_json):
        if not os.path.exists(archivo_json):
            print("⚠️ JSON no encontrado:", archivo_json)
            return

        with open(archivo_json, "r", encoding="utf-8") as f:
            cache = json.load(f)

        # Recorremos todas las aristas y buscamos coincidencia exacta en JSON
        for a in self.aristas:
            for b in self.aristas[a]:
                lat1, lon1 = self.coords[a]
                lat2, lon2 = self.coords[b]

                # Claves posibles
                k1 = f"{lat1},{lon1}|{lat2},{lon2}"
                k2 = f"{lat2},{lon2}|{lat1},{lon1}"

                datos = None
                if k1 in cache:
                    datos = cache[k1]
                elif k2 in cache:
                    datos = cache[k2]

                if datos:
                    # Actualizamos dist y tiempo desde JSON
                    self.aristas[a][b]["dist"] = datos.get("dist", self.aristas[a][b]["dist"])
                    t = datos.get("time_min")
                    # Solo asignamos si no es None y > 0
                    if t is not None and t > 0:
                        self.aristas[a][b]["time"] = t

        print("✔ Cache de distancias y tiempos cargada correctamente.")

    # ---------------------------------------------------------
    # Dijkstra para ruta más corta (por distancia)
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

        # Reconstruir ruta
        camino = []
        x = destino
        while x:
            camino.append(x)
            x = prev[x]
        camino.reverse()
        return camino, dist[destino]

    # ---------------------------------------------------------
    # Dibujar grafo con ruta destacada y hover completo
    # ---------------------------------------------------------
    def dibujar_grafo(self, ruta_destacada=None):
        pos = self.coords
        fig = go.Figure()
        usadas = set()

        def es_par_ruta(a, b, ruta):
            if not ruta:
                return False
            for i in range(len(ruta)-1):
                if (ruta[i] == a and ruta[i+1] == b) or (ruta[i] == b and ruta[i+1] == a):
                    return True
            return False

        # Aristas
        for a in self.aristas:
            for b, datos in self.aristas[a].items():
                if (b, a) in usadas:
                    continue
                usadas.add((a, b))

                x0, y0 = pos[a][1], pos[a][0]
                x1, y1 = pos[b][1], pos[b][0]

                t = datos.get("time")
                txt = f"<b>{a} → {b}</b><br>Distancia: {datos['dist']:.3f} km"
                txt += f"<br>Tiempo: {t:.2f} min" if t else "<br>Tiempo: N/A"

                color = "red" if es_par_ruta(a, b, ruta_destacada) else "blue"
                width = 5 if color == "red" else 1.5

                fig.add_trace(go.Scatter(
                    x=[x0, x1],
                    y=[y0, y1],
                    mode="lines",
                    line=dict(color=color, width=width),
                    hoverinfo="text",
                    text=[txt],
                    showlegend=False
                ))

        # Nodos
        fig.add_trace(go.Scatter(
            x=[pos[n][1] for n in pos],
            y=[pos[n][0] for n in pos],
            mode="markers",
            marker=dict(size=10, color="black"),
            text=list(pos.keys()),
            hoverinfo="text",
            name="Estaciones"
        ))

        fig.update_layout(
            title="Mapa interactivo del sistema Transmetro",
            showlegend=False,
            hovermode="closest",
            width=1200,
            height=900
        )

        fig.show()
