import asyncio
import json
import logging
from aiokafka import AIOKafkaProducer
from aiokafka.errors import KafkaConnectionError

KAFKA_QUERY_TOPIC = "query_processing"
KAFKA_URL = 'localhost:9092'

class ClientQueryPublisher:
    def __init__(self):
        self.kafka_producer: AIOKafkaProducer | None = None

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

        while True:
            query = await query_queue.get()  # Fetch a query from the queue
            logging.warning(f"Publishing query: {query}")
            await self.kafka_producer.send_and_wait(KAFKA_QUERY_TOPIC, json.dumps(query).encode('utf-8'))
            query_queue.task_done()

    async def main(self):
        self.kafka_producer = AIOKafkaProducer(bootstrap_servers=KAFKA_URL)
        await self.start()

if __name__ == "__main__":
    publisher = ClientQueryPublisher()
    asyncio.run(publisher.main())