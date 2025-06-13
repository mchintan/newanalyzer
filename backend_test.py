import requests
import json
import pytest
import numpy as np
from typing import Dict, List, Any

# Get the backend URL from the frontend .env file
BACKEND_URL = "https://3d76c22c-8d94-4987-af80-53a78c2c092d.preview.emergentagent.com"
API_URL = f"{BACKEND_URL}/api"

def test_api_health_check():
    """Test the API health check endpoint"""
    response = requests.get(f"{API_URL}/")
    assert response.status_code == 200
    data = response.json()
    assert "message" in data
    assert data["message"] == "Investment Portfolio Analyzer API"
    print("✅ API health check passed")

def test_default_assets():
    """Test the default assets endpoint"""
    response = requests.get(f"{API_URL}/default-assets")
    assert response.status_code == 200
    data = response.json()
    
    # Verify structure
    assert "asset_classes" in data
    assert "default_initial_investment" in data
    assert "default_time_horizon" in data
    assert "default_num_simulations" in data
    
    # Verify asset classes
    asset_classes = data["asset_classes"]
    assert len(asset_classes) == 4
    
    # Verify asset class names
    asset_names = [asset["name"] for asset in asset_classes]
    expected_names = ["Stocks", "Bonds", "Alternatives", "Private Credit"]
    assert set(asset_names) == set(expected_names)
    
    # Verify allocations sum to 100%
    total_allocation = sum(asset["allocation"] for asset in asset_classes)
    assert abs(total_allocation - 1.0) < 0.001
    
    # Verify default initial investment is $5MM
    assert data["default_initial_investment"] == 5000000
    
    # Verify default time horizon and simulation count
    assert data["default_time_horizon"] > 0
    assert data["default_num_simulations"] >= 5000
    
    print("✅ Default assets endpoint passed")

def test_monte_carlo_simulation():
    """Test the Monte Carlo simulation endpoint with default parameters"""
    # Get default assets
    default_response = requests.get(f"{API_URL}/default-assets")
    assert default_response.status_code == 200
    default_data = default_response.json()
    
    # Prepare simulation request
    simulation_request = {
        "asset_classes": default_data["asset_classes"],
        "initial_investment": default_data["default_initial_investment"],
        "time_horizon": default_data["default_time_horizon"],
        "num_simulations": default_data["default_num_simulations"]
    }
    
    # Run simulation
    response = requests.post(f"{API_URL}/simulate", json=simulation_request)
    assert response.status_code == 200
    result = response.json()
    
    # Verify result structure
    assert "id" in result
    assert "simulation_paths" in result
    assert "final_values" in result
    assert "statistics" in result
    assert "parameters" in result
    
    # Verify simulation paths
    assert len(result["simulation_paths"]) == simulation_request["num_simulations"]
    
    # Check first simulation path
    first_path = result["simulation_paths"][0]
    assert len(first_path) == simulation_request["time_horizon"] + 1  # +1 for initial year
    
    # Verify year progression
    years = [path["year"] for path in first_path]
    assert years == list(range(simulation_request["time_horizon"] + 1))
    
    # Verify initial value
    assert first_path[0]["portfolio_value"] == simulation_request["initial_investment"]
    
    # Verify final values
    assert len(result["final_values"]) == simulation_request["num_simulations"]
    
    # Verify statistics
    stats = result["statistics"]
    required_stats = [
        "final_value_5th_percentile", 
        "final_value_median", 
        "final_value_90th_percentile",
        "total_return_5th_percentile",
        "total_return_median",
        "total_return_90th_percentile"
    ]
    for stat in required_stats:
        assert stat in stats
    
    # Verify percentiles are in correct order
    assert stats["final_value_5th_percentile"] <= stats["final_value_median"]
    assert stats["final_value_median"] <= stats["final_value_90th_percentile"]
    
    print("✅ Monte Carlo simulation endpoint passed")

def test_simulation_with_custom_parameters():
    """Test the Monte Carlo simulation with custom parameters"""
    # Create custom asset allocation
    custom_request = {
        "asset_classes": [
            {
                "name": "Stocks",
                "median_return": 0.10,
                "std_deviation": 0.18,
                "min_return": -0.35,
                "max_return": 0.40,
                "allocation": 0.40
            },
            {
                "name": "Bonds",
                "median_return": 0.03,
                "std_deviation": 0.06,
                "min_return": -0.08,
                "max_return": 0.12,
                "allocation": 0.20
            },
            {
                "name": "Alternatives",
                "median_return": 0.12,
                "std_deviation": 0.22,
                "min_return": -0.25,
                "max_return": 0.45,
                "allocation": 0.25
            },
            {
                "name": "Private Credit",
                "median_return": 0.08,
                "std_deviation": 0.10,
                "min_return": -0.12,
                "max_return": 0.20,
                "allocation": 0.15
            }
        ],
        "initial_investment": 10000000,  # $10MM
        "time_horizon": 20,
        "num_simulations": 5000
    }
    
    # Run simulation
    response = requests.post(f"{API_URL}/simulate", json=custom_request)
    assert response.status_code == 200
    result = response.json()
    
    # Verify time horizon
    first_path = result["simulation_paths"][0]
    assert len(first_path) == custom_request["time_horizon"] + 1
    
    # Verify initial investment
    assert first_path[0]["portfolio_value"] == custom_request["initial_investment"]
    
    # Verify number of simulations
    assert len(result["simulation_paths"]) == custom_request["num_simulations"]
    
    print("✅ Custom parameter simulation passed")

