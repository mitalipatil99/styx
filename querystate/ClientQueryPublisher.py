import asyncio
import json
import logging
import csv
from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaConnectionError
from aiokafka.structs import RecordMetadata

KAFKA_QUERY_TOPIC = "query_processing"
KAFKA_URL = 'localhost:9092'
CSV_FILE_PATH = ("query_timestamps_produce.csv")

class ClientQueryPublisher:
    def __init__(self):
        self.kafka_producer: AIOKafkaProducer | None = None
        with open(CSV_FILE_PATH, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['uuid', 'produceTimeStamp'])

    async def start(self):
        """Start Kafka Producer"""
        logging.info("Starting Kafka Producer")
        try:
            while True:
                try:
                    logging.warning(f"Starting kafka producer for client side")
                    await self.kafka_producer.start()
                except KafkaConnectionError:
                    await asyncio.sleep(1)
                    logging.warning(f'Kafka at {KAFKA_URL} not ready yet, sleeping for 1 second')
                    continue
                break

            await self.publish_client_queries()

        except Exception as e:
            logging.error(f"Error in publisher: {e}")
        finally:
            await self.kafka_producer.stop()

    async def publish_client_queries(self):
        """Publish client queries to Kafka"""
        logging.warning("Publishing client queries")
        query_queue = asyncio.Queue()

        # Example: Add initial queries to the queue
        # await query_queue.put({"type": "GET_OPERATOR_PARTITION_STATE", "uuid": "2", "operator": "ycsb", "partition": 1})
        await query_queue.put({"type": "GET_KEY_STATE", "uuid": "91011-uuid", "operator": "ycsb", "key": 57})
        #add round-robin for three queries or random generator.
        # correctness benchmark
        while True:
            query = await query_queue.get()  # Fetch a query from the queue
            logging.warning(f"Publishing query: {query}")
            res: RecordMetadata = await self.kafka_producer.send_and_wait(KAFKA_QUERY_TOPIC, json.dumps(query).encode('utf-8'))
            self.record_query_timestamp(query['uuid'], res.timestamp)
            query_queue.task_done()

    def record_query_timestamp(self, query_id: str, timestamp: int) -> None:
        """Record query timestamp to CSV file.

        Args:
            query_id: Unique identifier for the query
            timestamp: Kafka message timestamp
        """
        try:
            with open(CSV_FILE_PATH, 'a', newline='') as csvfile:
                writer = csv.writer(csvfile)
                writer.writerow([query_id, timestamp])
        except IOError as e:
            logging.warning(f"Failed to write to CSV file: {str(e)}")

    async def main(self):
        self.kafka_producer = AIOKafkaProducer(bootstrap_servers=KAFKA_URL)
        await self.start()

if __name__ == "__main__":
    publisher = ClientQueryPublisher()
    asyncio.run(publisher.main())