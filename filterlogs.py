# filter_logs.py
import re

# Input log file and output filtered file
input_file = "worker-logs.log"
output_file = "filtered-logs.log"

def filter_logs(input_path, output_path):
    """
    Filters state epoch warning messages from a log file and writes them to a new file.
    """
    # Regular expression to match messages containing "state epoch"
    pattern = re.compile(r"state.*epoch", re.IGNORECASE)

    try:
        with open(input_path, "r") as infile, open(output_path, "w") as outfile:
            for line in infile:
                # Check if the current line matches the pattern
                if pattern.search(line):
                    outfile.write(line)
        print(f"Filtered logs written to '{output_path}' successfully.")
    except FileNotFoundError:
        print(f"Error: File '{input_path}' not found.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    filter_logs(input_file, output_file)