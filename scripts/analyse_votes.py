from pymongo import MongoClient

from src import utils

with open(".streamlit/secrets.toml") as f:
    toml_data = f.read()

MONGO_URL = toml_data.split("MONGO_URL = ")[1].split("\n")[0].replace('"', "").strip()
MONGO_DB_NAME = toml_data.split("MONGO_DB_NAME = ")[1].split("\n")[0].replace('"', "").strip()

client = MongoClient(MONGO_URL)[MONGO_DB_NAME]

if __name__ == "__main__":

    votes = utils.get_results(client)
    print(f"\nCollected {sum([doc["total_votes"] for doc in votes])} votes on a total of {len(list(votes))} categories")

    print("\nTop 5 categories by score:")
    for i, vote in enumerate(list(votes)[:5]):
        print(f"{i + 1}. {vote['categoryId']} - {vote['name']} - score = {vote['score']}")

    # set the categories with score >= 1 as "confirmed interesting",
    # and the ones with score < 0 as "confirmed not interesting"
    # and the ones in between as "confused"

    confirmed_interesting, confirmed_not_interesting, confused = [], [], []

    for vote in votes:
        if vote["score"] >= 1:
            confirmed_interesting.append(str(vote["categoryId"]))
        elif vote["score"] < 0:
            confirmed_not_interesting.append(str(vote["categoryId"]))
        else:
            confused.append(str(vote["categoryId"]))

    print("\nConfirmed interesting categories:", len(confirmed_interesting))
    print("Confirmed not interesting categories:", len(confirmed_not_interesting))
    print("Confused categories:", len(confused))

    # exit(0)

    # first, unset the confirmation_status field for all categories
    client["categories"].update_many(
        {"confirmation_status": {"$exists": True}},
        {"$unset": {"confirmation_status": ""}}
    )

    res = client["categories"].update_many(
        {"categoryId": {"$in": confirmed_interesting}}, 
        {"$set": {"confirmation_status": 1}}
    )
    print("Updated", res.modified_count, "categories as confirmed interesting")
    res = client["categories"].update_many(
        {"categoryId": {"$in": confirmed_not_interesting}}, 
        {"$set": {"confirmation_status": -1}}
    )
    print("Updated", res.modified_count, "categories as confirmed not interesting")
    res = client["categories"].update_many(
        {"categoryId": {"$in": confused}}, 
        {"$set": {"confirmation_status": 0}}
    )
    print("Updated", res.modified_count, "categories as confused")

    # make an histogram of the votes
    import matplotlib.pyplot as plt
    all_votes = [vote["score"] for vote in votes]

    plt.title("Histogram of categories scores")
    plt.hist(all_votes, bins=range(int(min(all_votes)) - 1, int(max(all_votes)) + 2, 1), alpha=0.75)
    plt.xticks(range(int(min(all_votes)) - 1, int(max(all_votes)) + 2, 1))
    plt.xlabel("Score")
    plt.ylabel("Number of categories")
    plt.grid(True)
    plt.savefig("scripts/categories_scores.png")

    print("\nConfused categories:")
    for categoryId in confused:
        # find back the name by iteraing over the votes
        for vote in votes:
            if vote["categoryId"] == categoryId:
                print(f"\t{categoryId}\t{vote['name']}")
                break

    # erase all products from hot1688_winning_products that are in the confirmed non-interesting categories
    res = client["hot1688_winning_products"].delete_many(
        {"categoryId": {"$in": confirmed_not_interesting}}
    )
    print("\nDeleted", res.deleted_count, "products from the confirmed not interesting categories")
