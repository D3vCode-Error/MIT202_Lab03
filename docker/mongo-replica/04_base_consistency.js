
const primaryConn = new Mongo(
  "mongodb://mongo1:27017,mongo2:27017,mongo3:27017/" +
  "?replicaSet=rs0&readPreference=primary"
);

const secondaryConn = new Mongo(
  "mongodb://mongo3:27017/" +
  "?directConnection=true&readPreference=secondary"
);

const primary = primaryConn.getDB("replication_lab");
const secondary = secondaryConn.getDB("replication_lab");

const collection = primary.base_visibility;
const secondaryCollection = secondary.base_visibility;

const runId = "E5_BASE_" + Date.now();
const total = 100;
let staleReads = 0;
let immediatelyVisible = 0;
let convergenceFailures = 0;
const convergenceTimes = [];

print("=== MONGODB BASE AND EVENTUAL CONSISTENCY ===");
print("Run ID:", runId);
print("Total tests:", total);

for (let i = 1; i <= total; i++) {
  const id = runId + "_" + i;

  const result = collection.insertOne(
    {
      _id: id,
      sequence: i,
      created_at: new Date()
    },
    { writeConcern: { w: 1 } }
  );

  if (!result.acknowledged) {
    throw new Error("Write not acknowledged: " + id);
  }

  const start = Date.now();

  const immediate = secondaryCollection.findOne({ _id: id });

  if (immediate === null) {
    staleReads++;
  } else {
    immediatelyVisible++;
  }

  let converged = immediate !== null;

  const deadline = Date.now() + 10000;

  while (!converged && Date.now() < deadline) {
    sleep(5);
    converged =
      secondaryCollection.findOne({ _id: id }) !== null;
  }

  if (converged) {
    convergenceTimes.push(Date.now() - start);
  } else {
    convergenceFailures++;
  }
}

convergenceTimes.sort((a, b) => a - b);

function percentile(values, percentage) {
  if (values.length === 0) return null;
  const index = Math.ceil(
    percentage / 100 * values.length
  ) - 1;
  return values[Math.max(0, index)];
}

print("\n=== OBSERVED RESULTS ===");
print("Writes attempted:", total);
print("Immediately visible:", immediatelyVisible);
print("Stale immediate reads:", staleReads);
print("Convergence failures:", convergenceFailures);
print("Converged within timeout:",
      convergenceTimes.length);
print("Convergence p50 (ms):",
      percentile(convergenceTimes, 50));
print("Convergence p95 (ms):",
      percentile(convergenceTimes, 95));
print("Maximum convergence time (ms):",
      convergenceTimes.length
        ? convergenceTimes[convergenceTimes.length - 1]
        : null);

print("\n=== BASE EXPERIMENT COMPLETE ===");
