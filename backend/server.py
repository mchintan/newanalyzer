from fastapi import FastAPI, APIRouter, HTTPException
from dotenv import load_dotenv
from starlette.middleware.cors import CORSMiddleware
from motor.motor_asyncio import AsyncIOMotorClient
import os
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import uuid
from datetime import datetime
import numpy as np
import json

ROOT_DIR = Path(__file__).parent
load_dotenv(ROOT_DIR / '.env')

# MongoDB connection
mongo_url = os.environ['MONGO_URL']
client = AsyncIOMotorClient(mongo_url)
db = client[os.environ['DB_NAME']]

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# Monte Carlo Simulation Models
class AssetClass(BaseModel):
    name: str
    median_return: float  # Expected annual return as decimal (e.g., 0.08 for 8%)
    std_deviation: float  # Standard deviation as decimal
    min_return: float     # Minimum return as decimal
    max_return: float     # Maximum return as decimal
    allocation: float     # Portfolio allocation as decimal (e.g., 0.3 for 30%)

class SimulationRequest(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    asset_classes: List[AssetClass]
    initial_investment: float
    time_horizon: int     # Years
    num_simulations: int  # Number of Monte Carlo runs
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class SimulationPath(BaseModel):
    year: int
    portfolio_value: float

class SimulationResult(BaseModel):
    id: str
    simulation_paths: List[List[SimulationPath]]  # Each simulation run's path
    final_values: List[float]  # Final portfolio values for each simulation
    statistics: Dict[str, float]  # Summary statistics
    parameters: SimulationRequest

# Monte Carlo Simulation Engine
class PortfolioSimulator:
    def __init__(self):
        pass
    
    def run_simulation(self, request: SimulationRequest) -> SimulationResult:
        """Run Monte Carlo simulation for portfolio analysis"""
        np.random.seed(42)  # For reproducible results in testing
        
        # Validate allocations sum to 1
        total_allocation = sum(asset.allocation for asset in request.asset_classes)
        if abs(total_allocation - 1.0) > 0.001:
            raise HTTPException(status_code=400, detail="Asset allocations must sum to 100%")
        
        # Run simulations
        simulation_paths = []
        final_values = []
        
        for sim in range(request.num_simulations):
            path = self._run_single_simulation(request)
            simulation_paths.append(path)
            final_values.append(path[-1].portfolio_value)
        
        # Calculate statistics
        statistics = self._calculate_statistics(final_values, request.initial_investment)
        
        return SimulationResult(
            id=request.id,
            simulation_paths=simulation_paths,
            final_values=final_values,
            statistics=statistics,
            parameters=request
        )
    
    def _run_single_simulation(self, request: SimulationRequest) -> List[SimulationPath]:
        """Run a single Monte Carlo simulation path"""
        portfolio_value = request.initial_investment
        path = [SimulationPath(year=0, portfolio_value=portfolio_value)]
        
        for year in range(1, request.time_horizon + 1):
            annual_return = 0.0
            
            # Calculate weighted portfolio return
            for asset in request.asset_classes:
                # Generate random return using normal distribution
                asset_return = np.random.normal(asset.median_return, asset.std_deviation)
                
                # Constrain return within min/max bounds
                asset_return = max(asset.min_return, min(asset.max_return, asset_return))
                
                # Add weighted return to portfolio
                annual_return += asset_return * asset.allocation
            
            # Compound the portfolio value
            portfolio_value *= (1 + annual_return)
            path.append(SimulationPath(year=year, portfolio_value=portfolio_value))
        
        return path
    
    def _calculate_statistics(self, final_values: List[float], initial_investment: float) -> Dict[str, float]:
        """Calculate summary statistics from simulation results"""
        final_values = np.array(final_values)
        
        # Calculate percentiles
        percentile_5 = np.percentile(final_values, 5)
        percentile_50 = np.percentile(final_values, 50)  # Median
        percentile_90 = np.percentile(final_values, 90)
        
        # Calculate returns
        return_5th = (percentile_5 / initial_investment) - 1
        return_median = (percentile_50 / initial_investment) - 1
        return_90th = (percentile_90 / initial_investment) - 1
        
        # Calculate annualized returns (assuming the simulation ran for multiple years)
        # This is a simplified calculation - in practice you'd want the actual time horizon
        mean_value = np.mean(final_values)
        mean_return = (mean_value / initial_investment) - 1
        
        return {
            "final_value_5th_percentile": float(percentile_5),
            "final_value_median": float(percentile_50),
            "final_value_90th_percentile": float(percentile_90),
            "total_return_5th_percentile": float(return_5th),
            "total_return_median": float(return_median),
            "total_return_90th_percentile": float(return_90th),
            "mean_final_value": float(mean_value),
            "mean_total_return": float(mean_return),
            "min_final_value": float(np.min(final_values)),
            "max_final_value": float(np.max(final_values)),
            "std_final_value": float(np.std(final_values))
        }

# Initialize simulator
simulator = PortfolioSimulator()

# API Routes
@api_router.get("/")
async def root():
    return {"message": "Investment Portfolio Analyzer API"}

@api_router.post("/simulate", response_model=SimulationResult)
async def run_portfolio_simulation(request: SimulationRequest):
    """Run Monte Carlo simulation for portfolio analysis"""
    try:
        # Validate minimum simulations
        if request.num_simulations < 5000:
            raise HTTPException(status_code=400, detail="Minimum 5,000 simulations required")
        
        # Validate time horizon
        if request.time_horizon > 50:
            raise HTTPException(status_code=400, detail="Maximum time horizon is 50 years")
        
        if request.time_horizon < 1:
            raise HTTPException(status_code=400, detail="Minimum time horizon is 1 year")
        
        # Run simulation
        result = simulator.run_simulation(request)
        
        # Store result in database for future reference
        await db.simulation_results.insert_one(result.dict())
        
        return result
    
    except Exception as e:
        logger.error(f"Simulation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")

@api_router.get("/simulations", response_model=List[Dict[str, Any]])
async def get_simulation_history():
    """Get history of simulation results"""
    try:
        results = await db.simulation_results.find().sort("timestamp", -1).limit(10).to_list(10)
        # Convert ObjectId to string for JSON serialization
        for result in results:
            result["_id"] = str(result["_id"])
        return results
    except Exception as e:
        logger.error(f"Error fetching simulation history: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch simulation history")

@api_router.get("/default-assets")
async def get_default_asset_classes():
    """Get default asset class parameters"""
    return {
        "asset_classes": [
            {
                "name": "Stocks",
                "median_return": 0.08,  # 8% annual return
                "std_deviation": 0.15,  # 15% volatility
                "min_return": -0.40,    # -40% worst case
                "max_return": 0.35,     # 35% best case
                "allocation": 0.30      # 30% allocation
            },
            {
                "name": "Bonds",
                "median_return": 0.04,  # 4% annual return
                "std_deviation": 0.08,  # 8% volatility
                "min_return": -0.10,    # -10% worst case
                "max_return": 0.15,     # 15% best case
                "allocation": 0.30      # 30% allocation
            },
            {
                "name": "Alternatives",
                "median_return": 0.10,  # 10% annual return
                "std_deviation": 0.20,  # 20% volatility
                "min_return": -0.30,    # -30% worst case
                "max_return": 0.50,     # 50% best case
                "allocation": 0.20      # 20% allocation
            },
            {
                "name": "Private Credit",
                "median_return": 0.07,  # 7% annual return
                "std_deviation": 0.12,  # 12% volatility
                "min_return": -0.15,    # -15% worst case
                "max_return": 0.25,     # 25% best case
                "allocation": 0.20      # 20% allocation
            }
        ],
        "default_initial_investment": 5000000,  # $5MM
        "default_time_horizon": 10,
        "default_num_simulations": 10000
    }

# Include the router in the main app
app.include_router(api_router)

app.add_middleware(
    CORSMiddleware,
    allow_credentials=True,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@app.on_event("shutdown")
async def shutdown_db_client():
    client.close()
