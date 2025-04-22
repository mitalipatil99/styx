import asyncio
import json
import socket
import traceback
import uuid
import os
from asyncio import StreamReader, StreamWriter


from aiokafka import AIOKafkaConsumer, AIOKafkaProducer, ConsumerRecord
from aiokafka.errors import UnknownTopicOrPartitionError, KafkaConnectionError

from styx.common.logging import logging
from styx.common.message_types import MessageType
from styx.common.tcp_networking import NetworkingManager, MessagingMode
from styx.common.serialization import Serializer
from styx.common.util.aio_task_scheduler import AIOTaskScheduler
from struct import unpack


SERVER_PORT = 8080

KAFKA_URL: str = os.getenv('KAFKA_URL', None)
KAFKA_CONSUME_TIMEOUT_MS = 10 # ms
KAFKA_QUERY_RESPONSE_TOPIC="query_state_response"


class QueryStateService(object):

    def __init__(self):

        self.total_workers = None # Total number of workers
        self.epoch_deltas = {}  # Stores {epoch: {worker_id: delta}}
        self.epoch_count = {}  # Tracks number of deltas received per epoch
        self.state_store = {}  #global state store
        self.latest_epoch_count = 1
        self.state_lock = asyncio.Lock()

        self.server_port = SERVER_PORT

        self.query_state_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.query_state_socket.bind(('0.0.0.0', self.server_port))
        self.query_state_socket.setblocking(False)

        self.networking = NetworkingManager(self.server_port)

        self.aio_task_scheduler = AIOTaskScheduler()

        self.query_processing_task: asyncio.Task | None = None

        self.kafka_producer: AIOKafkaProducer | None = None


    async def query_state_controller(self, data: bytes):
        """Handles incoming messages related to query state updates."""
        message_type: int = self.networking.get_msg_type(data)

        match message_type:
            case MessageType.Synchronize:
                self.total_workers = self.networking.decode_message(data)
                logging.warning(f'Number of Workers :{self.total_workers}')
            case MessageType.QueryMsg:
                # Decode the message
                worker_id, epoch_counter, state_delta = self.networking.decode_message(data)
                logging.warning(f"Received state delta from worker {worker_id} for epoch {epoch_counter}")

                await self.receive_delta(worker_id,epoch_counter,state_delta)

            case _:  # Handle unsupported message types
                logging.error(f"QUERY STATE SERVER: Unsupported message type: {message_type}")

    async def receive_delta(self, worker_id, epoch_counter, state_delta):
        """add workerid , epoch counter , state delta to a dictionary
           maintain a [workerid] [epoch] count , and once count reaches the predefined number of workers,
           lock state and merge all deltas and update the state store.
        """
        async with self.state_lock:
            if epoch_counter not in self.epoch_deltas:
                self.epoch_deltas[epoch_counter]={}
                self.epoch_count[epoch_counter] = 0

            self.epoch_deltas[epoch_counter][worker_id] = state_delta
            self.epoch_count[epoch_counter] += 1

    async def mergeDeltas_and_updateState(self, epoch_counter):
            deltas = self.epoch_deltas[epoch_counter]

            # Merge deltas directly into state_store
            for worker_delta in deltas.values():
                for operator_partition, kv_pairs in worker_delta.items():
                    if operator_partition not in self.state_store:
                        self.state_store[operator_partition] = {}  # Initialize if missing

                    for key, value in kv_pairs.items():
                        self.state_store[operator_partition][key] = (
                                self.state_store[operator_partition].get(key, 0) + value
                        )
            logging.warning(f"Epoch {epoch_counter} state updated")

            del self.epoch_deltas[epoch_counter]
            del self.epoch_count[epoch_counter]
            self.latest_epoch_count += 1

    async def start_tcp_service(self):

        async def request_handler(reader: StreamReader, writer: StreamWriter):
            try:
                while True:
                    data = await reader.readexactly(8)
                    (size,) = unpack('>Q', data)
                    message = await reader.readexactly(size)
                    self.aio_task_scheduler.create_task(self.query_state_controller(message))
            except asyncio.IncompleteReadError as e:
                logging.warning(f"Client disconnected unexpectedly: {e}")
            except asyncio.CancelledError:
                pass
            finally:
                logging.warning("Closing the connection")
                writer.close()
                await writer.wait_closed()

        server = await asyncio.start_server(request_handler, sock=self.query_state_socket, limit=2**32)
        logging.warning("Query State Started")
        async with server:
            await server.serve_forever()

    async def start_query_processing(self):
        kafka_consumer = AIOKafkaConsumer(bootstrap_servers=[KAFKA_URL])
        try:
            while True:
                # start the kafka consumer
                try:
                    logging.warning(f"Starting kafka consumer")
                    await kafka_consumer.start()
                    logging.warning(f"Starting kafka producer")
                    await self.kafka_producer.start()
                except (UnknownTopicOrPartitionError, KafkaConnectionError):
                    await asyncio.sleep(1)
                    logging.warning(f'Kafka at {KAFKA_URL} not ready yet, sleeping for 1 second')
                    continue
                break
            kafka_ingress_topic_name: str = 'query_processing'
            topics = await kafka_consumer.topics()
            wait_for_topic = True
            while wait_for_topic:
                wait_for_topic = False
                if kafka_ingress_topic_name not in topics:
                    wait_for_topic = True
                if not wait_for_topic:
                    break
                await asyncio.sleep(1)
                topics = await kafka_consumer.topics()
            kafka_consumer.subscribe([kafka_ingress_topic_name])
            # Kafka Consumer ready to consume
            logging.warning(f"Starting coroutine")
            while True:
                # TODO fix for freshness
                # logging.warning(f'{self.latest_epoch_count}')
                # logging.warning(f'{self.epoch_count}')
                if (self.latest_epoch_count in self.epoch_count and
                        self.epoch_count[self.latest_epoch_count]==self.total_workers):
                    await self.mergeDeltas_and_updateState(self.latest_epoch_count)
                try:
                    async with asyncio.timeout(KAFKA_CONSUME_TIMEOUT_MS / 1000):
                        msg: ConsumerRecord = await kafka_consumer.getone()
                        logging.warning(f"Received message from Kafka topic: {msg.topic}")
                        logging.warning(f"Message value: {msg.value}")
                        query=  json.loads(msg.value.decode('utf-8'))
                        response =  await self.get_query_state_response(query)
                        await self.send_response(response)

                except TimeoutError:
                    logging.info(f"No queries for {KAFKA_CONSUME_TIMEOUT_MS} ms")
                await asyncio.sleep(0.01)
        except Exception as e:
            logging.error(traceback.format_exc())
        finally:
            await kafka_consumer.stop()


    async def get_query_state_response(self, query):
        logging.warning(f'query received: {query}')
        query_type = query['type']
        query_uuid = query['uuid']
        response={"uuid": query_uuid}

        if query_type =="GET_STATE":
            response["state"] = self.state_store
        elif query_type == "GET_OPERATOR_STATE":
            logging.warning(f'getting ycsb operator state')
            operator = query['operator']
            logging.warning(f'operator: {operator}')
            operator_data = {}
            for (op, partition), data in self.state_store.items():
                if op == operator:
                    operator_data.update(data)
            logging.warning(f'operator_data: {operator_data}')
            response["operator_state"] = operator_data
        elif query_type == "GET_OPERATOR_PARTITION_STATE":
            operator = query['operator']
            partition = query['partition']
            operator_partition_data = {}
            for (op, part), data in self.state_store.items():
                if op == operator and part == partition:
                    operator_partition_data.update(data)
            logging.warning(f'operator_partition_data: {operator_partition_data}')
            response["operator_partition_state"] = operator_partition_data
        elif query_type == "GET_KEY_STATE":
            operator = query['operator']
            key = query['key']
            key_partition = self.get_partition(key)
            for(op, partition), data in self.state_store.items():
                if op == operator and partition == key_partition:
                    operator_key_data = data.get(key, None)
            logging.warning(f'operator_data for key:{key}:{operator_key_data}')
            response["operator_key_state"] = operator_key_data
        return response

    def get_partition(self, key):
        if key is None:
            return None
        return key % self.total_workers

    async def send_response(self, response):
        logging.warning("sending response to query topic")
        await self.kafka_producer.send_and_wait(KAFKA_QUERY_RESPONSE_TOPIC, json.dumps(response).encode('utf-8'))

    def start_networking_tasks(self):
        self.networking.start_networking_tasks()

    async def main(self):
        self.kafka_producer = AIOKafkaProducer(bootstrap_servers=KAFKA_URL)
        self.start_networking_tasks()
        self.query_processing_task = asyncio.create_task(self.start_query_processing())
        await self.start_tcp_service()

if __name__ == "__main__":
    query_state_service = QueryStateService()
    asyncio.run(query_state_service.main())


# get partition using modulo