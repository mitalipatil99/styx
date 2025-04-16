import asyncio
import json
import logging
import traceback
import uuid

from aiokafka import AIOKafkaProducer, AIOKafkaConsumer, ConsumerRecord
from aiokafka.errors import UnknownTopicOrPartitionError, KafkaConnectionError
from styx.common.message_types import MessageType
from styx.common.serialization import Serializer
from styx.common.tcp_networking import NetworkingManager

from querystate.querystate_service import KAFKA_CONSUME_TIMEOUT_MS


KAFKA_QUERY_TOPIC = "query_processing"
KAFKA_URL = 'localhost:9092'
# KAFKA_URL: str = os.getenv('KAFKA_URL', None)
SERVER_PORT=8080

class ClientQueries:
    def __init__(self):
        self.server_port = SERVER_PORT
        self.kafka_producer: AIOKafkaProducer | None = None
        self.kafka_consumer: AIOKafkaConsumer | None = None

        self.networking = NetworkingManager(self.server_port)
        self.response_future : dict[str]

    async def start(self):
        """Start Kafka Producer"""
        logging.info("Starting Kafka Producer and Consumer")
        try:
            while True:
                try:
                    logging.warning(f"Starting kafka consumer for client side")
                    await self.kafka_consumer.start()
                    logging.warning(f"Starting kafka producer for client side")
                    await self.kafka_producer.start()
                except (UnknownTopicOrPartitionError, KafkaConnectionError):
                    await asyncio.sleep(1)
                    logging.warning(f'Kafka at {KAFKA_URL} not ready yet, sleeping for 1 second')
                    continue
                break
            kafka_ingress_topic_name: str = 'query_state_response'
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

            while True:
                try:
                    await asyncio.create_task(self.publish_client_queries())
                    await asyncio.create_task(self.consume_query_response())
                except Exception as e:
                    logging.error(traceback.format_exc())

        except Exception as e:
            logging.error(traceback.format_exc())
        finally:
            await self.kafka_consumer.stop()



    async def stop(self):
        """Shutdown Kafka"""
        await self.kafka_producer.stop()
        await self.kafka_consumer.stop()

    async def publish_client_queries(self):

        '''api queries with uuid ..TO BE CHANGED'''
        logging.warning("Publishing client queries")
        queries = [
            # {"type": "GET_STATE", "uuid": "1234-uuid"},
            {"type": "GET_OPERATOR_STATE", "uuid": "1", "operator": "ycsb"},
            # {"type": "GET_KEY_STATE", "uuid": "91011-uuid", "operator": "operator2", "key": "key1"},
            # {"type": "GET_ALL_KEYS_FOR_OPERATOR", "uuid": "1213-uuid", "operator": "operator3"},
        ]
        # add range queries here and joins (query language)

        # Send each query to Kafka topic
        for query in queries:
            logging.warning(f"Publishing query: {query}")
            await self.kafka_producer.send_and_wait(KAFKA_QUERY_TOPIC, json.dumps(query).encode('utf-8'))

    async def consume_query_response(self):
        while True:
            try:
                logging.info("Waiting for response from querystate")
                async with asyncio.timeout(KAFKA_CONSUME_TIMEOUT_MS / 1000):
                    msg: ConsumerRecord = await self.kafka_consumer.getone()
                    logging.warning(f"Received message: {msg}")
                    response = json.loads(msg.value.decode('utf-8'))
                    req_res_id = response['uuid']
                    logging.warning(f"Received response for query uuid: {req_res_id}")
                    logging.warning(f':{response}')
                    '''send response back to client'''

            except TimeoutError:
               pass
            await asyncio.sleep(0.01)



    async def main(self):
        self.kafka_producer = AIOKafkaProducer(bootstrap_servers=KAFKA_URL)
        self.kafka_consumer = AIOKafkaConsumer(bootstrap_servers=[KAFKA_URL])
        await self.start()

if __name__ == "__main__":
    clientQueries = ClientQueries()
    asyncio.run(clientQueries.main())

#check responses. check where coroutine is getting stuck.