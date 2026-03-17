# Project Netfall

A FOSS application that gamifies STEM

## 🎮 The Core Concept

(To be completed)

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
- **Data Manipulation:** Polars
- **Plotting:** Seaborn / mpld3 (for generating plots of Probability Density Functions and converting them to HTML)
- **Database:** PostgreSQL
- **ORM:** SQLAlchemy / SQLModel
- **Package Manager:** [Pixi](https://pixi.prefix.dev/latest/)

### Frontend (The 2D Map and UI)

- **Language:** TypeScript 5
- **Framework:** React
- **Build Tool:** Vite
- **Visualization:** React Leaflet (for rendering 2D maps with drone locations)
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
