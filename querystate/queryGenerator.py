import json
import logging
import uuid
import random

# Query type constants
QUERY_TYPES = ["GET_KEY_STATE"]
KEY_RANGE = (1, 100)  # Range for random keys
PARTITION_RANGE = (0, 4)  # Range for random partitions
operator_type=["ycsb"]

def generate_query(query_type, operator= random.choice(operator_type), **kwargs):
    query = {
        "type": query_type,
        "uuid": str(uuid.uuid4()),
        "operator": operator
    }
    query.update(kwargs)
    return query



def generate_random_query():
    query_type = random.choice(QUERY_TYPES)
    if query_type == "GET_OPERATOR_PARTITION_STATE":
        return generate_query(query_type, partition=random.randint(*PARTITION_RANGE))
    elif query_type == "GET_KEY_STATE":
        return generate_query(query_type, key=random.randint(*KEY_RANGE))
    else:
        return generate_query(query_type)