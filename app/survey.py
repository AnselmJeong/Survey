import streamlit as st
from streamlit import session_state as sss
import streamlit_survey as ss
from streamlit_scrollable_textbox import scrollableTextbox
from streamlit_toggle import st_toggle_switch
import streamlit_antd_components as sac
from streamlit_extras.add_vertical_space import add_vertical_space
from streamlit_extras.row import row
from streamlit_extras.colored_header import colored_header


import functools
from time import sleep
from copy import deepcopy


import pandas as pd
from datetime import datetime
from utils import (
    prepare_case_evaluation,
    get_unique_IDs,
    get_authenticator,
    get_doc_ref,
    get_symptoms,
    get_reverse_symptoms,
    df_to_gpt_data
)

from navigator import generate_navigator

st.set_page_config(
    layout='wide',
    page_title='Mental Symptom Detector',
    page_icon='./assets/mental-health.png'
)

########### Session Variables  ####################


# sss['load_selection'] = sss['load_selection']
# sss['tab_selection'] = sss['tab_selection']

if 'authenticated' not in sss:
    sss['authenticated'] = None
if 'df' not in sss:
    sss['df'] = None
if 'name' not in sss:
    sss['name'] = ""
if 'username' not in sss:
    sss['username'] = ""

if 'doc_ref' not in sss:
    sss['doc_ref'] = None
if 'initialized' not in sss:
    sss['initialized'] = False
# if 'huma n_initialized' not in sss:
#     sss['human_initialized'] = False


if 'IDs' not in sss:
    sss['IDs'] = []
# if 'unevaluated_IDs' not in sss:
#     sss['unevaluated_IDs'] = []
# if 'unreviewed_IDs' not in sss:
#     sss['unreviewed_IDs'] = []
    
if 'current_index' not in sss:
    sss['current_index'] = 0
if 'current_ID' not in sss:
    sss['current_ID'] = None
# if 'human_current_index' not in sss:
#     sss['human_current_index'] = 0
# if 'human_current_ID' not in sss:
#     sss['human_current_ID'] = None

if 'tab_selection' not in sss:
    sss['tab_selection'] = '초기평가'
if 'load_selection' not in sss:
    sss['load_selection'] = '이전 재검토 자료'

if 'symptoms' not in sss:
    sss['symptoms'] = None
if 'categories' not in sss:
    sss['categories'] = None
if 'cases' not in sss:
    sss['cases'] = None

if 'ready' not in sss:
    sss['ready'] = False
if 'evaluated' not in sss:
    sss['evaluated'] = False
if 'reviewed' not in sss:
    sss['reviewed'] = False

## Associated Data
if 'initial_survey_data' not in sss:
    sss['initial_survey_data'] = {}
if 'human_survey_data' not in sss:
    sss['human_survey_data'] = {}
if 'gpt_survey_data' not in sss:
    sss['gpt_survey_data'] = {}
    
    
    

today = datetime.today().strftime('%Y-%m-%d')
initial_survey = ss.StreamlitSurvey('initial')
human_survey = ss.StreamlitSurvey('human')
gpt_survey = ss.StreamlitSurvey('gpt', disable_navigation=True)

SURVEY_NAMES = ['initial', 'gpt', 'human']
PAGES = {}
SURVEYS = {'initial': initial_survey,
           'gpt': gpt_survey,
           'human': human_survey}

# Set a default response
response_options = [
    "None", "Mild", "Moderate", "Severe"
]

##########  HELPER FUNCTIONS ################################


# def index_to_ID(which="initial"):
#     assert(which in ['initial', 'human'])
    
#     ID_type = 'unevaluated_IDs' if which == 'initial' else 'unreviewed_IDs'
    
#     sss[f'{which}_current_ID']=sss[ID_type][sss[f'{which}_current_index']]
    
# def rewind_index(which="initial"):
#     assert(which in ['initial', 'human'])
    
#     sss[f'{which}_current_index'] = 0
#     index_to_ID(which)

def copy_survey_data(source, target):
    temp2 = {}
    for k, v in sss[f'{source}_survey_data'].items():
        temp_v = v.copy()
        temp_v['widget_key'] = v['widget_key'].replace(source, target)
        temp2[k.replace(source, target)] = temp_v
    
    return temp2

