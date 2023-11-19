import jesse.helpers as jh
from jesse.research import backtest, get_candles
from collections import ChainMap
import csv
import logging
import multiprocessing
import datetime
from jesse.services.env import ENV_VALUES
import utils
import os
import atexit

now = datetime.datetime.now()
directory = './storage/brute-force/'
strategy_name = ENV_VALUES['BF_STRATEGY']
filename = strategy_name + now.strftime("_%Y-%m-%d__%H-%M.csv")
exchange_name = ENV_VALUES['BF_EXCHANGE']
symbol = ENV_VALUES['BF_SYMBOL']
timeframe = ENV_VALUES['BF_TIMEFRAME']
warmup_candles_num = int(ENV_VALUES['BF_WARMUP_CANDLES'])
start_date = ENV_VALUES['BF_START_DATE']
finish_date = ENV_VALUES['BF_FINISH_DATE']
starting_balance = ENV_VALUES['BF_STARTING_BALANCE']
fee = ENV_VALUES['BF_FEE']
type = ENV_VALUES['BF_TYPE']
futures_leverage = ENV_VALUES['BF_FUTURES_LEVERAGE']
futures_leverage_mode = ENV_VALUES['BF_FUTURES_LEVERAGE_MODE']

os.makedirs(directory, exist_ok=True)

StrategyClass = jh.get_strategy_class(strategy_name)
strategy_hyperparameters = StrategyClass().hyperparameters()

config = {
    'starting_balance': starting_balance,
    'fee': fee,
    'type': type,
    'futures_leverage': futures_leverage,
    'futures_leverage_mode': futures_leverage_mode,
    'exchange': exchange_name,
    'warm_up_candles': warmup_candles_num
}

routes = [
    {'exchange': exchange_name, 'strategy': StrategyClass, 'symbol': symbol, 'timeframe': timeframe}
]

extra_routes = []

start_date = utils.get_candle_start_date(start_date, timeframe, warmup_candles_num)

candles_import = get_candles(exchange_name, symbol, '1m', start_date=start_date, finish_date=finish_date)

candles = {
    jh.key(exchange_name, symbol): {
        'exchange': exchange_name,
        'symbol': symbol,
        'candles': candles_import,
    }
}

ranges = map(utils.generate_range_from_hyperparameter, strategy_hyperparameters)
ranges = dict(ChainMap(*ranges))

permutations = utils.generate_permutations(ranges)

# # # # # # # # # # # # # # #
# Start multiprocessing
# # # # # # # # # # # # # # #
logging.basicConfig(level=logging.INFO)

header_written = multiprocessing.Value('b', False)

completed_counter = multiprocessing.Value('i', 0)
counter_lock = multiprocessing.Lock()


def init_globals(lock, counter, header_flag):
    global csv_lock, completed_counter, counter_lock, header_written

    csv_lock = lock
    completed_counter = counter
    counter_lock = lock  # using the same lock for csv and counter
    header_written = header_flag


def perform_calculation(hyperparameters):
    backtest_output = backtest(
        config,
        routes,
        extra_routes,
        candles,
        hyperparameters=hyperparameters
    )

    save_result_to_csv(hyperparameters, backtest_output)

    with counter_lock:
        completed_counter.value += 1
        print(f"\rProgress: {completed_counter.value} / {len(permutations)}", end='', flush=True)


def save_result_to_csv(hyperparameters, backtest_output):
    global csv_lock, header_written

    hyperparameters_str = ', '.join(f"{key}: {value}" for key, value in hyperparameters.items())
    hyperparameters_str = f'"{hyperparameters_str}"'

    metrics = backtest_output['metrics']

    result = {
        'Total trades': metrics['total'],
        'Total Winning Trades': metrics['total_winning_trades'],
        'Total Losing Trades': metrics['total_losing_trades'],
        'Starting Balance': round(metrics['starting_balance'], 2),
        'Finishing Balance': round(metrics['finishing_balance'], 2),
        'Win Rate': round(metrics['win_rate'], 2),
        'Ratio Avg Win/Loss': round(metrics['ratio_avg_win_loss'], 2),
        'Longs Count': metrics['longs_count'],
        'Longs Percentage': round(metrics['longs_percentage'], 2),
        'Shorts Percentage': round(metrics['shorts_percentage'], 2),
        'Shorts Count': metrics['shorts_count'],
        'Fee': round(metrics['fee'], 2),
        'Net Profit': round(metrics['net_profit'], 2),
        'Net Profit Percentage': round(metrics['net_profit_percentage'], 2),
        'Average Win': round(metrics['average_win'], 2),
        'Average Loss': round(metrics['average_loss'], 2),
        'Expectancy': round(metrics['expectancy'], 2),
        'Expectancy Percentage': round(metrics['expectancy_percentage'], 2),
        'Expected Net Profit Every 100 Trades': round(metrics['expected_net_profit_every_100_trades'], 2),
        'Avg Holding Time (sec)': metrics['average_holding_period'],
        'Avg Holding Time': utils.format_duration(metrics['average_holding_period']),
        'Avg Winning Holding Time (sec)': metrics['average_winning_holding_period'],
        'Avg Winning Holding Time': utils.format_duration(metrics['average_winning_holding_period']),
        'Avg Losing Holding Time (sec)': metrics['average_losing_holding_period'],
        'Avg Losing Holding Time': utils.format_duration(metrics['average_losing_holding_period']),
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

    try:
        csv_lock.acquire()

        with open('./storage/brute-force/' + filename, 'a', newline='') as csv_file:
            csv_writer = csv.writer(csv_file)

            # If the header hasn't been written, write it
            if not header_written.value:
                header = list(result.keys())
                csv_writer.writerow(header)
                header_written.value = True

            # Write the data row
            data_row = [result[key] for key in result.keys()]
            csv_writer.writerow(data_row)

    except Exception as e:
        logging.error(f"An error occurred: {e}")
    finally:
        csv_lock.release()


def exit_handler():
    print('\nDone!')


if __name__ == '__main__':
    num_threads = int(ENV_VALUES['BF_CPU_COUNT']) if ENV_VALUES['BF_CPU_COUNT'] else multiprocessing.cpu_count()
    lock = multiprocessing.Lock()

    with open('./storage/brute-force/' + filename, 'w', newline='') as initial_csv_file:
        pass

    print(f'Strategy: {strategy_name}, {timeframe}, {symbol}')
    print(f'Number of threads: {num_threads}')

    # Print initial progress
    print(f"Progress: 0 / {len(permutations)}", end='', flush=True)

    with multiprocessing.Pool(num_threads, initializer=init_globals, initargs=(lock, completed_counter, header_written)) as pool:
        for _ in pool.imap_unordered(perform_calculation, permutations):
            pass

    atexit.register(exit_handler)
