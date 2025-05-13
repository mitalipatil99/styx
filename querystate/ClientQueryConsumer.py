import asyncio
import csv
import json
import logging
from aiokafka import AIOKafkaConsumer
from aiokafka.errors import KafkaConnectionError

# Create a separate logger for the specific logs
specific_logger = logging.getLogger("specific_logger")
specific_logger.setLevel(logging.WARNING)

# Create a file handler for the new logger
specific_log_handler = logging.FileHandler("query_response.log")
specific_log_handler.setLevel(logging.WARNING)

# Define the format for the logs
log_format = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
specific_log_handler.setFormatter(log_format)

# Add the handler to the specific logger
specific_logger.addHandler(specific_log_handler)


KAFKA_QUERY_RESPONSE_TOPIC = "query_state_response"
KAFKA_URL = 'localhost:9092'
KAFKA_CONSUME_TIMEOUT_MS = 100
CSV_FILE_PATH = ("query_timestamps_consume.csv")

class ClientQueryConsumer:
    def __init__(self):
        self.kafka_consumer: AIOKafkaConsumer | None = None
        with open(CSV_FILE_PATH, 'w', newline='') as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(['uuid', 'produceTimeStamp'])


    async def start(self):
        """Start Kafka Consumer"""
        logging.info("Starting Kafka Consumer")
        try:
            while True:
                try:
                    logging.warning(f"Starting kafka consumer for client side")
                    await self.kafka_consumer.start()
                except KafkaConnectionError:
                    await asyncio.sleep(1)
                    logging.warning(f'Kafka at {KAFKA_URL} not ready yet, sleeping for 1 second')
                    continue
                break

            kafka_ingress_topic_name: str = KAFKA_QUERY_RESPONSE_TOPIC
            topics = await self.kafka_consumer.topics()
            wait_for_topic = True
            while wait_for_topic:
                wait_for_topic = False
                if kafka_ingress_topic_name not in topics:
                    wait_for_topic = True
                if not wait_for_topic:
                    break
                await asyncio.sleep(1)
                topics = await self.kafka_consumer.topics()

            self.kafka_consumer.subscribe([kafka_ingress_topic_name])
            await self.consume_query_response()

        except Exception as e:
            logging.error(f"Error in consumer: {e}")
        finally:
            await self.kafka_consumer.stop()

    async def consume_query_response(self):
        """Consume query responses from Kafka"""
        while True:
            logging.info("Waiting for response from querystate")
            msg = await self.kafka_consumer.getmany(timeout_ms=KAFKA_CONSUME_TIMEOUT_MS)
            for tp, messages in msg.items():
                for message in messages:
                    # logging.warning(f"Received message: {message}")
                    response = json.loads(message.value.decode('utf-8'))
                    req_res_id = response['uuid']
                    self.record_query_timestamp(req_res_id,message.timestamp)
                    specific_logger.warning(f"Received response for query uuid: {req_res_id}")
                    specific_logger.warning(f':{response}')

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
        self.kafka_consumer = AIOKafkaConsumer(bootstrap_servers=[KAFKA_URL],auto_offset_reset="earliest")
        await self.start()

if __name__ == "__main__":
    consumer = ClientQueryConsumer()
    asyncio.run(consumer.main())