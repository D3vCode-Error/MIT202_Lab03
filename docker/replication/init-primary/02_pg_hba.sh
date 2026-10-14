#!/bin/bash
set -e

echo "host replication replicator all scram-sha-256" \
  >> "$PGDATA/pg_hba.conf"