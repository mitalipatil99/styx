#!/bin/bash

python init_orders.py

locust -f locustfile.py --host="localhost" --processes 2