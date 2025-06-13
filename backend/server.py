from fastapi import FastAPI, APIRouter, HTTPException
from starlette.middleware.cors import CORSMiddleware
import logging
from pathlib import Path
from pydantic import BaseModel, Field
from typing import List, Dict, Any
import uuid
from datetime import datetime
import numpy as np
from collections import deque

# Create the main app without a prefix
app = FastAPI()

# Create a router with the /api prefix
api_router = APIRouter(prefix="/api")

# In-memory storage
simulation_history = deque(maxlen=10)  # Keep last 10 simulations
default_asset_classes = [
    {
        "name": "Stocks",
        "median_return": 0.08,
        "std_deviation": 0.15,
        "min_return": -0.20,
        "max_return": 0.30,
        "allocation": 0.40
    },
    {
        "name": "Bonds",
        "median_return": 0.04,
        "std_deviation": 0.05,
        "min_return": -0.05,
        "max_return": 0.12,
        "allocation": 0.30
    },
    {
        "name": "Alternatives",
        "median_return": 0.06,
        "std_deviation": 0.10,
        "min_return": -0.15,
        "max_return": 0.25,
        "allocation": 0.20
    },
    {
        "name": "Private Credit",
        "median_return": 0.07,
        "std_deviation": 0.08,
        "min_return": -0.10,
        "max_return": 0.20,
        "allocation": 0.10
    }
]

# Monte Carlo Simulation Models
class TaxSettings(BaseModel):
    account_type: str = "taxable"  # "taxable", "tax_deferred", "tax_free"
    capital_gains_tax_rate: float = 0.15  # Federal capital gains tax rate
    ordinary_income_tax_rate: float = 0.22  # For tax-deferred withdrawals
    state_tax_rate: float = 0.0  # State tax rate

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
    enable_drawdown: bool = False  # Whether to enable annual withdrawals
    annual_drawdown: float = 0.0   # Annual withdrawal amount (first year)
    inflation_rate: float = 0.03   # Annual inflation rate for drawdown increases
    tax_settings: TaxSettings = Field(default_factory=TaxSettings)  # Tax configuration
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class SimulationPath(BaseModel):
    year: int
    portfolio_value: float

    class Config:
        json_encoders = {
            float: lambda v: round(v, 2)  # Round float values to 2 decimal places
        }

