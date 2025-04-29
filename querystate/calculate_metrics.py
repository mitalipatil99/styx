import pandas as pd
import numpy as np
from matplotlib import pyplot as plt

PRODUCE_CSV = "query_timestamps_produce.csv"
CONSUME_CSV = "query_timestamps_consume.csv"
OUTPUT_LATENCY_METRICS = "latency_metrics.json"

def calculate_latency_metrics():

    produce_df = pd.read_csv(PRODUCE_CSV)
    consume_df = pd.read_csv(CONSUME_CSV)

    # Merge the two datasets on the 'uuid' column
    merged_df = produce_df.merge(consume_df, on='uuid', how='right',suffixes=('_produce', '_consume'))

    print(merged_df.head(15))
    # Calculate latency for each record
    merged_df['latency_ms'] = merged_df['produceTimeStamp_consume'] - merged_df['produceTimeStamp_produce']
    print(merged_df.head(15))
    # Sort rows by the produced timestamp for chronological order
    merged_df = merged_df.sort_values(by='produceTimeStamp_produce')

    print(merged_df.head(15))

    # # Compute latency metrics
    # latency_metrics = {
    #     "latency (ms)": {
    #         10: np.percentile(merged_df['latency_ms'], 10),
    #         20: np.percentile(merged_df['latency_ms'], 20),
    #         30: np.percentile(merged_df['latency_ms'], 30),
    #         40: np.percentile(merged_df['latency_ms'], 40),
    #         50: np.percentile(merged_df['latency_ms'], 50),  # Median
    #         60: np.percentile(merged_df['latency_ms'], 60),
    #         70: np.percentile(merged_df['latency_ms'], 70),
    #         80: np.percentile(merged_df['latency_ms'], 80),
    #         90: np.percentile(merged_df['latency_ms'], 90),
    #         95: np.percentile(merged_df['latency_ms'], 95),
    #         99: np.percentile(merged_df['latency_ms'], 99),
    #         "max": merged_df['latency_ms'].max(),
    #         "min": merged_df['latency_ms'].min(),
    #         "mean": merged_df['latency_ms'].mean(),
    #     },
    #     "total_messages": len(merged_df),
    #     "missed_messages": 0  # Since we merged, no UUIDs are missing here
    # }
    # percentiles = [10, 50, 90, 95, 99]
    # latency_percentiles = np.percentile(merged_df['latency_ms'], percentiles)
    #
    plt.figure(figsize=(12, 6))
    plt.hist(merged_df['latency_ms'], bins=50, color='skyblue', edgecolor='k', alpha=0.7)
    # plt.axvline(latency_percentiles[2], color='r', linestyle='--', label=f"90th Percentile: {latency_percentiles[2]:.2f} ms")
    # plt.axvline(latency_percentiles[3], color='g', linestyle='--', label=f"95th Percentile: {latency_percentiles[3]:.2f} ms")
    # plt.axvline(latency_percentiles[4], color='orange', linestyle='--', label=f"99th Percentile: {latency_percentiles[4]:.2f} ms")
    #
    # # Adding labels and title
    plt.title("Query Latency Distribution")
    plt.xlabel("Latency (ms)")
    plt.ylabel("Frequency")
    # plt.legend()
    # plt.grid(axis='y', linestyle='--', linewidth=0.7)
    #
    # # Save and show
    plt.savefig("query_latency_distribution.png", dpi=300)
    # print("Latency plot saved as 'query_latency_distribution.png'")
    plt.show()
    #
    #
    # # Save latency metrics to a JSON file
    # import json
    # with open(OUTPUT_LATENCY_METRICS, 'w', encoding='utf-8') as f:
    #     json.dump(latency_metrics, f, ensure_ascii=False, indent=4)
    #
    # print(f"Latency metrics generated and saved to {OUTPUT_LATENCY_METRICS}")

if __name__ == "__main__":
    calculate_latency_metrics()