import asyncio
import json
import socket
import traceback
import uuid
import os
from asyncio import StreamReader, StreamWriter

import cityhash
from aiokafka import AIOKafkaConsumer, AIOKafkaProducer, ConsumerRecord
from aiokafka.errors import UnknownTopicOrPartitionError, KafkaConnectionError
from styx.common.exceptions import NonSupportedKeyType

from styx.common.logging import logging
from styx.common.message_types import MessageType
from styx.common.tcp_networking import NetworkingManager
from styx.common.util.aio_task_scheduler import AIOTaskScheduler
from struct import unpack

SERVER_PORT = 8080

KAFKA_URL: str = os.getenv('KAFKA_URL', None)
KAFKA_CONSUME_TIMEOUT_MS = 100 # ms
KAFKA_QUERY_RESPONSE_TOPIC="query_state_response"


class QueryStateService(object):

    def __init__(self):

        self.total_workers = None # Total number of workers
        self.epoch_deltas = {}  # Stores {epoch: {worker_id: delta}}
        self.epoch_count = {}  # Tracks number of deltas received per epoch
        self.state_store = {}  #global state store
        self.latest_epoch_count = 1
        self.state_lock = asyncio.Lock()
        self.task_queue = asyncio.PriorityQueue()  # PriorityQueue for tasks

        self.server_port = SERVER_PORT

        self.query_state_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.query_state_socket.bind(('0.0.0.0', self.server_port))
        self.query_state_socket.setblocking(False)

        self.networking = NetworkingManager(self.server_port)

        self.aio_task_scheduler = AIOTaskScheduler()

        self.query_processing_task: asyncio.Task | None = None

        self.kafka_producer: AIOKafkaProducer | None = None
        self.kafka_consumer: AIOKafkaConsumer | None = None

        self.received_workers = asyncio.Event()

    async def add_task_to_queue(self, timestamp: int, task_coro):
        """Adds a task to the priority queue with the given timestamp."""
        await self.task_queue.put((timestamp, task_coro))

    async def process_task_queue(self):
        while True:
            timestamp, task_coro = await self.task_queue.get()
            try:
                logging.warning(f"task timestamp:{timestamp}")
                logging.warning(f"task coro:{task_coro}")
                asyncio.create_task(task_coro)
            except Exception as e:
                logging.error(f"Error processing task: {e}")
            finally:
                self.task_queue.task_done()


    async def query_state_controller(self, data: bytes):
        """Handles incoming messages related to query state updates."""

        message_type: int = self.networking.get_msg_type(data)

        match message_type:
            case MessageType.Synchronize:
                self.total_workers = self.networking.decode_message(data)
                logging.warning(f'Number of Workers :{self.total_workers}')
                self.received_workers.set()
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
        await self.received_workers.wait()
        async with self.state_lock:
            if epoch_counter not in self.epoch_deltas:
                self.epoch_deltas[epoch_counter]={}
                self.epoch_count[epoch_counter] = 0

            self.epoch_deltas[epoch_counter][worker_id] = state_delta
            self.epoch_count[epoch_counter] += 1

    async def check_and_merge_deltas(self):
        if (self.latest_epoch_count in self.epoch_count and
                self.epoch_count[self.latest_epoch_count] == self.total_workers):
            await self.mergeDeltas_and_updateState(self.latest_epoch_count)

    async def mergeDeltas_and_updateState(self, epoch_counter):
            deltas = self.epoch_deltas[epoch_counter]

            # Merge deltas directly into state_store
            for worker_delta in deltas.values():
                for operator_partition, kv_pairs in worker_delta.items():
                    if operator_partition not in self.state_store:
                        self.state_store[operator_partition] = {}  # Initialize if missing

                    for key, value in kv_pairs.items():
                        self.state_store[operator_partition][key] = value
            logging.warning(f"Epoch {epoch_counter} state updated")

            del self.epoch_deltas[epoch_counter]
            del self.epoch_count[epoch_counter]
            self.latest_epoch_count += 1

    async def merge_scheduler(self):
        while True:
            await self.add_task_to_queue(asyncio.get_running_loop().time(), self.check_and_merge_deltas())
            await asyncio.sleep(0.05)

    async def kafka_query_scheduler(self):
        while True:
            await self.add_task_to_queue(asyncio.get_running_loop().time(), self.kafka_query_handler())
            await asyncio.sleep(0.01)

    async def kafka_query_handler(self):
        try:
            async with asyncio.timeout(KAFKA_CONSUME_TIMEOUT_MS / 1000):
                msg: ConsumerRecord = await self.kafka_consumer.getone()
                logging.warning(f"Received message from Kafka topic: {msg.topic}")
                logging.warning(f"Message value: {msg.value}")
                query = json.loads(msg.value.decode('utf-8'))
                response = await self.get_query_state_response(query)
                # logging.warning(f"Response: {response}")
                await self.send_response(response)

        except TimeoutError:
            logging.info(f"No queries for {KAFKA_CONSUME_TIMEOUT_MS} ms")



    async def start_tcp_service(self):

        async def request_handler(reader: StreamReader, writer: StreamWriter):
            try:
                while True:
                    data = await reader.readexactly(8)
                    (size,) = unpack('>Q', data)
                    message = await reader.readexactly(size)
                    await self.add_task_to_queue(asyncio.get_event_loop().time(),self.query_state_controller(message))
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
        try:
            while True:
                # start the kafka consumer
                try:
                    logging.warning(f"Starting kafka consumer")
                    await self.kafka_consumer.start()
                    logging.warning(f"Starting kafka producer")
                    await self.kafka_producer.start()
                except (UnknownTopicOrPartitionError, KafkaConnectionError):
                    await asyncio.sleep(1)
                    logging.warning(f'Kafka at {KAFKA_URL} not ready yet, sleeping for 1 second')
                    continue
                break
            kafka_ingress_topic_name: str = 'query_processing'
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
            # Kafka Consumer ready to consume
            logging.warning(f"Starting coroutine")
            await self.received_workers.wait()
            asyncio.create_task(self.merge_scheduler())
            asyncio.create_task(self.kafka_query_scheduler())
            while True:
                await asyncio.sleep(1)
        except Exception as e:
            logging.error(traceback.format_exc())
        finally:
            await self.kafka_consumer.stop()


    async def get_query_state_response(self, query):
        logging.warning(f'query received: {query}')
        query_type = query['type']
        query_uuid = query['uuid']
        response={"uuid": query_uuid}

        if query_type =="GET_STATE":
            response ["epoch"]= self.latest_epoch_count
            response["state"] = self.state_store
        elif query_type == "GET_OPERATOR_STATE":
            operator = query['operator']
            logging.warning(f'operator: {operator}')
            operator_data = {}
            for (op, partition), data in self.state_store.items():
                if op == operator:
                    operator_data.update(data)
            response["epoch"] = self.latest_epoch_count
            response["operator_state"] = operator_data
        elif query_type == "GET_OPERATOR_PARTITION_STATE":
            operator = query['operator']
            partition = query['partition']
            operator_partition_data = {}
            for (op, part), data in self.state_store.items():
                if op == operator and part == partition:
                    operator_partition_data.update(data)
            response["epoch"] = self.latest_epoch_count
            response["operator_partition_state"] = operator_partition_data
        elif query_type == "GET_KEY_STATE":
            operator = query['operator']
            key = query['key']
            key_partition = self.get_partition(key)
            for(op, partition), data in self.state_store.items():
                if op == operator and partition == key_partition:
                    operator_key_data = data.get(key, None)
            response["epoch"] = self.latest_epoch_count
            response["operator_key_state"] = operator_key_data
        return response

    def get_partition(self, key) -> int | None:
        if key is None:
            return None
        return self.make_key_hashable(key) % self.total_workers

    @staticmethod
    def make_key_hashable(key) -> int:
        if isinstance(key, int):
            return key
        else:
            try:
                return cityhash.CityHash64(key)
            except Exception:
                raise NonSupportedKeyType()

    async def send_response(self, response):
        logging.warning("sending response to query topic")
        await self.kafka_producer.send_and_wait(KAFKA_QUERY_RESPONSE_TOPIC, json.dumps(response).encode('utf-8'))

    def start_networking_tasks(self):
        self.networking.start_networking_tasks()

    async def main(self):
        self.kafka_producer = AIOKafkaProducer(bootstrap_servers=KAFKA_URL,
                                               compression_type="gzip",
                                                max_batch_size=1048576,
                                               )
        self.kafka_consumer = AIOKafkaConsumer(bootstrap_servers=[KAFKA_URL])
        self.start_networking_tasks()
        asyncio.create_task(self.process_task_queue())
        asyncio.create_task(self.start_query_processing())
        await self.start_tcp_service()

if __name__ == "__main__":
    query_state_service = QueryStateService()
    asyncio.run(query_state_service.main())