def rewind_pages():
    """
    Rewind to the first page of each StreamlitSurvey
    """
    for k, v in SURVEYS.items():
        v.multipages[0].update(0)
        

def set_doc_ref():
    sss['doc_ref'] = get_doc_ref(sss['username'], sss['current_ID'])


def fill_survey(source, target):
    """
    Fill target StreamlitSurvey with source data
    Data should have been prepared in session_state
    """
    print('Enter fill_survey')
    if source != target:
        payload = copy_survey_data(source, target)

    else:
        payload = sss[f'{source}_survey_data']
    SURVEYS[target].from_data(payload)

    
def on_ID_change():
    """
    indended to used as a callback function
    If current patient ID is changed, then...
    """
    print("on_ID_change")
    # current_ID를 current_index에 맞추어 갱신
    sss['current_ID'] = sss['IDs'][sss['current_index']]
    # 먼저 바뀐 ID에 맞추어 sss['doc_ref']를 갱신하고
    set_doc_ref()
    # 자료를 불러들이고
    fetch_db()
    # StreamlitSurvey가 표시하는 data를 바꾸고
    for which in SURVEY_NAMES:
        fill_survey(which, which)
    # 첫번째 page로 돌린다.
    rewind_pages()
    # 모두 준비되었음을 알린다.
    sss['initialized'] = True



def prepare_cases(case_directory, df, IDs):
    cases = {ID: prepare_case_evaluation(ID, 
                                     case_directory=case_directory, 
                                     df=df) for ID in IDs}
    return cases


# def set_unevaluated_IDs():
#     if sss['only_unevaluated']:
#         sss['unevaluated_IDs'] = [ID for ID in sss['IDs']
#                         if not is_evaluated(sss['username'], ID)]
#     else:
#         sss['unevaluated_IDs'] = sss['IDs'].copy()
    
#     rewind_index("initial")
    
    
# def set_unreviewed_IDs():
#     if sss['only_unreviewed']:
#         sss['unreviewed_IDs'] = [ID for ID in sss['IDs']
#                         if not is_reviewed(sss['username'], ID)]
#     else:
#         sss['unreviewed_IDs'] = sss['IDs'].copy()
        
#     rewind_index("human")
    

@st.cache_data
def prepare_symptoms(symptoms_json_path):
    symptoms = get_symptoms(symptoms_json_path)
    reverse_symptoms = get_reverse_symptoms(symptoms)
    categories = list(symptoms.keys())
    return (symptoms, reverse_symptoms, categories)

@st.cache_data    
def load_data(filepath: str) -> pd.DataFrame:
    return pd.read_excel(filepath, sheet_name="Sheet1")

@st.cache_resource
def produce_session_variables(GPT_output_filepath, case_directory, symptoms_json_path):
    df = load_data(GPT_output_filepath)
    IDs = get_unique_IDs(df)
    symptoms, reverse_symptoms, categories = prepare_symptoms(symptoms_json_path)
    cases = prepare_cases(case_directory, df, IDs)
    return (df, IDs, symptoms, reverse_symptoms, categories, cases)


@st.cache_resource
def initialize_main(GPT_output_filepath, case_directory, symptoms_json_path):
    df, IDs, symptoms, reverse_symptoms, categories, cases = produce_session_variables(GPT_output_filepath, case_directory, symptoms_json_path)
    sss['df'] = df
    sss['IDs'] = IDs
    # set_unevaluated_IDs()
    # set_unreviewed_IDs()
    sss['symptoms'], sss['reverse_symptoms'], sss['categories'] = symptoms, reverse_symptoms, categories
    # sss['flat_symptoms'] = functools.reduce(lambda x, y: x+y, list(sss['symptoms'].values()), [])
    sss['cases'] = cases
    sss['ready'] = True

    


def submit_survey_data(which):
    """
    Submit survey.data to firebase using doc_ref
    """
    payload = SURVEYS[which].data.copy()
    
    for k, v in payload.items():
        v.update({'timestamp': datetime.today().strftime('%Y-%m-%d, %H:%M:%S')})
    
    if which == "initial":
        payload['evaluated'] = True
    elif which == 'human':
        payload['reviewed'] = True
        
    sss['doc_ref'].set(payload, merge=True)
    messagebox = st.success("Data succesfully submitted") # Display the alert
    sleep(5) # Wait for 3 seconds
    messagebox.empty() # Clear the alert
    


