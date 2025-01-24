
import os, hmac
from dotenv import load_dotenv
from time import sleep
from pymongo import MongoClient

import streamlit as st
from st_aggrid import AgGrid, GridOptionsBuilder, GridUpdateMode
from st_aggrid.shared import JsCode

from utils import AGGREGATE_PRODUCTS, build_product_dataframe

load_dotenv(override=True)

# ---------------------------- AUTH ----------------------------
def check_password():
    def password_entered():
        if hmac.compare_digest(st.session_state["password"], st.secrets["password"]):
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Don't store the password.
        else:
            st.session_state["password_correct"] = False

    if st.session_state.get("password_correct", False):
        return True

    st.text_input(
        "Password", type="password", on_change=password_entered, key="password"
    )
    if "password_correct" in st.session_state:
        st.error("😕 Password incorrect")
    return False


def check_email():
    allowed_domain = "@" + st.secrets["companyDomain"]

    # Check if email is already stored in session state
    if "user_email" not in st.session_state:
        user_email = st.text_input("Enter your company email:", key="email_input")

        # Validate email when user enters something
        if user_email.endswith(allowed_domain):
            st.session_state["user_email"] = user_email  # Store valid email
            st.session_state["password_correct"] = True
            st.success(f"✅ Email validated: {user_email}")
            st.rerun()

        else:
            st.error(f"🚨 Please enter a valid company email 🚨")
            print("Stopping the script until email is validated.")
            st.stop()
        return False
    return True

# ---------------------------- AUTH CHECKS ----------------------------
if os.getenv("DEBUG", "").lower() == "true":
    print("Running in debug mode, skipping password check.")
    st.session_state["password_correct"] = True
    st.session_state["user_email"] = os.getenv("DEFAULT_EMAIL")
    pass # skip password check in debug mode

elif not check_password():
    print("Password incorrect, stopping the script.")
    st.stop()  # Do not continue if check_password is not True.

elif not check_email():
    print("Email incorrect, stopping the script.")
    st.stop()


st.write(f"Welcome, {st.session_state['user_email']}!")


## ---------------------------- MONGO ----------------------------
@st.cache_resource
def init_connection():
    return MongoClient(st.secrets["MONGO_URL"])[st.secrets["MONGO_DB_NAME"]]


@st.cache_data(ttl=600)
def get_data(_client: MongoClient) -> list:
    data = list(_client["hot1688_winning_products"].aggregate(AGGREGATE_PRODUCTS))
    data.sort(key=lambda x: 2 if x["importance"] == "high" else (0 if x["importance"] == "low" else 1), reverse=True)
    for category in data:
        for sub_category in category["sub_categories"]:
            # check unique
            sub_category["products"] = list({product["id1688"]: product for product in sub_category["products"]}.values())

            for prod in sub_category["products"]:
                prod["group_size"] = len(prod.pop("productIds"))
                if not prod.get("image"):
                    prod["image"] = None
    return data

mongo_client = init_connection()

st.session_state["categories"] = get_data(mongo_client)

print(f"Collected Categories: {len(st.session_state['categories'])}")

macro_category_names = list([f'{c["name"]} - ({len(c["sub_categories"])} sub categories)' for c in st.session_state["categories"]])

# ---------------------------- VOTING APP ----------------------------
st.write("# Voting App")

macro_category = st.selectbox("Pick a MACRO category", macro_category_names)

if not macro_category:
    macro_category = macro_category_names[0]

macro_category_name = macro_category.split(" - (")[0]

macro_category = next(c for c in st.session_state["categories"] if c["name"] == macro_category_name)
sub_categories = macro_category["sub_categories"]

# ask to select a sub category
category_name = st.selectbox("Pick a sub category", [c["category_name"] for c in sub_categories])
sub_category = next(c for c in sub_categories if c["category_name"] == category_name)


# Display the products
# st.write(f"## {category_name}")

# for product in sub_category["products"]:
#     st.write(f"### {product['title']}")
#     st.image(product["image"], caption=product["price"])
#     st.write(f"Sales: {product['sales']}")
#     st.write(f"Price: {product['price']*0.13:.2f} USD")
#     st.write(f"[View product](https://detail.1688.com/offer/{product['id1688']}.html)")



# st.title('Table of media')

# there should be up to 9 products max,
# num_cols = 3
# num_rows = int(len(sub_category["products"]) / 3) + 1

# for i in range(1, 3): # number of rows in your table! = 2

#     cols = st.beta_columns(2) # number of columns in each row! = 2

#     # first column of the ith row
#     cols[0].image('row_%i_col_0.png' %i, use_column_width=True, caption="")
#     cols[1].image('row_%i_col_1.jpg' %i, use_column_width=True, caption="") 
#     cols[3]


df = build_product_dataframe(sub_category["products"])

gb = GridOptionsBuilder.from_dataframe(df, editable=True)

cell_renderer =  JsCode("""
                        function(params) {return `<a href=${params.value} target="_blank">${params.value}</a>`}
                        """)


gb.configure_column(
    "link",
    headerName="link",
    width=100,
    cellRenderer=JsCode("""
        class UrlCellRenderer {
          init(params) {
            this.eGui = document.createElement('a');
            this.eGui.innerText = 'SomeText';
            this.eGui.setAttribute('href', params.value);
            this.eGui.setAttribute('style', "text-decoration:none");
            this.eGui.setAttribute('target', "_blank");
          }
          getGui() {
            return this.eGui;
          }
        }
    """)
)

grid = AgGrid(df,
            gridOptions=gb.build(),
            updateMode=GridUpdateMode.VALUE_CHANGED,
            allow_unsafe_jscode=True)


# votes are "interesting", "mid interesting", "not interesting"
vote = st.radio("How interesting is this category?", ["interesting", "mid interesting", "not interesting"])

# Submit the vote
if st.button("Submit vote"):
    vote_data = {
        "email": st.session_state["user_email"],
        "category_id": st.session_state["category"][category_name],
        "category_name": category_name,
        "vote": vote,
    }
    mongo_client["category_votes"].insert_one(vote_data)
    st.success("Vote submitted! 🎉")
    st.rerun()
