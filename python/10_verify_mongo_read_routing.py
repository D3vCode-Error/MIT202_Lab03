
from pymongo import MongoClient, ReadPreference

URI = (
    "mongodb://mongo1:27017,mongo2:27017,mongo3:27017/"
    "?replicaSet=rs0"
)

preferences = {
    "primary": ReadPreference.PRIMARY,
    "primaryPreferred": ReadPreference.PRIMARY_PREFERRED,
    "secondary": ReadPreference.SECONDARY,
}

client = MongoClient(
    URI,
    serverSelectionTimeoutMS=10000
)

database = client["replication_lab"]

for name, preference in preferences.items():
    db = database.with_options(read_preference=preference)

    print(f"\nRead preference: {name}")

    for trial in range(1, 6):
        result = db.command(
            {"hello": 1},
            read_preference=preference
        )

        print({
            "trial": trial,
            "server": result.get("me"),
            "is_primary": result.get("isWritablePrimary"),
            "is_secondary": result.get("secondary"),
        })

client.close()
