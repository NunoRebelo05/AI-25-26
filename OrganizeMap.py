import json

# Coordenadas "Idealizadas" para um layout limpo (Semi-Grid)
# Mantendo a lógica geográfica relativa, mas espaçando os nós.
# Centro de referência: 41.5500, -8.4200

new_coords = {
    # --- CENTRO ---
    "Centro":                   {"lat": 41.5500, "lon": -8.4200},
    "Avenida_Central":          {"lat": 41.5520, "lon": -8.4150},
    "Praca_Republica":          {"lat": 41.5520, "lon": -8.4250},
    "Posto_Recarga_Centro":     {"lat": 41.5480, "lon": -8.4200},

    # --- NORTE (Universidade, Hospital) ---
    "Infias":                   {"lat": 41.5600, "lon": -8.4200},
    "Estadio":                  {"lat": 41.5700, "lon": -8.4250},
    "Hospital":                 {"lat": 41.5650, "lon": -8.4350},
    "Real":                     {"lat": 41.5600, "lon": -8.4500},
    "Braga_Parque":             {"lat": 41.5600, "lon": -8.4050},
    "UMinho_Gualtar":           {"lat": 41.5650, "lon": -8.3900},
    "Posto_Recarga_Norte":      {"lat": 41.5700, "lon": -8.4000},
    "Adaufe":                   {"lat": 41.5800, "lon": -8.3900},

    # --- OESTE (Estação, Industrial) ---
    "Estacao_CP":               {"lat": 41.5430, "lon": -8.4350},
    "Maximinos":                {"lat": 41.5400, "lon": -8.4450},
    "Frossos":                  {"lat": 41.5500, "lon": -8.4600},
    "Sequeira":                 {"lat": 41.5350, "lon": -8.4650},

    # --- SUL (Comercial, Residencial) ---
    "Minho_Center":             {"lat": 41.5400, "lon": -8.4050},
    "Fraiao":                   {"lat": 41.5300, "lon": -8.4050},
    "Lamaçães":                 {"lat": 41.5500, "lon": -8.3950},
    "Lamaçaes":                 {"lat": 41.5500, "lon": -8.3950}, # Fallback for encoding issues
    "Nogueira":                 {"lat": 41.5200, "lon": -8.4150},
    "Ferreiros":                {"lat": 41.5250, "lon": -8.4450},
    "Celeiros":                 {"lat": 41.5150, "lon": -8.4350},
    "Posto_Recarga_Sul":        {"lat": 41.5250, "lon": -8.4350},

    # --- ESTE (Santuários) ---
    "Bom_Jesus":                {"lat": 41.5550, "lon": -8.3750},
    "Sameiro":                  {"lat": 41.5400, "lon": -8.3650},
}

def reorganize_map():
    try:
        with open("braga_mapa.json", "r", encoding="utf-8") as f:
            data = json.load(f)
        
        # Atualizar coordenadas
        count = 0
        for no in data["nos"]:
            if no["id"] in new_coords:
                no["lat"] = new_coords[no["id"]]["lat"]
                no["lon"] = new_coords[no["id"]]["lon"]
                count += 1
            else:
                print(f"Aviso: Nó {no['id']} não tem nova coordenada definida.")

        with open("braga_mapa.json", "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
            
        print(f"Sucesso! {count} nós atualizados em 'braga_mapa.json'.")
        
    except Exception as e:
        print(f"Erro ao atualizar mapa: {e}")

if __name__ == "__main__":
    reorganize_map()
