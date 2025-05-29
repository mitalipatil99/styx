# latency metric for the query : resposne - request.
# get latency between epoch end time in worker logs and the epoch state delta completion update timestamp in query state logs to see how late the eppch updates happen from worker to
# state container, get the overall average also.
import csv
#get freshness by checking the response epoch and time and the corresponding time epoch in the worker and then see the epoch differnce and time differnce.
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

        # Calculate average latency
        average_latency = sum(latencies) / len(latencies) if latencies else 0

        # Print average
        print(f"Average state update latency: {average_latency:.2f} ms")

        # Plot
        plt.figure(figsize=(10, 6))
        plt.plot(epochs, latencies, marker='o', color='blue')
        plt.axhline(y=average_latency, color='red', linestyle='--', label=f'Average: {average_latency:.2f} ms')
        plt.xlabel('Epoch')
        plt.ylabel('State Update Latency (ms)')
        plt.title('Epoch State Update Latency')
        plt.legend()
        plt.grid(True)
        plt.tight_layout()
        plt.show()

    def compute_freshness_report(self,uuid_csv_file, response_log_file, worker_log_file):
        # --- Load UUID timestamps from CSV ---
        def load_uuid_timestamps(file_path):
            uuid_to_timestamp = {}
            with open(file_path, mode='r') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    uuid = row["uuid"]
                    timestamp = int(row["consumeTimeStamp"])
                    uuid_to_timestamp[uuid] = timestamp
            return uuid_to_timestamp

        # --- Parse response log: UUID → epoch ---
        def parse_response_logs(file_path):
            uuid_to_epoch = {}
            with open(file_path, 'r') as f:
                for line in f:
                    match = re.search(r"'uuid': '([^']+)', 'epoch': (\d+)", line)
                    if match:
                        uuid = match.group(1)
                        epoch = int(match.group(2))
                        uuid_to_epoch[uuid] = epoch
            return uuid_to_epoch

        # --- Parse worker logs: epoch → snapshot end time ---
        def parse_worker_logs(file_path):
            epoch_to_end_time = {}
            with open(file_path, 'r') as f:
                for line in f:
                    match = re.search(r"Epoch\s+\|\|\|:\s+(\d+).*?Ended\s+@\s+\(ms\):\s+(\d+)", line)
                    if match:
                        epoch = int(match.group(1))
                        end_time = int(match.group(2))
                        epoch_to_end_time[epoch] = end_time
            return epoch_to_end_time

        # --- Calculate freshness ---
        def calculate_freshness(uuid_to_timestamp, uuid_to_epoch, epoch_to_end_time):
            freshness_results = {}
            for uuid, response_time in uuid_to_timestamp.items():
                epoch = uuid_to_epoch.get(uuid)
                if epoch is not None:
                    snapshot_end = epoch_to_end_time.get(epoch)
                    if snapshot_end is not None:
                        freshness = response_time - snapshot_end
                        freshness_results[uuid] = freshness
            return freshness_results

        # --- Main logic ---
        uuid_to_timestamp = load_uuid_timestamps(uuid_csv_file)
        uuid_to_epoch = parse_response_logs(response_log_file)
        epoch_to_end_time = parse_worker_logs(worker_log_file)
        freshness = calculate_freshness(uuid_to_timestamp, uuid_to_epoch, epoch_to_end_time)

        # --- Output results ---
        print("UUID\t\t\t\tFreshness (ms)")
        print("-" * 50)
        for uuid, f in freshness.items():
            print(f"{uuid}\t{f:+} ms")

        return freshness


if __name__ == '__main__':
    calculator = CalculateMetrics()
    # calculator.getLatencyofQueries()
    # calculator.getEpochLatency()
    calculator.compute_freshness_report(
        uuid_csv_file='query_timestamps_consume.csv',
        response_log_file='query_response.log',
        worker_log_file='/home/mitalipatil/PycharmProjects/styx/worker-logs.log'
    )