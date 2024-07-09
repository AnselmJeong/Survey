import google.cloud
from google.cloud import firestore
from datetime import datetime
import pandas as pd
import os, yaml, json
from collections.abc import Iterable
import streamlit_authenticator as stauth
import streamlit as st

from yaml.loader import SafeLoader

fb_credentials = st.secrets["firebase"]["firebase_settings"]

db = firestore.Client.from_service_account_info(fb_credentials)


def get_doc_ref(
    username: str, ID: str, callback=None
) -> google.cloud.firestore_v1.document.DocumentReference:
    """
    Retrieve firebase document reference (doc_ref) using
    an username (logged-in username) and a patient ID
    output: google.cloud.firestore_v1.document.DocumentReference
    """
    try:
        ID = str(ID)
        # Create a reference to the Google post.
        doc_ref = db.collection(username).document(ID)
        if callback:
            callback()
        return doc_ref
    except Exception as e:
        # print(f"Failed to get document reference with {e}")
        # print("You could not get the doc_ref")
        return None


def get_symptoms(json_path) -> dict:
    """
    Load a json file containing symptoms to evaluate
    output format: {category: [symptoms]}
    """
    try:
        with open(json_path) as f:
            symptoms = json.loads(f.read())
            temp = {}
            for k, vs in symptoms.items():
                temp[k] = []
                for v in vs:
                    temp[k].append(v)
            return temp
    except Exception as e:
        print(e)
        return None


def get_reverse_symptoms(symptoms: dict) -> dict:
    """
    Exchange values and keys of symptoms dictionary (output of get_symptoms())
    output format: {symptom: category}
    """
    new_dict = {}
    for k, vs in symptoms.items():
        for v in vs:
            new_dict[v] = k
    return new_dict


def get_authenticator(yaml_path: str):
    """
    Get an authenticator for accesing this program.
    Registered users and their passwords are stored in a yaml file.
    """
    with open(yaml_path, encoding="utf8") as f:
        config = yaml.load(f, Loader=SafeLoader)

    authenticator = stauth.Authenticate(
        config["credentials"],
        config["cookie"]["name"],
        config["cookie"]["key"],
        config["cookie"]["expiry_days"],
    )
    return authenticator


def load_case(id: str, case_directory: str) -> dict:
    """
    Read text files containing case description
    output format: {sex: str, age: str, description: str}
    """
    filepath = os.path.join(case_directory, ".".join([str(id), "txt"]))
    try:
        with open(filepath, encoding="utf8") as f:
            sex, age, *descriptions = [line.strip("\n") for line in f.readlines()]
            description = "\n".join(descriptions)
        return {"sex": sex, "age": age, "description": description}
    except:
        print(f"{id} not found in the case_directory")
        return None


def prepare_case_evaluation(id: str, case_directory: str, df: pd.DataFrame) -> dict:
    """
    Retrieve GPT evaluated results and attach them to case dictionary
    output format: {case_description: {sex: str,
                                       age: str,
                                       description: str},
                    evaluation: pd.DataFrame}
    """
    evaluation = df.loc[df.ID == id, ["symptom", "severity", "reason"]]
    case_description = load_case(id, case_directory)
    return {"case_description": case_description, "evaluation": evaluation}


def get_unique_IDs(df: pd.DataFrame) -> Iterable[str]:
    IDs = list(set(df.ID))
    return IDs


def df_to_gpt_data(df: pd.DataFrame, ID) -> dict:
    """
    Prepare gpt survey data from df
    output format: {
        gpt-{symptom}: {
            value: int,
            reason: str,
            label: str,
            widget_key: str
        }
    }
    """

    new_dict = {}

    ddf = df.loc[df.ID == int(ID)]
    for label, row in ddf.iterrows():
        temp = f"gpt-{row.symptom.lower()}"
        new_dict[temp] = {
            "value": row.severity,
            "reason": row.reason,
            "label": row.symptom.lower(),
            "widget_key": f"__survey_gpt_gpt-{row.symptom.lower()}",
        }
    return new_dict


def get_status(user, ID):
    """
    Get the 'evaluated' and 'reviewed' status of a case
    """
    status = {"ID": str(ID), "초기평가": "❌", "재검토": "❌"}
    if doc_ref := get_doc_ref(user, ID):
        if data := doc_ref.get().to_dict():
            status["초기평가"] = ["❌", "🔵"][data.get("evaluated", False)]
            status["재검토"] = ["❌", "🔵"][data.get("reviewed", False)]
    return status


def get_status_list(user, IDs):
    df = pd.DataFrame([get_status(user, ID) for ID in IDs])
    return df


# def is_reviewed(user, ID):
#     if data:= get_doc_ref(user, ID).get().to_dict():
#         return data.get('reviewed', False)
#     else:
#         return False

# def is_evaluated(user, ID):
#     if data := get_doc_ref(user, ID).get().to_dict():
#         return data.get("evaluated", False)
#     else:
#         return False


def get_value_list(gpt_data, human_data, symptoms):
    """
    match gpt evaluation with human evaluation on each symptom
    """

    value_list = {"gpt": [], "human": []}
    for evaluator in ["gpt", "human"]:
        data = gpt_data if evaluator == "gpt" else human_data
        for category in symptoms:
            for symptom in symptoms[category]:
                key = f"{evaluator}-{symptom}"
                value_list[evaluator].append(data.get(key, {"value": 0})["value"])

    return value_list
