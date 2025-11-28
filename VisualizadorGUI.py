import tkinter as tk
import customtkinter as ctk
from Taxi import EstadoVeiculo, TipoMotorizacao

class MapaVisualizador(ctk.CTkFrame):
    """
    Componente GUI para visualização da simulação em tempo real.
    Estilo Cyberpunk/Neon com fundo escuro.
    """
    
    def __init__(self, master, grafo, largura=800, altura=600):
        super().__init__(master, fg_color="transparent")
        self.grafo = grafo
        self.largura = largura
        self.altura = altura
        self.margem = 50
        self.simulador = None 
        
        # Cores Neon
        self.COLORS = {
            'bg': '#1a1a1a',
            'node': '#00f2ff', # Cyan
            'node_charger': '#00ff00', # Green
            'edge_normal': '#444444',
            'edge_traffic': '#ff0055', # Neon Red
            'taxi_free': '#00ff00', # Green
            'taxi_busy': '#ff0055', # Red
            'taxi_charge': '#00f2ff', # Cyan
            'taxi_gas': '#bd00ff', # Purple
            'text': '#ffffff'
        }

        # Layout Principal (Grid)
        self.grid_columnconfigure(0, weight=1) # Mapa
        self.grid_columnconfigure(1, weight=0) # Painel (Fixo)
        self.grid_rowconfigure(0, weight=1)
        
        # 1. Área do Mapa
        self.canvas = tk.Canvas(self, bg=self.COLORS['bg'], highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # 2. Painel Lateral
        self.painel_info = ctk.CTkFrame(self, width=300, corner_radius=15)
        self.painel_info.grid(row=0, column=1, sticky="nsew", padx=(0, 10), pady=10)
        self.painel_info.grid_propagate(False)
        
        # Conteúdo do Painel
        self.setup_painel()
        
        # Limites do Mapa
        lats = [n['lat'] for n in grafo.nos.values()]
        lons = [n['lon'] for n in grafo.nos.values()]
        self.min_lat, self.max_lat = min(lats), max(lats)
        self.min_lon, self.max_lon = min(lons), max(lons)
        
        # Bind resize event
        self.canvas.bind("<Configure>", self.on_resize)
        
        self.desenhar_mapa_base()

    def setup_painel(self):
        # Relógio
        self.lbl_hora = ctk.CTkLabel(self.painel_info, text="00:00:00", font=("Consolas", 24, "bold"), text_color=self.COLORS['node'])
        self.lbl_hora.pack(pady=(20, 10))
        
        # Controlos
        f_ctrl = ctk.CTkFrame(self.painel_info, fg_color="transparent")
        f_ctrl.pack(fill="x", padx=15, pady=10)
        
        self.btn_pause = ctk.CTkButton(f_ctrl, text="PAUSA", fg_color="#ff9800", hover_color="#f57c00", 
                                       font=("Roboto", 12, "bold"), command=self.toggle_pause)
        self.btn_pause.pack(fill="x", pady=5)
        
        ctk.CTkLabel(f_ctrl, text="Velocidade Simulação", font=("Roboto", 12)).pack(pady=(10,0))
        self.scale_speed = ctk.CTkSlider(f_ctrl, from_=1, to=20, number_of_steps=19, command=self.mudar_velocidade)
        self.scale_speed.set(5)
        self.scale_speed.pack(fill="x", pady=5)

        # Legenda Estilizada
        self.criar_legenda()

        # Estado da Frota (Scrollable)
        ctk.CTkLabel(self.painel_info, text="Estado da Frota", font=("Roboto", 14, "bold")).pack(pady=(10, 5))
        self.scroll_frota = ctk.CTkScrollableFrame(self.painel_info, fg_color="transparent")
        self.scroll_frota.pack(fill="both", expand=True, padx=5, pady=5)
        self.items_frota = {}

    def criar_legenda(self):
        f_legenda = ctk.CTkFrame(self.painel_info, fg_color="#2b2b2b", corner_radius=10)
        f_legenda.pack(fill="x", padx=15, pady=15)
        
        ctk.CTkLabel(f_legenda, text="Legenda", font=("Roboto", 12, "bold")).pack(pady=5)
        
        items = [
            (self.COLORS['taxi_free'], "Livre"),
            (self.COLORS['taxi_busy'], "Ocupado"),
            (self.COLORS['taxi_charge'], "A Carregar"),
            (self.COLORS['taxi_gas'], "A Abastecer"),
            (self.COLORS['edge_traffic'], "Trânsito Intenso")
        ]
        
        for color, text in items:
            row = ctk.CTkFrame(f_legenda, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=2)
            
            # Dot
            canvas_dot = tk.Canvas(row, width=12, height=12, bg="#2b2b2b", highlightthickness=0)
            canvas_dot.pack(side="left")
            canvas_dot.create_oval(2, 2, 10, 10, fill=color, outline="")
            
            ctk.CTkLabel(row, text=text, font=("Roboto", 11)).pack(side="left", padx=5)

    def on_resize(self, event):
        self.largura = event.width
        self.altura = event.height
        self.desenhar_mapa_base()

    def set_simulador(self, sim):
        self.simulador = sim

    def toggle_pause(self):
        if self.simulador:
            is_paused = self.simulador.toggle_pause()
            if is_paused: 
                self.btn_pause.configure(text="CONTINUAR", fg_color="#4caf50", hover_color="#388e3c")
            else: 
                self.btn_pause.configure(text="PAUSA", fg_color="#ff9800", hover_color="#f57c00")

    def mudar_velocidade(self, val):
        if self.simulador: self.simulador.set_delay(1.0 / int(val))

    def coords_para_pixel(self, lat, lon):
        if self.max_lat == self.min_lat: y_norm = 0.5
        else: y_norm = (lat - self.min_lat) / (self.max_lat - self.min_lat)
        if self.max_lon == self.min_lon: x_norm = 0.5
        else: x_norm = (lon - self.min_lon) / (self.max_lon - self.min_lon)
        
        x = self.margem + x_norm * (self.largura - 2 * self.margem)
        y = self.altura - (self.margem + y_norm * (self.altura - 2 * self.margem))
        return x, y

    def get_cor_transito(self, multiplicador):
        if multiplicador <= 1.0: return self.COLORS['edge_normal']
        # Gradiente de Cinza para Neon Red
        ratio = min(1.0, (multiplicador - 1.0) / 0.75)
        # Simples: se tiver trânsito, fica vermelho neon
        return self.COLORS['edge_traffic'] if ratio > 0.3 else self.COLORS['edge_normal']

    def desenhar_mapa_base(self):
        self.canvas.delete("base")
        for origem, destinos in self.grafo.arestas.items():
            x1, y1 = self.coords_para_pixel(self.grafo.nos[origem]['lat'], self.grafo.nos[origem]['lon'])
            for destino, dados in destinos.items():
                x2, y2 = self.coords_para_pixel(self.grafo.nos[destino]['lat'], self.grafo.nos[destino]['lon'])
                
                multiplicador = self.grafo.condicoes_transito.get((origem, destino), 1.0)
                cor = self.get_cor_transito(multiplicador)
                largura = 1 if cor == self.COLORS['edge_normal'] else 2
                
                self.canvas.create_line(x1, y1, x2, y2, fill=cor, width=largura, capstyle=tk.ROUND, tags="base")

        for id_no, info in self.grafo.nos.items():
            x, y = self.coords_para_pixel(info['lat'], info['lon'])
            cor = self.COLORS['node_charger'] if info.get('pode_carregar') else self.COLORS['node']
            r = 3 if info.get('pode_carregar') else 2
            self.canvas.create_oval(x-r, y-r, x+r, y+r, fill=cor, outline="", tags="base")

    def atualizar_estado(self, frota, pedidos_ativos, tempo_atual, descricoes_status):
        self.canvas.delete("dinamico")
        self.lbl_hora.configure(text=tempo_atual.strftime("%H:%M:%S"))

        # 1. Painel Lateral (Frota)
        for t_id, taxi in frota.items():
            status_text = descricoes_status.get(t_id, "Desconhecido")
            pct = taxi.autonomia_atual / taxi.autonomia_maxima
            pct = max(0.0, min(1.0, pct))
            
            color_bar = self.COLORS['node_charger'] if pct > 0.5 else (self.COLORS['taxi_busy'] if pct < 0.2 else "#ff9800")

            if t_id not in self.items_frota:
                frame = ctk.CTkFrame(self.scroll_frota, fg_color="#2b2b2b")
                frame.pack(fill="x", pady=2)
                
                f_head = ctk.CTkFrame(frame, fg_color="transparent")
                f_head.pack(fill="x", padx=5, pady=(2,0))
                ctk.CTkLabel(f_head, text=f"{t_id}", font=("Roboto", 11, "bold")).pack(side="left")
                lbl_pct = ctk.CTkLabel(f_head, text="100%", font=("Roboto", 10), text_color="gray")
                lbl_pct.pack(side="right")
                
                # Progress Bar customizada (Canvas)
                canvas_bar = tk.Canvas(frame, height=4, bg="#444", highlightthickness=0)
                canvas_bar.pack(fill="x", padx=5, pady=2)
                bar_id = canvas_bar.create_rectangle(0, 0, 0, 4, fill=color_bar, width=0)
                
                lbl_desc = ctk.CTkLabel(frame, text=status_text, font=("Roboto", 10), anchor="w", text_color="gray")
                lbl_desc.pack(fill="x", padx=5, pady=(0,2))
                
                self.items_frota[t_id] = {"lbl_desc": lbl_desc, "lbl_pct": lbl_pct, "canvas_bar": canvas_bar, "bar_id": bar_id}
            
            item = self.items_frota[t_id]
            item["lbl_desc"].configure(text=status_text)
            item["lbl_pct"].configure(text=f"{int(pct*100)}%")
            
            # Update bar
            w_canvas = item["canvas_bar"].winfo_width()
            if w_canvas < 10: w_canvas = 200 # Default fallback
            item["canvas_bar"].coords(item["bar_id"], 0, 0, w_canvas * pct, 4)
            item["canvas_bar"].itemconfig(item["bar_id"], fill=color_bar)

        # 2. Mapa: Pedidos
        for p in pedidos_ativos:
            ox, oy = self.coords_para_pixel(self.grafo.nos[p.origem]['lat'], self.grafo.nos[p.origem]['lon'])
            dx, dy = self.coords_para_pixel(self.grafo.nos[p.destino]['lat'], self.grafo.nos[p.destino]['lon'])
            
            # Linha tracejada
            self.canvas.create_line(ox, oy, dx, dy, fill=p.cor_mapa, dash=(2, 4), width=1, tags="dinamico")
            # Marcadores
            self.canvas.create_oval(ox-4, oy-4, ox+4, oy+4, outline=p.cor_mapa, width=2, tags="dinamico")
            self.canvas.create_rectangle(dx-4, dy-4, dx+4, dy+4, fill=p.cor_mapa, outline="", tags="dinamico")

        # 3. Mapa: Táxis
        for taxi in frota.values():
            tx, ty = self.coords_para_pixel(self.grafo.nos[taxi.localizacao_atual]['lat'], self.grafo.nos[taxi.localizacao_atual]['lon'])
            
            if taxi.estado == EstadoVeiculo.LIVRE: cor = self.COLORS['taxi_free']
            elif taxi.estado == EstadoVeiculo.A_CARREGAR: cor = self.COLORS['taxi_charge']
            elif taxi.estado == EstadoVeiculo.A_ABASTECER: cor = self.COLORS['taxi_gas']
            else: cor = self.COLORS['taxi_busy']
            
            r = 6
            # Efeito de brilho (glow) simples
            self.canvas.create_oval(tx-r-2, ty-r-2, tx+r+2, ty+r+2, fill=cor, stipple="gray50", outline="", tags="dinamico") 
            
            if taxi.tipo == TipoMotorizacao.COMBUSTAO:
                self.canvas.create_rectangle(tx-r, ty-r, tx+r, ty+r, fill=cor, outline="white", width=1, tags="dinamico")
            else:
                self.canvas.create_oval(tx-r, ty-r, tx+r, ty+r, fill=cor, outline="white", width=1, tags="dinamico")
                
            self.canvas.create_text(tx, ty-10, text=taxi.id_veiculo, font=("Arial", 8, "bold"), fill="white", tags="dinamico")

        self.update()