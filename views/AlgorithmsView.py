import customtkinter as ctk
import threading
import random
from datetime import datetime

from Grafo import Grafo
from Taxi import Taxi, TipoMotorizacao
from Gestor import GestorDeFrota, EstrategiaProcura
from Simulador import Simulador
from Pedido import EstadoPedido
from Config import cfg

class AlgorithmsView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Header
        self.header_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.header_frame.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        
        ctk.CTkLabel(self.header_frame, text="Comparação de Algoritmos", font=("Roboto Medium", 24)).pack(side="left")
        
        self.btn_run = ctk.CTkButton(self.header_frame, text="Executar Benchmark", command=self.start_benchmark, 
                                     font=("Roboto Medium", 14), height=40)
        self.btn_run.pack(side="right")

        # Log Area
        self.txt_log = ctk.CTkTextbox(self, font=("Consolas", 12))
        self.txt_log.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.txt_log.insert("0.0", "Clique em 'Executar Benchmark' para iniciar a comparação...\n")

    def start_benchmark(self):
        self.btn_run.configure(state="disabled", text="A Executar...")
        self.txt_log.delete("0.0", "end")
        threading.Thread(target=self.run_benchmark_thread).start()

    def append_log(self, msg):
        self.txt_log.insert("end", msg + "\n")
        self.txt_log.see("end")

    def run_benchmark_thread(self):
        def log(msg):
            self.after(0, self.append_log, msg)

        cfg.carregar()
        mapa_teste = Grafo.carregar_de_json("braga_mapa.json")
        if not mapa_teste: 
            log("Erro: Mapa não encontrado.")
            self.after(0, lambda: self.btn_run.configure(state="normal", text="Executar Benchmark"))
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
            
            random.seed(42)
            mapa_para_sim = Grafo.carregar_de_json("braga_mapa.json")
            gestor = GestorDeFrota(mapa_para_sim)
            self.setup_frota(gestor)
            gestor.definir_estrategia(estrategia)
            
            simulador = Simulador(gestor, hora_inicio, duracao_horas, usar_estaticos=True)
            simulador.run()
            
            # Metrics
            pedidos = simulador.pedidos_gerados
            total = len(pedidos)
            concluidos = [p for p in pedidos if p.estado == EstadoPedido.CONCLUIDO]
            rejeitados = [p for p in pedidos if p.estado == EstadoPedido.REJEITADO]
            
            taxa_rejeicao = (len(rejeitados) / total * 100) if total > 0 else 0.0
            
            tempo_medio = 0.0
            if concluidos:
                soma_tempos = sum(p.get_tempo_espera_total() for p in concluidos)
                tempo_medio = soma_tempos / len(concluidos)
                
            total_nos = gestor.stats['total_nos_visitados']
            total_procuras = gestor.stats['total_procuras']
            media_nos = (total_nos / total_procuras) if total_procuras > 0 else 0.0
            
            res = {
                'estrategia': estrategia.name,
                'total': total,
                'concluidos': len(concluidos),
                'rejeitados': len(rejeitados),
                'taxa_rejeicao': taxa_rejeicao,
                'tempo_espera': tempo_medio,
                'media_nos': media_nos
            }
            resultados_finais.append(res)
            log(f"   -> Concluído (Rejeição: {taxa_rejeicao:.1f}%)")
        
        self.after(0, self.show_results, resultados_finais)

    def setup_frota(self, gestor):
        specs_ev = cfg.get('frota.specs_eletrico')
        specs_gas = cfg.get('frota.specs_combustao')
        num_ev = cfg.get('frota.num_eletricos')
        num_gas = cfg.get('frota.num_combustao')
        locais = list(gestor.grafo.nos.keys())
        
        for i in range(num_ev):
            local = locais[i % len(locais)]
            taxi = Taxi(f"EV{i+1:02d}", TipoMotorizacao.ELETRICO, local, 
                        specs_ev['capacidade'], specs_ev['custo_km'], specs_ev['autonomia'])
            gestor.add_taxi(taxi)

        for i in range(num_gas):
            local = locais[(i + 3) % len(locais)]
            taxi = Taxi(f"GAS{i+1:02d}", TipoMotorizacao.COMBUSTAO, local,
                        specs_gas['capacidade'], specs_gas['custo_km'], specs_gas['autonomia'])
            gestor.add_taxi(taxi)

    def show_results(self, resultados):
        self.append_log("\n" + "="*105)
        self.append_log(f"{'--- TABELA DE COMPARAÇÃO FINAL DAS ESTRATÉGIAS ---':^105}")
        self.append_log("="*105)
        
        header = f"{'Estratégia':<12} | {'Total':>6} | {'Concl.':>6} | {'Rej.':>6} | {'Taxa Rej.':>10} | {'Espera (min)':>14} | {'Média Nós':>12}"
        self.append_log(header)
        self.append_log("-"*105)
        
        resultados_ordenados = sorted(resultados, key=lambda x: (x['taxa_rejeicao'], x['tempo_espera']))
        
        for res in resultados_ordenados:
            line = f"{res['estrategia']:<12} | {res['total']:>6} | {res['concluidos']:>6} | {res['rejeitados']:>6} | {res['taxa_rejeicao']:>9.1f}% | {res['tempo_espera']:>14.2f} | {res['media_nos']:>12.1f}"
            self.append_log(line)
            
        self.append_log("="*105)
        self.btn_run.configure(state="normal", text="Executar Benchmark")
