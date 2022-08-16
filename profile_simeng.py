import subprocess
import os
import json
import argparse
import re
from datetime import datetime

now = datetime.now()

argparser = argparse.ArgumentParser(description="Perf tool SimEng profiler arguments",
                                 formatter_class=argparse.ArgumentDefaultsHelpFormatter)

argparser.add_argument("profiler_config", help="Path to profiler config - must be absolute")
argparser.add_argument("simeng_binary", help="Path to simeng binary - must be absolute")
argparser.add_argument("simeng_config", help="Path to simeng config - must be absolute")
argparser.add_argument("--disable-column-headers", dest="disableColumnHeaders", action="store_true", help="Output CSV without headers/titles to the columns")
argparser.add_argument("--output-file-name", dest="outputFileName", type=str, help="Name of output file")
argparser.add_argument("--print-simeng-output",dest="printSimengOutput",action="store_true", help="Print stdout from simeng")

args = argparser.parse_args()

WRITE_COLUMN_HEADERS = not(args.disableColumnHeaders)
OUTPUT_FILE_NAME = "simeng_benchmark_results_{}.csv".format(now.strftime("%Y-%m-%d_%H:%M:%S"))

if(args.outputFileName):
    OUTPUT_FILE_NAME = args.outputFileName

config_file = open(args.profiler_config)
config = json.load(config_file)
benchmarks = config["benchmarks"]

simeng_cmd = "{} {} ".format(args.simeng_binary, args.simeng_config)

with open(OUTPUT_FILE_NAME, "a") as output_file:

    if WRITE_COLUMN_HEADERS:
        output_file.write("branch.executed,branch.mispredict,branch.missrate,cycles,decode.earlyFlushes,dispatch.rsStalls,fetch.branchStalls,flushes,ipc,issue.backendStalls,issue.frontendStalls,issue.portBusyStalls,lsq.loadViolations,rename.allocationStalls,rename.lqStalls,rename.robStalls,rename.sqStalls,retired\n")

    for benchmark in benchmarks:
        changed_directory = False

        try:
            run_from_dir = benchmark["run_from"]  ## will give KeyError exception if run_from is not a valid json key for this benchmark
            os.chdir(run_from_dir)
            changed_directory = True
            print("Changed directory to: {}".format(run_from_dir))
        except KeyError:  ## If there was no "run_from" field in the json, dont do anything
            pass

        cmd = simeng_cmd + benchmark["cmd"]
        cmd_output = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT).decode("utf-8")

        if(args.printSimengOutput):
            print(cmd_output)

        lines = cmd_output.splitlines()
        
        # Final 20 lines are the performance output, minus two lines of simeng performance stats
        performance_output = lines[-20:-2]
        
        output_line = ""
        for line in performance_output:
            output_line += "," + re.sub(r'[a-zA-Z]*\.*[a-zA-Z]+: ', '',line)
        
        output_line += "\n";

        output_file.write(output_line)

        print(">>>Finished Benchmark\n")
        # branch.executed: 2388270
        # branch.mispredict: 354600
        # branch.missrate: 14.8%
        # cycles: 21192293
        # decode.earlyFlushes: 299358
        # dispatch.rsStalls: 0
        # fetch.branchStalls: 0
        # flushes: 637571
        # ipc: 0.72
        # issue.backendStalls: 2517879
        # issue.frontendStalls: 1079298
        # issue.portBusyStalls: 290
        # lsq.loadViolations: 4037
        # rename.allocationStalls: 16852
        # rename.lqStalls: 0
        # rename.robStalls: 0
        # rename.sqStalls: 0
        # retired: 15246285

        # Finished 21192293 ticks in 480029ms (44 kHz, 0.032 MIPS)

