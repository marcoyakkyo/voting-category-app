from time import sleep
from pymongo import MongoClient
import streamlit as st


@st.cache_resource
def init_connection():
    return MongoClient(st.secrets["MONGO_URL"])[st.secrets["MONGO_DB_NAME"]]


@st.cache_data(ttl=30)
def get_data(_client: MongoClient) -> list:
    AGGREGATE_PRODUCTS = [
        {
            '$group': {
                '_id': '$categoryId', 
                'products': {
                    '$push': {
                        'id1688': '$id1688', 
                        'image': '$imgUrl', 
                        'title': '$title', 
                        'sales': '$soldOut'
                    }
                }, 
                'tot': {'$sum': 1}, 
                'tot_sales': {'$sum': '$soldOut'}
            }
        }, {
            '$addFields': {
                'products': {'$slice': ['$products', 10]}
            }
        }, {
            '$lookup': {
                'from': 'categories', 
                'localField': '_id', 
                'foreignField': 'categoryId', 
                'as': 'category'
            }
        }, {
            '$unwind': {
                'path': '$category', 
                'preserveNullAndEmptyArrays': False
            }
        }, {
            '$addFields': {
                'parentCateId': '$category.parentCateId', 
                'name': '$category.name'
            }
        }, {
            '$group': {
                '_id': '$parentCateId', 
                'sub_categories': {'$push': '$$ROOT'}
            }
        }, {
            '$lookup': {
                'from': 'categories', 
                'localField': '_id', 
                'foreignField': 'categoryId', 
                'as': 'parent'
            }
        }, {
            '$unwind': {
                'path': '$parent', 
                'preserveNullAndEmptyArrays': False
            }
        }, {
            '$addFields': {
                'name': '$parent.name', 
                'importance': '$parent.importance'
            }
        }, {
            '$project': {'parent': 0, "sub_categories.category": 0}
        }
    ]

    # check if already voted for this category
    voted_categories = list(_client["category_votes"].find({"email": st.session_state["user_email"]}, {"categoryId": 1}))
    voted_categories_ids = set(c["categoryId"] for c in voted_categories)
    print(f"Voted categories: {voted_categories_ids}")

    categories = list(_client["products_for_voting"].aggregate(AGGREGATE_PRODUCTS))
    categories.sort(key=lambda x: len(x["sub_categories"]), reverse=True)

    allowed_macro_categories = []

    for category in categories:
        # eliminate voted categories
        category["sub_categories"] = [c for c in category["sub_categories"] if c["_id"] not in voted_categories_ids]

        if "name" not in category:
            category["name"] = "All primary categories"

        if not len(category["sub_categories"]):
            continue
        
        category["sub_categories"].sort(key=lambda x: x["name"])

        for sub_category in category["sub_categories"]:
            # check unique
            sub_category["products"] = list({product["id1688"]: product for product in sub_category["products"]}.values())
            sub_category["categoryId"] = sub_category.pop("_id")
            for prod in sub_category["products"]:
                if not prod.get("image"):
                    prod["image"] = None

        allowed_macro_categories.append(category)

    return allowed_macro_categories


def on_vote(mongo_client: MongoClient, vote: str, sub_category: dict, idx_selected: int):

    query = {
        "email": st.session_state["user_email"],
        "categoryId": sub_category["categoryId"],
    }

    if mongo_client["category_votes"].find_one(query) is None:
        res = mongo_client["category_votes"].insert_one({
            "email": st.session_state["user_email"],
            "categoryId": sub_category["categoryId"],
            "name": sub_category["name"],
            "vote": vote,
        })
        if not res.acknowledged:
            st.error("Error submitting vote!")
            return None
    else:
        mongo_client["category_votes"].update_one(query, {"$set": {"vote": vote, "name": sub_category["name"]}})

    ## remove te sub_category from the macro
    new_allowd_sub_categories = [c for c in st.session_state["categories"][idx_selected]["sub_categories"] if c["name"] != sub_category["name"]]

    st.session_state["categories"][idx_selected]["sub_categories"] = new_allowd_sub_categories

    if not len(new_allowd_sub_categories):
        st.session_state["categories"] = [c for c in st.session_state["categories"] if c["name"] != st.session_state["macro_category_name"]]
        st.session_state["macro_category_name"] = None

    st.success("Vote submitted! 🎉")
    sleep(2)
    st.rerun()


def display_products(products: list):
    row = 0
    cols = st.columns(3)

    for prod in products[:9]:

        if row % 3 == 0 and row > 0:
            row = 0
            cols = st.columns(3)

        prod_link = f"https://detail.1688.com/offer/{prod['id1688']}.html"

        product_info = f"\nSales: {prod['sales']}\nTitle: {prod['title']}\n[Link to Product]({prod_link})"

        cols[row].image(prod["image"], caption=product_info, width=200) #, use_column_width=True
        row += 1


def get_results(client: MongoClient):

    category_votes = list(client["category_votes"].aggregate([
    {
        '$group': {
            '_id': '$categoryId', 
            'name': {'$first': '$name'}, 
            'total_votes': {'$sum': 1}, 
            'votes': {
                '$push': {'email': '$email', 'vote': '$vote'}
            }
        }
    }, {
        '$sort': {'total_votes': -1}
    }
    ]))

    for category in category_votes:
        category["categoryId"] = category.pop("_id")
        category["score"] = 0
        category["good_votes"] = 0
        category["mid_votes"] = 0
        category["bad_votes"] = 0
        category["users"] = list(set([v["email"] for v in category["votes"]]))

        for vote in category["votes"]:

            if vote["vote"] == "interesting":
                category["good_votes"] += 1
                category["score"] += 1
            elif vote["vote"] == "mid interesting":
                category["mid_votes"] += 1
                category["score"] += 0.5
            else:
                category["bad_votes"] += 1
                category["score"] -= 1

        category["total_votes"] = len(category["votes"])

    category_votes.sort(key=lambda x: x["score"], reverse=True)

    return category_votes


def get_bad_categories(client: MongoClient) -> list:
    category_votes = get_results(client)
    return [c["categoryId"] for c in category_votes if c["score"] < 0]


def get_confirmed_interesting(client: MongoClient) -> list:
    category_votes = get_results(client)
    return [c["categoryId"] for c in category_votes if c["score"] >= 1]


def get_confused_categories(client: MongoClient) -> list:
    category_votes = get_results(client)
    return [c["categoryId"] for c in category_votes if 0 <= c["score"] < 1]
