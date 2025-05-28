# latency metric for the query : resposne - request.
# get latency between epoch end time in worker logs and the epoch state delta completion update timestamp in query state logs to see how late the eppch updates happen from worker to
# state container, get the overall average also.
import re

import pandas as pd
import matplotlib.pyplot as plt



class CalculateMetrics:

    def getLatencyofQueries(self):
        # Load the CSV files
        consume_df = pd.read_csv('query_timestamps_consume.csv')  # Replace with your actual file name
        produce_df = pd.read_csv('query_timestamps_produce.csv')  # Replace with your actual file name

        # Merge both dataframes on the uuid column
        merged_df = pd.merge(consume_df, produce_df, on='uuid')

        # Calculate latency
        merged_df['latency_ms'] = merged_df['consumeTimeStamp'] - merged_df['produceTimeStamp']

        # Sort by produce timestamp for better plotting
        merged_df.sort_values(by='produceTimeStamp', inplace=True)

        # Plot the latency
        plt.figure(figsize=(12, 6))
        plt.plot(merged_df['produceTimeStamp'], merged_df['latency_ms'], marker='o', linestyle='-')
        plt.xlabel('Produce Timestamp')
        plt.ylabel('Latency (ms)')
        plt.title('Query Latency (Consume - Produce Timestamp)')
        plt.grid(True)
        plt.tight_layout()
        plt.show()

    def getEpochLatency(self):
        querystate_log_path = '/home/mitalipatil/PycharmProjects/styx/querystate-logs.log'
        worker_log_path = '/home/mitalipatil/PycharmProjects/styx/worker-logs.log'

        # Regex patterns
        querystate_pattern = re.compile(r'Epoch (\d+) state updated @ (\d+)')
        worker_pattern = re.compile(r'\|\|\| Epoch \|\|\|: (\d+).*?Ended @ \(ms\): (\d+)')

        # Parse querystate log
        epoch_updates = {}
        with open(querystate_log_path, 'r') as f:
            for line in f:
                match = querystate_pattern.search(line)
                if match:
                    epoch = int(match.group(1))
                    update_ts = int(match.group(2))
                    epoch_updates[epoch] = update_ts

        # Parse worker log
        epoch_ends = {}
        with open(worker_log_path, 'r') as f:
            for line in f:
                match = worker_pattern.search(line)
                if match:
                    epoch = int(match.group(1))
                    end_ts = int(match.group(2))
                    epoch_ends[epoch] = end_ts

        # Compute latencies
        epochs = sorted(set(epoch_updates.keys()) & set(epoch_ends.keys()))
        latencies = [epoch_updates[e] - epoch_ends[e] for e in epochs]

        # Plot
        plt.figure(figsize=(10, 10))
        plt.plot(epochs, latencies, marker='o', linestyle='-', color='blue')
        plt.xlabel('Epoch')
        plt.ylabel('State Update Latency (ms)')
        plt.title('Epoch State Update Latency')
        plt.grid(True)
        plt.tight_layout()
        plt.show()


if __name__ == '__main__':
    calculator = CalculateMetrics()
    # calculator.getLatencyofQueries()
    calculator.getEpochLatency()