import React, { useState, useEffect } from 'react';
import './App.css';
import axios from 'axios';
import {
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer,
  BarChart,
  Bar
} from 'recharts';

const BACKEND_URL = process.env.REACT_APP_BACKEND_URL;
const API = `${BACKEND_URL}/api`;

const App = () => {
  const [assetClasses, setAssetClasses] = useState([]);
  const [initialInvestment, setInitialInvestment] = useState(5000000);
  const [timeHorizon, setTimeHorizon] = useState(10);
  const [numSimulations, setNumSimulations] = useState(10000);
  const [enableDrawdown, setEnableDrawdown] = useState(false);
  const [annualDrawdown, setAnnualDrawdown] = useState(300000);
  const [inflationRate, setInflationRate] = useState(0.03);
  const [isSimulating, setIsSimulating] = useState(false);
  const [simulationResult, setSimulationResult] = useState(null);
  const [error, setError] = useState(null);

  // Load default asset classes on component mount
  useEffect(() => {
    loadDefaultAssets();
  }, []);

  const loadDefaultAssets = async () => {
    try {
      const response = await axios.get(`${API}/default-assets`);
      setAssetClasses(response.data.asset_classes);
    } catch (e) {
      console.error('Error loading default assets:', e);
      setError('Failed to load default asset classes');
    }
  };

  const updateAssetClass = (index, field, value) => {
    const updated = [...assetClasses];
    updated[index][field] = parseFloat(value) || 0;
    setAssetClasses(updated);
  };

  const formatCurrency = (value) => {
    return new Intl.NumberFormat('en-US', {
      style: 'currency',
      currency: 'USD',
      minimumFractionDigits: 0,
      maximumFractionDigits: 0,
    }).format(value);
  };

  const formatPercentage = (value) => {
    return `${(value * 100).toFixed(1)}%`;
  };

  const runSimulation = async () => {
    setIsSimulating(true);
    setError(null);
    setSimulationResult(null);

    try {
      const request = {
        asset_classes: assetClasses,
        initial_investment: initialInvestment,
        time_horizon: timeHorizon,
        num_simulations: numSimulations
      };

      const response = await axios.post(`${API}/simulate`, request);
      setSimulationResult(response.data);
    } catch (e) {
      console.error('Simulation error:', e);
      setError(e.response?.data?.detail || 'Simulation failed');
    } finally {
      setIsSimulating(false);
    }
  };

  // Prepare chart data for visualization
  const prepareChartData = () => {
    if (!simulationResult) return [];

    const chartData = [];
    const maxPaths = Math.min(100, simulationResult.simulation_paths.length); // Show max 100 paths for performance

    // Create data points for each year
    for (let year = 0; year <= timeHorizon; year++) {
      const dataPoint = { year };
      
      // Add selected simulation paths
      for (let i = 0; i < maxPaths; i++) {
        const path = simulationResult.simulation_paths[i];
        dataPoint[`path_${i}`] = path[year]?.portfolio_value || 0;
      }

      chartData.push(dataPoint);
    }

    return chartData;
  };

  const prepareStatisticsChart = () => {
    if (!simulationResult) return [];

    const stats = simulationResult.statistics;
    return [
      {
        name: '5th Percentile',
        value: stats.final_value_5th_percentile,
        return: stats.total_return_5th_percentile
      },
      {
        name: 'Median',
        value: stats.final_value_median,
        return: stats.total_return_median
      },
      {
        name: '90th Percentile',
        value: stats.final_value_90th_percentile,
        return: stats.total_return_90th_percentile
      }
    ];
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <div className="container mx-auto px-4 py-8">
        <div className="max-w-7xl mx-auto">
          {/* Header */}
          <div className="text-center mb-8">
            <h1 className="text-4xl font-bold text-gray-900 mb-2">
              Investment Portfolio Analyzer
            </h1>
            <p className="text-xl text-gray-600">
              Monte Carlo Simulation for Portfolio Analysis
            </p>
          </div>

          {/* Input Section */}
          <div className="bg-white rounded-lg shadow-lg p-6 mb-8">
            <h2 className="text-2xl font-semibold mb-6 text-gray-800">
              Portfolio Configuration
            </h2>

            {/* Portfolio Parameters */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-8">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Initial Investment
                </label>
                <input
                  type="number"
                  value={initialInvestment}
                  onChange={(e) => setInitialInvestment(parseInt(e.target.value) || 0)}
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="5000000"
                />
                <p className="text-sm text-gray-500 mt-1">
                  {formatCurrency(initialInvestment)}
                </p>
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Time Horizon (Years)
                </label>
                <input
                  type="number"
                  value={timeHorizon}
                  onChange={(e) => setTimeHorizon(parseInt(e.target.value) || 1)}
                  min="1"
                  max="50"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-2">
                  Number of Simulations
                </label>
                <input
                  type="number"
                  value={numSimulations}
                  onChange={(e) => setNumSimulations(parseInt(e.target.value) || 5000)}
                  min="5000"
                  className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500"
                />
              </div>
            </div>

            {/* Asset Classes */}
            <div className="mb-8">
              <h3 className="text-lg font-semibold mb-4 text-gray-800">
                Asset Class Parameters
              </h3>
              <div className="overflow-x-auto">
                <table className="w-full table-auto">
                  <thead>
                    <tr className="bg-gray-100">
                      <th className="px-4 py-2 text-left">Asset Class</th>
                      <th className="px-4 py-2 text-left">Allocation (%)</th>
                      <th className="px-4 py-2 text-left">Median Return (%)</th>
                      <th className="px-4 py-2 text-left">Std Deviation (%)</th>
                      <th className="px-4 py-2 text-left">Min Return (%)</th>
                      <th className="px-4 py-2 text-left">Max Return (%)</th>
                    </tr>
                  </thead>
                  <tbody>
                    {assetClasses.map((asset, index) => (
                      <tr key={index} className="border-t">
                        <td className="px-4 py-2 font-medium">{asset.name}</td>
                        <td className="px-4 py-2">
                          <input
                            type="number"
                            value={asset.allocation * 100}
                            onChange={(e) => updateAssetClass(index, 'allocation', e.target.value / 100)}
                            className="w-20 px-2 py-1 border rounded text-sm"
                            step="0.1"
                          />
                        </td>
                        <td className="px-4 py-2">
                          <input
                            type="number"
                            value={asset.median_return * 100}
                            onChange={(e) => updateAssetClass(index, 'median_return', e.target.value / 100)}
                            className="w-20 px-2 py-1 border rounded text-sm"
                            step="0.1"
                          />
                        </td>
                        <td className="px-4 py-2">
                          <input
                            type="number"
                            value={asset.std_deviation * 100}
                            onChange={(e) => updateAssetClass(index, 'std_deviation', e.target.value / 100)}
                            className="w-20 px-2 py-1 border rounded text-sm"
                            step="0.1"
                          />
                        </td>
                        <td className="px-4 py-2">
                          <input
                            type="number"
                            value={asset.min_return * 100}
                            onChange={(e) => updateAssetClass(index, 'min_return', e.target.value / 100)}
                            className="w-20 px-2 py-1 border rounded text-sm"
                            step="0.1"
                          />
                        </td>
                        <td className="px-4 py-2">
                          <input
                            type="number"
                            value={asset.max_return * 100}
                            onChange={(e) => updateAssetClass(index, 'max_return', e.target.value / 100)}
                            className="w-20 px-2 py-1 border rounded text-sm"
                            step="0.1"
                          />
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>

            {/* Run Simulation Button */}
            <div className="text-center">
              <button
                onClick={runSimulation}
                disabled={isSimulating}
                className="bg-blue-600 hover:bg-blue-700 disabled:bg-gray-400 text-white font-bold py-3 px-8 rounded-lg text-lg transition-colors duration-200"
              >
                {isSimulating ? 'Running Simulation...' : 'Run Monte Carlo Simulation'}
              </button>
            </div>
          </div>

          {/* Error Display */}
          {error && (
            <div className="bg-red-100 border-l-4 border-red-500 text-red-700 p-4 mb-8 rounded">
              <p className="font-bold">Error</p>
              <p>{error}</p>
            </div>
          )}

          {/* Results Section */}
          {simulationResult && (
            <div className="space-y-8">
              {/* Summary Statistics Header */}
              <div className="bg-white rounded-lg shadow-lg p-6">
                <h2 className="text-2xl font-semibold mb-6 text-gray-800">
                  Monte Carlo Simulation Summary
                </h2>
                
                {/* Key Metrics Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-6">
                  <div className="bg-blue-50 p-4 rounded-lg">
                    <h3 className="font-semibold text-blue-800 mb-1">Simulations Run</h3>
                    <p className="text-2xl font-bold text-blue-600">
                      {simulationResult.parameters.num_simulations.toLocaleString()}
                    </p>
                    <p className="text-sm text-blue-600">
                      Time Horizon: {simulationResult.parameters.time_horizon} years
                    </p>
                  </div>
                  
                  <div className="bg-green-50 p-4 rounded-lg">
                    <h3 className="font-semibold text-green-800 mb-1">Mean Return</h3>
                    <p className="text-2xl font-bold text-green-600">
                      {formatPercentage(simulationResult.statistics.mean_annualized_return)} / year
                    </p>
                    <p className="text-sm text-green-600">
                      Total: {formatPercentage(simulationResult.statistics.mean_total_return)}
                    </p>
                  </div>
                  
                  <div className="bg-purple-50 p-4 rounded-lg">
                    <h3 className="font-semibold text-purple-800 mb-1">Expected Value</h3>
                    <p className="text-2xl font-bold text-purple-600">
                      {formatCurrency(simulationResult.statistics.mean_final_value)}
                    </p>
                    <p className="text-sm text-purple-600">
                      Growth: {formatCurrency(simulationResult.statistics.mean_final_value - initialInvestment)}
                    </p>
                  </div>
                  
                  <div className="bg-orange-50 p-4 rounded-lg">
                    <h3 className="font-semibold text-orange-800 mb-1">Risk Level</h3>
                    <p className="text-2xl font-bold text-orange-600">
                      {formatPercentage(simulationResult.statistics.volatility)}
                    </p>
                    <p className="text-sm text-orange-600">
                      Volatility (CV)
                    </p>
                  </div>
                </div>

                {/* Detailed Statistics */}
                <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
                  {/* Return Distribution */}
                  <div>
                    <h3 className="text-lg font-semibold mb-4 text-gray-800">Return Distribution</h3>
                    <div className="space-y-3">
                      <div className="flex justify-between items-center p-3 bg-red-50 rounded">
                        <span className="font-medium text-red-800">5th Percentile (Worst 5%)</span>
                        <div className="text-right">
                          <div className="font-bold text-red-600">
                            {formatPercentage(simulationResult.statistics.annualized_return_5th_percentile)}/yr
                          </div>
                          <div className="text-sm text-red-600">
                            {formatCurrency(simulationResult.statistics.final_value_5th_percentile)}
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex justify-between items-center p-3 bg-yellow-50 rounded">
                        <span className="font-medium text-yellow-800">25th Percentile</span>
                        <div className="text-right">
                          <div className="font-bold text-yellow-600">
                            {formatPercentage(simulationResult.statistics.total_return_25th_percentile)} total
                          </div>
                          <div className="text-sm text-yellow-600">
                            {formatCurrency(simulationResult.statistics.final_value_25th_percentile)}
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex justify-between items-center p-3 bg-blue-50 rounded">
                        <span className="font-medium text-blue-800">Median (50th Percentile)</span>
                        <div className="text-right">
                          <div className="font-bold text-blue-600">
                            {formatPercentage(simulationResult.statistics.annualized_return_median)}/yr
                          </div>
                          <div className="text-sm text-blue-600">
                            {formatCurrency(simulationResult.statistics.final_value_median)}
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex justify-between items-center p-3 bg-green-50 rounded">
                        <span className="font-medium text-green-800">75th Percentile</span>
                        <div className="text-right">
                          <div className="font-bold text-green-600">
                            {formatPercentage(simulationResult.statistics.total_return_75th_percentile)} total
                          </div>
                          <div className="text-sm text-green-600">
                            {formatCurrency(simulationResult.statistics.final_value_75th_percentile)}
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex justify-between items-center p-3 bg-emerald-50 rounded">
                        <span className="font-medium text-emerald-800">90th Percentile (Best 10%)</span>
                        <div className="text-right">
                          <div className="font-bold text-emerald-600">
                            {formatPercentage(simulationResult.statistics.annualized_return_90th_percentile)}/yr
                          </div>
                          <div className="text-sm text-emerald-600">
                            {formatCurrency(simulationResult.statistics.final_value_90th_percentile)}
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>

                  {/* Risk Metrics */}
                  <div>
                    <h3 className="text-lg font-semibold mb-4 text-gray-800">Risk Analysis</h3>
                    <div className="space-y-3">
                      <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                        <span className="font-medium text-gray-800">Probability of Loss</span>
                        <div className="font-bold text-red-600">
                          {formatPercentage(simulationResult.statistics.probability_of_loss)}
                        </div>
                      </div>
                      
                      <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                        <span className="font-medium text-gray-800">Probability of Doubling</span>
                        <div className="font-bold text-green-600">
                          {formatPercentage(simulationResult.statistics.probability_of_doubling)}
                        </div>
                      </div>
                      
                      <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                        <span className="font-medium text-gray-800">Best Case Scenario</span>
                        <div className="text-right">
                          <div className="font-bold text-green-600">
                            {formatCurrency(simulationResult.statistics.best_case_value)}
                          </div>
                          <div className="text-sm text-green-600">
                            {formatPercentage(simulationResult.statistics.best_case_return)} return
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                        <span className="font-medium text-gray-800">Worst Case Scenario</span>
                        <div className="text-right">
                          <div className="font-bold text-red-600">
                            {formatCurrency(simulationResult.statistics.worst_case_value)}
                          </div>
                          <div className="text-sm text-red-600">
                            {formatPercentage(simulationResult.statistics.worst_case_return)} return
                          </div>
                        </div>
                      </div>
                      
                      <div className="flex justify-between items-center p-3 bg-gray-50 rounded">
                        <span className="font-medium text-gray-800">Standard Deviation</span>
                        <div className="font-bold text-gray-600">
                          {formatCurrency(simulationResult.statistics.std_final_value)}
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              {/* Quick Summary Cards */}
              <div className="bg-white rounded-lg shadow-lg p-6">
                <h2 className="text-2xl font-semibold mb-6 text-gray-800">
                  Key Outcomes Summary
                </h2>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
                  <div className="bg-red-50 p-4 rounded-lg">
                    <h3 className="font-semibold text-red-800 mb-2">5th Percentile (Worst Case)</h3>
                    <p className="text-2xl font-bold text-red-600">
                      {formatCurrency(simulationResult.statistics.final_value_5th_percentile)}
                    </p>
                    <p className="text-sm text-red-600">
                      Total Return: {formatPercentage(simulationResult.statistics.total_return_5th_percentile)}
                    </p>
                  </div>
                  <div className="bg-blue-50 p-4 rounded-lg">
                    <h3 className="font-semibold text-blue-800 mb-2">Median (Expected)</h3>
                    <p className="text-2xl font-bold text-blue-600">
                      {formatCurrency(simulationResult.statistics.final_value_median)}
                    </p>
                    <p className="text-sm text-blue-600">
                      Total Return: {formatPercentage(simulationResult.statistics.total_return_median)}
                    </p>
                  </div>
                  <div className="bg-green-50 p-4 rounded-lg">
                    <h3 className="font-semibold text-green-800 mb-2">90th Percentile (Best Case)</h3>
                    <p className="text-2xl font-bold text-green-600">
                      {formatCurrency(simulationResult.statistics.final_value_90th_percentile)}
                    </p>
                    <p className="text-sm text-green-600">
                      Total Return: {formatPercentage(simulationResult.statistics.total_return_90th_percentile)}
                    </p>
                  </div>
                </div>
              </div>

              {/* Portfolio Value Over Time Chart */}
              <div className="bg-white rounded-lg shadow-lg p-6">
                <h2 className="text-2xl font-semibold mb-6 text-gray-800">
                  Portfolio Value Simulation Paths
                </h2>
                <div className="h-96">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={prepareChartData()}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis 
                        dataKey="year" 
                        label={{ value: 'Years', position: 'insideBottom', offset: -10 }}
                      />
                      <YAxis 
                        tickFormatter={(value) => `$${(value / 1000000).toFixed(1)}M`}
                        label={{ value: 'Portfolio Value', angle: -90, position: 'insideLeft' }}
                      />
                      <Tooltip 
                        formatter={(value) => [formatCurrency(value), 'Portfolio Value']}
                        labelFormatter={(label) => `Year ${label}`}
                      />
                      {/* Render multiple simulation paths */}
                      {Array.from({ length: Math.min(20, simulationResult.simulation_paths.length) }, (_, i) => (
                        <Line
                          key={`path_${i}`}
                          type="monotone"
                          dataKey={`path_${i}`}
                          stroke={`hsl(${i * 15}, 70%, 50%)`}
                          strokeWidth={1}
                          dot={false}
                          strokeOpacity={0.3}
                        />
                      ))}
                    </LineChart>
                  </ResponsiveContainer>
                </div>
                <p className="text-sm text-gray-600 mt-2">
                  Showing 20 sample simulation paths out of {simulationResult.simulation_paths.length} total simulations
                </p>
              </div>

              {/* Outcome Distribution */}
              <div className="bg-white rounded-lg shadow-lg p-6">
                <h2 className="text-2xl font-semibold mb-6 text-gray-800">
                  Outcome Distribution
                </h2>
                <div className="h-80">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={prepareStatisticsChart()}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis tickFormatter={(value) => `$${(value / 1000000).toFixed(1)}M`} />
                      <Tooltip 
                        formatter={(value) => [formatCurrency(value), 'Final Value']}
                      />
                      <Bar dataKey="value" fill="#3B82F6" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default App;