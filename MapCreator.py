import folium
from Grafo import Grafo 

def criar_grafo_teste_braga():
    """
    Cria um grafo de teste com alguns pontos de interesse em Braga.
    
    Útil para testes rápidos sem necessidade de carregar o ficheiro JSON completo.
    
    Returns:
        Grafo: Um objeto Grafo preenchido com nós e arestas de teste.
    """
    mapa_braga = Grafo()
    
    # Adicionar Nós (com coordenadas approx. de Braga)
    mapa_braga.add_no("Centro", 41.5518, -8.4231, tipo="ZonaRecolha")
    mapa_braga.add_no("UMinho_Gualtar", 41.5623, -8.3952, tipo="ZonaRecolha")
    mapa_braga.add_no("Estacao_CP", 41.5471, -8.4326, tipo="PontoInteresse")
    mapa_braga.add_no("Estacao_Recarga_Eletrica", 41.5580, -8.4100, tipo="EstacaoRecarga")

    # Adicionar Arestas
    mapa_braga.add_aresta("Centro", "UMinho_Gualtar", 4.5, 8.0)
    mapa_braga.add_aresta("UMinho_Gualtar", "Centro", 4.2, 7.5)
    mapa_braga.add_aresta("Centro", "Estacao_CP", 1.8, 4.0)
    mapa_braga.add_aresta("Estacao_CP", "Centro", 2.0, 5.0)
    mapa_braga.add_aresta("Centro", "Estacao_Recarga_Eletrica", 2.5, 6.0)
    mapa_braga.add_aresta("UMinho_Gualtar", "Estacao_Recarga_Eletrica", 2.2, 5.0)
    
    return mapa_braga

def desenhar_grafo_em_mapa(grafo: Grafo, nome_ficheiro_html="mapa_grafo_braga.html"):
    """
    Gera um mapa interativo HTML visualizando o grafo.
    
    Usa a biblioteca Folium para plotar os nós como marcadores e as arestas como linhas.
    Os marcadores têm cores diferentes dependendo do tipo de nó.
    
    Args:
        grafo (Grafo): O grafo a ser visualizado.
        nome_ficheiro_html (str, optional): Caminho de saída para o ficheiro HTML.
    """
    
    # 1. Encontrar o ponto central do mapa (média das coordenadas)
    if not grafo.nos:
        print("Grafo está vazio, não é possível desenhar.")
        return
        
    avg_lat = sum(info['lat'] for info in grafo.nos.values()) / len(grafo.nos)
    avg_lon = sum(info['lon'] for info in grafo.nos.values()) / len(grafo.nos)
    
    # 2. Criar o mapa Folium, centrado
    mapa_interativo = folium.Map(location=[avg_lat, avg_lon], zoom_start=14)
    
    # 3. Adicionar os Nós ao mapa como marcadores
    for id_no, info in grafo.nos.items():
        # Escolher um ícone/cor com base no tipo
        tipo = info.get('tipo', 'PontoInteresse')
        if tipo == 'EstacaoRecarga':
            cor_icone = 'blue'
            icone = 'charging-station'
        elif tipo == 'ZonaRecolha':
            cor_icone = 'green'
            icone = 'user'
        else:
            cor_icone = 'red'
            icone = 'info-sign'
            
        folium.Marker(
            location=[info['lat'], info['lon']],
            popup=f"<b>{id_no}</b><br>Tipo: {tipo}", # Popup ao clicar
            tooltip=id_no, # Tooltip ao pairar
            icon=folium.Icon(color=cor_icone, icon=icone, prefix='glyphicon')
        ).add_to(mapa_interativo)
        
    # 4. Adicionar as Arestas ao mapa como linhas
    for origem, destinos in grafo.arestas.items():
        for destino in destinos:
            # Obter coordenadas de origem e destino
            pos_origem = (grafo.nos[origem]['lat'], grafo.nos[origem]['lon'])
            pos_destino = (grafo.nos[destino]['lat'], grafo.nos[destino]['lon'])
            
            # Desenhar a linha
            folium.PolyLine(
                locations=[pos_origem, pos_destino],
                color='blue',
                weight=3,
                opacity=0.7,
                tooltip=f"{origem} -> {destino}"
            ).add_to(mapa_interativo)
            
    # 5. Salvar o mapa como um ficheiro HTML
    mapa_interativo.save(nome_ficheiro_html)
    print(f"Mapa guardado como '{nome_ficheiro_html}'. Abra este ficheiro no seu browser.")


# --- Executar a visualização ---
if __name__ == "__main__":
    print("A criar o grafo de teste...")
    grafo_braga = criar_grafo_teste_braga()
    
    print("A gerar o mapa interativo com Folium...")
    desenhar_grafo_em_mapa(grafo_braga)