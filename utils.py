import jesse.helpers as jh
import numpy as np
import math
from jesse.services.env import ENV_VALUES
from datetime import datetime
from jesse.research import get_candles
from collections import ChainMap
from pydoc import locate

def generate_range_from_hyperparameter(hp):
    min_of_range = hp['min']
    max_of_range = hp['max']
    param_type = hp['type']
    default_step = 0.1 if param_type == float else 1
    step = hp.get('step', default_step)

    decimals = len(str(step).split('.')[1]) if '.' in str(step) and param_type == float else 0

    result = dict()

    if param_type == float:
        samples = round((max_of_range - min_of_range) / step) + 1
        range_values = np.linspace(min_of_range, max_of_range, num=samples)
        result[hp['name']] = [round(val, decimals) for val in range_values]
    elif param_type == int:
        result[hp['name']] = list(range(min_of_range, max_of_range + 1, step))

    return result


def format_duration(seconds):
    if not seconds or math.isnan(seconds):
        return '–'

    hours = int(seconds // 3600)
    seconds %= 3600

    minutes = int(seconds // 60)
    seconds %= 60

    return f"{hours}h {minutes}m {seconds:.2f}s"


def get_backtest_config():
    return {
        'starting_balance': ENV_VALUES['BF_STARTING_BALANCE'],
        'fee': ENV_VALUES['BF_FEE'],
        'type': ENV_VALUES['BF_TYPE'],
        'futures_leverage': ENV_VALUES['BF_FUTURES_LEVERAGE'],
        'futures_leverage_mode': ENV_VALUES['BF_FUTURES_LEVERAGE_MODE'],
        'exchange': ENV_VALUES['BF_EXCHANGE'],
        'warm_up_candles': int(ENV_VALUES['BF_WARMUP_CANDLES'])
    }


def get_backtest_candles():
    exchange_name = ENV_VALUES['BF_EXCHANGE']
    symbol = ENV_VALUES['BF_SYMBOL']
    timeframe = ENV_VALUES['BF_TIMEFRAME']
    start_date_str = ENV_VALUES['BF_START_DATE']
    finish_date_str = ENV_VALUES['BF_FINISH_DATE']
    config = get_backtest_config()
    warm_up_candles = config['warm_up_candles']

    warmup_candles, trading_candles = get_candles(
        exchange_name,
        symbol,
        timeframe,
        jh.date_to_timestamp(start_date_str),
        jh.date_to_timestamp(finish_date_str),
        warm_up_candles,
        caching=True,
        is_for_jesse=True
    )

    trading_candles = {
        jh.key(exchange_name, symbol): {
            'exchange': exchange_name,
            'symbol': symbol,
            'candles': trading_candles
        },
    }

    warmup_candles = {
        jh.key(exchange_name, symbol): {
            'exchange': exchange_name,
            'symbol': symbol,
            'candles': warmup_candles
        }
    }

    return warmup_candles, trading_candles


def get_backtest_routes():
    exchange_name = ENV_VALUES['BF_EXCHANGE']
    symbol = ENV_VALUES['BF_SYMBOL']
    timeframe = ENV_VALUES['BF_TIMEFRAME']
    strategy = locate(f'strategies.{ENV_VALUES["BF_STRATEGY"]}.{ENV_VALUES["BF_STRATEGY"]}')

    routes = [
        {'exchange': exchange_name, 'strategy': strategy, 'symbol': symbol, 'timeframe': timeframe}
    ]

    return routes


def prepare_metrics(metrics, hyperparameters_str):
    return {
        'Total trades': metrics['total'],
        'Total Winning Trades': metrics['total_winning_trades'],
        'Total Losing Trades': metrics['total_losing_trades'],
        'Starting Balance': round(metrics['starting_balance'], 2),
        'Finishing Balance': round(metrics['finishing_balance'], 2),
        'Win Rate': round(metrics['win_rate'], 2),
        'Ratio Avg Win/Loss': round(metrics['ratio_avg_win_loss'], 2),
        'Longs Count': metrics['longs_count'],
        'Longs %': round(metrics['longs_percentage'], 2),
        'Shorts %': round(metrics['shorts_percentage'], 2),
        'Shorts Count': metrics['shorts_count'],
        'Fee': round(metrics['fee'], 2),
        'Net Profit': round(metrics['net_profit'], 2),
        'Net Profit %': round(metrics['net_profit_percentage'], 2),
        'Average Win': round(metrics['average_win'], 2),
        'Average Loss': round(metrics['average_loss'], 2),
        'Expectancy': round(metrics['expectancy'], 2),
        'Expectancy %': round(metrics['expectancy_percentage'], 2),
        'Expected Net Profit Every 100 Trades': round(metrics['expected_net_profit_every_100_trades'], 2),
        'Avg Holding Time': format_duration(metrics['average_holding_period']),
        'Avg Winning Holding Time': format_duration(metrics['average_winning_holding_period']),
        'Avg Losing Holding Time': format_duration(metrics['average_losing_holding_period']),
        'Gross Profit': round(metrics['gross_profit'], 2),
        'Gross Loss': round(metrics['gross_loss'], 2),
        'Max Drawdown': round(metrics['max_drawdown'], 2),
        'Annual Return': round(metrics['annual_return'], 2),
        'Sharpe Ratio': round(metrics['sharpe_ratio'], 2),
        'Calmar Ratio': round(metrics['calmar_ratio'], 2),
        'Sortino Ratio': round(metrics['sortino_ratio'], 2),
        'Omega Ratio': round(metrics['omega_ratio'], 2),
        'Serenity Index': round(metrics['serenity_index'], 2),
        'Smart Sharpe': round(metrics['smart_sharpe'], 2),
        'Smart Sortino': round(metrics['smart_sortino'], 2),
        'Total Open Trades': metrics['total_open_trades'],
        'Open PL': round(metrics['open_pl'], 2),
        'Winning Streak': metrics['winning_streak'],
        'Losing Streak': metrics['losing_streak'],
        'Largest Losing Trade': round(metrics['largest_losing_trade'], 2),
        'Largest Winning Trade': round(metrics['largest_winning_trade'], 2),
        'Current Streak': metrics['current_streak'],
        'Hyperparameters': hyperparameters_str
    }


def generate_file_name():
    now = datetime.now()
    return ENV_VALUES['BF_EXCHANGE'] + now.strftime("_%Y-%m-%d__%H-%M.csv")


def get_strategy_hyperparameters():
    strategy = locate(f'strategies.{ENV_VALUES["BF_STRATEGY"]}.{ENV_VALUES["BF_STRATEGY"]}')
    strategy_hyperparameters = strategy().hyperparameters()

    return strategy_hyperparameters


def generate_permutations_old(hp):
    result = [{}]

    for key, value in hp.items():
        if isinstance(value, list):
            result = [{**d, key: v} for d in result for v in value]
        else:
            result = [{**d, key: value} for d in result]

    return result


def generate_permutations():
    strategy_hyperparameters = get_strategy_hyperparameters()

    ranges = map(generate_range_from_hyperparameter, strategy_hyperparameters)
    ranges = dict(ChainMap(*ranges))

    result = [{}]

    for key, value in ranges.items():
        if isinstance(value, list):
            result = [{**d, key: v} for d in result for v in value]
        else:
            result = [{**d, key: value} for d in result]

    return result