def fetch_db():
    with st.spinner(f"Loading data..."):
        print("Enter fetch db")
        
        doc = sss['doc_ref'].get()

        
        if doc.exists:
            sss['initial_survey_data'] = {k: v for k, v in doc.to_dict().items() if f"initial-" in k}
            sss['human_survey_data'] = {k: v for k, v in doc.to_dict().items() if "human-" in k}
            
            sss['evaluated'] = doc.to_dict().get('evaluated', False)
            sss['reviewed'] = doc.to_dict().get('reviewed', False)
            
            if 'df' in sss:
                sss['gpt_survey_data'] = df_to_gpt_data(sss['df'], sss['current_ID'])
        else:
            sss['initial_survey_data'] = {}
            sss['gpt_survey_data'] = {}
            sss['human_survey_data'] = {}
            sss['evaluated'] = False
            sss['reviewed'] = False
        
        

initialize_main("./data/symptoms_evaluated.xlsx", "./data/case_files", "./assets/symptoms.json")

for which in SURVEY_NAMES:
    PAGES[which] = SURVEYS[which].pages(len(sss['categories']), label=which, 
                                        on_submit=submit_survey_data)


##########################################################################################
# sss.update(sss)

with st.sidebar:
  
    authenticator = get_authenticator("./.streamlit/credentials.yaml")
    st.session_state['name'], authenticated, st.session_state['username'] = authenticator.login('Login', 'main')
    
    if authenticated == False:
        st.error('Username/password is incorrect')
    elif authenticated == None:
        st.warning('Please enter your username and password')
        
    else:
        st.header(f'__{sss["name"]}__ 님 반갑습니다.')
        st.subheader(f"{today}에 입장하셨습니다.")
        # st.checkbox("아직 판독하지 않은 사례들만 표시", False, key='only_unevaluated', on_change=set_unevaluated_IDs)
        authenticator.logout('Logout', 'main')
        
        
    sss['authenticated'] = authenticated
 
############################################################################################################

# st.write([k for k, v in sss.items()])



colored_header(
    label="Mental Symptom Detector",
    description=f":orange[GPT와 함께 정신증상을 평가해보세요]",
    color_name="red-70",
)

