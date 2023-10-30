import jesse.helpers as jh
import numpy as np
import datetime
import math


def get_candle_start_date(start_date, timeframe, num_candles_to_fetch):
    one_min_count = jh.timeframe_to_one_minutes(timeframe)
    start_date = jh.date_to_timestamp(start_date)

    result_timestamp = start_date - (num_candles_to_fetch * one_min_count * 60_000)
    date = datetime.datetime.utcfromtimestamp(result_timestamp / 1000)

    return date.strftime("%Y-%m-%d")


def generate_range_from_hyperparameter(hp):
    min_of_range = hp['min']
    max_of_range = hp['max']
    param_type = hp['type']

    result = dict()

    if param_type == float:
        step = hp['step'] if 'step' in hp else 0.1
        samples = round((max_of_range - min_of_range) / step) + 1
        result[hp['name']] = list(np.linspace(min_of_range, max_of_range, num=samples))
    elif param_type == int:
        result[hp['name']] = list(range(min_of_range, max_of_range + 1))

    return result


def generate_permutations(hp):
    result = [{}]

    for key, value in hp.items():
        if isinstance(value, list):
            result = [{**d, key: v} for d in result for v in value]
        else:
            result = [{**d, key: value} for d in result]

    return result


def format_duration(seconds):
    if not seconds or math.isnan(seconds):
        return '–'

    hours = int(seconds // 3600)
    seconds %= 3600

    minutes = int(seconds // 60)
    seconds %= 60

    return f"{hours}h {minutes}m {seconds:.2f}s"
