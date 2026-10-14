
const uri =
  "mongodb://mongo1:27017,mongo2:27017,mongo3:27017/" +
  "?replicaSet=rs0";

const client = new Mongo(uri);
const lab = client.getDB("replication_lab");

const accounts = lab.e5_accounts;
const audit = lab.e5_audit;

const runId = "E5_TX_SAGA_" + Date.now();

function balance(id) {
  const record = accounts.findOne({
    run_id: runId,
    account: id
  });
  return record.balance;
}

function showBalances(label) {
  print(label);
  print("A:", balance("A"));
  print("B:", balance("B"));
  print("Total:", balance("A") + balance("B"));
}

accounts.insertMany([
  { run_id: runId, account: "A", balance: 1000 },
  { run_id: runId, account: "B", balance: 1000 }
]);

print("=== MONGODB TRANSACTION VS SAGA ===");
print("Run ID:", runId);

showBalances("\nINITIAL BALANCES");

print("\n=== PART A: FAILED ACID TRANSACTION ===");

const session = client.startSession();
const txdb = session.getDatabase("replication_lab");
const txAccounts = txdb.e5_accounts;
const txAudit = txdb.e5_audit;

let transactionFailed = false;

try {
  session.startTransaction({
    readConcern: { level: "snapshot" },
    writeConcern: { w: "majority" }
  });

  txAccounts.updateOne(
    { run_id: runId, account: "A" },
    { $inc: { balance: -200 } }
  );

  txAccounts.updateOne(
    { run_id: runId, account: "B" },
    { $inc: { balance: 200 } }
  );

  txAudit.insertOne({
    run_id: runId,
    method: "transaction",
    status: "transfer attempted"
  });

  throw new Error("Simulated failure before commit");

} catch (error) {
  transactionFailed = true;
  print("Expected transaction failure:", error.message);
  session.abortTransaction();
} finally {
  session.endSession();
}

showBalances("BALANCES AFTER TRANSACTION ABORT");

print("Transaction failure detected:", transactionFailed);

print("Committed transaction audit records:",
  audit.countDocuments({
    run_id: runId,
    method: "transaction"
  })
);

print("\n=== PART B: FAILED SAGA WITH COMPENSATION ===");

let sagaFailed = false;
let compensated = false;

try {
  // Step 1 commits independently.
  accounts.updateOne(
    { run_id: runId, account: "A" },
    { $inc: { balance: -200 } }
  );

  print("Saga Step 1 committed: debited A by 200");

  // Simulate failure before crediting account B.
  throw new Error("Simulated failure before crediting B");

} catch (error) {
  sagaFailed = true;
  print("Expected saga failure:", error.message);

  // Compensating action reverses the debit.
  accounts.updateOne(
    { run_id: runId, account: "A" },
    { $inc: { balance: 200 } }
  );

  compensated = true;

  audit.insertOne({
    run_id: runId,
    method: "saga",
    status: "compensated"
  });

  print("Compensation completed: restored A by 200");
}

showBalances("BALANCES AFTER SAGA COMPENSATION");

print("Saga failure detected:", sagaFailed);
print("Compensation executed:", compensated);

print("Saga compensation audit records:",
  audit.countDocuments({
    run_id: runId,
    method: "saga",
    status: "compensated"
  })
);

print("\n=== FINAL VERIFICATION ===");

const finalA = balance("A");
const finalB = balance("B");

print("Transaction rollback successful:",
  transactionFailed &&
  audit.countDocuments({
    run_id: runId,
    method: "transaction"
  }) === 0
);

print("Saga restored original balances:",
  sagaFailed &&
  compensated &&
  finalA === 1000 &&
  finalB === 1000
);

print("Total funds preserved:", finalA + finalB === 2000);

print("\n=== TRANSACTION VS SAGA COMPLETE ===");

client.close();
