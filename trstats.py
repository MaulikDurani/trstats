#!/usr/bin/env python3

import argparse
import subprocess
from subprocess import PIPE
import json
import os
import numpy as np
import statistics
import re
import matplotlib.pyplot as plt
import seaborn as sns
from time import sleep

# global variables to store data after multiple executions
result_arr = []
just_times = [[] for i in range(1024)]
just_hosts = [[] for i in range(1024)]

# parses through user input
def args_parser():
    parser = argparse.ArgumentParser(description="Run traceroute")
    parser.add_argument('-t', dest='target', metavar='-t', type=str, required=True, help="target")
    parser.add_argument('-o', dest='output', metavar='-o', type=str, required=False, help="name of output file")
    parser.add_argument('-n', dest='num_runs', metavar='-n', type=int, required=False, help="number of times to run traceroute")
    parser.add_argument('-m', dest='max_hops', metavar='-m', type=int, required=False, help="max hops")
    parser.add_argument('--test', dest='test_dir', metavar='--test', type=str, required=False, help="data compilation for executed traceroute")
    parser.add_argument('-d', dest='run_delay', metavar='-d', type=str, required=False, help="delay (in seconds) between two consecutive runs")
    return parser.parse_args()

# run traceroute and return data
def run_traceroute(target, num_runs, max_hops, run_delay):
    all_data = []
    hops_data = 0
    just_times = [[] for i in range(max_hops)]
    just_hosts = [[] for i in range(max_hops)]
    # will run num_runs times
    for i in range(num_runs):
        # run traceroute
        print("running traceroute...")
        result = subprocess.run(['traceroute', '-m', str(max_hops), '-n', target], capture_output=True, text=True)
        print("traceroute complete.")
        # save the data as a string
        hops_data = parse_traceroute_output(result.stdout)

        # extract rtt_times and save to global array
        j = 0
        for item in hops_data:
            time = item.get("rtt_times")
            for val in time:  
                just_times[j].append(val)
            j += 1
        # extract hosts and save to global array
        k = 0
        for thing in hops_data:
            host = thing.get("host")
            for val in host:  
                just_hosts[k].append(val)
            k += 1
        if run_delay is not None:
            sleep(int(run_delay))

    # create the final JSON node
    frog = 1
    for i in range (max_hops):
        data = file_JSON_node(just_hosts[i], just_times[i], frog)
        frog += 1
        all_data.append(data)
    
    return all_data

# parse through traceroute output
def parse_traceroute_output(output):
    hops_data = []
    output = output.replace("ms", ' ')
    lines = output.splitlines()
    result = ["  "] * len(lines)
    # Process each line
    for i in range(len(lines)):
    # Check if the line starts with a hop number (e.g., "1", "2", "3", etc.)
        if re.match(r'^\d\s', lines[i]):
        # If it starts with a hop number, it's a new line, so just append it
            result.append(lines[i])
        else:
        # If it doesn't start with a hop number, it belongs to the previous line, so we join it
            result[-1] += '' + lines[i]
    
    changed_input = str(result[len(lines) - 1])
    thing = re.split(r'(?<=\s)\d+(?=\s)', changed_input)
    del thing[0]
   
    frog = 1
    
    for thin in thing:
        data = {}
        data = create_JSON_node(thin, frog)
        frog += 1
        hops_data.append(data)
   
    return hops_data

# create JSON-esque objects for each hop
def create_JSON_node(item, hop_num):
    # hop
    hop = hop_num
    # hostname
    host = []
    ip_regex = re.compile("(\d+\.\d+\.\d+\.\d+)")
    host_matches = ip_regex.finditer(item)
    for match in host_matches:
        host.append(match.group(0))
        item = item.replace(match.group(0), ' ')
    #print(item)

    # times extraction
    rtt_times = []
    time_regex = re.compile("\d+\.\d{3}\s")
    time_matches = time_regex.finditer(item)
    for match in time_matches:
        if len(rtt_times) < 4:  # Only add the first 4 RTT values
            num = match.group(0)
            rtt_times.append(float(num))

    raw_stats = {
        'hop': hop,
        'host': host,
        'rtt_times': rtt_times
    }
    return raw_stats

