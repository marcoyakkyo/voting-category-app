from pymongo import MongoClient
import streamlit as st

@st.cache_resource
def init_connection():
    return MongoClient(st.secrets["MONGO_URL"])[st.secrets["MONGO_DB_NAME"]]

@st.cache_data(ttl=600)
def get_data(_client: MongoClient) -> list:

    AGGREGATE_PRODUCTS = [
        {
            '$group': {
                '_id': '$categoryId', 
                'products': {
                    '$push': {
                        'id1688': '$masterId', 
                        'image': '$image', 
                        'productIds': '$productIds', 
                        'title': '$title', 
                        'price': '$price', 
                        'sales': '$sales'
                    }
                }, 
                'tot': {'$sum': 1}, 
                'tot_sales': {'$sum': '$sales'}
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
                'preserveNullAndEmptyArrays': True
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

    categories = list(_client["hot1688_winning_products"].aggregate(AGGREGATE_PRODUCTS))
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
                prod["group_size"] = len(prod.pop("productIds"))
                if not prod.get("image"):
                    prod["image"] = None

        allowed_macro_categories.append(category)

    return allowed_macro_categories

