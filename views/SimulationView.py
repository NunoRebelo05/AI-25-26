import customtkinter as ctk
from tkinter import messagebox
import threading
from datetime import datetime
import traceback
from PIL import Image
import os

from Grafo import Grafo
from Taxi import Taxi, TipoMotorizacao
from Gestor import GestorDeFrota, EstrategiaProcura
from Simulador import Simulador
from VisualizadorGUI import MapaVisualizador
from Config import cfg

class CounterCard(ctk.CTkFrame):
    def __init__(self, master, title, icon_path=None, initial_value=0, min_val=0, max_val=100, step=1, **kwargs):
        super().__init__(master, corner_radius=20, fg_color=("#e0e0e0", "#2b2b2b"), **kwargs)
        self.value = ctk.IntVar(value=initial_value)
        self.min_val = min_val
        self.max_val = max_val
        self.step = step
        
        # Main container for vertical centering
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(expand=True, fill="both", pady=10)
        
        # Title
        ctk.CTkLabel(container, text=title, font=("Roboto", 14), text_color="gray").pack(pady=(0, 5))
        
        # Icon
        if icon_path and os.path.exists(icon_path):
            try:
                img = ctk.CTkImage(light_image=Image.open(icon_path), dark_image=Image.open(icon_path), size=(50, 50))
                ctk.CTkLabel(container, text="", image=img).pack(pady=5)
            except Exception as e:
                print(f"Error loading icon {icon_path}: {e}")
        
        # Controls
        ctrl_frame = ctk.CTkFrame(container, fg_color="transparent")
        ctrl_frame.pack(pady=5)
        
        ctk.CTkButton(ctrl_frame, text="−", width=35, height=35, font=("Roboto", 20), fg_color="transparent", 
                      hover_color=("#d0d0d0", "#3a3a3a"), text_color=("black", "white"), command=self.decrement).pack(side="left", padx=2)
        
        ctk.CTkLabel(ctrl_frame, textvariable=self.value, font=("Roboto", 28, "bold")).pack(side="left", padx=8)
        
        ctk.CTkButton(ctrl_frame, text="+", width=35, height=35, font=("Roboto", 20), fg_color="transparent", 
                      hover_color=("#d0d0d0", "#3a3a3a"), text_color=("black", "white"), command=self.increment).pack(side="left", padx=2)

    def increment(self):
        if self.value.get() < self.max_val:
            self.value.set(self.value.get() + self.step)

    def decrement(self):
        if self.value.get() > self.min_val:
            self.value.set(self.value.get() - self.step)
            
    def get(self):
        return self.value.get()

class SelectorCard(ctk.CTkFrame):
    def __init__(self, master, title, options, icon_path=None, **kwargs):
        super().__init__(master, corner_radius=20, fg_color=("#e0e0e0", "#2b2b2b"), **kwargs)
        self.options = options
        self.current_idx = 0
        self.value = ctk.StringVar(value=options[0])
        
        # Main container for vertical centering
        container = ctk.CTkFrame(self, fg_color="transparent")
        container.pack(expand=True, fill="both", pady=10)
        
        ctk.CTkLabel(container, text=title, font=("Roboto", 14), text_color="gray").pack(pady=(0, 5))
        
        # Icon
        if icon_path and os.path.exists(icon_path):
            try:
                img = ctk.CTkImage(light_image=Image.open(icon_path), dark_image=Image.open(icon_path), size=(50, 50))
                ctk.CTkLabel(container, text="", image=img).pack(pady=5)
            except Exception as e:
                print(f"Error loading icon {icon_path}: {e}")
        
        ctrl_frame = ctk.CTkFrame(container, fg_color="transparent")
        ctrl_frame.pack(pady=5)
        
        ctk.CTkButton(ctrl_frame, text="<", width=35, height=35, font=("Roboto", 18, "bold"), fg_color="transparent", 
                      hover_color=("#d0d0d0", "#3a3a3a"), text_color=("black", "white"), command=self.prev).pack(side="left", padx=5)
        
        self.lbl_val = ctk.CTkLabel(ctrl_frame, textvariable=self.value, font=("Roboto", 18, "bold"), width=120)
        self.lbl_val.pack(side="left", padx=5)
        
        ctk.CTkButton(ctrl_frame, text=">", width=35, height=35, font=("Roboto", 18, "bold"), fg_color="transparent", 
                      hover_color=("#d0d0d0", "#3a3a3a"), text_color=("black", "white"), command=self.next).pack(side="left", padx=5)

    def next(self):
        self.current_idx = (self.current_idx + 1) % len(self.options)
        self.value.set(self.options[self.current_idx])

    def prev(self):
        self.current_idx = (self.current_idx - 1) % len(self.options)
        self.value.set(self.options[self.current_idx])
        
    def get(self):
        return self.value.get()