# compute everything needed and return JSON node
def file_JSON_node(host_arr, time_arr, hop_num):
    if len(time_arr) == 0: 
        avg = 0
        min = 0
        max = 0
        med = 0
    else:     
        avg = np.mean(time_arr)
        min = np.min(time_arr)
        max = np.max(time_arr)
        med = np.median(time_arr)
    
    stats = {
             'hop': hop_num,
             'host': host_arr,
                 'avg': avg,
                 'min': min,
                 'max': max,
                 'med': med
         }
    return stats

# create boxplot graph based on data
def createGraph(data, value):
    rtt_data = []

    for entry in data:
        rtt_data.append([entry['min'], entry['avg'], entry['max']])

    # create boxplot
    plt.figure(figsize=(10, 6))
    sns.boxplot(data=rtt_data)
    plt.title('Boxplot of RTT for Each Hop')        
    plt.ylabel('Latency (ms)')

    plt.xticks(range(len(rtt_data)), ['Hop ' + str(i+1) for i in range(len(rtt_data))])

    plt.savefig(value + '_boxplot.png')
    return 0

# parse through data from files
def file_data_parser(item, frog):
    hop = frog
    
    host = []
    ip_regex = re.compile("(\d+\.\d+\.\d+\.\d+)")
    host_matches = ip_regex.finditer(item)
    for match in host_matches:
        host.append(match.group(0))
        item = item.replace(match.group(0), ' ')

    # times extraction
    rtt_times = []
    time_regex = re.compile("\d+\.\d{3}\s")
    time_matches = time_regex.finditer(item)
    for match in time_matches:
        if len(rtt_times) < 4:  
            num = match.group(0)
            rtt_times.append(float(num))
    raw_stats = {
        'hop': hop,
        'host': host,
        'rtt_times': rtt_times
    }

    return raw_stats


def main():
    args = args_parser()

    # for testing purposes
    test_dir_data = []
    temp_data = []
    if args.test_dir:
        print("processing input directory", args.test_dir)
        # Iterate through the files in the directory
        for filename in os.listdir(args.test_dir):
            file_path = os.path.join(args.test_dir, filename)
            file_content = ""
            lines = ""

            # Only process files (not directories)
            if os.path.isfile(file_path):
                print(f"\tProcessing file: {file_path}")
        
            # Open the file and do something with it
            with open(file_path, 'r') as file:
                # For example, print the contents of the file (you can replace this with your own logic)
                file_content = file.read()
                file_content = file_content.replace('ms', ' ')
                lines = file_content.split("\n")
                file_content = [line for line in lines if "traceroute" not in line]

            i = 0

            for segment in file_content:
                i += 1
                data_segment = file_data_parser(segment, i)
                temp_data.append(data_segment)

                # extract rtt_times and save to global array
            j = 0
            for item in temp_data:
                time = item.get("rtt_times")
                for val in time: 
                    just_times[j].append(val)
                j += 1
            j = 0
            # extract hosts and save to global array
            k = 0
            for thing in temp_data:
                host = thing.get("host")
                for val in host:  
                    just_hosts[k].append(val)
                k += 1
            k = 0
             
        frog = 1
        for p in range (i):
            data = file_JSON_node(just_hosts[p], just_times[p], frog)
            frog += 1
            test_dir_data.append(data)
        with open(args.output, 'w') as json_file:
            json.dump(test_dir_data, json_file, indent=4)
        print("finshed processing input directory", args.test_dir)
    else:    
        all_data = run_traceroute(args.target, args.num_runs, args.max_hops, args.run_delay)

        # Write JSON output
        with open(args.output, 'w') as json_file:
            json.dump(all_data, json_file, indent=4)
    
    print("creating boxplot graph...")
    with open(args.output) as f:
        data = json.load(f)
        createGraph(data, args.target)
    print("graph generation complete.")
if __name__ == '__main__':
    main()