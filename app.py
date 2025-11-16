# main.py
from graph import Graph

CSV_ESTACIONES = "transmetro_stations_unique.csv"
CSV_RUTAS = "transmetro_routes_detailed.csv"
CACHE_JSON = "cache_distancias.json"
VELOCIDAD_PROMEDIO = 5  # km/h para estimar tiempos cuando no hay JSON

def main():
    print("=== 🚍 SIMULADOR DE RUTAS TRANSMETRO ===")

    grafo = Graph()

    # -------------------------------
    # Cargar estaciones y rutas
    # -------------------------------
    print("\nCargando estaciones...")
    grafo.cargar_estaciones(CSV_ESTACIONES)
    print(f"✔ Estaciones cargadas: {len(grafo.nodos)}")

    print("Cargando rutas...")
    grafo.cargar_rutas(CSV_RUTAS)
    print("✔ Rutas cargadas.\n")

    # -------------------------------
    # Cargar cache de distancias y tiempos
    # -------------------------------
    print("Cargando distancias y tiempos desde JSON...")
    grafo.cargar_cache_aristas(CACHE_JSON)
    print("✔ Distancias y tiempos cargados.\n")

    # -------------------------------
    # Dibujar grafo completo
    # -------------------------------
    print("Dibujando grafo completo con distancias...")
    grafo.dibujar_grafo()

    # -------------------------------
    # Pedir origen/destino
    # -------------------------------
    origen = input("\nIngrese estación de origen (exacto): ").strip()
    destino = input("Ingrese estación de destino (exacto): ").strip()

    ruta, distancia = grafo.ruta_mas_corta(origen, destino)

    if not ruta:
        print("⚠️ No se encontró ruta entre esas estaciones.")
        return

    # -------------------------------
    # Mostrar ruta y calcular tiempo total
    # -------------------------------
    print("\n=== 🟢 RUTA MÁS CORTA (DIJKSTRA) ===")
    print(" → ".join(ruta))
    print(f"Distancia total (km): {distancia:.3f}")

    tiempo_total = 0
    for i in range(len(ruta)-1):
        a, b = ruta[i], ruta[i+1]
        t = grafo.aristas[a][b].get("time")
        if t is None:
            # si no hay tiempo, estimar con distancia y velocidad promedio
            dist = grafo.aristas[a][b]["dist"]
            t = (dist / VELOCIDAD_PROMEDIO) * 60  # minutos
        tiempo_total += t

    print(f"Tiempo aproximado total (min): {tiempo_total:.1f}")

    # -------------------------------
    # Dibujar ruta destacada
    # -------------------------------
    print("\nDibujando ruta destacada...")
    grafo.dibujar_grafo(ruta_destacada=ruta)

    print("\n✔ Fin del programa.")


if __name__ == "__main__":
    main()
