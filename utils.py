import pandas as pd


def build_product_dataframe(products):
    data = {
        "Name": [],
        "Price": [],
        "Image": [],
    }

    for product in products:
        data["Name"].append(product["title"])
        data["Price"].append(product["price"])
        data["Image"].append(product["image"])
    
    return pd.DataFrame(data)


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
            'category_name': '$category.name'
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

