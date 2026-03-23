# Project Netfall

A FOSS application that gamifies STEM

## 🎮 The Core Concept

_Project Netfall_ is a tactical interception simulator that bridges the gap between STEM education and RPG progression. Players take on the role of an independent interception contractor operating a high-altitude UAV. The objective is to ambush mid-sized autonomous courier drones carrying valuable loot through complex, semi-hidden urban "sky lanes."

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

### Development Roadmap

#### Phase I: The Core Physics & UI Loop

- [ ] **Backend Math Engine**: Implement the spatial parametric curves and temporal modulation in Python/Polars to generate dynamic PDFs.

- [ ] **Frontend Map Integration**: Render the Leaflet 2D map and overlay the downsampled PDF heatmap.

- [ ] **Time-Scrubbing UI**: Build the interactive timeline slider in React to allow users to observe PDF shifts over a 24-hour simulation cycle.

- [ ] **Basic Interception Logic**: Create the FastAPI endpoint to validate a "Drop Net" event based on target coordinates, net radius, and time of impact.

#### Phase II: RPG Mechanics & Persistence

- [ ] **Database Initialization**: Spin up PostgreSQL with SQLModel for the Users, Stats, and Targets schemas.

- [ ] **Loot Distribution System**: Implement the NumPy/SciPy logic to generate randomized loot drops based on the target's specific Gaussian distribution parameters.

- [ ] **Loadout Management**: Build the frontend UI forms for players to view their Traits, spend loot on Upgrades, and see how it modifies their base interception stats.

- [ ] **Target Tiering**: Introduce Small, Medium, and Large target classes with varying speed and acceleration profiles, requiring different predictive strategies.

---

## Application Requirements

### Objective

To learn Probability Density Functions (PDFs) through analysis of randomized drone behavior in order to capture and gain loot and progress.

### Initial Backend API

1. Simulate semi-random drone behavior in NumPy/SciPy.
2. Calculate the PDF trend over time.
3. Generate a visualization of the PDF using Seaborn.
4. Convert Seaborn plot to HTML with mpld3 to send to the frontend.
5. Interact with the PostgreSQL database to save/fetch the user's traits, stats, upgrades, etc.
6. Provide API endpoints to the frontend.

### Frontend Prototype

1. Generate or load a 2D Leaflet map.
2. Overlay map with the PDFs obtained from the backend API.
3. Display the user's traits, stats, upgrades, etc. retrieved from the backend.

### UI/UX Prototype Design

1. Render the 2D map with a PDF overlay that can be enabled/disabled via a checkbox.
2. Provide a UI form for user setup.
3. Design the UI for displaying and interacting with user traits, stats, upgrades, etc.

### Database Schema

- Users table
  - Id
  - Name
  - Class_Name
- Classes table
  - Id
  - Name
  - Description
  - Trait_1
  - Trait_2
  - Trait_3
- Traits table
  - Id
  - Name
  - Description
  - Category
  - Modifies
  - Multiplier
  - Offset
- Stats table
  - Id
  - User_Id
  - Stat_Type
  - Stat_Min
  - Stat_Max
  - Base_Value
  - Current_Value
- Upgrades table
  - Id
  - Name
  - Cost
  - Effected_Stat
  - Stat_Multiplier
  - Stat_Offset
- Targets table
  - Id
  - Category
  - Top_Speed
  - Accel_Max
  - Decel_Max
  - Hit_Box
  - Loot_Dist
  - Loot_Min
  - Loot_Max
  - Loot_Mean
  - Loot_StdDev

### Other Requirements

## 🛠 Tech Stack

### Backend (The Physics Engine)

- **Language:** `Python 3.14`
- **Framework:** `FastAPI`
- **Dev API Server:** `uvicorn`
- **Math Kernel:** `NumPy` / `SciPy` (for generating and analyzing semi-random drone behavior)
- **Data Manipulation:** `Polars`
- **Database:** `PostgreSQL`
- **ORM:** `SQLAlchemy` / `SQLModel`
- **Unit tests:** `pytest`
- **Package Manager:** [Pixi](https://pixi.prefix.dev/latest/)

### Frontend (The 2D Map and UI)

- **Language:** `TypeScript 5`
- **Framework:** `React`
- **Build Tool:** `Vite`
- **Visualization:** `Apache ECharts` (for rendering streamed target traffic heatmaps to overlay over a generated 2D game map)
- **State Management:** React Hooks / Context API
- **Unit tests:** `jest`

### CI/CD

- **Automatic Actions on `Git` Commits:**
  - `pre-commit` (performs `Python` formatting with `Ruff`)
  - `Husky` (performs formatting with `Prettier` on `TypeScript` files and other supported text files)
- **GitHub Actions:** (not implemented yet)
  - `Ruff` (`Python` linter)
  - `ESLint` (`TypeScript` linter)
  - `pytest` (backend unit tests)
  - `jest` (frontend unit tests)

## 🚀 Getting Started

**Note: An app prototype is planned, but nothing runs for now.**

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

### Database Setup (not yet implemented)

Ensure PostgreSQL is not already globally installed and running before proceeding.

```bash
pixi run create-db
```

### Backend Unit Tests

```bash
# Run backend unit tests (pytest)
pixi run -e test-py314 backend-tests
```

## 🤝 Contributing

1. Fork the project
2. Create your feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Ensure that the GitHub Actions pass
6. Open a Pull Request

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.
