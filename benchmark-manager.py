import subprocess
import os
import re
from datetime import datetime
from types import NoneType

## TODO:
## - CLI args for core count to make the script processor-agnostic

# Must be sudo for perf stat to work properly
if os.geteuid() != 0:
    print("Aborted: This script must be run as sudo.")
    exit(1)


PID = os.getpid()  # process id of this script, the pid is used to dynamically reschedule the script onto cores other than the one being profiled
RUNS = 10  # how many times to run each benchmark
now = datetime.now()

benchmarks = [{"name": "loop/1000000", "cmd": "awk 'BEGIN{for(i=0;i<1000000;i++){}}'"}, {"name": "ls", "cmd": "ls empty"}]

# M1 has 8 cores
cpus = [0, 1, 2, 3, 4, 5, 6, 7]

perf_cmd = "perf stat --all-user -C {} -e cycles,instructions -r {} "
taskset_cmd = "taskset --cpu-list {} "
with open("benchmark_results_{}.csv".format(now.strftime("%Y-%m-%d_%H:%M:%S")), "a") as output_file:

    # csv column names
    output_file.write("benchmark_name,benchmark_cmd,target_cpu,RUNS,n_cycles,cycles_variance_percent,n_instr,ipc,instructions_variance_percent,mean_time,time_variance,time_variance_percent\n")

    for benchmark in benchmarks:
        for target_cpu in cpus:

            # Assembly benchmar command
            cmd = taskset_cmd.format(target_cpu) + perf_cmd.format(target_cpu, RUNS) + benchmark["cmd"]

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

            # Remove blank lines
            lines = [x for x in lines if x != ""]

            # Get cycle data
            print(lines[1])
            regex_pattern_cycle = " *([0-9,]+) *cycles *\( +\+\- +([0-9\.\%]*) +\)"
            line_cycle_match = re.match(regex_pattern_cycle, lines[1])
            if line_cycle_match == None:
                print("Regex failed: exting")
                print(lines[1])
                print(regex_pattern_cycle)
                print(cmd_output)
                exit(1)

            n_cycles = line_cycle_match.group(1).replace(",", "")  # mean over all runs, remove commas to avoid corrupting .csv
            cycles_variance_percent = line_cycle_match.group(2)

            # Get instructions data
            line_instructons_match = re.match(" *([0-9,]+) *instructions[\ \#]* *([0-9\.]*)  insn per cycle *\( \+\-  ([0-9\.\%]*) \)", lines[2])
            n_instr = line_instructons_match.group(1).replace(",", "")  # mean over all runs
            ipc = line_instructons_match.group(2)
            instructions_variance_percent = line_instructons_match.group(3)

            # Get time data
            line_time_match = re.match(" *([0-9\.]*) \+\- ([0-9\.]*) seconds time elapsed +\( \+\- +([0-9\.\%]*) \)", lines[3])
            mean_time = line_time_match.group(1)
            time_variance = line_time_match.group(2)
            time_variance_percent = line_time_match.group(3)

            output_str = "{},{},{},{},{},{},{},{},{},{},{},{}\n".format(
                benchmark["name"], benchmark["cmd"], target_cpu, RUNS, n_cycles, cycles_variance_percent, n_instr, ipc, instructions_variance_percent, mean_time, time_variance, time_variance_percent
            )

            output_file.write(output_str)

    output_file.close()