def test_simulation_validation_errors():
    """Test validation errors in the simulation endpoint"""
    # Get default assets for base request
    default_response = requests.get(f"{API_URL}/default-assets")
    assert default_response.status_code == 200
    default_data = default_response.json()
    
    base_request = {
        "asset_classes": default_data["asset_classes"],
        "initial_investment": default_data["default_initial_investment"],
        "time_horizon": default_data["default_time_horizon"],
        "num_simulations": default_data["default_num_simulations"]
    }
    
    # Test 1: Invalid allocation (not summing to 1.0)
    invalid_allocation_request = base_request.copy()
    # We need to create a deep copy of the asset_classes list
    invalid_allocation_request["asset_classes"] = []
    for asset in base_request["asset_classes"]:
        invalid_allocation_request["asset_classes"].append(asset.copy())
    
    # Modify the first asset's allocation
    invalid_allocation_request["asset_classes"][0]["allocation"] = 0.5  # Change from 0.3 to 0.5
    
    # Print the total allocation to verify it's not 1.0
    total = sum(asset["allocation"] for asset in invalid_allocation_request["asset_classes"])
    print(f"Total allocation in test request: {total}")
    
    response = requests.post(f"{API_URL}/simulate", json=invalid_allocation_request)
    print(f"Invalid allocation test response: {response.status_code}")
    print(f"Response body: {response.text}")
    
    # For now, let's just check if we get an error response
    assert response.status_code != 200
    
    # Test 2: Too few simulations
    few_sims_request = base_request.copy()
    few_sims_request["num_simulations"] = 1000  # Below minimum 5,000
    
    response = requests.post(f"{API_URL}/simulate", json=few_sims_request)
    print(f"Few simulations test response: {response.status_code}")
    print(f"Response body: {response.text}")
    assert response.status_code == 400
    assert "Minimum 5,000 simulations required" in response.text
    
    # Test 3: Excessive time horizon
    long_horizon_request = base_request.copy()
    long_horizon_request["time_horizon"] = 60  # Above maximum 50
    
    response = requests.post(f"{API_URL}/simulate", json=long_horizon_request)
    print(f"Long horizon test response: {response.status_code}")
    print(f"Response body: {response.text}")
    assert response.status_code == 400
    assert "Maximum time horizon is 50 years" in response.text
    
    # Test 4: Invalid time horizon (too short)
    short_horizon_request = base_request.copy()
    short_horizon_request["time_horizon"] = 0  # Below minimum 1
    
    response = requests.post(f"{API_URL}/simulate", json=short_horizon_request)
    print(f"Short horizon test response: {response.status_code}")
    print(f"Response body: {response.text}")
    assert response.status_code == 400
    assert "Minimum time horizon is 1 year" in response.text
    
    print("✅ Validation error tests passed")

def test_simulation_history():
    """Test the simulation history endpoint"""
    # First run a simulation to ensure there's history
    default_response = requests.get(f"{API_URL}/default-assets")
    assert default_response.status_code == 200
    default_data = default_response.json()
    
    simulation_request = {
        "asset_classes": default_data["asset_classes"],
        "initial_investment": default_data["default_initial_investment"],
        "time_horizon": default_data["default_time_horizon"],
        "num_simulations": default_data["default_num_simulations"]
    }
    
    # Run simulation
    sim_response = requests.post(f"{API_URL}/simulate", json=simulation_request)
    assert sim_response.status_code == 200
    
    # Now get history
    response = requests.get(f"{API_URL}/simulations")
    assert response.status_code == 200
    history = response.json()
    
    # Verify history structure
    assert isinstance(history, list)
    
    # If history is not empty, check the structure
    if history:
        first_record = history[0]
        assert "_id" in first_record
        assert "parameters" in first_record
        assert "statistics" in first_record
    
    print("✅ Simulation history endpoint passed")

if __name__ == "__main__":
    print("Running Investment Portfolio Analyzer API Tests")
    print("==============================================")
    
    try:
        test_api_health_check()
        test_default_assets()
        test_monte_carlo_simulation()
        test_simulation_with_custom_parameters()
        test_simulation_validation_errors()
        test_simulation_history()
        
        print("\n✅ All tests passed successfully!")
    except Exception as e:
        print(f"\n❌ Test failed: {str(e)}")
        raise
