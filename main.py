import json
from datetime import datetime
from Grafo import Grafo
from Taxi import Taxi, TipoMotorizacao
from Gestor import GestorDeFrota, EstrategiaProcura 
from Simulador import Simulador
from Pedido import EstadoPedido # Necessário para calcular as métricas aqui

def carregar_grafo_de_json(ficheiro_json: str) -> Grafo:
    """Cria e retorna um objeto Grafo a partir de um ficheiro JSON."""
    mapa = Grafo()
    try:
        with open(ficheiro_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
            for no in data['nos']:
                mapa.add_no(no['id'], no['lat'], no['lon'], no.get('tipo', 'PontoInteresse'))
                # Carregar a flag de carregamento se existir
                if no.get('pode_carregar'):
                     mapa.nos[no['id']]['pode_carregar'] = True
            
            for aresta in data['arestas']:
                mapa.add_aresta(aresta['origem'], aresta['destino'], aresta['distancia_km'], aresta['tempo_base_min'])
            
            print(f"INFO: Grafo carregado de '{ficheiro_json}' com {len(mapa.nos)} nós.")
            return mapa
    except Exception as e:
        print(f"ERRO: Falha ao ler o JSON do mapa: {e}")
        return None

def setup_frota(gestor: GestorDeFrota):
    """Adiciona a frota inicial ao gestor."""
    frota = [
        Taxi("EV01", TipoMotorizacao.ELETRICO, "Centro", 4, 0.15, 250),
        Taxi("EV02", TipoMotorizacao.ELETRICO, "UMinho", 4, 0.15, 300),
        Taxi("GAS01", TipoMotorizacao.COMBUSTAO, "Estacao_CP", 4, 0.25, 600),
        Taxi("GAS02", TipoMotorizacao.COMBUSTAO, "Hospital", 6, 0.30, 550)
    ]
    for taxi in frota:
        gestor.add_taxi(taxi)

def imprimir_tabela_comparativa(resultados: list):
    """Imprime a tabela final com os dados recolhidos."""
    print("\n" + "="*90)
    print(f"{'--- 🏆 TABELA DE COMPARAÇÃO FINAL DAS ESTRATÉGIAS 🏆 ---':^90}")
    print("="*90)
    
    # Cabeçalho
    print(f"{'Estratégia':<12} | {'Total':>6} | {'Concl.':>6} | {'Rej.':>6} | {'Taxa Rej.':>10} | {'Espera (min)':>14}")
    print("-"*90)
    
    # Ordenar (Menor taxa de rejeição primeiro)
    resultados_ordenados = sorted(resultados, key=lambda x: (x['taxa_rejeicao'], x['tempo_espera']))
    
    for res in resultados_ordenados:
        print(f"{res['estrategia']:<12} | {res['total']:>6} | {res['concluidos']:>6} | {res['rejeitados']:>6} | {res['taxa_rejeicao']:>9.1f}% | {res['tempo_espera']:>14.2f}")
        
    print("="*90)

# --- Ponto de Entrada Principal ---
if __name__ == "__main__":
    
    # Verificar se o mapa existe
    mapa_teste = carregar_grafo_de_json("braga_mapa.json")
    if not mapa_teste: exit()
        
    hora_inicio = datetime(2025, 10, 20, 8, 0, 0)
    duracao_horas = 12
    
    estrategias = [
        EstrategiaProcura.A_STAR,
        EstrategiaProcura.UCS,
        EstrategiaProcura.GULOSA,
        EstrategiaProcura.DFS,
        EstrategiaProcura.BFS
    ]

    print("\n--- 🚀 INÍCIO DO BENCHMARK 🚀 ---")
    resultados_finais = []

    for estrategia in estrategias:
        print(f"\n>> A TESTAR: {estrategia.name}...")
        
        # 1. Setup Limpo
        mapa_para_sim = carregar_grafo_de_json("braga_mapa.json")
        gestor = GestorDeFrota(mapa_para_sim)
        setup_frota(gestor)
        gestor.definir_estrategia(estrategia)
        
        # 2. Correr Simulação
        # Nota: Assume-se que o Simulador corre sem GUI (rápido) por defeito se gui_interface=None
        simulador = Simulador(gestor, hora_inicio, duracao_horas)
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
        
        # Guardar dados
        resultados_finais.append({
            'estrategia': estrategia.name,
            'total': total,
            'concluidos': len(concluidos),
            'rejeitados': len(rejeitados),
            'taxa_rejeicao': taxa_rejeicao,
            'tempo_espera': tempo_medio
        })
    
    # 4. Imprimir Tabela Final
    imprimir_tabela_comparativa(resultados_finais)