import subprocess
import os
import json
import sys
from datetime import datetime

WRITE_COLUMN_HEADERS = True

# Must be sudo for perf stat to work properly
if os.geteuid() != 0:
    print("Aborted: This script must be run as sudo.")
    exit(1)

config_file = open(sys.argv[1])
config = json.load(config_file)

wd = os.getcwd() # get starting working directory to change back to if any benchmarks requre being run from a different dir

PID = os.getpid()  # process id of this script, the pid is used to dynamically reschedule the script onto cores other than the one being profiled
RUNS = 10  # how many times to run each benchmark
now = datetime.now()

# import config
benchmarks = config["benchmarks"]
cpus = config["cores"]

events = ["cycles", "instructions"]
events_str = ",".join(events)
perf_cmd = "perf stat -x, --all-user -C {} -e {} -r {} "
taskset_cmd = "taskset --cpu-list {} "
with open("benchmark_results_{}.csv".format(now.strftime("%Y-%m-%d_%H:%M:%S")), "a") as output_file:

    # write csv column headers
    # Add scripts details then fields from https://man7.org/linux/man-pages/man1/perf-stat.1.html#CSV_FORMAT
    if WRITE_COLUMN_HEADERS:
        output_file.write(
            "benchmark_name,benchmark_cmd,target_cpu,runs,counter_value,counter_value_unit,event_name,variance_between_runs,run_time_of_counter,percentage_of_time_counter_was_running,metric_value,unit_of_metric\n"
        )

    for benchmark in benchmarks:
        for target_cpu in cpus:
            
            changed_directory = False

            try:
                run_from_dir = benchmark["run_from"]  ## will give KeyError exception if run_from is not a valid json key for this benchmark
                os.chdir(run_from_dir)
                changed_directory = True
                print("Changed directory to: {}".format(run_from_dir))
            except KeyError:  ## If there was no "run_from" field in the json, dont do anything
                pass


            # Assembly benchmar command
            cmd = taskset_cmd.format(target_cpu) + perf_cmd.format(target_cpu, events_str, RUNS) + benchmark["cmd"]

            # UNSURE IF NECESSARY: Schedule *this python script* to run on different core(s) to the one being profiled:
            # Masks:  0x00000001 is cpu 1, 0x00000003 is cpu(s) 1,3... etc
            # So running this python script on cores ¬(2^target_cpu) schedules it on all cores except the profiler target core
            cpu_affinity_mask = ~pow(2, target_cpu) & 0xFFFFFFFF  # logical and to prevent a weird python types querk returing something lie "-0x02"
            cpu_affinity_mask_string = "{0:#0{1}x}".format(cpu_affinity_mask, 10)
            subprocess.call("taskset -p {} {} ".format(cpu_affinity_mask_string, PID), shell=True)
            print("Benchmark manager scheduled with cpu mask: {}".format(hex(cpu_affinity_mask)))

            # Run the benchmark and decode perf's output into utf-8 for parsing
            print("Running: " + cmd)
            cmd_output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode("utf-8")

            # Parse and format data
            lines = cmd_output.splitlines()

            # Perf output will be the final n lines of stdout (benchmark might print stuff), where n is the number of events
            lines = lines[-len(events) :]

            # Put current benchmark and target cpu into the csv output from perf
            lines = ["{},{},{},{},".format(benchmark["name"], benchmark["cmd"], target_cpu, RUNS) + x for x in lines]

            for line in lines:
                output_file.write(line + "\n")

            if changed_directory:
                os.chdir(wd)

    output_file.close()
    config_file.close()
