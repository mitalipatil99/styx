#!/bin/bash

docker compose logs worker > worker-logs.log
docker compose logs coordinator > coordinator-logs.log
docker compose logs querystate > querystate-logs.log

# DELETE PREVIOUS DEPLOYMENT
docker compose down --volumes --remove-orphans
docker compose -f docker-compose-kafka.yml down --volumes --remove-orphans
docker compose -f docker-compose-minio.yml down --volumes --remove-orphans
