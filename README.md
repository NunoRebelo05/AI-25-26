<div align="center">

# 🚖 TaxiGreen Simulator

### AI-Powered Electric & Hybrid Taxi Fleet Management System

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)](https://www.python.org/)
[![Grade](https://img.shields.io/badge/Grade-18%2F20-brightgreen?style=flat-square)](.)
[![License](https://img.shields.io/badge/License-Academic-blue?style=flat-square)](.)
[![CustomTkinter](https://img.shields.io/badge/GUI-CustomTkinter-blueviolet?style=flat-square)](https://github.com/TomSchimansky/CustomTkinter)

> **Academic Project — Artificial Intelligence (2025/2026)**  
> Grade: **18 / 20** 🏆

</div>

---

## 📋 Table of Contents

- [Overview](#-overview)
- [Key Features](#-key-features)
- [Architecture](#-architecture)
- [Search Algorithms](#-search-algorithms)
- [Tech Stack](#-tech-stack)
- [Getting Started](#-getting-started)
- [Configuration](#-configuration)
- [Project Structure](#-project-structure)

---

## 🌍 Overview

**TaxiGreen Simulator** is a full-stack desktop simulation platform that models the intelligent dispatch and routing of a mixed electric/combustion taxi fleet across a real city map (Braga, Portugal). The simulator integrates **real OpenStreetMap data**, **graph-based pathfinding algorithms** (A\*, Greedy, BFS, DFS, UCS), and a **dynamic GUI** to visualise fleet movement in real time.

The project was developed as part of the Artificial Intelligence course (2025/26) and received a grade of **18/20**. It demonstrates the practical application of AI search strategies to a real-world optimization problem: minimising passenger wait times while balancing fleet cost, CO₂ emissions, and battery autonomy.

---

## ✨ Key Features

| Feature | Description |
|---|---|
| 🗺️ **Real Map Integration** | Imports road networks from OpenStreetMap via `osmnx`; pre-built Braga city map included |
| 🤖 **5 Search Algorithms** | A\*, Greedy Best-First, UCS (Dijkstra), DFS, BFS — switchable at runtime |
| ⚡ **Mixed Fleet** | Electric (EV) and combustion vehicles with individual autonomy, charge, and CO₂ tracking |
| 📊 **Algorithm Benchmarking** | Side-by-side comparison of all algorithms across configurable scenarios |
| 🚦 **Dynamic Traffic** | Peak-hour traffic multipliers affect edge travel times in real time |
| 🎯 **Smart Dispatch** | Multi-criteria taxi selection (wait time, cost, km without passenger, priority, EV preference) |
| 📈 **Live Statistics** | Real-time fleet dashboard: completed / pending / rejected trips, CO₂ saved, costs |
| 🛠️ **Fully Configurable** | All parameters (fleet size, probabilities, weights, peak hours) tunable via `config.json` |
| 🎨 **Dark-Mode GUI** | Uber-style map canvas with animated taxi icons, route highlighting, and a status sidebar |

---

## 🏗️ Architecture

The project follows a clean **Model-View-Controller (MVC)**-inspired layered architecture:

```
┌─────────────────────────────────────────────────────────┐
│                   App.py  (Entry Point)                  │
│           Sidebar navigation + view lifecycle            │
└──────────────────────────┬──────────────────────────────┘
                           │
        ┌──────────────────┼──────────────────┐
        ▼                  ▼                  ▼
  HomeView.py      SimulationView.py   AlgorithmsView.py
  (Welcome)        (Map + Controls)    (Benchmark Runner)
        │                  │
        │           VisualizadorGUI.py
        │           (Real-time canvas)
        │                  │
        └──────────────────▼──────────────────┐
                   Simulador.py               │
               (Simulation engine)            │
                           │                  │
              ┌────────────┤                  │
              ▼            ▼                  │
         Gestor.py      Pedido.py             │
       (Fleet manager) (Trip request)         │
              │                               │
              ▼                               ▼
          Taxi.py                         Grafo.py
       (Vehicle model)             (Weighted directed graph
                                    + Haversine heuristic)
              │                               │
              └──────────────┬────────────────┘
                             ▼
                  AlgoritmosDeProcura.py
               (A*, Greedy, UCS, DFS, BFS)
```

**Supporting modules:**

| Module | Role |
|---|---|
| `Config.py` | Singleton config manager with JSON hot-reload and nested key access |
| `RealMapImporter.py` | OSMnx bridge — downloads & converts OSM graphs to the internal `Grafo` format |
| `MapCreator.py` | Utility to generate or edit custom map JSON files |
| `OrganizeMap.py` | Cleans and simplifies raw OSM exports |

---

## 🔍 Search Algorithms

All algorithms are implemented from scratch in `AlgoritmosDeProcura.py` and optimise either **travel distance (km)** or **travel time (minutes)**.

### A\* (A-Star) — *Default*
- Uses an **admissible Haversine heuristic** (straight-line distance / maximum speed)
- Heuristic is dynamically calibrated per graph to guarantee optimality
- Falls back to **Dijkstra / UCS** when `use_heuristic=False`
- Returns: optimal path, cost, nodes visited

### Greedy Best-First Search
- Expands the node *closest to the goal* according to the heuristic only
- Faster than A\* in practice but does **not** guarantee optimality
- Useful baseline for speed vs. quality trade-off analysis

### Breadth-First Search (BFS)
- Guarantees the **minimum-hop** path
- Cost-agnostic; useful for connectivity checks and short networks

### Depth-First Search (DFS)
- Memory-efficient exploration; does **not** guarantee shortest path
- Included for completeness and academic benchmarking

### Uniform Cost Search (UCS / Dijkstra)
- A\* with zero heuristic; guarantees optimal cost
- Explores more nodes than A\* but serves as the gold-standard reference

#### Benchmark comparison output (example)
```
Algorithm  | Path Length | Cost   | Nodes Visited | Time (ms)
-----------|-------------|--------|---------------|----------
A*         | 7 nodes     | 3.2 km | 14            | 1.2
Greedy     | 9 nodes     | 4.1 km | 8             | 0.6
UCS        | 7 nodes     | 3.2 km | 31            | 2.1
BFS        | 6 nodes     | 5.8 km | 22            | 1.8
DFS        | 12 nodes    | 8.4 km | 19            | 0.9
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Language | Python 3.10+ |
| GUI Framework | [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) + Tkinter Canvas |
| Map Data | [OSMnx](https://osmnx.readthedocs.io/) + [NetworkX](https://networkx.org/) |
| Image Processing | [Pillow (PIL)](https://python-pillow.org/) |
| Data Processing | [Pandas](https://pandas.pydata.org/) |
| Pathfinding | Custom implementations (heapq, deque) |
| Graph Format | Custom JSON + Haversine distance |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10 or higher
- pip

### Installation

```bash
# 1. Clone the repository
git clone https://github.com/NunoRebelo05/AI-25-26.git
cd AI-25-26

# 2. Install dependencies
pip install -r requirements.txt

# 3. Launch the application
python main.py
```

### First Run

The application ships with a pre-built **Braga city map** (`braga_mapa.json` — ~400 nodes, real road network). No internet connection is required for the default scenario.

To download a fresh map for any city:
```python
# Inside RealMapImporter.py or via the import tool
from RealMapImporter import importar_mapa_osm
grafo = importar_mapa_osm("Braga, Portugal", dist=3000)
```

---

## ⚙️ Configuration

All simulation parameters are controlled via `config.json`:

```json
{
  "simulacao": {
    "duracao_horas": 12,
    "prob_pedido": 0.15,
    "horas_ponta": [8, 9, 17, 18],
    "velocidade_media_cidade_kmh": 40.0,
    "multiplicador_transito_ponta": 1.75,
    "limiar_recarga_eletrico": 0.25
  },
  "frota": {
    "num_eletricos": 2,
    "num_combustao": 2,
    "specs_eletrico":   { "capacidade": 4, "custo_km": 0.15, "autonomia": 250.0 },
    "specs_combustao":  { "capacidade": 4, "custo_km": 0.25, "autonomia": 600.0 }
  },
  "pesos_estrategia": {
    "W_TEMPO_ESPERA":       1.5,
    "W_CUSTO_OPER":         1.0,
    "W_KM_SEM_PAX":         0.8,
    "PENALIZACAO_AMBIENTAL": 50.0,
    "PENALIZACAO_PRIORIDADE": 3.0
  }
}
```

Key parameters:
- **`prob_pedido`** — probability of a new trip request each simulated minute
- **`multiplicador_transito_ponta`** — peak-hour travel time multiplier (e.g. `1.75` = 75% slower)
- **`limiar_recarga_eletrico`** — battery threshold below which an EV is sent to charge
- **`PENALIZACAO_AMBIENTAL`** — extra cost score assigned to combustion vehicles when a customer prefers EV

---

## 📁 Project Structure

```
AI-25-26/
├── main.py                    # Entry point
├── App.py                     # Main application window & navigation
├── Config.py                  # Singleton configuration manager
├── Grafo.py                   # Weighted directed graph + Haversine heuristic
├── AlgoritmosDeProcura.py     # A*, Greedy, UCS, DFS, BFS implementations
├── Gestor.py                  # Fleet manager & dispatch logic
├── Simulador.py               # Simulation engine (time-stepped)
├── Taxi.py                    # Vehicle model (EV & combustion)
├── Pedido.py                  # Trip request model
├── VisualizadorGUI.py         # Real-time map canvas (Tkinter)
├── RealMapImporter.py         # OSMnx → Grafo converter
├── MapCreator.py              # Map creation utility
├── OrganizeMap.py             # Map simplification utility
├── config.json                # Runtime configuration
├── braga_mapa.json            # Pre-built Braga road network
├── requirements.txt           # Python dependencies
├── assets/                    # Taxi icons (EV / combustion, colours)
└── views/
    ├── HomeView.py            # Welcome screen
    ├── SimulationView.py      # Simulation controls & map view
    └── AlgorithmsView.py      # Algorithm benchmark runner
```

---

<div align="center">

**Developed for the Artificial Intelligence course (2025/2026)**  
Grade: **18 / 20** 🏆

</div>