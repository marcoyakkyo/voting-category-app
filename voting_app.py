import os
from dotenv import load_dotenv
from collections import defaultdict
import streamlit as st

from src import auth, utils

load_dotenv(override=True)

# ---------------------------- AUTH CHECKS ----------------------------
if os.getenv("DEBUG", "").lower() == "true":
    print("Running in debug mode, skipping password check.")
    st.session_state["password_correct"] = True
    st.session_state["user_email"] = os.getenv("DEFAULT_EMAIL")
    pass      # skip password check in debug mode

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

print("Num categories", len(all_categories))

st.session_state["show_results"] = st.checkbox("Show results", False)

has_finished = len(st.session_state["categories"]) == 0 and mongo_client["category_votes"].find_one({"email": st.session_state["user_email"]}) is not None

if st.session_state["show_results"] or has_finished:

    st.write("No more categories to vote on!") \
        if has_finished else \
    st.write("Showing results...")

    category_votes = utils.get_results(mongo_client)

    user_votes = defaultdict(lambda: defaultdict(int))

    for category in category_votes:
        for vote in category.pop("votes"):
            user_votes[vote["email"]][vote["vote"]] += 1

    for user, votes in user_votes.items():
        user_votes[user] = dict(votes)
        user_votes[user]["total"] = sum(votes.values())

    st.write("Here are the users that already voted:")
    st.write(dict(user_votes))

    st.write("Here are the results by category:")
    st.write(category_votes)

else:

    print(f"Collected Categories: {len(st.session_state['categories'])}")

    # for testing, delete all votes of the test user
    if os.getenv("DEBUG", "").lower() == "true" and not st.session_state.get("already_deleted", False):
        mongo_client["category_votes"].delete_many({"email": st.session_state["user_email"]})
        st.session_state["already_deleted"] = True

    # ---------------------------- Selecting Categories ----------------------------
    st.write("# Voting App")
    st.write(f"You still have to vote on {sum([len(c['sub_categories']) for c in st.session_state['categories']])} sub-categories")

    already_selected = st.session_state.get("macro_category_name", None)

    idx_selected = 0 if not already_selected else \
        [c["name"] for c in st.session_state["categories"]].index(already_selected)

    macro_category_name = st.selectbox("Pick a MACRO category", list([f'{c["name"]} - ({len(c["sub_categories"])} sub categories)' for c in st.session_state["categories"]]), index= idx_selected)

    if not macro_category_name:
        macro_category_name = st.session_state["categories"][0]["name"]
    else:
        macro_category_name = macro_category_name.split(" - (")[0]

    macro_category = next(c for c in st.session_state["categories"] if c["name"] == macro_category_name)

    st.session_state["macro_category_name"] = macro_category["name"]

    # ask to select a sub category
    sub_categories = macro_category["sub_categories"]
    sub_category_name = st.selectbox("Pick a sub category", [c["name"] for c in sub_categories])
    sub_category = next(c for c in sub_categories if c["name"] == sub_category_name)

    st.markdown(f'#### <font color="red">ATTENTION:</font> How interesting is the category: {sub_category_name}?', unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)

    with col1:
        button1 = st.button('Interesting')

    with col2:
        button2 = st.button('Mid interesting')

    with col3:
        button3 = st.button('Not interesting')

    if button1:
        utils.on_vote(mongo_client, 'interesting', sub_category, idx_selected)

    if button2:
        utils.on_vote(mongo_client, 'mid interesting', sub_category, idx_selected)

    if button3:
        utils.on_vote(mongo_client, 'not interesting', sub_category, idx_selected)


    # ---------------------------- DISPLAY ----------------------------
    st.title(f'Products in "{macro_category_name}" -> "{sub_category_name}"')

    utils.display_products(sub_category["products"])
