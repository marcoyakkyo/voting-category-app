
import os
from dotenv import load_dotenv
from pymongo import MongoClient
from time import sleep

import streamlit as st

from src import auth, utils

load_dotenv(override=True)

# ---------------------------- AUTH CHECKS ----------------------------
if os.getenv("DEBUG", "").lower() == "true":
    print("Running in debug mode, skipping password check.")
    st.session_state["password_correct"] = True
    st.session_state["user_email"] = os.getenv("DEFAULT_EMAIL")
    pass # skip password check in debug mode

elif not auth.check_password():
    print("Password incorrect, stopping the script.")
    st.stop()  # Do not continue if check_password is not True.

elif not auth.check_email():
    print("Email incorrect, stopping the script.")
    st.stop()


st.write(f"Welcome, {st.session_state['user_email']}!")


## ---------------------------- MONGO ----------------------------

mongo_client = utils.init_connection()

all_categories = utils.get_data(mongo_client)

if "categories" not in st.session_state:
    st.session_state["categories"] = all_categories

print(f"Collected Categories: {len(st.session_state['categories'])}: {st.session_state['categories'][0].keys()}")

# for testing, delete all votes of the user
if os.getenv("DEBUG", "").lower() == "true" and not st.session_state.get("already_deleted", False):
    mongo_client["category_votes"].delete_many({"email": st.session_state["user_email"]})
    st.session_state["already_deleted"] = True

# ---------------------------- VOTING APP ----------------------------
st.write("# Voting App")

already_selected = st.session_state.get("macro_category_name", None)

idx_selected = 0 if not already_selected else \
    [c["name"] for c in st.session_state["categories"]].index(already_selected)

macro_category_name = st.selectbox("Pick a MACRO category", list([f'{c["name"]} - ({len(c["sub_categories"])} sub categories)' for c in st.session_state["categories"]]), index= idx_selected)

if not macro_category_name:
    macro_category_name = st.session_state["categories"][0]["name"]
else:
    macro_category_name = macro_category_name.split(" - (")[0]

macro_category = next(c for c in st.session_state["categories"] if c["name"] == macro_category_name)

st.session_state["macro_category_name"] = macro_category_name

# ask to select a sub category
sub_categories = macro_category["sub_categories"]
sub_category_name = st.selectbox("Pick a sub category", [c["name"] for c in sub_categories])
sub_category = next(c for c in sub_categories if c["name"] == sub_category_name)


## ---------------------------- VOTING ----------------------------
vote = st.radio("How interesting is this category?", ["interesting", "mid interesting", "not interesting"])


# Submit the vote
if st.button("Submit vote"):
    vote_data = {
        "email": st.session_state["user_email"],
        "categoryId": sub_category["categoryId"],
        "name": sub_category["name"],
        "vote": vote,
    }
    mongo_client["category_votes"].insert_one(vote_data)

    ## remove te sub_category from the macro
    print("Initial sub categories:", len(st.session_state["categories"][idx_selected]["sub_categories"]))

    new_allowd_sub_categories = [c for c in st.session_state["categories"][idx_selected]["sub_categories"] if c["name"] != sub_category_name]
    print("New allowed sub categories:", len(new_allowd_sub_categories))

    print("before:", len(st.session_state["categories"][idx_selected]["sub_categories"]))

    st.session_state["categories"][idx_selected]["sub_categories"] = new_allowd_sub_categories

    print(f"after: {len(st.session_state['categories'][idx_selected]['sub_categories'])}")

    if not len(new_allowd_sub_categories):
        st.session_state["categories"] = [c for c in st.session_state["categories"] if c["name"] != macro_category_name]
        st.session_state["macro_category_name"] = None
        print("Removed category from the list")

    st.success("Vote submitted! 🎉")
    print("Vote submitted!")
    sleep(2)
    st.rerun()


# ---------------------------- DISPLAY ----------------------------
st.title(f'Products in "{macro_category_name}" -> "{sub_category_name}"')
row = 0
cols = st.columns(3)
for prod in sub_category["products"][:9]:

    if row % 3 == 0 and row > 0:
        row = 0
        cols = st.columns(3)

    prod_price = f'{float(prod["price"])* 0.13:.2f} $'
    prod_link = f"https://detail.1688.com/offer/{prod['id1688']}.html"

    product_info = f"Price: {prod_price}\nSales: {prod['sales']}\nGroup size: {prod['group_size']}\n[View product]({prod_link})"

    cols[row].image(prod["image"], caption=product_info, width=200) #, use_column_width=True
    row += 1

    ## or use this
    # st.image(prod["image"], caption=prod_price, width=150)
    # st.write(product_info)
    # st.write("___________________________")


