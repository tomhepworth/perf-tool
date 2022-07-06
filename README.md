# Automated Perf Profiling Tool

Tests a list of benchmarks on a single core at a time using taskset and perf. Parses results and writes them to a CSV

Aimed towards the Apple M1 which can currently only count cycles and instructions with perf. Edit the events list and config for other processors. In both graph.py and b, CSV headers may need adjusting depending on your perf command, see https://man7.org/linux/man-pages/man1/perf-stat.1.html#CSV_FORMAT