if sss['ready'] and sss['authenticated']:
    if not sss['initialized']:
        on_ID_change() # sss[initialized] = True 상태로 전환
    
    
    _,col_nav,col_info = st.columns([0.1,0.6,0.3])
    with col_nav:
        generate_navigator(sss, callback=on_ID_change)
    with col_info:
        evaluated, reviewed = sss['evaluated'], sss['reviewed']    
        st.markdown(f"초기평가: {'✅' if evaluated else '⌛'}, 재검토: {'✅' if reviewed else '💢'}")
    
        
    sac.divider(icon='magic', align='center')
    

    # st.info(f"Evaluation: :red[{'yes' if evaluated else 'not yet'}], Review: :blue[{'yes' if reviewed else 'not yet'}]")
   
    case = sss['cases'][sss['current_ID']]
    
    _,col_tab,_ = st.columns([0.2,0.6,0.2])
    with col_tab:
        sss['tab_selection']=sac.segmented([
            sac.SegmentedItem(label='초기평가'),
            sac.SegmentedItem(label='재검토'),
        ], grow=True)
    
    if sss['tab_selection'] == "초기평가":
        #### ========= initial evaluation ========== ###

        eval_col1, _, eval_col2 = st.columns([0.63, 0.02, 0.35])
        

        
        with eval_col1:
            st.caption(f":orange[증례를 잃고, 우측에 나열된 정신 증상이 얼마나 심한 편인지 평가해주세요.]")        
            st.subheader(f":blue[{sss['current_ID']}: {case['case_description']['sex']}/{case['case_description']['age']}]")
            
            scrollableTextbox(case['case_description']['description'], height=800, border=False)
     

        with eval_col2:
            

            
            with PAGES['initial'] as initial_page:
                category = sss['categories'][initial_page.current]
                # st.info(f"__{initial_page.current+1}/{len(sss['categories'])}: {category}__")
                
                def temp_format_func(x):
                    return f"{(x+1):02}: {sss['categories'][x].replace('_', ' ')}"
                
                def on_change():
                    initial_page.update(sss['current_category'])
                    
                
                st.selectbox("Select catetory", options=range(len(sss['categories'])),
                            index=initial_page.current,
                            format_func=temp_format_func,
                            key='current_category',
                            label_visibility='collapsed',
                            on_change=on_change)    
                
                
                for index in range(len(sss['symptoms'][category])):
                    
                    symptom = sss['symptoms'][category][index]
                    
                    initial_survey.radio(symptom,
                                        options=range(4), 
                                        # index = (initial_survey.data[f'initial-{symptom}']['value']),
                                        format_func=lambda x: response_options[x],
                                        horizontal=True, 
                                        id=f"initial-{symptom}")
                # st.write(initial_survey.data)
            
    if sss['tab_selection'] == "재검토":
        st.subheader(f":blue[{case['case_description']['sex']}/{case['case_description']['age']}]")
        scrollableTextbox(case['case_description']['description'], height=400, border=False)

        rev_col1, rev_col2 = st.columns(2)
                        
        with rev_col2:
            
            with PAGES['human'] as human_page:
                
                category = sss['categories'][human_page.current]
                
                st.warning("재검토: GPT 결과를 참조하여 수정할 수 있습니다.")
                sss['load_selection'] = sac.buttons([
                    sac.ButtonsItem(label='이전 재검토 자료', icon='box-fill'),
                    sac.ButtonsItem(label='초기평가 자료', icon='rewind-circle-fill')
                ], format_func='title', align='start', size='small',
                label='__어떤 자료를 불러들일까요?__', position='left')
                
                if sss['load_selection'] == '이전 재검토 자료':
                    fill_survey('human', 'human')
                elif sss['load_selection'] == '초기평가 자료':
                    fill_survey('initial', 'human')

                st.info(f"__{human_page.current+1}/{len(sss['categories'])}: {category}__")
                
                for index in range(len(sss['symptoms'][category])):
                    symptom = sss['symptoms'][category][index]
                    reason = gpt_survey.data.get(f"gpt-{symptom}", {'reason': ''})['reason']
                    reason = "" if reason!=reason else reason
                    concordance = gpt_survey.data.get(f"gpt-{symptom}", {'value':0})['value'] == human_survey.data.get(f"human-{symptom}", {'value':0})['value']
                    
                    human_survey.radio(symptom + ('' if concordance else ' :x:'), 
                                        options=range(4), 
                                        format_func=lambda x: response_options[x],
                                        horizontal=True,
                                        id=f"human-{symptom}")
                    # if reason:
                    #     st.caption("☘️")
                    
        with rev_col1:
            
            with PAGES['gpt'] as gpt_page:
                category = sss['categories'][human_page.current]
                st.warning("GPT 판독결과")
                # add_vertical_space(1)
                sac.divider()
                                
                st.info(f"__{human_page.current+1}/{len(sss['categories'])}: {category}__")
                
                for index in range(len(sss['symptoms'][category])):
                    symptom = sss['symptoms'][category][index]
                
                    # severity = response_options[gpt_survey.data[f"gpt-{symptom}"]['value']]
                    
                    reason = gpt_survey.data.get(f"gpt-{symptom}", {'reason': ''})['reason']
                    reason = "" if reason!=reason else reason
                    concordance = gpt_survey.data[f"gpt-{symptom}"]['value'] == human_survey.data[f"human-{symptom}"]['value']
                    
                    gpt_survey.radio(symptom,
                                    options=range(4), 
                                    format_func=lambda x: response_options[x],
                                    horizontal=True, 
                                    disabled=True,
                                    help=f":blue[{reason}]" if reason else None,
                                    id=f"gpt-{symptom}")

                    
                    # if not concordance:
                    #     st.markdown("<hr>", unsafe_allow_html=True)
                    # if reason != "":
                    #     st.caption(f":blue[{reason}]" if reason else "")












st.markdown("""
            <style>
                .stRadio p {
                    font-size: 16px;
                    color: coral;
                    
                }
                .stRadio p::first-letter {
                    text-transform: uppercase;
                }
                

} 
            </style>
            """, unsafe_allow_html=True)     