class SimulationView(ctk.CTkFrame):
    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        
        # Load config
        cfg.carregar()
        
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(0, weight=1)
        
        # --- Config Frame ---
        self.config_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.config_frame.grid(row=0, column=0, sticky="nsew", padx=20, pady=20)
        
        self.setup_config_ui()
        
        # --- Simulation Frame (Map) ---
        self.sim_frame = ctk.CTkFrame(self, fg_color="transparent")
        self.simulador = None
        self.gui_mapa = None

    def setup_config_ui(self):
        # Header
        header = ctk.CTkFrame(self.config_frame, fg_color="transparent")
        header.pack(fill="x", pady=(0, 15))
        ctk.CTkLabel(header, text="Preparar Simulação", font=("Roboto", 28, "bold"), text_color=("gray30", "gray80")).pack(side="left")
        
        # Main Grid (3x2)
        grid = ctk.CTkFrame(self.config_frame, fg_color="transparent")
        grid.pack(fill="both", expand=True)
        for i in range(3): grid.grid_columnconfigure(i, weight=1)
        for i in range(2): grid.grid_rowconfigure(i, weight=1)
        
        # --- Row 0 ---
        # Electric Taxis
        self.card_ev = CounterCard(grid, "Taxis Elétricos", "assets/electric-taxi.png", 
                                   initial_value=cfg.get('frota.num_eletricos'), min_val=0)
        self.card_ev.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        
        # Combustion Taxis
        self.card_gas = CounterCard(grid, "Taxis Combustão", "assets/taxi.png", 
                                    initial_value=cfg.get('frota.num_combustao'), min_val=0)
        self.card_gas.grid(row=0, column=1, sticky="nsew", padx=8, pady=8)
        
        # Duration
        self.card_dur = CounterCard(grid, "Duração (h)", "assets/clock.png", 
                                    initial_value=cfg.get('simulacao.duracao_horas'), min_val=1, max_val=24)
        self.card_dur.grid(row=0, column=2, sticky="nsew", padx=8, pady=8)
        
        # --- Row 1 ---
        # Rush Hours
        rush_card = ctk.CTkFrame(grid, corner_radius=20, fg_color=("#e0e0e0", "#2b2b2b"))
        rush_card.grid(row=1, column=0, sticky="nsew", padx=8, pady=8)
        
        # Container for centering
        rush_container = ctk.CTkFrame(rush_card, fg_color="transparent")
        rush_container.pack(expand=True, fill="both", pady=10)
        
        ctk.CTkLabel(rush_container, text="Horas de Trânsito", font=("Roboto", 14), text_color="gray").pack(pady=(0, 5))
        
        hours_frame = ctk.CTkFrame(rush_container, fg_color="transparent")
        hours_frame.pack(expand=True)
        
        self.hour_vars = []
        default_hours = cfg.get('simulacao.horas_ponta')
        
        # 4x6 Grid for 24h
        for h in range(24):
            row = h // 6
            col = h % 6
            var = ctk.BooleanVar(value=(h in default_hours))
            self.hour_vars.append(var)
            btn = ctk.CTkCheckBox(hours_frame, text=f"{h}", variable=var, width=35, height=35, corner_radius=17,
                                  font=("Roboto", 9), fg_color="#ff0055")
            btn.grid(row=row, column=col, padx=2, pady=2)

        # Requests
        req_card = ctk.CTkFrame(grid, corner_radius=20, fg_color=("#e0e0e0", "#2b2b2b"))
        req_card.grid(row=1, column=1, sticky="nsew", padx=8, pady=8)
        
        # Container for centering
        req_container = ctk.CTkFrame(req_card, fg_color="transparent")
        req_container.pack(expand=True, fill="both", pady=10)
        
        ctk.CTkLabel(req_container, text="Quantidade de Pedidos", font=("Roboto", 14), text_color="gray").pack(pady=(0, 5))
        
        # Icon for Requests
        req_icon_path = "assets/request.png"
        if os.path.exists(req_icon_path):
             try:
                img = ctk.CTkImage(light_image=Image.open(req_icon_path), dark_image=Image.open(req_icon_path), size=(50, 50))
                ctk.CTkLabel(req_container, text="", image=img).pack(pady=5)
             except: pass

        self.prob = ctk.DoubleVar(value=cfg.get('simulacao.prob_pedido'))
        slider_frame = ctk.CTkFrame(req_container, fg_color="transparent")
        slider_frame.pack(fill="x", padx=15, pady=5)
        
        ctk.CTkLabel(slider_frame, text="−", font=("Roboto", 18)).pack(side="left")
        ctk.CTkSlider(slider_frame, from_=0.05, to=1.0, variable=self.prob).pack(side="left", fill="x", expand=True, padx=5)
        ctk.CTkLabel(slider_frame, text="+", font=("Roboto", 18)).pack(side="left")
        
        ctk.CTkLabel(req_container, textvariable=self.prob, font=("Roboto", 12)).pack()
        
        self.usar_estaticos = ctk.BooleanVar(value=cfg.get('pedidos_estaticos.usar_estaticos'))
        ctk.CTkSwitch(req_container, text="Pedidos Pré-Calculados", variable=self.usar_estaticos).pack(pady=10)

        # Algorithm Selector
        self.card_algo = SelectorCard(grid, "Algoritmo de Procura", [e.name for e in EstrategiaProcura], icon_path="assets/algorithm.png")
        self.card_algo.grid(row=1, column=2, sticky="nsew", padx=8, pady=8)
        
        # Start Button
        self.btn_start = ctk.CTkButton(self.config_frame, text="INICIAR SIMULAÇÃO", command=self.start_simulation, 
                                       height=45, corner_radius=22, font=("Roboto", 15, "bold"), 
                                       fg_color="#4caf50", hover_color="#388e3c")
        self.btn_start.pack(fill="x", padx=150, pady=20)

        # Loading Screen
        self.loading_frame = ctk.CTkFrame(self, fg_color="#1a1a1a")
        ctk.CTkLabel(self.loading_frame, text="A carregar mapa...", font=("Roboto", 24, "bold")).pack(expand=True)
        
    def start_simulation(self):
        try:
            self.h_ponta = [i for i, var in enumerate(self.hour_vars) if var.get()]
            self.num_ev = self.card_ev.get()
            self.num_gas = self.card_gas.get()
            self.duracao = self.card_dur.get()
            self.algo_name = self.card_algo.get()
        except ValueError:
            messagebox.showerror("Erro", "Valores inválidos.")
            return

        # Show Loading
        self.config_frame.grid_forget()
        self.loading_frame.grid(row=0, column=0, sticky="nsew")
        self.update() # Force update to show loading screen immediately
        
        # Schedule actual start to allow UI to update
        self.after(100, self._start_simulation_impl)

    def _start_simulation_impl(self):
        config = {
            'estrategia': EstrategiaProcura[self.algo_name],
            'num_eletricos': self.num_ev,
            'num_combustao': self.num_gas,
            'duracao_horas': self.duracao,
            'horas_ponta': self.h_ponta,
            'prob_pedido': self.prob.get(),
            'usar_estaticos': self.usar_estaticos.get()
        }
        
        # 1. Prepare Sim Frame BUT keep Loading Screen on top
        self.sim_frame.grid(row=0, column=0, sticky="nsew")
        self.loading_frame.lift() # Ensure loading is on top
        
        # Clear previous simulation if any
        for widget in self.sim_frame.winfo_children():
            widget.destroy()
            
        # Add Back Button
        btn_back = ctk.CTkButton(self.sim_frame, text="← Voltar / Parar", command=self.stop_simulation, 
                                 fg_color="#f44336", hover_color="#d32f2f", width=120)
        btn_back.pack(side="top", anchor="w", padx=10, pady=10)
        
        # Embed Map
        mapa = Grafo.carregar_de_json("braga_mapa.json")
        self.gui_mapa = MapaVisualizador(self.sim_frame, mapa, largura=800, altura=600)
        self.gui_mapa.pack(fill="both", expand=True)
        
        # 2. Force layout update so map calculates scale and renders
        self.update()
        
        # 3. NOW remove loading screen
        self.loading_frame.grid_forget()
        
        # Start Thread
        threading.Thread(target=self.run_sim_thread, args=(config, mapa)).start()

    def run_sim_thread(self, config, mapa):
        try:
            gestor = GestorDeFrota(mapa)
            gestor.definir_estrategia(config['estrategia'])
            
            locais = list(mapa.nos.keys())
            specs_electric = cfg.get('frota.specs_eletrico')
            specs_combustion = cfg.get('frota.specs_combustao')

            for i in range(config['num_eletricos']):
                local_inicio = locais[i % len(locais)]
                novo_taxi = Taxi(f"EV{i+1:02d}", TipoMotorizacao.ELETRICO, local_inicio, 
                                 specs_electric['capacidade'], specs_electric['custo_km'], specs_electric['autonomia'])
                gestor.add_taxi(novo_taxi)
                
            for i in range(config['num_combustao']):
                local_inicio = locais[(i + 3) % len(locais)]
                novo_taxi = Taxi(f"GAS{i+1:02d}", TipoMotorizacao.COMBUSTAO, local_inicio, 
                                 specs_combustion['capacidade'], specs_combustion['custo_km'], specs_combustion['autonomia'])
                gestor.add_taxi(novo_taxi)

            self.simulador = Simulador(
                gestor=gestor,
                hora_inicio=datetime(2025, 10, 20, 8, 0, 0),
                duracao_sim_horas=config['duracao_horas'],
                horas_ponta=config['horas_ponta'],
                prob_pedido=config['prob_pedido'],
                gui_interface=self.gui_mapa,
                usar_estaticos=config['usar_estaticos']
            )
            
            self.gui_mapa.set_simulador(self.simulador)
            self.simulador.run()
            
        except Exception as e:
            print(f"Erro na simulação: {e}")
            traceback.print_exc()

    def stop_simulation(self):
        if self.simulador:
            self.simulador.stop()
        
        self.sim_frame.grid_forget()
        self.config_frame.grid(row=0, column=0, sticky="nsew")
