import tkinter as tk
import customtkinter as ctk
from PIL import Image, ImageTk
import math
import os
from Taxi import EstadoVeiculo, TipoMotorizacao

class MapaVisualizador(ctk.CTkFrame):
    """
    Componente GUI para visualização da simulação em tempo real.
    Estilo Uber-like com estradas largas e ícones de carros rotativos.
    """
    
    def __init__(self, master, grafo, layers=None, largura=800, altura=600):
        super().__init__(master, fg_color="transparent")
        self.grafo = grafo
        self.layers = layers
        self.largura = largura
        self.altura = altura
        self.margem = 50
        self.simulador = None 
        
        # Cores e Estilo
        self.COLORS = {
            'bg': '#1a1a1a',      # Fundo escuro
            'road': '#333333',    # Estradas cinza escuro
            'road_traffic': '#552222', # Trânsito (avermelhado subtil)
            'node': '#444444',    # Nós discretos
            'text': '#ffffff'
        }

        # Layout Principal
        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=0)
        self.grid_rowconfigure(0, weight=1)
        
        # 1. Área do Mapa
        self.canvas = tk.Canvas(self, bg=self.COLORS['bg'], highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        
        # 2. Painel Lateral (Overlay ou Fixo? Vamos manter fixo por enquanto para consistência)
        self.painel_info = ctk.CTkFrame(self, width=280, corner_radius=0, fg_color="#2b2b2b")
        self.painel_info.grid(row=0, column=1, sticky="nsew")
        self.painel_info.grid_propagate(False)
        
        self.setup_painel()
        
        # Limites do Mapa
        lats = [n['lat'] for n in grafo.nos.values()]
        lons = [n['lon'] for n in grafo.nos.values()]
        self.min_lat, self.max_lat = min(lats), max(lats)
        self.min_lon, self.max_lon = min(lons), max(lons)
        
        # Carregar Assets
        self.car_images = {}
        self.load_assets()
        
        # Cache de imagens rotacionadas para performance
        # Chave: (tipo_taxi, estado, angulo_inteiro) -> ImageTk
        self.rotated_cache = {}

        # Inicializar variáveis de escala
        self.scale = 1.0
        self.offset_x = 0
        self.offset_y = 0
        self.lon_correction = 1.0
        self.recalc_scale()

        # Bind resize event
        self.canvas.bind("<Configure>", self.on_resize)
        
        # Bind Zoom and Pan events
        self.canvas.bind("<MouseWheel>", self.do_zoom)
        self.canvas.bind("<ButtonPress-1>", self.start_pan)
        self.canvas.bind("<B1-Motion>", self.do_pan)
        
        # Zoom and Pan state
        self.zoom_level = 1.0
        self.pan_x = 0
        self.pan_y = 0
        self.drag_start_x = 0
        self.drag_start_y = 0
        
        self.desenhar_mapa_base()

    def load_assets(self):
        """Carrega as imagens dos táxis."""
        asset_dir = os.path.join(os.path.dirname(__file__), "assets")
        
        # Mapeamento: (Tipo, Estado) -> Filename
        # EstadoVeiculo: LIVRE (Verde), OCUPADO/BUSY (Branco), CARREGAR/ABASTECER (Azul)
        # Nota: Usaremos 'BUSY' para qualquer estado ocupado que não seja carregar
        
        files = {
            (TipoMotorizacao.COMBUSTAO, 'FREE'): "Taxi_Verde.png",
            (TipoMotorizacao.COMBUSTAO, 'BUSY'): "Taxi_Branco.png",
            (TipoMotorizacao.COMBUSTAO, 'CHARGE'): "Taxi_azul.png",
            
            (TipoMotorizacao.ELETRICO, 'FREE'): "Taxi_Eletrico_Verde.png",
            (TipoMotorizacao.ELETRICO, 'BUSY'): "Taxi_Eletrico_Branco.png",
            (TipoMotorizacao.ELETRICO, 'CHARGE'): "Taxi_Eletrico_azul.png",
        }
        
        for key, filename in files.items():
            path = os.path.join(asset_dir, filename)
            if os.path.exists(path):
                try:
                    # Carregar e redimensionar para um tamanho razoável (ex: 32x32 ou 40x40)
                    # O user pediu proporção certa, então vamos fixar largura e manter aspect ratio se possível
                    # Mas para rotação é melhor ser quadrado ou gerido com cuidado.
                    # Vamos tentar 40px de largura.
                    img = Image.open(path)
                    w, h = img.size
                    ratio = h / w
                    new_w = 40
                    new_h = int(new_w * ratio)
                    img = img.resize((new_w, new_h), Image.Resampling.LANCZOS)
                    self.car_images[key] = img
                except Exception as e:
                    print(f"Erro ao carregar {filename}: {e}")
            else:
                print(f"Aviso: Imagem não encontrada: {path}")

    def setup_painel(self):
        # Relógio Digital
        self.lbl_hora = ctk.CTkLabel(self.painel_info, text="00:00", font=("Roboto", 40, "bold"), text_color="white")
        self.lbl_hora.pack(pady=(30, 10))
        
        # Controlos
        f_ctrl = ctk.CTkFrame(self.painel_info, fg_color="transparent")
        f_ctrl.pack(fill="x", padx=20, pady=10)
        
        self.btn_pause = ctk.CTkButton(f_ctrl, text="PAUSA", fg_color="#ff9800", hover_color="#f57c00", 
                                       font=("Roboto", 12, "bold"), command=self.toggle_pause)
        self.btn_pause.pack(fill="x", pady=5)
        
        ctk.CTkLabel(f_ctrl, text="Velocidade", font=("Roboto", 12)).pack(pady=(10,0))
        self.scale_speed = ctk.CTkSlider(f_ctrl, from_=1, to=20, number_of_steps=19, command=self.mudar_velocidade)
        self.scale_speed.set(1)
        self.scale_speed.pack(fill="x", pady=5)

        # Legenda Simples (Cores)
        self.criar_legenda()

        # Estado da Frota (Scrollable)
        ctk.CTkLabel(self.painel_info, text="Frota em Tempo Real", font=("Roboto", 14, "bold")).pack(pady=(20, 5))
        self.scroll_frota = ctk.CTkScrollableFrame(self.painel_info, fg_color="transparent")
        self.scroll_frota.pack(fill="both", expand=True, padx=5, pady=5)
        self.items_frota = {}

    def criar_legenda(self):
        f_legenda = ctk.CTkFrame(self.painel_info, fg_color="#333333", corner_radius=10)
        f_legenda.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(f_legenda, text="Legenda", font=("Roboto", 12, "bold")).pack(pady=5)
        
        # Apenas cores como pedido: Verde (Livre), Branco (Ocupado), Azul (Carregar)
        items = [
            ("#4caf50", "Livre"),      # Verde
            ("#ffffff", "Ocupado"),    # Branco
            ("#2196f3", "Carregar")    # Azul
        ]
        
        for color, text in items:
            row = ctk.CTkFrame(f_legenda, fg_color="transparent")
            row.pack(fill="x", padx=10, pady=2)
            
            canvas_dot = tk.Canvas(row, width=12, height=12, bg="#333333", highlightthickness=0)
            canvas_dot.pack(side="left")
            canvas_dot.create_oval(2, 2, 10, 10, fill=color, outline="")
            
            ctk.CTkLabel(row, text=text, font=("Roboto", 11), text_color="white").pack(side="left", padx=5)

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
        if self.simulador: self.simulador.set_speed(int(val))

    def on_resize(self, event):
        self.largura = event.width
        self.altura = event.height
        self.recalc_scale()
        self.desenhar_mapa_base()

    def start_pan(self, event):
        self.drag_start_x = event.x
        self.drag_start_y = event.y

    def do_pan(self, event):
        """
        Executa a translação do viewport (Pan).
        
        Utiliza a primitiva 'move' do Canvas para otimização de desempenho,
        evitando o redesenho completo da geometria durante a interação (Fast Panning).
        """
        dx = event.x - self.drag_start_x
        dy = event.y - self.drag_start_y
        
        # Otimização: Translação direta de objetos gráficos
        self.canvas.move("all", dx, dy)
        
        self.pan_x += dx
        self.pan_y += dy
        self.drag_start_x = event.x
        self.drag_start_y = event.y
        # Redesenho completo adiado para o fim da interação

    def do_zoom(self, event):
        # Windows: event.delta is usually 120 or -120
        # Linux: Button-4 / Button-5 (handled differently, but MouseWheel might work)
        factor = 1.1 if event.delta > 0 else 0.9
        
        mouse_x = event.x
        mouse_y = event.y
        
        # Adjust pan to keep mouse point stable
        self.pan_x = mouse_x - (mouse_x - self.pan_x) * factor
        self.pan_y = mouse_y - (mouse_y - self.pan_y) * factor
        self.zoom_level *= factor
        
        self.desenhar_mapa_base()

    def recalc_scale(self):
        """Calcula escala e offsets para manter o aspect ratio."""
        if not self.grafo.nos: return

        # Margem em pixels
        m = self.margem

        # Dimensões do Canvas úteis
        w_canvas = self.largura - 2 * m
        h_canvas = self.altura - 2 * m
        
        if w_canvas <= 0 or h_canvas <= 0: return

        # Dimensões do Grafo (Geográficas)
        d_lat = self.max_lat - self.min_lat
        d_lon = self.max_lon - self.min_lon
        
        if d_lat == 0: d_lat = 0.0001
        if d_lon == 0: d_lon = 0.0001

        # Fator de correção de longitude (aproximação para a latitude média)
        mean_lat_rad = math.radians((self.min_lat + self.max_lat) / 2)
        lon_correction = math.cos(mean_lat_rad)
        
        # Aspect Ratio do Grafo (Height / Width)
        # Nota: Latitude é Y, Longitude é X.
        # Distância Y ~ d_lat
        # Distância X ~ d_lon * cos(lat)
        graph_aspect = d_lat / (d_lon * lon_correction)

        # Aspect Ratio do Canvas
        canvas_aspect = h_canvas / w_canvas

        # Determinar Escala (Pixels por Grau de Latitude)
        if graph_aspect > canvas_aspect:
            # Grafo é mais alto que o canvas (limitado pela altura)
            self.scale = h_canvas / d_lat
        else:
            # Grafo é mais largo que o canvas (limitado pela largura)
            # scale = pixels_y / degrees_y
            # Queremos que (d_lon * lon_correction) * scale = w_canvas
            # scale = w_canvas / (d_lon * lon_correction)
            # Mas a nossa scale base é em Y (latitude).
            # Se usarmos a mesma scale para X e Y (após correção), garantimos proporção.
            self.scale = w_canvas / (d_lon * lon_correction)

        # Calcular Offsets para centrar
        # Tamanho final do grafo em pixels
        graph_h_px = d_lat * self.scale
        graph_w_px = d_lon * lon_correction * self.scale
        
        self.offset_x = m + (w_canvas - graph_w_px) / 2
        self.offset_y = m + (h_canvas - graph_h_px) / 2
        
        self.lon_correction = lon_correction

    def coords_para_pixel(self, lat, lon):
        # Y cresce para baixo no ecrã, mas Latitude cresce para cima.
        # Pixel Y = OffsetY + (MaxLat - Lat) * Scale
        # Pixel X = OffsetX + (Lon - MinLon) * LonCorrection * Scale
        
        # Base coords (fitted to screen)
        y_base = self.offset_y + (self.max_lat - lat) * self.scale
        x_base = self.offset_x + (lon - self.min_lon) * self.lon_correction * self.scale
        
        # Apply Zoom and Pan
        x_final = x_base * self.zoom_level + self.pan_x
        y_final = y_base * self.zoom_level + self.pan_y
        
        return x_final, y_final

    def get_cor_transito(self, multiplicador):
        if multiplicador <= 1.0: return self.COLORS['road']
        return self.COLORS['road_traffic']

        return self.COLORS['road_traffic']

    def desenhar_camadas_fundo(self):
        """Desenha as camadas de polígonos (água, parques, edifícios)."""
        # Ordem de desenho: Água -> Parques -> Edifícios
        
        # Cores
        C_WATER = "#1a2639" # Azul muito escuro/subtil
        C_PARK = "#1e2b1e"  # Verde muito escuro
        C_BUILD = "#262626" # Cinza ligeiramente mais claro que o fundo
        
        # Helper para desenhar geometria
        def draw_geom(gdf, color):
            if gdf is None or gdf.empty: return
            for geom in gdf.geometry:
                if geom.geom_type == 'Polygon':
                    coords = list(geom.exterior.coords)
                    pixels = [self.coords_para_pixel(lat, lon) for lon, lat in coords] # Note: OSM uses (lon, lat)
                    # Flatten list for create_polygon
                    flat_pixels = [val for sublist in pixels for val in sublist]
                    if len(flat_pixels) >= 6: # Pelo menos 3 pontos
                        self.canvas.create_polygon(flat_pixels, fill=color, outline="", tags="base")
                elif geom.geom_type == 'MultiPolygon':
                    for poly in geom.geoms:
                        coords = list(poly.exterior.coords)
                        pixels = [self.coords_para_pixel(lat, lon) for lon, lat in coords]
                        flat_pixels = [val for sublist in pixels for val in sublist]
                        
                        # Culling for Polygons
                        xs = flat_pixels[0::2]
                        ys = flat_pixels[1::2]
                        w_curr = self.canvas.winfo_width()
                        h_curr = self.canvas.winfo_height()
                        if (max(xs) < -100 or min(xs) > w_curr + 100 or
                            max(ys) < -100 or min(ys) > h_curr + 100):
                            continue

                        if len(flat_pixels) >= 6:
                            self.canvas.create_polygon(flat_pixels, fill=color, outline="", tags="base")

        # Desenhar
        if 'water' in self.layers: draw_geom(self.layers['water'], C_WATER)
        if 'parks' in self.layers: draw_geom(self.layers['parks'], C_PARK)
        if 'buildings' in self.layers: draw_geom(self.layers['buildings'], C_BUILD)

    def desenhar_mapa_base(self):
        """
        Agenda o desenho do mapa base para a thread principal.
        Evita conflitos de threads entre o Simulador e a GUI.
        """
        self.after(0, self._desenhar_mapa_base_impl)

    def _desenhar_mapa_base_impl(self):
        if not self.winfo_exists(): return
        self.canvas.delete("base")
        
        # 0. Desenhar Camadas de Fundo (Se existirem)
        if self.layers:
            self.desenhar_camadas_fundo()

        # Viewport Culling: Definição da área visível + margem de segurança
        w_curr = self.canvas.winfo_width()
        h_curr = self.canvas.winfo_height()
        margin = 100 

        # Renderização de Arestas (Estradas)
        for origem, destinos in self.grafo.arestas.items():
            x1, y1 = self.coords_para_pixel(self.grafo.nos[origem]['lat'], self.grafo.nos[origem]['lon'])
            
            for destino, dados in destinos.items():
                x2, y2 = self.coords_para_pixel(self.grafo.nos[destino]['lat'], self.grafo.nos[destino]['lon'])
                
                # Otimização: Culling Geométrico
                # Descarta primitivas totalmente fora do viewport ativo
                if (max(x1, x2) < -margin or min(x1, x2) > w_curr + margin or
                    max(y1, y2) < -margin or min(y1, y2) > h_curr + margin):
                    continue
                
                multiplicador = self.grafo.condicoes_transito.get((origem, destino), 1.0)
                cor = self.get_cor_transito(multiplicador)
                
                # Desenho da linha com estilo arredondado
                self.canvas.create_line(x1, y1, x2, y2, fill=cor, width=5, capstyle=tk.ROUND, tags="base")

        # Nós (opcional, podem ser invisíveis ou muito discretos)
        for id_no, info in self.grafo.nos.items():
            x, y = self.coords_para_pixel(info['lat'], info['lon'])
            if info.get('pode_carregar'):
                # Estação de carregamento discreta
                self.canvas.create_oval(x-3, y-3, x+3, y+3, fill="#2196f3", outline="", tags="base")

    def get_car_image(self, taxi, angle):
        """Retorna a imagem do táxi rodada para o ângulo correto."""
        # Determinar estado visual
        if taxi.estado == EstadoVeiculo.LIVRE:
            state_key = 'FREE'
        elif taxi.estado in [EstadoVeiculo.A_CARREGAR, EstadoVeiculo.A_ABASTECER]:
            state_key = 'CHARGE'
        else:
            state_key = 'BUSY'
            
        key = (taxi.tipo, state_key)
        if key not in self.car_images:
            return None
            
        base_img = self.car_images[key]
        
        # Arredondar ângulo para cache (ex: a cada 5 graus)
        angle_int = int(angle // 5) * 5
        cache_key = (key, angle_int)
        
        if cache_key in self.rotated_cache:
            return self.rotated_cache[cache_key]
        
        # Rotacionar
        # PIL rotate roda no sentido anti-horário.
        # O nosso ângulo 0 é "Este" (Direita) se usarmos atan2 normal?
        # Precisamos ajustar dependendo da orientação original da imagem.
        # Assumindo que a imagem original aponta para a DIREITA (Este) ou CIMA (Norte)?
        # Geralmente sprites de carros apontam para CIMA ou DIREITA.
        # Vamos assumir que apontam para a DIREITA (0 graus).
        # Se apontarem para CIMA, subtrair 90 graus.
        
        # Nota: O sistema de coordenadas de tela: Y cresce para baixo.
        # atan2(dy, dx) onde dy = y2-y1.
        
        rotated = base_img.rotate(angle, expand=True, resample=Image.Resampling.BICUBIC)
        tk_img = ImageTk.PhotoImage(rotated)
        self.rotated_cache[cache_key] = tk_img
        return tk_img

    def atualizar_estado(self, frota, pedidos_ativos, tempo_atual, descricoes_status):
        """
        Agenda a atualização da GUI para ser executada na thread principal.
        Isto resolve problemas de concorrência (glitches visuais) quando chamado da thread de simulação.
        """
        self.after(0, lambda: self._atualizar_estado_impl(frota, pedidos_ativos, tempo_atual, descricoes_status))

    def _atualizar_estado_impl(self, frota, pedidos_ativos, tempo_atual, descricoes_status):
        if not self.winfo_exists(): return
        self.canvas.delete("dinamico")
        self.lbl_hora.configure(text=tempo_atual.strftime("%H:%M"))

        # 1. Painel Lateral (Frota)
        for t_id, taxi in frota.items():
            status_text = descricoes_status.get(t_id, "Desconhecido")
            pct = taxi.autonomia_atual / taxi.autonomia_maxima
            pct = max(0.0, min(1.0, pct))
            
            if t_id not in self.items_frota:
                frame = ctk.CTkFrame(self.scroll_frota, fg_color="#333333")
                frame.pack(fill="x", pady=2)
                
                f_head = ctk.CTkFrame(frame, fg_color="transparent")
                f_head.pack(fill="x", padx=5, pady=(2,0))
                ctk.CTkLabel(f_head, text=f"{t_id}", font=("Roboto", 11, "bold")).pack(side="left")
                lbl_pct = ctk.CTkLabel(f_head, text="100%", font=("Roboto", 10), text_color="gray")
                lbl_pct.pack(side="right")
                
                canvas_bar = tk.Canvas(frame, height=4, bg="#444", highlightthickness=0)
                canvas_bar.pack(fill="x", padx=5, pady=2)
                bar_id = canvas_bar.create_rectangle(0, 0, 0, 4, fill="#4caf50", width=0)
                
                lbl_desc = ctk.CTkLabel(frame, text=status_text, font=("Roboto", 10), anchor="w", text_color="gray")
                lbl_desc.pack(fill="x", padx=5, pady=(0,2))
                
                self.items_frota[t_id] = {"lbl_desc": lbl_desc, "lbl_pct": lbl_pct, "canvas_bar": canvas_bar, "bar_id": bar_id}
            
            item = self.items_frota[t_id]
            item["lbl_desc"].configure(text=status_text)
            item["lbl_pct"].configure(text=f"{int(pct*100)}%")
            
            w_canvas = item["canvas_bar"].winfo_width()
            if w_canvas < 10: w_canvas = 200
            item["canvas_bar"].coords(item["bar_id"], 0, 0, w_canvas * pct, 4)

        # 2. Mapa: Pedidos (Marcadores Simples)
        for p in pedidos_ativos:
            ox, oy = self.coords_para_pixel(self.grafo.nos[p.origem]['lat'], self.grafo.nos[p.origem]['lon'])
            dx, dy = self.coords_para_pixel(self.grafo.nos[p.destino]['lat'], self.grafo.nos[p.destino]['lon'])
            
            # Linha de pedido discreta
            self.canvas.create_line(ox, oy, dx, dy, fill=p.cor_mapa, dash=(2, 4), width=1, tags="dinamico")
            # Marcador Origem (Bola pequena)
            self.canvas.create_oval(ox-3, oy-3, ox+3, oy+3, fill=p.cor_mapa, outline="", tags="dinamico")
            # Marcador Destino (Quadrado pequeno)
            self.canvas.create_rectangle(dx-3, dy-3, dx+3, dy+3, fill=p.cor_mapa, outline="", tags="dinamico")

        # 3. Mapa: Táxis (Ícones Rotacionados com Interpolação)
        for taxi in frota.values():
            # Posição padrão (nó atual)
            lat_atual = self.grafo.nos[taxi.localizacao_atual]['lat']
            lon_atual = self.grafo.nos[taxi.localizacao_atual]['lon']
            tx, ty = self.coords_para_pixel(lat_atual, lon_atual)
            
            angle = 0
            
            # Se estiver em movimento, interpolar posição
            if self.simulador and taxi.id_veiculo in self.simulador.movimentos_ativos:
                mov = self.simulador.movimentos_ativos[taxi.id_veiculo]
                
                # Verificar se temos dados para interpolar
                if 'tempo_total_aresta' in mov and mov['tempo_total_aresta'] > 0:
                    # Calcular progresso (0.0 a 1.0)
                    # tempo_restante vai de total -> 0
                    progress = 1.0 - (mov['tempo_restante_aresta'] / mov['tempo_total_aresta'])
                    progress = max(0.0, min(1.0, progress)) # Clamp
                    
                    # Obter próximo nó
                    if mov['idx_prox_no'] < len(mov['caminho']):
                        prox_no = mov['caminho'][mov['idx_prox_no']]
                        lat_prox = self.grafo.nos[prox_no]['lat']
                        lon_prox = self.grafo.nos[prox_no]['lon']
                        
                        px, py = self.coords_para_pixel(lat_prox, lon_prox)
                        
                        # Interpolação Linear
                        tx = tx + (px - tx) * progress
                        ty = ty + (py - ty) * progress
                        
                        # Calcular ângulo baseado no vetor de movimento
                        dx = px - tx
                        dy = -(py - ty) # Inverter Y do canvas
                        rads = math.atan2(dy, dx)
                        angle = math.degrees(rads)
            
            img = self.get_car_image(taxi, angle)
            if img:
                self.canvas.create_image(tx, ty, image=img, tags="dinamico")
            else:
                cor = "#ffffff"
                self.canvas.create_oval(tx-5, ty-5, tx+5, ty+5, fill=cor, tags="dinamico")

            # Nome do Taxi (ID)
            self.canvas.create_text(tx, ty - 25, text=taxi.id_veiculo, fill="white", font=("Roboto", 9, "bold"), tags="dinamico")
