# 🌍 Strategic AI Nexus

**Real-time Geopolitical Simulation with Reinforcement Learning Agents**

A sophisticated multi-agent simulation platform where Hegemon and Sovereign powers compete through adaptive strategies, game-theoretic decision-making, and continuous reinforcement learning in a dynamic geopolitical landscape.

---

## ✨ Key Features

- **🧠 Reinforcement Learning Agents** – Q-learning with epsilon-greedy exploration
- **🎮 Game Theory Engine** – Nash equilibrium analysis, mixed strategy solvers
- **📊 Real-time Dashboard** – Live state visualization with WebSocket updates
- **🔄 Configurable Scenarios** – Multiple geopolitical scenarios
- **📈 Predictive Analytics** – Linear-trend forecasting with confidence bands
- **🎯 Agent Telemetry** – Real-time learning progress metrics

---

## 🛠️ Technology Stack

| Component | Technology |
|-----------|------------|
| **Backend** | Python 3.9+, FastAPI, WebSocket |
| **AI/ML** | Custom Q-learning, NumPy, SciPy |
| **Game Theory** | Nash equilibrium, LP solvers |
| **Frontend** | Next.js 14, TypeScript, Tailwind CSS |
| **Realtime** | WebSocket with heartbeat management |
| **Database** | SQLite with SQLAlchemy ORM |
| **Charts** | Recharts |











---

## 📁 Project Structure
strategic-ai-nexus/
│
├── backend/ # FastAPI Backend
│ ├── app/
│ │ ├── agents/ # RL Agent Implementation
│ │ │ ├── base_agent.py # Q-learning base class
│ │ │ ├── hegemon_agent.py # Hegemon (4 strategies)
│ │ │ └── sovereign_agent.py # Sovereign (4 strategies)
│ │ │
│ │ ├── game_theory/ # Game Theory Engine
│ │ │ ├── equilibrium.py # Nash equilibrium analyzer
│ │ │ ├── mixed_strategy.py # LP + fictitious play solver
│ │ │ └── payoff_matrix.py # Adaptive payoff matrix
│ │ │
│ │ ├── simulation/ # Simulation Core
│ │ │ ├── engine.py # Round execution engine
│ │ │ ├── runner.py # Simulation lifecycle manager
│ │ │ └── scenarios.py # Predefined scenarios
│ │ │
│ │ ├── realtime/ # WebSocket Management
│ │ │ └── websocket.py # Connection manager
│ │ │
│ │ ├── analytics/ # Forecasting Engine
│ │ │ └── forecast.py # Trend analysis
│ │ │
│ │ ├── api/ # REST API Routes
│ │ │ ├── routes/
│ │ │ │ ├── simulation.py # Simulation CRUD
│ │ │ │ ├── state.py # State management
│ │ │ │ ├── analytics.py # Analytics endpoints
│ │ │ │ └── websocket.py # WebSocket route handler
│ │ │ └── websocket.py # WebSocket handler
│ │ │
│ │ ├── environment/ # Environment State
│ │ │ ├── environment.py # Environment wrapper
│ │ │ ├── state.py # State models
│ │ │ └── transition.py # State transition logic
│ │ │
│ │ ├── core/ # Core Utilities
│ │ │ └── runtime.py # Application runtime
│ │ │
│ │ ├── database/ # Database Layer
│ │ │ ├── models.py # SQLAlchemy models
│ │ │ ├── crud.py # CRUD operations
│ │ │ └── session.py # Database session
│ │ │
│ │ └── utils/ # Helpers
│ │ ├── config.py # Configuration
│ │ └── logger.py # Logging setup
│ │
│ ├── requirements.txt
│ ├── Dockerfile
│ └── run.py # Entry point
│
└── frontend/ # Next.js Frontend
├── app/
│ ├── components/
│ │ └── Dashboard/ # UI Components
│ │ ├── Dashboard.tsx # Main orchestrator
│ │ ├── Sidebar.tsx # Navigation
│ │ ├── KpiStrip.tsx # Real-time KPIs
│ │ ├── PowerBalance.tsx # Agent influence
│ │ ├── WorldMap.tsx # Geopolitical map
│ │ ├── AgentIntelligence.tsx # RL telemetry
│ │ ├── ForecastPanel.tsx # Trend forecasting
│ │ └── MilitaryOverview.tsx # Conflict metrics
│ │
│ ├── hooks/
│ │ ├── useSimulation.ts # Simulation API hooks
│ │ └── useWebSocket.ts # WebSocket client
│ │
│ └── types/
│ └── index.ts # TypeScript definitions
│
├── package.json
├── tailwind.config.js
└── tsconfig.json

text

---












## 🚀 Getting Started

### Prerequisites

- Python 3.9 or higher
- Node.js 18 or higher
- npm or yarn

### Installation

**1. Clone the repository**

```bash
git clone https://github.com/nh30073007/GEO_POLIS_SIMULATION.git
cd GEO_POLIS_SIMULATION
2. Backend Setup

bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python run.py
The backend will start at http://localhost:8000

3. Frontend Setup

bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
The frontend will start at http://localhost:3000

🎮 How It Works
Core Loop
Agents (Hegemon and Sovereign) select strategies from their doctrine sets

Environment processes the combined strategies and transitions state

Utilities are calculated based on the new state

Q-learning updates agent Q-tables with the received rewards

Epsilon decays, shifting from exploration to exploitation

Game Theory engines analyze equilibrium states

Agent Strategies
Agent	Strategy	Description
Hegemon	H1	Expansionist - Aggressive territorial growth
H2	Stabilizer - Maintain status quo
H3	Disruptor - Create uncertainty
H4	Dominator - Overwhelming force projection
Sovereign	S1	Diplomatic - Alliance building
S2	Resilient - Defense and fortification
S3	Assertive - Proactive counter-measures
S4	Adaptive - Flexible response
State Metrics
Economy: 0-100 scale (higher = stronger)

Tension: 0-100 scale (higher = conflict-prone)

Stability: Composite metric of overall system health

📊 Dashboard Features
Component	Description
KPI Strip	Real-time economic, tension, and stability metrics
Power Balance	Visual comparison of agent influence
World Map	Interactive geopolitical visualization
Agent Intelligence	RL learning progress and Q-value trends
Forecast Panel	Trend predictions with confidence intervals
Conflict Tracker	Active and resolved conflict monitoring
Military Overview	Force deployment and readiness metrics
Diplomatic Relations	Alliance and tension visualizations
🔬 API Endpoints
Simulation Management
text
POST   /api/simulation/create
POST   /api/simulation/start/{sim_id}
POST   /api/simulation/pause/{sim_id}
POST   /api/simulation/resume/{sim_id}
POST   /api/simulation/stop/{sim_id}
State & Analytics
text
GET    /api/state/current/{sim_id}
GET    /api/state/history/{sim_id}?limit=120
GET    /api/analytics/forecast/{sim_id}?horizon=8
GET    /api/analytics/performance/{sim_id}
WebSocket
text
WS     /ws?room={sim_id}
🤝 Contributing
Fork the repository

Create your feature branch (git checkout -b feature/amazing-feature)

Commit your changes (git commit -m 'Add amazing feature')

Push to the branch (git push origin feature/amazing-feature)

Open a Pull Request

📄 License
This project is licensed under the MIT License - see the LICENSE file for details.

Built with passion for AI, strategy, and simulation science