class SimulationResult(BaseModel):
    id: str
    simulation_paths: List[List[SimulationPath]]  # Each simulation run's path
    final_values: List[float]  # Final portfolio values for each simulation
    statistics: Dict[str, float]  # Summary statistics
    parameters: SimulationRequest

    class Config:
        json_encoders = {
            float: lambda v: round(v, 2)  # Round float values to 2 decimal places
        }

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
        statistics = self._calculate_statistics(final_values, request.initial_investment, request.time_horizon, request)
        
        return SimulationResult(
            id=request.id,
            simulation_paths=simulation_paths,
            final_values=final_values,
            statistics=statistics,
            parameters=request
        )
    
    def _calculate_withdrawal_tax(self, withdrawal_amount: float, portfolio_value: float, cost_basis: float, tax_settings: TaxSettings) -> float:
        """Calculate taxes owed on withdrawal based on account type"""
        if tax_settings.account_type == "tax_free":
            # Roth IRA/401k - no taxes on qualified withdrawals
            return 0.0
        elif tax_settings.account_type == "tax_deferred":
            # Traditional IRA/401k - entire withdrawal taxed as ordinary income
            federal_tax = withdrawal_amount * tax_settings.ordinary_income_tax_rate
            state_tax = withdrawal_amount * tax_settings.state_tax_rate
            return federal_tax + state_tax
        else:
            # Taxable account - only gains are taxed at capital gains rate
            if portfolio_value <= cost_basis:
                # No gains, no tax
                return 0.0
            
            # Calculate proportion of gains in the withdrawal
            total_gains = portfolio_value - cost_basis
            gains_proportion = total_gains / portfolio_value if portfolio_value > 0 else 0
            taxable_amount = withdrawal_amount * gains_proportion
            
            federal_tax = taxable_amount * tax_settings.capital_gains_tax_rate
            state_tax = taxable_amount * tax_settings.state_tax_rate
            return federal_tax + state_tax

    def _run_single_simulation(self, request: SimulationRequest) -> List[SimulationPath]:
        """Run a single Monte Carlo simulation path with optional drawdowns and taxes"""
        portfolio_value = request.initial_investment
        cost_basis = request.initial_investment  # Track cost basis for tax calculations
        path = [SimulationPath(year=0, portfolio_value=portfolio_value)]
        total_taxes_paid = 0.0
        
        for year in range(1, request.time_horizon + 1):
            # Calculate drawdown for this year (if enabled)
            gross_drawdown = 0.0
            net_drawdown = 0.0
            taxes_this_year = 0.0
            
            if request.enable_drawdown and request.annual_drawdown > 0:
                # Calculate gross withdrawal needed (before taxes)
                gross_drawdown = request.annual_drawdown * (1 + request.inflation_rate) ** (year - 1)
                
                # For tax-deferred accounts, we need to gross up the withdrawal to get the desired net amount
                if request.tax_settings.account_type == "tax_deferred":
                    # Calculate what gross withdrawal is needed to get the desired net amount
                    combined_tax_rate = request.tax_settings.ordinary_income_tax_rate + request.tax_settings.state_tax_rate
                    gross_drawdown = gross_drawdown / (1 - combined_tax_rate)
                
                # Calculate taxes on the withdrawal
                taxes_this_year = self._calculate_withdrawal_tax(
                    gross_drawdown, portfolio_value, cost_basis, request.tax_settings
                )
                total_taxes_paid += taxes_this_year
                
                # Net amount available after taxes
                net_drawdown = gross_drawdown - taxes_this_year
                
                # Apply gross withdrawal to portfolio
                portfolio_value = max(0, portfolio_value - gross_drawdown)
                
                # Update cost basis proportionally for taxable accounts
                if request.tax_settings.account_type == "taxable" and portfolio_value > 0:
                    cost_basis = cost_basis * (portfolio_value / (portfolio_value + gross_drawdown))
            
            # Only continue if portfolio has value remaining
            if portfolio_value <= 0:
                # Portfolio depleted - set remaining years to 0
                for remaining_year in range(year, request.time_horizon + 1):
                    path.append(SimulationPath(year=remaining_year, portfolio_value=0.0))
                break
            
            annual_return = 0.0
            
            # Calculate weighted portfolio return
            for asset in request.asset_classes:
                # Generate random return using normal distribution
                asset_return = np.random.normal(asset.median_return, asset.std_deviation)
                
                # Constrain return within min/max bounds
                asset_return = max(asset.min_return, min(asset.max_return, asset_return))
                
                # Add weighted return to portfolio
                annual_return += asset_return * asset.allocation
            
            # Apply return to remaining portfolio value
            portfolio_value *= (1 + annual_return)
            
            # For taxable accounts, increase cost basis by new contributions (none in this model)
            # Cost basis grows with the portfolio for non-taxable accounts
            if request.tax_settings.account_type != "taxable":
                cost_basis = portfolio_value  # No tax basis tracking needed for tax-advantaged accounts
            
            path.append(SimulationPath(year=year, portfolio_value=portfolio_value))
        
        return path
    
    def _calculate_statistics(self, final_values: List[float], initial_investment: float, time_horizon: int, request: SimulationRequest) -> Dict[str, float]:
        """Calculate comprehensive summary statistics from simulation results"""
        final_values = np.array(final_values)
        
        # Calculate percentiles
        percentile_5 = np.percentile(final_values, 5)
        percentile_10 = np.percentile(final_values, 10)
        percentile_25 = np.percentile(final_values, 25)
        percentile_50 = np.percentile(final_values, 50)  # Median
        percentile_75 = np.percentile(final_values, 75)
        percentile_90 = np.percentile(final_values, 90)
        percentile_95 = np.percentile(final_values, 95)
        
        # Calculate total returns
        return_5th = (percentile_5 / initial_investment) - 1
        return_10th = (percentile_10 / initial_investment) - 1
        return_25th = (percentile_25 / initial_investment) - 1
        return_median = (percentile_50 / initial_investment) - 1
        return_75th = (percentile_75 / initial_investment) - 1
        return_90th = (percentile_90 / initial_investment) - 1
        return_95th = (percentile_95 / initial_investment) - 1
        
        # Calculate annualized returns
        def annualized_return(total_return, years):
            if years == 0:
                return 0
            return (1 + total_return) ** (1/years) - 1
        
        annualized_return_5th = annualized_return(return_5th, time_horizon)
        annualized_return_median = annualized_return(return_median, time_horizon)
        annualized_return_90th = annualized_return(return_90th, time_horizon)
        
        # Calculate risk metrics
        mean_value = np.mean(final_values)
        mean_return = (mean_value / initial_investment) - 1
        mean_annualized_return = annualized_return(mean_return, time_horizon)
        
        std_final_value = np.std(final_values)
        volatility = std_final_value / mean_value if mean_value > 0 else 0  # Coefficient of variation
        
        # Calculate probability of loss (portfolio depletion)
        probability_of_depletion = np.sum(final_values <= 0) / len(final_values)
        
        # Calculate probability of maintaining initial value (despite drawdowns)
        probability_of_maintaining = np.sum(final_values >= initial_investment) / len(final_values)
        
        # Calculate probability of doubling
        probability_of_doubling = np.sum(final_values >= initial_investment * 2) / len(final_values)
        
        # Best and worst case scenarios
        best_case = np.max(final_values)
        worst_case = np.min(final_values)
        best_case_return = (best_case / initial_investment) - 1 if initial_investment > 0 else 0
        worst_case_return = (worst_case / initial_investment) - 1 if initial_investment > 0 else 0
        
        # Calculate total drawdowns over time horizon (if enabled)
        total_drawdowns = 0.0
        if request.enable_drawdown and request.annual_drawdown > 0:
            for year in range(1, time_horizon + 1):
                yearly_drawdown = request.annual_drawdown * (1 + request.inflation_rate) ** (year - 1)
                total_drawdowns += yearly_drawdown
        
        statistics = {
            # Percentile values
            "final_value_5th_percentile": float(percentile_5),
            "final_value_10th_percentile": float(percentile_10),
            "final_value_25th_percentile": float(percentile_25),
            "final_value_median": float(percentile_50),
            "final_value_75th_percentile": float(percentile_75),
            "final_value_90th_percentile": float(percentile_90),
            "final_value_95th_percentile": float(percentile_95),
            
            # Total returns
            "total_return_5th_percentile": float(return_5th),
            "total_return_10th_percentile": float(return_10th),
            "total_return_25th_percentile": float(return_25th),
            "total_return_median": float(return_median),
            "total_return_75th_percentile": float(return_75th),
            "total_return_90th_percentile": float(return_90th),
            "total_return_95th_percentile": float(return_95th),
            
            # Annualized returns
            "annualized_return_5th_percentile": float(annualized_return_5th),
            "annualized_return_median": float(annualized_return_median),
            "annualized_return_90th_percentile": float(annualized_return_90th),
            "mean_annualized_return": float(mean_annualized_return),
            
            # Basic statistics
            "mean_final_value": float(mean_value),
            "mean_total_return": float(mean_return),
            "best_case_value": float(best_case),
            "worst_case_value": float(worst_case),
            "best_case_return": float(best_case_return),
            "worst_case_return": float(worst_case_return),
            
            # Risk metrics
            "volatility": float(volatility),
            "std_final_value": float(std_final_value),
            "probability_of_depletion": float(probability_of_depletion),
            "probability_of_maintaining": float(probability_of_maintaining),
            "probability_of_doubling": float(probability_of_doubling),
            
            # Drawdown analysis
            "total_drawdowns": float(total_drawdowns),
            "drawdown_enabled": request.enable_drawdown,
            "annual_drawdown_start": float(request.annual_drawdown) if request.enable_drawdown else 0.0,
            "inflation_rate": float(request.inflation_rate) if request.enable_drawdown else 0.0,
            
            # Simulation metadata
            "time_horizon_years": time_horizon,
            "initial_investment": initial_investment
        }
        
        return statistics

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
        
        # Log the response data structure
        logger.info("Simulation result structure:", {
            "has_paths": bool(result.simulation_paths),
            "num_paths": len(result.simulation_paths) if result.simulation_paths else 0,
            "first_path_length": len(result.simulation_paths[0]) if result.simulation_paths else 0,
            "has_final_values": bool(result.final_values),
            "num_final_values": len(result.final_values) if result.final_values else 0,
            "has_stats": bool(result.statistics),
            "sample_path": result.simulation_paths[0][:3] if result.simulation_paths else None,
            "sample_stats": {k: v for k, v in list(result.statistics.items())[:5]} if result.statistics else None
        })
        
        # Convert to dict and log the actual response
        response_dict = result.dict()
        logger.info("Response dict structure:", {
            "has_paths": "simulation_paths" in response_dict,
            "num_paths": len(response_dict.get("simulation_paths", [])),
            "has_final_values": "final_values" in response_dict,
            "num_final_values": len(response_dict.get("final_values", [])),
            "has_stats": "statistics" in response_dict
        })
        
        # Store result in memory
        simulation_history.append(response_dict)
        
        return result
    
    except Exception as e:
        logger.error(f"Simulation error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Simulation failed: {str(e)}")

@api_router.get("/simulations", response_model=List[Dict[str, Any]])
async def get_simulation_history():
    """Get history of simulation results"""
    try:
        return list(simulation_history)
    except Exception as e:
        logger.error(f"Error fetching simulation history: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to fetch simulation history")

@api_router.get("/default-assets")
async def get_default_assets():
    """Get default asset classes and simulation parameters"""
    return {
        "asset_classes": default_asset_classes,
        "default_initial_investment": 5000000,
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
