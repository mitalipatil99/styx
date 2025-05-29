import asyncio
import json
import logging
import csv
import time
from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaConnectionError
from aiokafka.structs import RecordMetadata

from querystate.queryGenerator import generate_random_query


# Create a separate logger for the specific logs
specific_logger = logging.getLogger("specific_logger")
specific_logger.setLevel(logging.WARNING)

# Create a file handler for the new logger
specific_log_handler = logging.FileHandler("query_request.log")
specific_log_handler.setLevel(logging.WARNING)

# Define the format for the logs
log_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
specific_log_handler.setFormatter(log_format)

# Add the handler to the specific logger
specific_logger.addHandler(specific_log_handler)

QUERY_DURATION_SECONDS = 120  # Duration to run queries
QUERY_INTERVAL_SECONDS = 5  # Time between queries

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
        start_time = time.time()

        while time.time() - start_time < QUERY_DURATION_SECONDS:
            random_query = generate_random_query()
            specific_logger.warning(f"Publishing query: {random_query}")
            res: RecordMetadata = await self.kafka_producer.send_and_wait(KAFKA_QUERY_TOPIC,
                                                                          json.dumps(random_query).encode('utf-8'))
            self.record_query_timestamp(random_query['uuid'], res.timestamp)
            await asyncio.sleep(QUERY_INTERVAL_SECONDS)
        logging.warning("Finished publishing queries after specified duration")

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