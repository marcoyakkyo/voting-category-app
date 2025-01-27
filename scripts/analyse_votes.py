from pymongo import MongoClient

with open(".streamlit/secrets.toml") as f:
    toml_data = f.read()

MONGO_URL = toml_data.split("MONGO_URL = ")[1].split("\n")[0].replace('"', "").strip()
MONGO_DB_NAME = toml_data.split("MONGO_DB_NAME = ")[1].split("\n")[0].replace('"', "").strip()

client = MongoClient(MONGO_URL)[MONGO_DB_NAME]

if __name__ == "__main__":

    votes = list(client["category_votes"].aggregate([{
        '$group': {
            '_id': '$categoryId', 
            'name': {'$first': '$name'}, 
            'total_votes': {'$sum': 1}, 
            'bad_votes': {
                '$sum': {'$cond': [{'$eq': ['$vote', 'not interesting']}, 1, 0]}
            }, 
            'good_votes': {
                '$sum': {'$cond': [{'$eq': ['$vote', 'interesting']}, 1, 0]}
            }, 
            'mid_votes': {
                '$sum': {'$cond': [{'$eq': ['$vote', 'mid interesting']}, 1, 0]}
            }, 
            'users': {
                '$push': '$email'
            }
        }
    }, {
        '$sort': {
            'total_votes': -1, 
            'good_votes': -1
        }
    }]))

    print(f"\nCollected {sum([doc["total_votes"] for doc in votes])} votes on a total of {len(list(votes))} categories")

    print("\nTop 5 categories by total votes:")    
    for i, vote in enumerate(list(votes)[:5]):
        print(f"{i + 1}. {vote['name']} - {vote['total_votes']} votes")

    votes.sort(key=lambda x: x["good_votes"], reverse=True)
    print("\nTop 5 categories by good votes:")
    for i, vote in enumerate(list(votes)[:5]):
        print(f"{i + 1}. {vote['name']} - {vote['good_votes']} good votes")

    votes.sort(key=lambda x: x["bad_votes"], reverse=True)
    print("\nTop 5 categories by bad votes:")
    for i, vote in enumerate(list(votes)[:5]):
        print(f"{i + 1}. {vote['name']} - {vote['bad_votes']} bad votes")

    for vote in votes:
        vote["score"] = vote["good_votes"] + 0.5 * vote["mid_votes"] - vote["bad_votes"]

    votes.sort(key=lambda x: x["score"], reverse=True)

    print("\nTop 5 categories by score:")
    for i, vote in enumerate(list(votes)[:5]):
        print(f"{i + 1}. {vote['_id']} - {vote['name']} - score = {vote['score']}")

    # set the categories with score >= 1 as "confirmed interesting",
    # and the ones with score < 0 as "confirmed not interesting"
    # and the ones in between as "confused"

    confirmed_interesting, confirmed_not_interesting, confused = [], [], []

    for vote in votes:
        if vote["score"] >= 1:
            confirmed_interesting.append(str(vote["_id"]))
        elif vote["score"] < 0:
            confirmed_not_interesting.append(str(vote["_id"]))
        else:
            confused.append(str(vote["_id"]))

    print("\nConfirmed interesting categories:", len(confirmed_interesting))
    print("Confirmed not interesting categories:", len(confirmed_not_interesting))
    print("Confused categories:", len(confused))

    exit(0)

    client["categories"].update_many(
        {"categoryId": {"$in": confirmed_interesting}}, 
        {"$set": {"confirmation_status": "confirmed_interesting"}}
    )
    client["categories"].update_many(
        {"categoryId": {"$in": confirmed_not_interesting}}, 
        {"$set": {"confirmation_status": "confirmed_not_interesting"}}
    )
    client["categories"].update_many(
        {"categoryId": {"$in": confused}}, 
        {"$set": {"confirmation_status": "confused"}}
    )
