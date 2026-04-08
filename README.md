# Microservice-based Data Aggregator Project
Created for ACIT 3855 (Service Based Architecture) during the Winter 2026 term at BCIT.

## Table of Contents
- [Huh?](#huh)
  - [Why am I publishing this on GitHub?](#why-am-i-publishing-this-on-github)
- [Local Deployment Instructions](#local-deployment-instructions)
- [Service Overview](#service-overview)
  - [Public](#public)
    - [Dashboard (Port `8000`)](#dashboard-port-8000)
    - [Receiver API (Port `8080`)](#receiver-api-port-8080)
    - [Processor API (Port `8100`)](#processor-api-port-8100)
    - [Analyzer API (Port `8110`)](#analyzer-api-port-8110)
    - [Health Status API (Port `8120`)](#health-status-api-port-8120)
  - [Internal](#internal)
    - [Storage Service](#storage-service)
    - [Storage Database](#storage-database)
    - [Kafka](#kafka)

## Huh?
This was a course-long project where we had to design and implement a microservice-based application that receives/stores/processes data from ✨*something*✨. I chose smart plugs!

For the love of all things, don't actually use this.

### Why am I publishing this on GitHub?
Mainly because it's easier to demo if I can just clone and run it on a random cloud VM ¯\\\_(ツ)\_/¯

## Local Deployment Instructions
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
    http://<your-docker-host>:8000
    ```

## Service Overview
### Public
#### Dashboard (Port `8000`)
Super simple single-page web application that lets you view some basic info about the services and the data they're collecting.

#### Receiver API (Port `8080`)
A simple two-endpoint REST API that receives data from smart plugs (or jMeter, in my case) and sends it to the internal storage service via Kafka.

#### Processor API (Port `8100`)
Another simple REST API that periodically queries the internal storage service for new data, calculates some basic statistics, and provides an endpoint for the dashboard to query them.

#### Analyzer API (Port `8110`)
A REST API with three endpoints that acts as a window into Kafka, providing event counts and index-based queries for raw messages.

#### Health Status API (Port `8120`)
A single endpoint on `/status` that reports which services are responsive.

### Internal
#### Storage Service
A service that consumes messages from Kafka and stores them in the configured database (MySQL in this case). It also provides a simple REST API for querying the stored data, which is used by the processor API.

#### Storage Database
The database used by the storage service. Currently configured to use MySQL, but could be swapped out as needed.

#### Kafka
The message broker used for scalable asynchronous communication between the receiver API and the storage service.