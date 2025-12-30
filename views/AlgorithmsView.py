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
        
        self.controls_frame = ctk.CTkFrame(self.header_frame, fg_color="transparent")
        self.controls_frame.pack(side="right")

        cenarios_dict = cfg.get('pedidos_estaticos.cenarios', {})
        cenarios_dict = cfg.get('pedidos_estaticos.cenarios', {})
        opcoes = ["Aleatório", "Todos os Cenários"] + (list(cenarios_dict.keys()) if cenarios_dict else [])
        self.cenario_var = ctk.StringVar(value="Aleatório")
        
        self.combo_cenario = ctk.CTkComboBox(self.controls_frame, values=opcoes, variable=self.cenario_var, width=200)
        self.combo_cenario.pack(side="left", padx=10)

        self.btn_run = ctk.CTkButton(self.controls_frame, text="Executar Benchmark", command=self.start_benchmark, 
                                     font=("Roboto Medium", 14), height=40)
        self.btn_run.pack(side="left")

        # Log Area
        self.txt_log = ctk.CTkTextbox(self, font=("Consolas", 12))
        self.txt_log.grid(row=1, column=0, sticky="nsew", padx=20, pady=(0, 20))
        self.txt_log.insert("0.0", "Clique em 'Executar Benchmark' para iniciar a comparação...\n")

    def start_benchmark(self):
        self.btn_run.configure(state="disabled", text="A Executar...")
        self.txt_log.delete("0.0", "end")
        cenario = self.cenario_var.get()
        threading.Thread(target=self.run_benchmark_thread, args=(cenario,)).start()

    def append_log(self, msg):
        self.txt_log.insert("end", msg + "\n")
        self.txt_log.see("end")

    def run_benchmark_thread(self, cenario_selecionado):
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

        # Determinar quais cenários rodar
        cenarios_a_rodar = []
        if cenario_selecionado == "Todos os Cenários":
            cenarios_dict = cfg.get('pedidos_estaticos.cenarios', {})
            # Adicionar todos os cenários nomeados
            cenarios_a_rodar = sorted(list(cenarios_dict.keys()))
        else:
            cenarios_a_rodar = [cenario_selecionado]

        log("\n--- INÍCIO DO BENCHMARK ---")
        
        for cenario_nome in cenarios_a_rodar:
            log("\n" + "#"*60)
            log(f"### {cenario_nome.upper()} ###")
            log("#"*60 + "\n")
            
            resultados_deste_cenario = []
            
            for estrategia in estrategias:
                log(f">> A TESTAR: {estrategia.name}...")
                
                random.seed(42)
                mapa_para_sim = Grafo.carregar_de_json("braga_mapa.json")
                gestor = GestorDeFrota(mapa_para_sim)
                self.setup_frota(gestor)
                gestor.definir_estrategia(estrategia)
                
                usar_estaticos = (cenario_nome != "Aleatório")
                lista_pedidos = cfg.get(f'pedidos_estaticos.cenarios.{cenario_nome}', []) if usar_estaticos else []

                simulador = Simulador(gestor, hora_inicio, duracao_horas, 
                                      usar_estaticos=usar_estaticos,
                                      lista_estaticos=lista_pedidos)
                try:
                    # Supressed output for batch run? Maybe kept to show progress
                    metrics = simulador.run()
                except Exception as e:
                    log(f"ERRO ao correr {estrategia.name}: {e}")
                    continue
                
                # Metrics
                total_nos = gestor.stats['total_nos_visitados']
                total_procuras = gestor.stats['total_procuras']
                media_nos = (total_nos / total_procuras) if total_procuras > 0 else 0.0
                
                metrics['estrategia'] = estrategia.name
                metrics['media_nos'] = media_nos
                
                resultados_deste_cenario.append(metrics)
                log(f"   -> Concluído (Rejeição: {metrics['taxa_rejeicao']:.1f}%)")
            
            # Show table for THIS scenario immediately
            self.after(0, self.show_results_table, resultados_deste_cenario, cenario_nome)

        self.after(0, lambda: self.btn_run.configure(state="normal", text="Executar Benchmark"))

    def show_results(self, resultados):
        # Wrapper legacy ou usado internamente se precisar
        self.show_results_table(resultados, "Resultados")

    def show_results_table(self, resultados, titulo):
        pad = " "
        # Definição das larguras das colunas
        w_strat, w_rej, w_esp, w_ocup, w_cust, w_co2, w_km, w_vaz, w_nos = 12, 8, 10, 8, 10, 8, 10, 8, 8
        
        # Headers e Separadores
        top_border = f"┌{'─'*w_strat}┬{'─'*w_rej}┬{'─'*w_esp}┬{'─'*w_ocup}┬{'─'*w_cust}┬{'─'*w_co2}┬{'─'*w_km}┬{'─'*w_vaz}┬{'─'*w_nos}┐"
        mid_border = f"├{'─'*w_strat}┼{'─'*w_rej}┼{'─'*w_esp}┼{'─'*w_ocup}┼{'─'*w_cust}┼{'─'*w_co2}┼{'─'*w_km}┼{'─'*w_vaz}┼{'─'*w_nos}┤"
        bot_border = f"└{'─'*w_strat}┴{'─'*w_rej}┴{'─'*w_esp}┴{'─'*w_ocup}┴{'─'*w_cust}┴{'─'*w_co2}┴{'─'*w_km}┴{'─'*w_vaz}┴{'─'*w_nos}┘"
        
        header_str = (f"│{' Estratégia':<{w_strat}}│{' Rej.%':>{w_rej}}│{' Esp(m)':>{w_esp}}│{' Ocup%':>{w_ocup}}│"
                      f"{' Custo':>{w_cust}}│{' CO2':>{w_co2}}│{' KmTot':>{w_km}}│{' Vaz%':>{w_vaz}}│{' Nós':>{w_nos}}│")

        self.append_log("")
        self.append_log(top_border)
        # Ajustar titulo para caber
        safe_title = f"{titulo}"[:len(top_border)-4]
        self.append_log(f"│{safe_title:^{len(top_border)-2}}│")
        self.append_log(mid_border)
        self.append_log(header_str)
        self.append_log(mid_border)
        
        resultados_ordenados = sorted(resultados, key=lambda x: (x['custos_totais'], x['media_nos']))
        
        for res in resultados_ordenados:
            pct_vazio = (res['km_vazios'] / res['total_km'] * 100) if res.get('total_km', 0) > 0 else 0.0
            
            line = (f"│ {res['estrategia']:<{w_strat-1}}│"
                    f"{res['taxa_rejeicao']:>{w_rej-1}.1f} │"
                    f"{res['tempo_espera']:>{w_esp-1}.2f} │"
                    f"{res['taxa_ocupacao']:>{w_ocup-1}.1f} │"
                    f"{res['custos_totais']:>{w_cust-1}.1f} │"
                    f"{res['emissoes_co2']:>{w_co2-1}.1f} │" 
                    f"{res['total_km']:>{w_km-1}.1f} │"
                    f"{pct_vazio:>{w_vaz-1}.1f} │"
                    f"{res['media_nos']:>{w_nos-1}.0f} │")
            self.append_log(line)
            
        self.append_log(bot_border)

    def setup_frota(self, gestor):
        specs_ev = cfg.get('frota.specs_eletrico')
        specs_gas = cfg.get('frota.specs_combustao')
        num_ev = cfg.get('frota.num_eletricos')
        num_gas = cfg.get('frota.num_combustao')
        locais = list(gestor.grafo.nos.keys())
        
        for i in range(num_ev):
            local = locais[i % len(locais)]
            taxi = Taxi(f"EV{i+1:02d}", TipoMotorizacao.ELETRICO, local, 
                        specs_ev['capacidade'], specs_ev['custo_km'], specs_ev['autonomia'], 
                        specs_ev.get('emissao_co2_km', 0.0), specs_ev.get('tempo_recarga_min', 30))
            gestor.add_taxi(taxi)

        for i in range(num_gas):
            local = locais[(i + 3) % len(locais)]
            taxi = Taxi(f"GAS{i+1:02d}", TipoMotorizacao.COMBUSTAO, local,
                        specs_gas['capacidade'], specs_gas['custo_km'], specs_gas['autonomia'], 
                        specs_gas.get('emissao_co2_km', 0.14), specs_gas.get('tempo_abastecimento_min', 5))
            gestor.add_taxi(taxi)
