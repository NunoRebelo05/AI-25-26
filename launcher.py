import tkinter as tk
from tkinter import messagebox
import customtkinter as ctk
import threading
import json
from datetime import datetime
import traceback

from Grafo import Grafo
from Taxi import Taxi, TipoMotorizacao
from Gestor import GestorDeFrota, EstrategiaProcura
from Simulador import Simulador
from VisualizadorGUI import MapaVisualizador
from Config import cfg

def iniciar_simulacao(config_launch: dict, app_gui: 'AppLauncher'):
    """
    Inicializa e executa a simulação em uma thread separada.
    """
    try:
        # 1. Carregar o mapa e configurar o gestor
        mapa = Grafo.carregar_de_json("braga_mapa.json")
        if not mapa:
            print("Erro: Não foi possível carregar o mapa.")
            return

        gestor = GestorDeFrota(mapa)
        gestor.definir_estrategia(config_launch['estrategia'])
        
        # 2. Configurar a Frota
        locais = list(mapa.nos.keys())
        specs_electric = cfg.get('frota.specs_eletrico')
        specs_combustion = cfg.get('frota.specs_combustao')

        # Inicializar táxis elétricos
        for i in range(config_launch['num_eletricos']):
            local_inicio = locais[i % len(locais)]
            novo_taxi = Taxi(
                id_veiculo=f"EV{i+1:02d}",
                tipo=TipoMotorizacao.ELETRICO,
                localizacao_atual=local_inicio, 
                capacidade_passageiros=specs_electric['capacidade'],
                custo_por_km=specs_electric['custo_km'],
                autonomia_maxima=specs_electric['autonomia']
            )
            gestor.add_taxi(novo_taxi)
            
        # Inicializar táxis a combustão
        for i in range(config_launch['num_combustao']):
            local_inicio = locais[(i + 3) % len(locais)]
            novo_taxi = Taxi(
                id_veiculo=f"GAS{i+1:02d}",
                tipo=TipoMotorizacao.COMBUSTAO,
                localizacao_atual=local_inicio, 
                capacidade_passageiros=specs_combustion['capacidade'],
                custo_por_km=specs_combustion['custo_km'],
                autonomia_maxima=specs_combustion['autonomia']
            )
            gestor.add_taxi(novo_taxi)

        # 3. Criar Janela de Visualização
        # Usamos tk.Toplevel padrão para a visualização pois o MapaVisualizador usa Canvas do tk
        janela_simulacao = tk.Toplevel()
        janela_simulacao.title(f"Simulação TaxiGreen - {config_launch['estrategia'].name}")
        janela_simulacao.geometry("1150x650")
        
        gui_mapa = MapaVisualizador(janela_simulacao, mapa, largura=800, altura=600)
        gui_mapa.pack(fill="both", expand=True)

        # 4. Iniciar o Simulador
        simulador = Simulador(
            gestor=gestor,
            hora_inicio=datetime(2025, 10, 20, 8, 0, 0),
            duracao_sim_horas=config_launch['duracao_horas'],
            horas_ponta=config_launch['horas_ponta'],
            prob_pedido=config_launch['prob_pedido'],
            gui_interface=gui_mapa,
            prob_pedido=config_launch['prob_pedido'],
            gui_interface=gui_mapa,
            usar_estaticos=config_launch['usar_estaticos'],
            lista_estaticos=config_launch.get('lista_estaticos')
        )
        
        gui_mapa.set_simulador(simulador)
        print("\n[Sistema] A iniciar a simulação...")
        simulador.run() 
        
        messagebox.showinfo("Sucesso", "Simulação concluída com sucesso!")

    except Exception as e:
        print(f"ERRO FATAL NA SIMULAÇÃO: {e}")
        traceback.print_exc()
    finally:
        app_gui.reativar_botao()

