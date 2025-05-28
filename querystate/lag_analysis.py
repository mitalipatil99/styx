import re
import pandas as pd
import matplotlib.pyplot as plt
from io import StringIO
import matplotlib.dates as mdates

# --- 1. Load the new consume data ---
consume_csv_data_new = """
uuid,consumeTimeStamp
6f4544bb-4d9f-41fb-9f96-0f59fe44e326,1748358061388
8d5f9c9d-8dd2-4caf-a519-095a50ce8362,1748358066402
00fe6048-5451-4ffe-9892-c27dd0c2548e,1748358071448
17b13d5c-c3cb-4f9c-afed-f636bda1524f,1748358076460
1ff5f991-52a5-4f94-81c8-47509b32cf8a,1748358081489
5d751d20-de60-442b-bc8f-5c2746a7f12c,1748358086513
3cd5eec0-ae7f-4eb5-aa97-4c8569e91a7f,1748358091540
0d0589ff-ab38-4b8b-b359-8dbd47a4de12,1748358096569
b1e069a1-740f-4ef7-af47-e91e8088b378,1748358101594
64473cef-b01d-4e1a-98b7-a56ae1d6aedc,1748358106620
28258993-a28a-4e96-821e-a9249a50c71d,1748358111648
9e1f82a9-9af2-4e6b-9e33-88f2df46e401,1748358116674
25175c16-3b6f-4163-ac7a-6ec3b28f7721,1748358121702
838480d4-7855-45d0-9dc4-3529f3470628,1748358126729
5dca16c5-8f20-46d5-8f08-6aba02518940,1748358131757
cd6c5983-b0bb-48a5-ac9a-adb4c4db0947,1748358136783
d016ddae-c0ee-4d6a-a0a9-e00b37af1792,1748358141813
7ec4689c-048b-4032-8887-c0d246090b3f,1748358146840
7585f129-b472-4856-8caa-6550b9d3f9bc,1748358151871
aaea1e23-a0a9-4128-be2b-db180b78b82d,1748358156895
"""

consume_df_new = pd.read_csv(StringIO(consume_csv_data_new))
consume_df_new['consumeTimeStamp'] = pd.to_datetime(consume_df_new['consumeTimeStamp'], unit='ms')

# --- 2. Extract Epoch intervals from log file ---
# (Assuming log file lines are already loaded in the variable 'log_lines'.)
# Use the provided pattern:
input_file = r"/home/mitalipatil/PycharmProjects/styx/worker-logs.log"
with open(input_file) as f:
    log_lines= f.readlines()
epoch_pattern = re.compile(r"Epoch\s+\|\|\|\s*:\s*(\d+)\s+\|\|\|\s+start in milliseconds:\s+(\d+)\s+\|\|\|\s+end in milliseconds:\s+(\d+)")
epoch_entries = []
for line in log_lines:
    match = epoch_pattern.search(line)
    if match:
        epoch_id = int(match.group(1))
        start_ms = int(match.group(2))
        end_ms = int(match.group(3))
        epoch_entries.append({
            'epoch_id': epoch_id,
            'start': pd.to_datetime(start_ms, unit='ms'),
            'end': pd.to_datetime(end_ms, unit='ms')
        })
epoch_df = pd.DataFrame(epoch_entries)

# --- 3. Create the chart: plotting consume events and epoch intervals ---
plt.figure(figsize=(12, 6))

# Plot consume timestamps from the new data as points
plt.plot(consume_df_new['consumeTimeStamp'], [1]*len(consume_df_new), 'o', label='Consume Timestamp', color='blue')

# Plot each epoch as a shaded interval
for _, row in epoch_df.iterrows():
    plt.axvspan(row['start'], row['end'], color='gray', alpha=0.3)

plt.yticks([1], ['Consume Event'])
plt.xlabel("Time")
plt.title("State Consume Events and Epoch Intervals")
plt.legend()
plt.grid(True)
plt.tight_layout()
plt.show()

# --- 4. Compute the numerical lag analysis ---
def find_latest_epoch_lag(consume_ts, epochs):
    relevant_epochs = epochs[epochs['end'] <= consume_ts]
    if not relevant_epochs.empty:
        latest_epoch_end = relevant_epochs['end'].max()
        lag = (consume_ts - latest_epoch_end).total_seconds() * 1000  # convert to milliseconds
        return latest_epoch_end, lag
    else:
        return pd.NaT, None

lags = []
for ts in consume_df_new['consumeTimeStamp']:
    latest_epoch_end, lag_ms = find_latest_epoch_lag(ts, epoch_df)
    lags.append({'consume_time': ts, 'latest_epoch_end': latest_epoch_end, 'lag_ms': lag_ms})
lag_df_new = pd.DataFrame(lags)

# Display the lag analysis results
print("Consume - Epoch Lag Analysis:")
print(lag_df_new)


## latency for queries : req , response
## delta update latency: epoch level update difference
## freshness between epoch and timestamps.