# Microservice-based Data Aggregator Project
Created for ACIT 3855 (Service Based Architecture) during the Winter 2026 term at BCIT.

## Table of Contents
- [Huh?](#huh)
  - [Why am I publishing this on GitHub?](#why-am-i-publishing-this-on-github)
- [Deployment Instructions](#deployment-instructions)
  - [Locally (via Docker Compose)](#locally-via-docker-compose)
  - [Cloud (via AWS EC2)](#cloud-via-aws-ec2)
  - [Configuration](#configuration)
- [Service Overview](#service-overview)
  - [Public](#public)
    - [Dashboard (Port `80`)](#dashboard-port-80)
  - [Proxied](#proxied)
    - [Receiver API (`/receiver`)](#receiver-api-receiver)
    - [Processor API (`/processor`)](#processor-api-processor)
    - [Analyzer API (`/analyzer`)](#analyzer-api-analyzer)
    - [Health Status API (`/healthcheck`)](#health-status-api-healthcheck)
  - [Internal](#internal)
    - [Storage Service](#storage-service)
    - [Storage Database](#storage-database)
    - [Kafka](#kafka)

## Huh?
This was a course-long project where we had to design and implement a microservice-based application that receives/stores/processes data from ✨*something*✨. I chose smart plugs!

For the love of all things, don't actually use this.

### Why am I publishing this on GitHub?
Mainly because it's easier to demo if I can just clone and run it on a random cloud VM ¯\\\_(ツ)\_/¯

## Deployment Instructions
### Locally (via Docker Compose)
> [!NOTE]
> This requires:
> - Docker
> - Docker Compose
> - Port `80` to be free on the host machine (or you can change it in `docker-compose.yml`)

1. Clone!
    ```bash
    git clone https://github.com/Tredecate/smartplug-msa-project.git
    ```

2. Navigate!
    ```bash
    cd smartplug-msa-project
    ```

3. Run!
    ```bash
    docker compose up -d
    ```

4. Browse! (To the dashboard)
    ```
    http://<your-docker-host>:80
    ```

### Cloud (via AWS EC2)
> [!NOTE]
> This requires:
> - Ansible
> - Terraform
> - AWS credentials configured for Terraform

1. Clone!
    ```bash
    git clone https://github.com/Tredecate/smartplug-msa-project.git
    ```

2. Navigate!
    ```bash
    cd smartplug-msa-project/_deployment
    ```

3. Run!
    ```bash
    ./deploy.sh [--auto|-y]
    ```

4. Browse! (To the dashboard)
    ```
    http://<your-cloud-host>:80
    ```

### Configuration
All services have a variety of configuration options for logging, connectivity, and other settings.
- All configuration files can be found in the [`/_mounts/config/`](./_mounts/config/) directory.
- Additional configuration can be done in [`docker-compose.yml`](./docker-compose.yml).

> [!WARNING]
> Some settings may require changes in both locations to work correctly!

Environment variable `CORS_ALLOW_ALL` can be set to `true` to remove CORS restrictions on Processor/Analyzer/Healthcheck APIs (or you can set specific allowed origins in the respective config files).

## Service Overview
### Public
#### Dashboard (Port `80`)
- An nginx container that serves two purposes:
  - Serving a super simple single-page web application that lets you view some basic info about the services and the data they're collecting.
  - Acting as a reverse proxy to the other public APIs

### Proxied
#### Receiver API (`/receiver`)
- A simple two-endpoint REST API that receives data from smart plugs (or jMeter, in my case) and sends it to the internal storage service via Kafka.
- Internally listens on port `8080`
- Is configured by default to create 3 replicas for basic load balancing, which can be changed in [`docker-compose.yml`](./docker-compose.yml).

#### Processor API (`/processor`)
- Another simple REST API that periodically queries the internal storage service for new data, calculates some basic statistics, and provides an endpoint for the dashboard to query them.
- Internally listens on port `8100`

#### Analyzer API (`/analyzer`)
- A REST API with three endpoints that acts as a window into Kafka, providing event counts and index-based queries for raw messages.
- Internally listens on port `8110`

#### Health Status API (`/healthcheck`)
- An API with a single endpoint at `service_url/status` that reports which services are responsive.
- Internally listens on port `8120`

### Internal
#### Storage Service
- A service that consumes messages from Kafka and stores them in the configured database (MySQL in this case). It also provides a simple REST API for querying the stored data, which is used by the processor API.
- Internally listens on port `8090`
- Is configured by default to create 2 replicas for basic load balancing, which can be changed in [`docker-compose.yml`](./docker-compose.yml).
  - Note that the Kafka partitions are set to match, so additional replicas will require changes to both `storage_svc` and `kafka` in [`docker-compose.yml`](./docker-compose.yml) to work correctly.

#### Storage Database
- The database used by the storage service. Currently configured to use MySQL, but could be swapped out as needed.

#### Kafka
- The message broker used for scalable asynchronous communication between the receiver API and the storage service.
