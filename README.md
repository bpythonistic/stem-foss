# Project Netfall

A FOSS application that gamifies STEM

## 🎮 The Core Concept

*Project Netfall* is a tactical interception simulator that bridges the gap between STEM education and RPG progression. Players take on the role of an independent interception contractor operating a high-altitude UAV. The objective is to ambush mid-sized autonomous courier drones carrying valuable loot through complex, semi-hidden urban "sky lanes."

Because the enemy drones are too fast and erratic for direct pursuit, players must rely on spatiotemporal analysis and kinematics. By deploying passive sensors, analyzing Probability Density Functions (PDFs) of drone traffic over time, and calculating the perfect drop physics, players spring traps from above.

## Gameplay Objectives

### 1. Deploy & Observe (Data Gathering)

- **Goal**: Map the invisible sky lanes.

- **Mechanic**: Players deploy limited sensor nodes across a 2D topographical map. Over time, these sensors gather discrete data points on target movements, revealing high-traffic routes based on the target's `Category` and behavior profiles.

### 2. Analyze & Predict (Reading the PDF)

- **Goal**: Identify temporal "choke points."

- **Mechanic**: The game translates raw sensor data into a dynamic 2D Probability Density Function (PDF) heatmap. Players scrub through a timeline to see how the probability of a drone's location shifts throughout the day. The objective is to find the exact coordinates and time where the PDF variance (σ2) is lowest, indicating a highly predictable target location.

### 3. Ambush & Capture (Kinematic Interception)

- **Goal**: Execute a perfectly timed net drop.

- **Mechanic**: Once an ambush point is selected, players position their UAV. When the target approaches, players must factor in target speed (`Top_Speed`), altitude, and net descent rate to calculate the exact release window. A successful capture occurs when the target intersects the net's hit radius at the time of impact.

### 4. Extract & Upgrade (RPG Progression)

- **Goal**: Scale operations to capture higher-tier targets.

- **Mechanic**: Captured targets yield rewards based on statistical distributions (`Loot_Mean`, `Loot_StdDev`). Players use this loot to invest in their loadout:

  - **Classes & Traits**: Select operator backgrounds that offer baseline multipliers to sensor range or net aerodynamics.

  - **Stats & Upgrades**: Purchase better hardware to modify base stats, such as increasing sensor sampling rates, buying heavier nets that fall faster (reducing lead time), or upgrading UAV batteries for longer loiter times.

### Development Roadmap (TBD)

#### Phase I

- [ ] First objective

#### Phase II

### Frontend Web UI

### Backend API

### PostgreSQL Database

---

## 🛠 Tech Stack

### Backend (The Physics Engine)

- **Language:** Python 3.14
- **Framework:** FastAPI
- **Math Kernel:** NumPy / SciPy (for generating and analyzing semi-random drone behavior)
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy / SQLModel
- **Package Manager:** [Pixi](https://pixi.prefix.dev/latest/)

### Frontend (The 2D Map and UI)

- **Language:** TypeScript 5
- **Framework:** React
- **Build Tool:** Vite
- **Visualization:** TBD (map/graphics rendering tools like [Top 5 map libraries for React](https://it-waves.com/blogs/top-5-map-libraries-for-react-in-2024))
- **State Management:** React Hooks / Context API

## 🚀 Getting Started

**Note: The development environment and folder structure has NOT been set up yet.**

### Prerequisites

- [Pixi](https://pixi.prefix.dev/latest/#installation)

### Backend Setup

```bash
# Clone the repository
git clone https://github.com/bpythonistic/stem-foss.git
cd stem-foss

# Initialize the environment and install dependencies
pixi install

# Create .env file
cp back-end/app/.env.example back-end/app/.env
```

The API will be available at [http://localhost:8000](http://localhost:8000).

You can view the interactive docs at [http://localhost:8000/docs](http://localhost:8000/docs).

### Frontend Setup

Once the API server is running, open a new terminal before proceeding.

```bash
# Install dependencies
pixi run update-nodejs
```

The game client will be available at [http://localhost:5173](http://localhost:5173)

### Database Setup

Ensure PostgreSQL is not already globally installed and running before proceeding.

```bash
pixi run create-db
```

## 🤝 Contributing

1. Fork the project
2. Create your feature branch (git checkout -b feature/AmazingFeature)
3. Commit your changes (git commit -m 'Add some AmazingFeature')
4. Push to the branch (git push origin feature/AmazingFeature)
5. Ensure that the GitHub Actions pass
6. Open a Pull Request

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
