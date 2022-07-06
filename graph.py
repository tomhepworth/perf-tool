import sys
import json
import pandas as pd
from matplotlib import pyplot as plt

column_headers = [
    "benchmark_name",
    "benchmark_cmd",
    "target_cpu",
    "runs",
    "counter_value",
    "counter_value_unit",
    "event_name",
    "variance_between_runs",
    "run_time_of_counter",
    "percentage_of_time_counter_was_running",
    "metric_value",
    "unit_of_metric",
]

input_file = sys.argv[1]
csv = pd.read_csv(input_file, usecols=column_headers)
print(csv)

# TODO - DRYifiy this... code is repeated in profile.py
config_file = open("config.json")
config = json.load(config_file)

# import config
benchmarks = config["benchmarks"]
cpus = config["cores"]

for benchmark in benchmarks:
    filter_benchmark = csv.loc[csv["benchmark_name"] == benchmark["name"]]
    filter_cycle_events = filter_benchmark.loc[filter_benchmark["event_name"] == "cycles"]
    filter_instruction_events = filter_benchmark.loc[filter_benchmark["event_name"] == "instructions"]
    print(filter_cycle_events)
    plt.scatter(filter_cycle_events.target_cpu, filter_cycle_events.counter_value)
    plt.show()

config_file.close()
