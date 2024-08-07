import sys

from aiokafka import AIOKafkaConsumer
import asyncio
import pandas as pd

import uvloop
from styx.common.serialization import msgpack_deserialization

SAVE_DIR: str = sys.argv[1]

EGRESS_TOPIC_NAME = 'styx-egress'

async def consume():
    records = []
    consumer = AIOKafkaConsumer(
        auto_offset_reset='earliest',
        value_deserializer=msgpack_deserialization,
        bootstrap_servers='localhost:9092')
    await consumer.start()
    topics = []
    # Ensure topic is created by the producer (and not auto-created by this
    # consumer). This is important because it is the producer who holds the
    # information regarding the required partitions.
    while EGRESS_TOPIC_NAME not in topics:
        topics = await consumer.topics()
        print(
            f"Awaiting topic {EGRESS_TOPIC_NAME} to be created by the Styx "
              "coordinator"
        )
        await asyncio.sleep(5)
    print(f"Topic {EGRESS_TOPIC_NAME} has been created.")
    consumer.subscribe([EGRESS_TOPIC_NAME])
    print(f"Consumer subscribed to topic {EGRESS_TOPIC_NAME}.")
    try:
        # Consume messages
        while True:
            data = await consumer.getmany(timeout_ms=60_000)
            if not data:
                break
            for messages in data.values():
                for msg in messages:
                    # print("consumed: ", msg.key, msg.value, msg.timestamp)
                    records.append((msg.key, msg.value, msg.timestamp))
    finally:
        # Will leave consumer group; perform autocommit if enabled.
        await consumer.stop()
        pd.DataFrame.from_records(records,
                                  columns=['request_id', 'response', 'timestamp']).to_csv(f'{SAVE_DIR}/output.csv',
                                                                                          index=False)

uvloop.run(consume())
