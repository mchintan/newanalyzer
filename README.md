# Investment Portfolio Analyzer

A Monte Carlo simulation tool for analyzing investment portfolio performance, built with React and FastAPI.

## Features

- Monte Carlo simulation for portfolio analysis
- Multiple asset class support with customizable parameters
- Tax-aware withdrawal modeling
- Interactive charts and statistics
- In-memory storage for simulation history

## Prerequisites

- Python 3.8+ for backend
- Node.js 16+ and Yarn/npm for frontend
- Git for version control

## Project Structure

```
.
├── backend/               # FastAPI backend
│   ├── requirements.txt   # Python dependencies
│   └── server.py         # Main server code
├── frontend/             # React frontend
│   ├── package.json      # Node.js dependencies
│   └── src/             # React source code
└── tests/               # Test files
```

## Setup Instructions

### Backend Setup

1. Create and activate a Python virtual environment:
   ```bash
   cd backend
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. Install Python dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Start the backend server:
   ```bash
   uvicorn server:app --reload --host 0.0.0.0 --port <port_no>
   ```
   The backend will be available at http://<hostname>:<backend_port>

### Frontend Setup

1. Install Node.js dependencies:
   ```bash
   cd frontend
   yarn install  # or npm install
   ```

2. Start the development server:
   ```bash
   yarn start    # or npm start
   ```
   The frontend will be available at http://<hostname>:<frontend_port>

## Running the Application

1. Ensure both backend and frontend servers are running:
   - Backend: http://<hostname>:<backend_port>
   - Frontend: http://<hostname>:<frontend_port>

2. Open http://localhost:3000 in your browser

3. Configure your portfolio:
   - Set initial investment amount
   - Adjust asset class allocations
   - Configure tax settings
   - Enable/disable withdrawals as needed

4. Click "Run Monte Carlo Simulation" to analyze your portfolio

## Development

- Backend API documentation is available at http://<hostname>:<backend_port>/docs
- Frontend code is in the `frontend/src` directory
- Backend code is in the `backend` directory

## Testing

Run backend tests:
```bash
cd backend
pytest
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.
