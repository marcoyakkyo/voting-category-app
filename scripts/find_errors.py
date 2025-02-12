from pymongo import MongoClient

with open(".streamlit/secrets.toml") as f:
    toml_data = f.read()

MONGO_URL = toml_data.split("MONGO_URL = ")[1].split("\n")[0].replace('"', "").strip()
MONGO_DB_NAME = toml_data.split("MONGO_DB_NAME = ")[1].split("\n")[0].replace('"', "").strip()

client = MongoClient(MONGO_URL)[MONGO_DB_NAME]

email_1 = toml_data.split("EMAIL = ")[1].split("\n")[0].replace('"', "").strip()
email_2 = toml_data.split("EMAIL_2 = ")[1].split("\n")[0].replace('"', "").strip()

if __name__ == "__main__":

    votes_1 = client["category_votes"].find({"email": email_1})
    votes_2 = client["category_votes"].find({"email": email_2})

    # check which categories are voted by 1 but not by 2
    categories_1 = set([vote["categoryId"] for vote in votes_1])
    categories_2 = set([vote["categoryId"] for vote in votes_2])

    missing_votes = categories_1.difference(categories_2)

    print(len(categories_1), len(categories_2), len(missing_votes))

    print("\nCategories voted by 1 but not by 2:")
    for i, categoryId in enumerate(missing_votes):
        print(f"{i + 1}. {categoryId}")

    import json

    with open("missing_votes.json", "w") as f:
        json.dump(list(missing_votes), f, indent=4)

    # for each of those categories, find how many other users voted
    result = list(client["category_votes"].aggregate([
        {
            '$match': {
                'categoryId': {'$in': list(missing_votes)},
                'email': {"$ne": email_1}
            }
        }, {
            '$group': {
                '_id': '$categoryId', 
                'total_votes': {'$sum': 1}
            }
        }
    ]))

    print("got", len(result), "results")
    print(*result, sep="\n")


    # for each category in missing_votes, check if there are products associated into the "products_for_voting"
    prods = list(client["products_for_voting"].find(
        {"categoryId": {"$in": list(missing_votes)}},
        {"categoryId": 1, "id1688": 1, "_id": 0}
    ))

    print(len(prods), "products found")

    print(*prods[:3], sep="\n")

    # check how many of the missing categories are first-level categories
    first_level_categories = list(client["categories"].find({"parentCateId": "0"}, {"categoryId": 1}))

    first_level_categories_ids = set([c["categoryId"] for c in first_level_categories])

    print("First level categories:", len(first_level_categories_ids))

    missing_first_level = missing_votes.intersection(first_level_categories_ids)
    print("Missing first level categories:", len(missing_first_level))
    print("while total missing votes are", len(missing_votes))

    # eliminate votes from those missing categories
    res = client["category_votes"].delete_many({"categoryId": {"$in": list(missing_votes)}})
    print(res.deleted_count, "votes deleted")