class AppLauncher(ctk.CTkToplevel):
    """
    Janela de configuração e lançamento da simulação.
    """
    def __init__(self, master=None):
        super().__init__(master)
        self.title("Configuração TaxiGreen")
        self.geometry("500x650")
        
        # Carregar config inicial
        cfg.carregar()
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)

        main_frame = ctk.CTkFrame(self)
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)

        # Título
        ctk.CTkLabel(main_frame, text="Configurar Simulação", font=("Roboto Medium", 20)).pack(pady=(10, 20))

        # --- Estratégia ---
        ctk.CTkLabel(main_frame, text="Estratégia de Procura:", anchor="w").pack(fill="x", pady=(5, 0))
        self.strat_var = ctk.StringVar(value=EstrategiaProcura.A_STAR.name)
        self.combo_strat = ctk.CTkComboBox(main_frame, values=[e.name for e in EstrategiaProcura], variable=self.strat_var)
        self.combo_strat.pack(fill="x", pady=5)
        
        # --- Frota ---
        # Frame Frota
        frota_frame = ctk.CTkFrame(main_frame)
        frota_frame.pack(fill="x", pady=15)
        ctk.CTkLabel(frota_frame, text="Frota", font=("Roboto Medium", 14)).pack(pady=5)
        
        # Elétricos
        f_ev = ctk.CTkFrame(frota_frame, fg_color="transparent")
        f_ev.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(f_ev, text="Elétricos:", width=100, anchor="w").pack(side="left")
        self.num_ev = ctk.StringVar(value=str(cfg.get('frota.num_eletricos')))
        ctk.CTkEntry(f_ev, textvariable=self.num_ev, width=60).pack(side="right")

        # Combustão
        f_gas = ctk.CTkFrame(frota_frame, fg_color="transparent")
        f_gas.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(f_gas, text="Combustão:", width=100, anchor="w").pack(side="left")
        self.num_gas = ctk.StringVar(value=str(cfg.get('frota.num_combustao')))
        ctk.CTkEntry(f_gas, textvariable=self.num_gas, width=60).pack(side="right")

        # --- Simulação ---
        sim_frame = ctk.CTkFrame(main_frame)
        sim_frame.pack(fill="x", pady=15)
        ctk.CTkLabel(sim_frame, text="Parâmetros", font=("Roboto Medium", 14)).pack(pady=5)

        # Duração
        f_dur = ctk.CTkFrame(sim_frame, fg_color="transparent")
        f_dur.pack(fill="x", padx=10, pady=5)
        ctk.CTkLabel(f_dur, text="Duração (horas):", width=120, anchor="w").pack(side="left")
        self.duracao = ctk.StringVar(value=str(cfg.get('simulacao.duracao_horas')))
        ctk.CTkEntry(f_dur, textvariable=self.duracao, width=60).pack(side="right")
        
        # Probabilidade
        ctk.CTkLabel(sim_frame, text="Probabilidade Pedido/min:", anchor="w").pack(fill="x", padx=10, pady=(10, 0))
        self.prob = ctk.DoubleVar(value=cfg.get('simulacao.prob_pedido'))
        self.lbl_prob_val = ctk.CTkLabel(sim_frame, text=f"{self.prob.get():.2f}")
        self.lbl_prob_val.pack(anchor="e", padx=10)
        
        def update_prob_label(val):
            self.lbl_prob_val.configure(text=f"{float(val):.2f}")
            
        ctk.CTkSlider(sim_frame, from_=0.05, to=1.0, variable=self.prob, command=update_prob_label).pack(fill="x", padx=10, pady=5)
        
        # Cenários
        ctk.CTkLabel(sim_frame, text="Cenário de Pedidos:", anchor="w").pack(fill="x", padx=10, pady=(10, 0))
        
        cenarios_dict = cfg.get('pedidos_estaticos.cenarios', {})
        cenarios_nomes = list(cenarios_dict.keys()) if cenarios_dict else ["Cenario 1 (Base)"]
        opcoes = ["Aleatório"] + cenarios_nomes
        
        self.cenario_var = ctk.StringVar(value="Aleatório")
        self.combo_cenario = ctk.CTkComboBox(sim_frame, values=opcoes, variable=self.cenario_var)
        self.combo_cenario.pack(fill="x", padx=10, pady=5)

        # Horas de Ponta
        ctk.CTkLabel(sim_frame, text="Horas de Ponta (sep. vírgula):", anchor="w").pack(fill="x", padx=10)
        horas_ponta_default = ",".join(map(str, cfg.get('simulacao.horas_ponta')))
        self.h_ponta = ctk.StringVar(value=horas_ponta_default)
        ctk.CTkEntry(sim_frame, textvariable=self.h_ponta).pack(fill="x", padx=10, pady=(0, 10))

        # Botão Iniciar
        self.btn = ctk.CTkButton(main_frame, text="INICIAR SIMULAÇÃO", command=self.on_start, height=40, font=("Roboto Medium", 14))
        self.btn.pack(side="bottom", fill="x", pady=20)

    def on_start(self):
        """Valida os inputs e inicia a thread de simulação."""
        self.btn.configure(state="disabled", text="A Executar...")
        try:
            h_ponta = [int(h.strip()) for h in self.h_ponta.get().split(',') if h.strip()]
            num_ev = int(self.num_ev.get())
            num_gas = int(self.num_gas.get())
            duracao = int(self.duracao.get())
        except ValueError:
            messagebox.showerror("Erro", "Valores inválidos. Verifique os números.")
            self.reativar_botao()
            return

        config = {
            'estrategia': EstrategiaProcura[self.strat_var.get()],
            'num_eletricos': num_ev,
            'num_combustao': num_gas,
            'duracao_horas': duracao,
            'horas_ponta': h_ponta,
            'prob_pedido': self.prob.get(),
            'prob_pedido': self.prob.get(),
            'usar_estaticos': (self.cenario_var.get() != "Aleatório"),
            'lista_estaticos': cfg.get(f'pedidos_estaticos.cenarios.{self.cenario_var.get()}', []) if self.cenario_var.get() != "Aleatório" else []
        }
        threading.Thread(target=iniciar_simulacao, args=(config, self)).start()

    def reativar_botao(self):
        """Restaura o estado do botão de início."""
        self.btn.configure(state="normal", text="INICIAR SIMULAÇÃO")

if __name__ == "__main__":
    # Para teste isolado
    app = ctk.CTk()
    app.withdraw() # Esconder janela raiz dummy
    launcher = AppLauncher(app)
    launcher.protocol("WM_DELETE_WINDOW", app.quit)
    app.mainloop()