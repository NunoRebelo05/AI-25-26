"""
Script utilitário para verificar a consistência dos dados do mapa (Grafo).

Realiza duas verificações principais:
1. Velocidade Máxima Implícita: Calcula a velocidade necessária para percorrer cada aresta
   no tempo definido, identificando valores irrealistas.
2. Consistência de Distâncias: Compara a distância definida no JSON com a distância
   Haversine (linha reta). Se a distância do JSON for menor, há uma inconsistência
   (impossível percorrer menos que a linha reta).
"""

from Grafo import Grafo

# Carregar o grafo a partir do ficheiro JSON
mapa = Grafo.carregar_de_json("braga_mapa.json")
print(f"Max Speed calculated: {0}")

max_speed = 0
inconsistent_edges = []

# Iterar sobre todas as arestas para verificar consistência
for u, vizinhos in mapa.arestas.items():
    for v, dados in vizinhos.items():
        dist_json = dados['distancia_km']
        tempo_min = dados['tempo_base_min']
        
        # Calcular distância em linha reta (Haversine)
        dist_haversine = mapa.get_distancia_heuristica(u, v)
        
        # Verificação 1: Distância JSON vs Haversine
        # A distância de condução não pode ser menor que a distância em linha reta
        if dist_json < dist_haversine:
            inconsistent_edges.append((u, v, dist_json, dist_haversine))
            
        # Verificação 2: Velocidade Implícita
        # Velocidade = Distância / Tempo
        speed = dist_json / (tempo_min / 60.0)
        if speed > max_speed:
            max_speed = speed

print(f"Max Speed in Graph: {max_speed:.2f} km/h")
print(f"Inconsistent Edges (JSON dist < Haversine): {len(inconsistent_edges)}")
for u, v, d_json, d_hav in inconsistent_edges:
    print(f"  {u} -> {v}: JSON={d_json}km, Hav={d_hav:.2f}km")
