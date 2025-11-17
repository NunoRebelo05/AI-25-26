import json
from datetime import datetime
from Grafo import Grafo
from Taxi import Taxi, TipoMotorizacao
from Gestor import GestorDeFrota, EstrategiaProcura # Agora isto vai funcionar
from Simulador import Simulador

def carregar_grafo_de_json(ficheiro_json: str) -> Grafo:
    """
    Cria e retorna um objeto Grafo a partir de um ficheiro JSON.
    """
    mapa = Grafo()
    try:
        with open(ficheiro_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
            
            # 1. Carregar os Nós
            for no in data['nos']:
                mapa.add_no(no['id'], no['lat'], no['lon'], no.get('tipo', 'PontoInteresse'))
            
            # 2. Carregar as Arestas
            for aresta in data['arestas']:
                mapa.add_aresta(
                    aresta['origem'],
                    aresta['destino'],
                    aresta['distancia_km'],
                    aresta['tempo_base_min']
                )
            
            print(f"INFO: Grafo carregado de '{ficheiro_json}' com {len(mapa.nos)} nós e {len(data['arestas'])} arestas.")
            return mapa
            
    except FileNotFoundError:
        print(f"ERRO: Ficheiro do mapa '{ficheiro_json}' não encontrado.")
        return None
    except Exception as e:
        print(f"ERRO: Falha ao ler o JSON do mapa: {e}")
        return None

def setup_frota(gestor: GestorDeFrota):
    """
    Adiciona a frota inicial ao gestor.
    """
    frota = [
        Taxi("EV01", TipoMotorizacao.ELETRICO, "Centro", 4, 0.15, 250),
        Taxi("EV02", TipoMotorizacao.ELETRICO, "UMinho", 4, 0.15, 300),
        Taxi("GAS01", TipoMotorizacao.COMBUSTAO, "Estacao_CP", 4, 0.25, 600),
        Taxi("GAS02", TipoMotorizacao.COMBUSTAO, "Hospital", 6, 0.30, 550)
    ]
    for taxi in frota:
        gestor.add_taxi(taxi)

# --- NOVA FUNÇÃO PARA IMPRIMIR A TABELA ---
def imprimir_tabela_comparativa(resultados: list):
    """
    Recebe a lista de resultados e imprime uma tabela formatada no terminal.
    """
    print("\n" + "="*80)
    print("--- 🏆 TABELA DE COMPARAÇÃO FINAL DAS ESTRATÉGIAS 🏆 ---")
    print("="*80)
    
    # Cabeçalho
    # Ajusta os números (ex: <10, >13) para alinhar as colunas
    print(f"{'Estratégia':<10} | {'Total Pedidos':>13} | {'Concluídos':>10} | {'Rejeitados':>10} | {'Taxa Rej. (%)':>15} | {'Espera Média (min)':>20}")
    print("-"*80)
    
    # Ordenar os resultados (do melhor para o pior, ex: por taxa de rejeição)
    resultados_ordenados = sorted(resultados, key=lambda x: (x['taxa_rejeicao'], x['tempo_espera']))
    
    for res in resultados_ordenados:
        print(f"{res['estrategia']:<10} | {res['total_pedidos']:>13} | {res['concluidos']:>10} | {res['rejeitados']:>10} | {res['taxa_rejeicao']:>15.1f} | {res['tempo_espera']:>20.2f}")
        
    print("="*80)
    print("(Menor taxa de rejeição e tempo de espera = Melhor)")


# --- Ponto de Entrada Principal (Atualizado) ---
if __name__ == "__main__":
    
    mapa_braga = carregar_grafo_de_json("braga_mapa.json")
    if not mapa_braga:
        print("A simulação não pode continuar sem um mapa.")
        exit()
        
    hora_inicio = datetime(2025, 10, 20, 8, 0, 0)
    duracao_horas = 12
    
    estrategias = [
        EstrategiaProcura.A_STAR,
        EstrategiaProcura.UCS,
        EstrategiaProcura.GULOSA,
        EstrategiaProcura.DFS,
        EstrategiaProcura.BFS
    ]

    print("\n--- 🚀 INÍCIO DA COMPARAÇÃO DE ESTRATÉGIAS 🚀 ---")
    
    # --- LISTA PARA GUARDAR RESULTADOS ---
    resultados_finais = []

    for estrategia in estrategias:
        print("\n" + "="*50)
        print(f"A EXECUTAR SIMULAÇÃO COM ESTRATÉGIA: {estrategia.name}")
        
        mapa_para_sim = carregar_grafo_de_json("braga_mapa.json")
        gestor = GestorDeFrota(mapa_para_sim)
        setup_frota(gestor)
        gestor.definir_estrategia(estrategia)
        
        simulador = Simulador(gestor, hora_inicio, duracao_horas)
        
        resultados = simulador.run()
        resultados['estrategia'] = estrategia.name # Adicionar o nome
        resultados_finais.append(resultados)
    
    print("\n" + "="*50)
    print("--- 🏆 COMPARAÇÃO CONCLUÍDA 🏆 ---")
    
    imprimir_tabela_comparativa(resultados_finais)