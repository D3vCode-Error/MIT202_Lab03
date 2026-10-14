\# Laboratory Activity No. 03 — Advanced System Design and Implementation



\## Project Overview



This repository contains the scripts, Docker configurations, and experimental results I used to evaluate relational and non-relational database systems for a simulated e-commerce application.



The laboratory covers PostgreSQL 16, MongoDB 7, Redis 7.2, Python, and Docker.



\## Laboratory Exercises



1\. \*\*Relational vs. Non-Relational Data Models:\*\* I compared PostgreSQL with embedded and referenced MongoDB document models.

2\. \*\*Replication:\*\* I configured PostgreSQL synchronous/asynchronous streaming replication and a three-member MongoDB replica set.

3\. \*\*Partitioning and Sharding:\*\* I evaluated PostgreSQL range/hash partitioning and MongoDB hashed/ranged shard keys.

4\. \*\*Caching:\*\* I tested Redis cache-aside, write-through consistency, stampede mitigation, and LRU versus LFU.

5\. \*\*ACID and BASE:\*\* I conducted transaction, isolation, durability, replica-consistency, and network-partition experiments.



\## Dataset



I used synthetic e-commerce data containing:



\- 100,000 customers

\- 1,000,000 orders

\- 3,000,000 order items



\## Repository Contents



\- `docker/` — container configurations

\- `sql/` — SQL scripts

\- `python/` — benchmark and monitoring scripts

\- `results/` — experimental output files

\- `evidence/` — screenshot evidence

\- `report/` — report files, where included



\## Software Requirements



\- Docker Desktop

\- PostgreSQL 16

\- MongoDB 7

\- Redis 7.2

\- Python 3 with required libraries

\- Windows PowerShell



\## Reproducibility Notes



The recorded results were obtained from my local experimental environment. Performance measurements can vary depending on system hardware, caching, concurrency, and container resources.



Destructive tests, database failover, and network-isolation experiments require separate test environments or appropriate safeguards. Running the scripts without reviewing their configuration may alter or delete test data.



\## Academic and AI-Use Disclosure



I performed the laboratory execution and collected the measurements in my local environment. AI assistance was used for portions of script development, troubleshooting, and report drafting. Experimental results were reviewed against the recorded terminal outputs and screenshots.

