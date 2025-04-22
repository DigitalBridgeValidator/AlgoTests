# Jesse Algorithmic Trading Platform

This project is a customized Jesse algorithmic trading platform setup with built-in brute-force backtesting capabilities. 

## Project Overview

The platform includes:
- Docker-based environment for both x86 and ARM (Apple Silicon) architectures
- Brute-force testing module for strategy optimization
- Sample trading strategies
- Dashboard interface for monitoring and analysis

## Setup Instructions

### 1. Docker Environment

#### For Apple Silicon (M1/M2/M3) Mac users:

```sh
# Start the environment
docker compose -f docker/docker-compose.yml --env-file docker/.env up -d
```

#### For Intel/AMD users:
Edit the `docker/.env` file first:
```
# Redis and Postgres platforms
# For Apple Silicon (M1/M2/M3):
# DB_PLATFORM=linux/arm64/v8
# For Intel/AMD:
DB_PLATFORM=linux/amd64
```

Then run:
```sh
docker compose -f docker/docker-compose.yml --env-file docker/.env up -d
```

### 2. Local Development Setup

For local development without Docker:

```sh
# Start local development database services
docker compose -f docker-compose.dev.yml up -d

# Run Jesse from your local Python environment
jesse run
```

## Running Strategies

### Backtesting with Brute Force

The brute-force script tests multiple parameter combinations to find optimal settings:

1. Configure the strategy in `.env`:

```
BF_STRATEGY=SimpleTestStrategy  # Name of the strategy to test
BF_EXCHANGE=Bybit USDT Perpetual
BF_SYMBOL=BTC-USDT
BF_TIMEFRAME=4h
BF_WARMUP_CANDLES=100
BF_START_DATE=2023-01-01
BF_FINISH_DATE=2023-06-01
BF_STARTING_BALANCE=10000
BF_FEE=0.00075
BF_TYPE=futures
BF_FUTURES_LEVERAGE=4
BF_FUTURES_LEVERAGE_MODE=cross
BF_BACKTEST_FAST_MODE=on
```

2. Run the brute force script:

```sh
python brute-force.py
```

3. View results in `/storage/brute-force/` as CSV files.

### Running the Dashboard

To use the Jesse dashboard:

```sh
jesse run
```

The dashboard will be available at [http://localhost:9000](http://localhost:9000)

## Creating a New Strategy

To add a new strategy to the project:

1. Create a new directory under `/strategies/YourStrategyName/`:

```sh
mkdir -p strategies/YourStrategyName
```

2. Create an `__init__.py` file with your strategy:

```python
from jesse.strategies import Strategy
import jesse.indicators as ta
from jesse import utils


class YourStrategyName(Strategy):
    def hyperparameters(self):
        return [
            {'name': 'param1', 'type': int, 'min': 5, 'max': 20, 'default': 10},
            {'name': 'param2', 'type': float, 'min': 0.1, 'max': 0.9, 'default': 0.5},
        ]
        
    def should_long(self):
        # Your long entry logic here
        return False
        
    def should_short(self):
        # Your short entry logic here (or return False if not using shorts)
        return False
        
    def should_cancel_entry(self):
        # Logic for when to cancel pending entries
        return False
        
    def go_long(self):
        # Logic for entering a long position
        # Example:
        entry = self.price
        stop = entry * 0.95  # 5% below entry
        qty = self.position_size_percent(1, entry, stop)  # Risk 1%
        
        self.buy = qty, self.price
        self.stop_loss = qty, stop
        self.take_profit = qty, entry * 1.15  # 15% profit target
        
    def go_short(self):
        # Logic for entering a short position
        pass
        
    def update_position(self):
        # Logic to update an open position (e.g., trailing stop)
        pass
        
    def position_size_percent(self, risk_percentage, entry_price, stop_price):
        """Calculate position size based on risk percentage"""
        capital_at_risk = self.balance * (risk_percentage / 100)
        risk_per_unit = abs(entry_price - stop_price)
        return 0 if risk_per_unit == 0 else capital_at_risk / risk_per_unit
```

3. Update your `.env` file to use the new strategy:

```
BF_STRATEGY=YourStrategyName
```

4. Run a backtest or brute force optimization:

```sh
python brute-force.py
# or for a regular backtest in the dashboard
jesse run
```

## Available Strategies

The project includes several sample strategies:

1. **SimpleTestStrategy**: A basic strategy that enters trades at regular intervals.
2. **TradingViewRSI**: A strategy based on the RSI indicator.
3. **ResistanceLevelStrategy**: A strategy that identifies and trades resistance levels.

## Troubleshooting

- If you encounter connection issues with the database, ensure the Docker containers are running:
  ```
  docker ps
  ```

- For port conflicts, modify the exposed ports in the docker-compose files.

- Check the logs if a container fails to start:
  ```
  docker logs jesse
  docker logs postgres
  docker logs redis
  ```