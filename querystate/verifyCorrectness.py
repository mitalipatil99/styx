import copy
from collections import defaultdict
import ast
import re

state_log_path = '/home/mitalipatil/PycharmProjects/styx/worker-logs.log'
total_workers = 4
latest_epoch_count = 1
epoch_state_store = {}
state_store = {}
epoch_deltas = defaultdict(dict)
epoch_count = defaultdict(int)

def parse_state_log():
    global latest_epoch_count
    pattern = re.compile(r'\|\|\| State at Epoch \|\|\|: (\d+): (.*)')

    with open(state_log_path, 'r') as f:
        for line in f:
            match = pattern.search(line)
            if match:
                epoch = int(match.group(1))
                state_dict_str = match.group(2)

                try:
                    state = ast.literal_eval(state_dict_str)
                    # Fake worker_id using count of entries seen for this epoch
                    worker_id = epoch_count[epoch]
                    epoch_deltas[epoch][worker_id] = state
                    epoch_count[epoch] += 1
                except Exception as e:
                    print(f"Error parsing state at epoch {epoch}: {e}")

    # Try to merge state when all deltas are present
    while latest_epoch_count in epoch_deltas and epoch_count[latest_epoch_count] == total_workers:
        merge_deltas_and_update_state(latest_epoch_count)
        latest_epoch_count += 1

def merge_deltas_and_update_state(epoch_counter):
    deltas = epoch_deltas[epoch_counter]

    for worker_delta in deltas.values():
        for operator_partition, kv_pairs in worker_delta.items():
            if operator_partition not in state_store:
                state_store[operator_partition] = {}

            for key, value in kv_pairs.items():
                state_store[operator_partition][key] = value
    epoch_state_store[epoch_counter] = copy.deepcopy(state_store)
    # print(f"\n✅ Epoch {epoch_counter} state updated.")
    # for op_part, kv in state_store.items():
    #     print(f"  {op_part} -> {kv}")

    del epoch_deltas[epoch_counter]
    del epoch_count[epoch_counter]

if __name__ == '__main__':
    parse_state_log()
    print(epoch_state_store.get(2005, None))

