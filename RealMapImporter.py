import osmnx as ox
import networkx as nx
from Grafo import Grafo
import random

def importar_mapa_osm(localizacao: str, dist: int = 2000) -> Grafo:
    """
    Importa um grafo de rua do OpenStreetMap para uma localização dada
    e converte-o para o formato Grafo da aplicação.
    
    Args:
        localizacao (str): Nome do local (ex: "Braga, Portugal", "Manhattan, NY").
        dist (int): Raio em metros para descarregar (default: 2000m).
        
    Returns:
        Grafo: Instância de Grafo populada ou None em caso de erro.
    """
    print(f"INFO: A descarregar mapa para '{localizacao}' (Raio: {dist}m) via OSMnx...")
    
    try:
        # 1. Obter coordenadas do local
        point = ox.geocode(localizacao)
        
        # 2. Descarregar o grafo a partir do ponto com raio
        # simplify=True remove nós intermediários de geometria, mantendo apenas interseções
        G_osm = ox.graph_from_point(point, dist=dist, network_type='drive', simplify=True)
        
        # 3. Garantir que o grafo é fortemente conexo (evitar ilhas e ruas sem saída)
        # Isto é crucial para garantir que qualquer ponto é alcançável a partir de qualquer outro
        if not nx.is_strongly_connected(G_osm):
            print("INFO: O grafo não é fortemente conexo. A filtrar pela maior componente...")
            largest_cc = max(nx.strongly_connected_components(G_osm), key=len)
            G_osm = G_osm.subgraph(largest_cc).copy()
            print(f"INFO: Grafo filtrado. Nós restantes: {len(G_osm.nodes)}")
        
        # 2. Converter para o nosso formato Grafo
        novo_grafo = Grafo()
        
        # Adicionar Nós
        # G_osm.nodes(data=True) retorna (id, {atibutos})
        for node_id, data in G_osm.nodes(data=True):
            # OSMnx retorna 'y' (lat) e 'x' (lon)
            lat = data['y']
            lon = data['x']
            
            # Determinar tipo aleatoriamente ou baseado em tags se existissem
            # Para simplificar, vamos colocar alguns como pontos de recarga
            tipo = 'PontoInteresse'
            pode_carregar = False
            
            if random.random() < 0.05: # 5% de chance de ser posto de carga
                tipo = 'EstacaoRecarga'
                pode_carregar = True
            
            novo_grafo.add_no(str(node_id), lat, lon, tipo)
            if pode_carregar:
                novo_grafo.nos[str(node_id)]['pode_carregar'] = True

        # Adicionar Arestas
        # G_osm.edges(data=True) retorna (u, v, {atributos})
        for u, v, data in G_osm.edges(data=True):
            u_str = str(u)
            v_str = str(v)
            
            # Calcular distância se não existir (osmnx geralmente traz 'length' em metros)
            dist_m = data.get('length', 0)
            dist_km = dist_m / 1000.0
            
            # Calcular tempo base (assumindo velocidade média se não houver 'maxspeed')
            # Se 'maxspeed' for lista, pegamos o primeiro. Se não existir, assumimos 50km/h
            maxspeed = data.get('maxspeed', 50)
            if isinstance(maxspeed, list):
                try:
                    maxspeed = float(maxspeed[0])
                except:
                    maxspeed = 50
            else:
                try:
                    maxspeed = float(maxspeed)
                except:
                    maxspeed = 50
            
            # Tempo em minutos = (dist_km / speed_kmh) * 60
            if maxspeed <= 0: maxspeed = 50
            tempo_min = (dist_km / maxspeed) * 60
            
            novo_grafo.add_aresta(u_str, v_str, dist_km, tempo_min)
            
            # Como o OSMnx é dirigido, se a rua for de duplo sentido, ele já deve ter a aresta inversa?
            # O 'drive' network type geralmente trata disso. Se for oneway=False, ele cria duas arestas.
            
        print(f"INFO: Mapa importado com sucesso! {len(novo_grafo.nos)} nós, {sum(len(v) for v in novo_grafo.arestas.values())} arestas.")
        return novo_grafo

    except Exception as e:
        print(f"ERRO ao importar mapa OSM: {e}")
        return None
