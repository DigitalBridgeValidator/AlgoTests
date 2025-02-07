from jesse.services.env import ENV_VALUES
from jesse.research import backtest
import multiprocessing
import logging
import atexit
import utils
import csv
import os

filename = utils.generate_file_name()
directory = './storage/brute-force/'

os.makedirs(directory, exist_ok=True)

config = utils.get_backtest_config()
routes = utils.get_backtest_routes()
warmup_candles, trading_candles = utils.get_backtest_candles()
permutations = utils.generate_permutations()

logging.basicConfig(level=logging.ERROR)

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
        [],
        trading_candles,
        warmup_candles,
        hyperparameters=hyperparameters,
        fast_mode=ENV_VALUES['BF_BACKTEST_FAST_MODE'] in ("1", "true", "yes", "on")
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

    result = utils.prepare_metrics(metrics, hyperparameters_str)

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
    if completed_counter.value == len(permutations):
        print('\nAll tasks completed successfully!')


if __name__ == '__main__':
    num_threads = int(ENV_VALUES['BF_CPU_COUNT']) if ENV_VALUES['BF_CPU_COUNT'] else multiprocessing.cpu_count()
    lock = multiprocessing.Lock()

    with open('./storage/brute-force/' + filename, 'w', newline='') as initial_csv_file:
        pass

    print(f"Strategy: {ENV_VALUES['BF_EXCHANGE']}, {ENV_VALUES['BF_TIMEFRAME']}, {ENV_VALUES['BF_SYMBOL']}")
    print(f"Number of threads: {num_threads}")

    # Print initial progress
    print(f"Progress: 0 / {len(permutations)}", end='', flush=True)

    try:
        with multiprocessing.Pool(num_threads, initializer=init_globals, initargs=(lock, completed_counter, header_written)) as pool:
            for _ in pool.imap_unordered(perform_calculation, permutations):
                pass
    except KeyboardInterrupt:
        print("\nExecution interrupted by user.")
        pool.terminate()
        pool.join()

    atexit.register(exit_handler)
