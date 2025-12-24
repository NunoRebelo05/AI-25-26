import json
from datetime import datetime
import threading
import random
import customtkinter as ctk
import tkinter as tk # For some constants if needed

from Grafo import Grafo
from Taxi import Taxi, TipoMotorizacao
from Gestor import GestorDeFrota, EstrategiaProcura 
from Simulador import Simulador
from Pedido import EstadoPedido
from Config import cfg

def setup_frota(gestor: GestorDeFrota):
    """
    Inicializa e adiciona a frota de táxis ao gestor.
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
                    specs_ev['capacidade'], specs_ev['custo_km'], specs_ev['autonomia'], 
                    specs_ev.get('emissao_co2_km', 0.0), specs_ev.get('tempo_recarga_min', 30))
        gestor.add_taxi(taxi)

    # 3. Criar Combustão
    for i in range(num_gas):
        local = locais[(i + 3) % len(locais)] # Offset para variar
        taxi = Taxi(f"GAS{i+1:02d}", TipoMotorizacao.COMBUSTAO, local,
                    specs_gas['capacidade'], specs_gas['custo_km'], specs_gas['autonomia'], 
                    specs_gas.get('emissao_co2_km', 0.14), specs_gas.get('tempo_abastecimento_min', 5))
        gestor.add_taxi(taxi)

def run_benchmark(log_callback=None, finish_callback=None):
    """
    Executa o benchmark de todas as estratégias.
    
    Args:
        log_callback (func): Função para receber mensagens de log (str).
        finish_callback (func): Função chamada com os resultados finais (list).
    """
    def log(msg):
        if log_callback: log_callback(msg)
        else: print(msg)

    # Carregar Configuração
    cfg.carregar()

    # Verificar se o mapa existe
    mapa_teste = Grafo.carregar_de_json("braga_mapa.json")
    if not mapa_teste: 
        log("Erro: Mapa não encontrado.")
        return
        
    hora_inicio = datetime(2025, 10, 20, 8, 0, 0)
    duracao_horas = cfg.get('simulacao.duracao_horas')
    
    estrategias = [
        EstrategiaProcura.A_STAR,
        EstrategiaProcura.UCS,
        EstrategiaProcura.GULOSA,
        EstrategiaProcura.DFS,
        EstrategiaProcura.BFS
    ]

    log("\n--- INÍCIO DO BENCHMARK ---\n")
    resultados_finais = []

    for estrategia in estrategias:
        log(f">> A TESTAR: {estrategia.name}...")
        
        # 1. Setup Limpo para cada iteração
        random.seed(42) # Garantir reprodutibilidade entre estratégias
        mapa_para_sim = Grafo.carregar_de_json("braga_mapa.json")
        gestor = GestorDeFrota(mapa_para_sim)
        setup_frota(gestor)
        gestor.definir_estrategia(estrategia)
        
        # 2. Correr Simulação
        # 2. Correr Simulação
        simulador = Simulador(gestor, hora_inicio, duracao_horas, usar_estaticos=True)
        metrics = simulador.run()
        
        # Média de Nós Visitados (Eficiência do algoritmo)
        total_nos = gestor.stats['total_nos_visitados']
        total_procuras = gestor.stats['total_procuras']
        media_nos = (total_nos / total_procuras) if total_procuras > 0 else 0.0
        
        # Enriquecer métricas com dados do gestor
        metrics['estrategia'] = estrategia.name
        metrics['media_nos'] = media_nos
        
        resultados_finais.append(metrics)
        log(f"   -> Concluído (Rejeição: {metrics['taxa_rejeicao']:.1f}%)")
    
    if finish_callback:
        finish_callback(resultados_finais)

class BenchmarkWindow(ctk.CTkToplevel):
    def __init__(self, master=None):
        super().__init__(master)
        self.title("Benchmark de Algoritmos")
        self.geometry("900x600")
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1) # Log area expands

        # Header
        self.header_frame = ctk.CTkFrame(self)
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        
        ctk.CTkLabel(self.header_frame, text="Comparação de Algoritmos", font=("Roboto Medium", 20)).pack(side="left", padx=20)
        
        self.btn_run = ctk.CTkButton(self.header_frame, text="Executar Benchmark", command=self.start_benchmark)
        self.btn_run.pack(side="right", padx=20, pady=10)

        # Log Area / Results
        self.txt_log = ctk.CTkTextbox(self, font=("Consolas", 12))
        self.txt_log.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.txt_log.insert("0.0", "Clique em 'Executar Benchmark' para iniciar a comparação...\n")

    def start_benchmark(self):
        self.btn_run.configure(state="disabled", text="A Executar...")
        self.txt_log.delete("0.0", "end")
        
        # Run in thread to not freeze GUI
        threading.Thread(target=run_benchmark, args=(self.append_log, self.show_results)).start()

    def append_log(self, msg):
        self.txt_log.insert("end", msg + "\n")
        self.txt_log.see("end")

    def show_results(self, resultados):
        self.append_log("\n" + "="*105)
        self.append_log(f"{'--- TABELA DE COMPARAÇÃO FINAL DAS ESTRATÉGIAS ---':^105}")
        self.append_log("="*105)
        
        # Info da Frota
        num_ev = cfg.get('frota.num_eletricos')
        num_gas = cfg.get('frota.num_combustao')
        self.append_log(f"Frota: {num_ev} Elétricos | {num_gas} Combustão")
        self.append_log("-" * 105)
        
        # Cabeçalho
        header = f"{'Estratégia':<10} | {'Rej.%':>5} | {'Esp.(m)':>8} | {'Ocup.%':>6} | {'Custo':>8} | {'CO2':>6} | {'Vazio%':>6} | {'Nós':>6}"
        self.append_log(header)
        self.append_log("-"*105)
        
        # Ordenar (Menor taxa de rejeição primeiro)
        resultados_ordenados = sorted(resultados, key=lambda x: (x['taxa_rejeicao'], x['tempo_espera']))
        
        for res in resultados_ordenados:
            km_total = res['km_toais'] if 'km_toais' in res else res.get('total_km_vazio', 0) + res.get('km_com_passageiro', 0) # Fallback if specific key missing
            
            # Nota: 'km_vazios' vem do Simulador.print_summary -> 'km_vazios'
            # Mas espera, print_summary retorna 'km_vazios' e 'total_pedidos'...
            # Vamos usar os nomes do dict retornado em Simulador.print_summary
            
            # Calculo percentagem kms vazios
            # TOTAL KM não está no return do print_summary?? Vamos adicionar ou calcular.
            # print_summary retorna 'custos_totais', 'emissoes_co2', 'km_vazios'
            # Precisamos de 'km_totais' para %. Mas custo total / custo medio? Não.
            # Deixa simples: mostra Km Vazio Absoluto ou Custo e CO2 que são os principais.
            
            # Vamos ajustar as colunas para caber:
            # Estrat | Rej% | Espera | Ocup% | Custo | CO2 | Nós
            
            taxa_vazios = 0.0 # Placeholder se não tivermos km totais directos no dict.
            # Verifiquei o código do Simulador: ele devolve 'km_vazios' no return. 
            # NÃO DEVOLVE 'km_total'. Vou ter de confiar nos valores absolutos ou adicionar no simulator.
            
            line = (f"{res['estrategia']:<10} | "
                    f"{res['taxa_rejeicao']:>5.1f} | "
                    f"{res['tempo_espera']:>8.2f} | "
                    f"{res['taxa_ocupacao']:>6.1f} | "
                    f"{res['custos_totais']:>8.2f} | "
                    f"{res['emissoes_co2']:>6.2f} | " 
                    f"{res['km_vazios']:>6.1f} | "
                    f"{res['media_nos']:>6.1f}")
            self.append_log(line)
            
        self.append_log("="*105)
        self.btn_run.configure(state="normal", text="Executar Benchmark")

if __name__ == "__main__":
    # Teste isolado
    app = ctk.CTk()
    app.withdraw()
    win = BenchmarkWindow(app)
    win.protocol("WM_DELETE_WINDOW", app.quit)
    app.mainloop()