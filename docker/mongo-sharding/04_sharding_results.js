
const lab = db.getSiblingDB("sharding_lab");

print("=== DOCUMENT COUNTS ===");
print("Hashed:", lab.orders_hashed.countDocuments({}));
print("Ranged:", lab.orders_ranged.countDocuments({}));

print("\n=== HASHED SHARD DISTRIBUTION ===");
lab.orders_hashed.getShardDistribution();

print("\n=== RANGED SHARD DISTRIBUTION ===");
lab.orders_ranged.getShardDistribution();

const tests = [
  {
    name: "Hashed - Customer Filter",
    collection: "orders_hashed",
    filter: { customer_id: 42 }
  },
  {
    name: "Ranged - Customer Filter",
    collection: "orders_ranged",
    filter: { customer_id: 42 }
  },
  {
    name: "Hashed - Date Filter",
    collection: "orders_hashed",
    filter: {
      order_date: {
        $gte: ISODate("2026-04-01T00:00:00Z"),
        $lt: ISODate("2026-07-01T00:00:00Z")
      }
    }
  },
  {
    name: "Ranged - Date Filter",
    collection: "orders_ranged",
    filter: {
      order_date: {
        $gte: ISODate("2026-04-01T00:00:00Z"),
        $lt: ISODate("2026-07-01T00:00:00Z")
      }
    }
  }
];

for (const test of tests) {
  const explain = lab
    .getCollection(test.collection)
    .find(test.filter)
    .explain("executionStats");

  print("\n=== " + test.name + " ===");
  print("Execution time (ms):",
        explain.executionStats.executionTimeMillis);
  print("Documents returned:",
        explain.executionStats.nReturned);
  print("Documents examined:",
        explain.executionStats.totalDocsExamined);

  print("Winning query plan:");
  printjson(explain.queryPlanner.winningPlan);
}

print("\n=== EXERCISE 3 COMPLETE ===");
