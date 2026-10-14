
const database = db.getSiblingDB("replication_lab");

const cases = [
  { name: "w1", w: 1 },
  { name: "majority", w: "majority" },
  { name: "w3", w: 3 }
];

const TOTAL = 1000;
const results = [];

print("MongoDB Write Concern Benchmark");
print("Replica set: rs0");
print("Operations per test: " + TOTAL);
print("Start time: " + new Date().toISOString());

const hello = db.adminCommand({ hello: 1 });

if (!hello.isWritablePrimary) {
  throw new Error("Connected node is not PRIMARY.");
}

for (const test of cases) {
  const collectionName = "write_test_" + test.name;
  const collection = database.getCollection(collectionName);

  collection.drop();

  let successful = 0;
  let failed = 0;
  let firstError = "";

  // Use 1000 individually acknowledged writes.
  const started = Date.now();

  for (let i = 1; i <= TOTAL; i++) {
    try {
      const response = collection.insertOne(
        {
          test_case: test.name,
          sequence: i,
          value: "LAB03",
          created_at: new Date()
        },
        {
          writeConcern: {
            w: test.w,
            wtimeout: 10000
          }
        }
      );

      if (response.acknowledged) {
        successful++;
      } else {
        failed++;
      }
    } catch (error) {
      failed++;

      if (!firstError) {
        firstError = String(error);
      }
    }
  }

  const durationMs = Date.now() - started;
  const count = collection.countDocuments({});

  const result = {
    write_concern: test.name,
    total_attempted: TOTAL,
    acknowledged_writes: successful,
    failed_writes: failed,
    stored_documents: count,
    duration_ms: durationMs,
    average_ms_per_write: +(durationMs / TOTAL).toFixed(3),
    first_error: firstError
  };

  results.push(result);

  print("\nRESULT " + test.name);
  printjson(result);
}

print("\nFINAL_BENCHMARK_RESULTS");
printjson(results);
print("End time: " + new Date().toISOString());
