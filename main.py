import json
from datetime import datetime
from Grafo import Grafo
from Taxi import Taxi, TipoMotorizacao
from Gestor import GestorDeFrota, EstrategiaProcura 
from Simulador import Simulador
from Pedido import EstadoPedido
from Config import cfg
import random

def setup_frota(gestor: GestorDeFrota):
    """
    Inicializa e adiciona a frota de táxis ao gestor.
    
    Lê as configurações de 'frota' (número de veículos, especificações)
    e cria instâncias de Taxi (Elétricos e Combustão), distribuindo-os
    pelos nós do grafo.
    
    Args:
        gestor (GestorDeFrota): O gestor onde a frota será registada.
    """
    # 1. Carregar specs da config
    specs_ev = cfg.get('frota.specs_eletrico')
    specs_gas = cfg.get('frota.specs_combustao')
    
    num_ev = cfg.get('frota.num_eletricos')
    num_gas = cfg.get('frota.num_combustao')
    
    locais = list(gestor.grafo.nos.keys())
    if not locais: return

    # 2. Criar Elétricos
    for i in range(num_ev):
        local = locais[i % len(locais)]
        taxi = Taxi(f"EV{i+1:02d}", TipoMotorizacao.ELETRICO, local, 
                    specs_ev['capacidade'], specs_ev['custo_km'], specs_ev['autonomia'])
        gestor.add_taxi(taxi)

    # 3. Criar Combustão
    for i in range(num_gas):
        local = locais[(i + 3) % len(locais)] # Offset para variar
        taxi = Taxi(f"GAS{i+1:02d}", TipoMotorizacao.COMBUSTAO, local,
                    specs_gas['capacidade'], specs_gas['custo_km'], specs_gas['autonomia'])
        gestor.add_taxi(taxi)

def imprimir_tabela_comparativa(resultados: list):
    """
    Imprime uma tabela formatada comparando o desempenho das estratégias.
    
    Exibe métricas como total de pedidos, concluídos/rejeitados, tempo médio de espera
    e eficiência da procura (média de nós visitados).
    
    Args:
        resultados (list): Lista de dicionários com os resultados de cada simulação.
    """
    print("\n" + "="*105)
    print(f"{'--- TABELA DE COMPARAÇÃO FINAL DAS ESTRATÉGIAS ---':^105}")
    print("="*105)
    
    # Info da Frota
    num_ev = cfg.get('frota.num_eletricos')
    num_gas = cfg.get('frota.num_combustao')
    print(f"Frota: {num_ev} Elétricos | {num_gas} Combustão")
    print("-" * 105)
    
    # Cabeçalho
    print(f"{'Estratégia':<12} | {'Total':>6} | {'Concl.':>6} | {'Rej.':>6} | {'Taxa Rej.':>10} | {'Espera (min)':>14} | {'Média Nós':>12}")
    print("-"*105)
    
    # Ordenar (Menor taxa de rejeição primeiro)
    resultados_ordenados = sorted(resultados, key=lambda x: (x['taxa_rejeicao'], x['tempo_espera']))
    
    for res in resultados_ordenados:
        print(f"{res['estrategia']:<12} | {res['total']:>6} | {res['concluidos']:>6} | {res['rejeitados']:>6} | {res['taxa_rejeicao']:>9.1f}% | {res['tempo_espera']:>14.2f} | {res['media_nos']:>12.1f}")
        
    print("="*105)

# --- Ponto de Entrada Principal ---
if __name__ == "__main__":
    
    # Carregar Configuração
    cfg.carregar()

    # Verificar se o mapa existe
    mapa_teste = Grafo.carregar_de_json("braga_mapa.json")
    if not mapa_teste: exit()
        
    hora_inicio = datetime(2025, 10, 20, 8, 0, 0)
    duracao_horas = cfg.get('simulacao.duracao_horas')
    
    # Lista de estratégias a testar no benchmark
    estrategias = [
        EstrategiaProcura.A_STAR,
        EstrategiaProcura.UCS,
        EstrategiaProcura.GULOSA,
        EstrategiaProcura.DFS,
        EstrategiaProcura.BFS
    ]

    print("\n--- INÍCIO DO BENCHMARK ---")
    resultados_finais = []

    for estrategia in estrategias:
        print(f"\n>> A TESTAR: {estrategia.name}...")
        
        # 1. Setup Limpo para cada iteração
        random.seed(42) # Garantir reprodutibilidade entre estratégias
        mapa_para_sim = Grafo.carregar_de_json("braga_mapa.json")
        gestor = GestorDeFrota(mapa_para_sim)
        setup_frota(gestor)
        gestor.definir_estrategia(estrategia)
        
        # 2. Correr Simulação
        # Nota: Assume-se que o Simulador corre sem GUI (rápido) por defeito se gui_interface=None
        # Forçamos usar_estaticos=True para garantir comparação justa (mesmos pedidos)
        simulador = Simulador(gestor, hora_inicio, duracao_horas, usar_estaticos=True)
        simulador.run()
        
        # 3. CALCULAR MÉTRICAS (Aqui mesmo, sem depender do return do Simulador)
        pedidos = simulador.pedidos_gerados
        total = len(pedidos)
        concluidos = [p for p in pedidos if p.estado == EstadoPedido.CONCLUIDO]
        rejeitados = [p for p in pedidos if p.estado == EstadoPedido.REJEITADO]
        
        taxa_rejeicao = (len(rejeitados) / total * 100) if total > 0 else 0.0
        
        tempo_medio = 0.0
        if concluidos:
            soma_tempos = sum(p.get_tempo_espera_total() for p in concluidos)
            tempo_medio = soma_tempos / len(concluidos)
            
        # Média de Nós Visitados (Eficiência do algoritmo)
        total_nos = gestor.stats['total_nos_visitados']
        total_procuras = gestor.stats['total_procuras']
        media_nos = (total_nos / total_procuras) if total_procuras > 0 else 0.0
        
        # Guardar dados
        resultados_finais.append({
            'estrategia': estrategia.name,
            'total': total,
            'concluidos': len(concluidos),
            'rejeitados': len(rejeitados),
            'taxa_rejeicao': taxa_rejeicao,
            'tempo_espera': tempo_medio,
            'media_nos': media_nos
        })
    
    # 4. Imprimir Tabela Final
    imprimir_tabela_comparativa(resultados_finais)