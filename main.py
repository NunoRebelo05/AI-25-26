from datetime import datetime
from Grafo import Grafo
from Taxi import Taxi, TipoMotorizacao
from Gestor import GestorDeFrota
from Simulador import Simulador

def setup_simulacao():
    """
    Cria todos os objetos iniciais para a simulação.
    """
    
    # 1. Criar o Grafo (simples)
    mapa_braga = Grafo()
    mapa_braga.add_no("Centro", 41.5518, -8.4231, tipo="ZonaRecolha")
    mapa_braga.add_no("UMinho", 41.5623, -8.3952, tipo="ZonaRecolha")
    mapa_braga.add_no("Estacao_CP", 41.5471, -8.4326, tipo="PontoInteresse")
    mapa_braga.add_no("Hospital", 41.5600, -8.4350, tipo="ZonaRecolha")
    mapa_braga.add_no("Estacao_Recarga_1", 41.5580, -8.4100, tipo="EstacaoRecarga")
    
    mapa_braga.add_aresta("Centro", "UMinho", 4.5, 10.0)
    mapa_braga.add_aresta("UMinho", "Centro", 4.2, 9.0)
    mapa_braga.add_aresta("Centro", "Estacao_CP", 1.8, 5.0)
    mapa_braga.add_aresta("Estacao_CP", "Centro", 2.0, 6.0)
    mapa_braga.add_aresta("Centro", "Hospital", 2.5, 7.0)
    mapa_braga.add_aresta("Hospital", "Centro", 2.6, 8.0)
    mapa_braga.add_aresta("UMinho", "Hospital", 3.0, 6.0)
    mapa_braga.add_aresta("Hospital", "UMinho", 3.0, 6.0)
    mapa_braga.add_aresta("UMinho", "Estacao_Recarga_1", 2.2, 5.0)
    mapa_braga.add_aresta("Centro", "Estacao_Recarga_1", 2.0, 4.0)

    # 2. Criar a Frota
    frota = [
        Taxi("EV01", TipoMotorizacao.ELETRICO, "Centro", 4, 0.15, 250),
        Taxi("EV02", TipoMotorizacao.ELETRICO, "UMinho", 4, 0.15, 300),
        Taxi("GAS01", TipoMotorizacao.COMBUSTAO, "Estacao_CP", 4, 0.25, 600),
        Taxi("GAS02", TipoMotorizacao.COMBUSTAO, "Hospital", 6, 0.30, 550)
    ]
    
    # 3. Criar o Gestor
    gestor = GestorDeFrota(mapa_braga)
    for taxi in frota:
        gestor.add_taxi(taxi)
        
    return gestor

# --- Ponto de Entrada Principal ---
if __name__ == "__main__":
    
    # 1. Configurar o mundo
    print("A configurar o ambiente da simulação...")
    gestor_taxi_green = setup_simulacao()
    
    # 2. Definir parâmetros da simulação
    hora_inicio = datetime(2025, 10, 20, 8, 0, 0) # 20/10/2025 às 08:00
    duracao_horas = 12 # Simular um dia de 12 horas (até às 20:00)
    
    # 3. Criar e correr o simulador
    simulador = Simulador(gestor_taxi_green, hora_inicio, duracao_horas)
    
    print("\nA iniciar a simulação...")
    simulador.run()