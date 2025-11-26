from Grafo import Grafo

mapa = Grafo.carregar_de_json("braga_mapa.json")
print(f"Max Speed calculated: {0}")

max_speed = 0
inconsistent_edges = []

for u, vizinhos in mapa.arestas.items():
    for v, dados in vizinhos.items():
        dist_json = dados['distancia_km']
        tempo_min = dados['tempo_base_min']
        
        dist_haversine = mapa.get_distancia_heuristica(u, v)
        
        if dist_json < dist_haversine:
            inconsistent_edges.append((u, v, dist_json, dist_haversine))
            
        speed = dist_json / (tempo_min / 60.0)
        if speed > max_speed:
            max_speed = speed

print(f"Max Speed in Graph: {max_speed:.2f} km/h")
print(f"Inconsistent Edges (JSON dist < Haversine): {len(inconsistent_edges)}")
for u, v, d_json, d_hav in inconsistent_edges:
    print(f"  {u} -> {v}: JSON={d_json}km, Hav={d_hav:.2f}km")
