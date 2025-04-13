import streamlit as st
import random
import uuid
import secrets

from chatbot_setup import handle_chat_interaction
from app_utils import log_entry, export_logs_github, save_participation_code

# ----- Study Configuration -----

TASKS = [
    "Task 1: Explain the key differences between three fundamental approaches by which a learning computer program can enhance its performance based on data or experience: ",
    "Task 2: Describe how the retention of new information can be negatively impacted when similar content is already stored in memory. Explain the underlying mechanisms and provide an example that illustrates this effect. ",
    "Task 3: Name the five formal parameters by which a Finite-State Automaton (FSA) can be precisely defined in formal language theory. ",
    "Task 4: Which structure in the outer envelope of a nerve cell prevents hydrophile substances from easily entering or leaving the cell interior? ",
    "Task 5: Explain how information can be represented in the brain by neurons. Describe at least three different mechanisms of neural information coding and briefly summarize how these mechanisms contribute to information processing and storage."
]

PRE_QUESTIONNAIRE = [
    {"question": "How often do you use AI based search engines (like Perplexity, Bing Chat, ChatGPT with Web Search,...) to look up any kind of information?\n\n(1 = Never, 5 = Very frequently)", "type": "slider",   "min":1, "max":5, "help": "1 = Never, 5 = Very frequently"},
    {"question": "How satisfied are you with the possibilities currently provided by the university to search for information from your courses?\n\n(1 = Very unsatisfied, 5 = Very satisfied)",  "type": "slider",   "min":1, "max":5, "help": "1 = Very unsatisfied, 5 = Very satisfied"},
    {"question": "What do you expect from a course material search assistant? Which features would be most helpful for your personal use?", "type": "text"}
]

PER_TASK_QUESTIONNAIRE = [
    {"question": "Did you already know the answer or the relevant concept (e.g. specific term or topic) to the question before asking the chatbot?", "type": "radio", "options": ["Yes", "Partially" , "No"]},
    {"question": "How well did the chatbot help you complete the task?\n\n (1 = The chatbot was not helpful at all, 5 = The chatbot was very helpful)", "type": "slider", "min": 1, "max": 5, "help": "1 = The chatbot was not helpful at all, 5 = The chatbot was extremely helpful"},
    {"question": "Why did you find the chatbot helpful or not helpful for this task?", "type": "text"}
]

POST_QUESTIONNAIRE = [
    {"question": "Would you use this chatbot to search for information covered in your courses if it were integrated in StudIP?", "type": "radio", "options": ["Yes" ,"Maybe", "No"]},
    {"question": "How helpful did you find the chatbot during your free exploration?\n\n(1 = The chatbot was not helpful at all, 5 = The chatbot was very helpful)", "type": "slider", "min": 1, "max": 5, "help": "1 = The chatbot was not helpful at all, 5 = The chatbot was extremely helpful"},
    {"question": "Why did you find the chatbot helpful or not helpful?", "type": "text"},
    {"question": "What improvements or advantages do you think this tool could offer compared to your current approach to search for information covered in your courses", "type": "text"},
    {"question": "Any further comments (functionalities that you found or would find helpful, performance of the tool, things that where missing, ...)? ", "type": "text"}
]

# ----- Study State Management -----

def initialize_study():
    """Initialize study session state variables if they don't exist"""
    if "study_id" not in st.session_state:
        st.session_state.study_id = str(uuid.uuid4())[:8]
        st.session_state.current_task = 0  
        st.session_state.task_methods = [random.choice(["rag", "keyword"]) for _ in TASKS]
        st.session_state.logs = []
        st.session_state.chat_history = {}
        st.session_state.task_ready_for_feedback = False

def get_current_task():
    """Get the description of the current task"""
    if isinstance(st.session_state.current_task, int):
        return TASKS[st.session_state.current_task]
    if st.session_state.current_task == "free":
        return " **Time to Explore!**\n\nAsk anything you'd like related to the course material."
    return ""

def get_current_method():
    """Get the search method for the current task"""
    if isinstance(st.session_state.current_task, int):
        return st.session_state.task_methods[st.session_state.current_task]
    return "rag"  # Default to 'rag' for free exploration or non-task phase

def advance_task():
    """Move to the next task or to free exploration mode"""
    if isinstance(st.session_state.current_task, int) and st.session_state.current_task >= len(TASKS) - 1:
        st.session_state.current_task = "free"  # switch to free exploration
    else:
        st.session_state.current_task += 1
    st.session_state.task_ready_for_feedback = False

def is_last_task():
    """Check if we're on the last task"""
    return isinstance(st.session_state.current_task, int) and st.session_state.current_task >= len(TASKS) - 1

# ----- Questionnaire Rendering -----

def render_questionnaire(questions, key_prefix=""):
    """Render a questionnaire in the Streamlit UI and collect responses"""
    responses = {}
    for i, q in enumerate(questions):
        key = f"{key_prefix}_{i}"
        left, main, right = st.columns([0.001, 2.5, 2.5])
        with main:
            question_html = f"<span style='font-size: 18px; font-weight: 400'>{q['question']}</span>"
            if q["type"] == "radio":
                st.markdown(question_html, unsafe_allow_html=True)
                responses[q["question"]] = st.radio("", q["options"], key=key)
            elif q["type"] == "slider":
                st.markdown(question_html, unsafe_allow_html=True)
                responses[q["question"]] = st.slider("", min_value=q["min"], max_value=q["max"], key=key)
            elif q["type"] == "text":
                st.markdown(question_html, unsafe_allow_html=True)
                responses[q["question"]] = st.text_area("", key=key)

    return responses

# ----- Study Interface Components -----

def show_intro():
    """Show the introduction page"""
    st.write("""
    ### Study Overview:
    In this study you will test a course material search assistant designed to help students find relevant information 
    from their lecture materials.
 
    - First you will complete a **start questionnaire** about your background and experience with AI-based search.
    - Then you will be given a few **tasks to solve** using the chatbot. The topics of those tasks have been covered in the mandatory modules of the Cognitive Science Bachelor program. Here are a few things to consider while trying to solve the tasks:
       - For each task you can enter as many queries as you want, they should be in english. 
       - Don't worry if the chatbot does not find an answer for certain tasks. You can safely continue with the feedback questionair, even if you did not get a good answer.
       - It can take a few seconds until an answer is displayed on the screen after entering a query. Please wait for the answer, before you take any other action. 
    - After each task, you will answer a **quick feedback questionnaire** to the respective task and answers.
    - At the end, it's time for **free exploration** of the chatbot and you will complete a **final questionnaire** where you can give feedback on the chatbot.

    Your interactions and answers will be recorded anonymously and used for research purposes only.
    """)
    if st.button("Start Study"):
        st.session_state.intro_shown = True
        st.rerun()

def show_pre_questionnaire():
    """Show the pre-study questionnaire"""
    st.header("Getting Started")
    responses = render_questionnaire(PRE_QUESTIONNAIRE, key_prefix="pre")
    if st.button("Submit"):
        log_entry({"type": "pre_survey", "responses": responses})
        st.session_state.pre_survey_done = True
        st.rerun()

def show_task_feedback():
    """Show feedback questionnaire for the current task"""
    current_task_id = st.session_state.current_task
    st.subheader("Quick Feedback on this Task")
    feedback = render_questionnaire(PER_TASK_QUESTIONNAIRE, key_prefix=f"task_{current_task_id}")

    if len(st.session_state.chat_history[current_task_id]) == 0:
        st.info("Please ask at least one question before continuing to the next task.")
    else:
        next_label = "Continue to last Task" if is_last_task() else "Continue to Next Task"
        if st.button(next_label):
            log_entry({
                "type": "task_interaction",
                "task_id": current_task_id,
                "method": st.session_state.last_method,
                "queries_and_responses": [
                    {
                        "query": entry["query"],
                        "response": entry["response"],
                        "filters": entry["filters"]
                    } for entry in st.session_state.chat_history[current_task_id]
                ],
                "feedback": feedback
            })
            st.session_state.task_ready_for_feedback = False
            advance_task()
            st.rerun()

def show_task_interface(pipeline, vectorstore):
    """Display the task interface with chat"""
    current_task_id = st.session_state.current_task
    task = get_current_task()
    method = get_current_method()

    if isinstance(current_task_id, int):
        st.subheader(f"Task {current_task_id + 1}")
    else:
        st.subheader("Free Exploration")

    col1, col2 = st.columns([2, 5])
    with col1:
        st.markdown("**Task Description:**")
        st.info(task)

    handle_chat_interaction(pipeline, method, vectorstore, "Ask the chatbot to solve this task...", current_task_id)

    if len(st.session_state.chat_history[current_task_id]) > 0 and not st.session_state.task_ready_for_feedback:
        if st.button("I'm done with this task, continue to feedback"):
            st.session_state.task_ready_for_feedback = True
            st.rerun()

def show_free_exploration(pipeline, vectorstore):
    """Show the free exploration interface"""
    st.session_state["current_task"] = "free"
    st.subheader("Time to Explore!")
    st.markdown("""
    During the previous tasks, the chatbot used **different search modes**, including a rather basic keyword search and a more advanced AI-based approach (RAG).  
    In this final exploration step, the chatbot will **only use the AI-based method** to answer your questions.  
    Please consider that the questionnaire afterwards only refers to this free exploration part of the study.

    You can ask any kind of questions about topics that have been covered in the following courses:

    - Introduction to Neurobiology  
    - Foundations of Logic and Argumentation Theory  
    - Foundations of Cognitive Science  
    - Introduction to Artificial Intelligence and Logic Programming  
    - Sensory Physiology  
    - Philosophy for Cognitive Science  
    - Introduction to Cognitive (Neuro-)Psychology  
    - Introduction to Computational Linguistics  
    - Methods of AI  
    - Statistics and Data Analysis  
    - Neuroinformatics  

    """)

    handle_chat_interaction(pipeline, "rag", vectorstore, "What is machine learning ? ...", "free")

    if len(st.session_state.chat_history["free"]) > 0:
        if st.button("Continue to Final Questionnaire"):
            log_entry({
                "type": "free_exploration",
                "task_id": "free",
                "queries_and_responses": [
                    {
                        "query": entry["query"],
                        "response": entry["response"],
                        "filters": entry["filters"]
                    } for entry in st.session_state.chat_history["free"]
                ]
            })
            st.session_state.free_exploration_done = True
            st.rerun()

def show_post_questionnaire():
    """Show the post-study questionnaire"""
    st.header("Final Survey")
    st.markdown("""
    ###### Please answer the following questions only based on the impressions you got while using the chatbot in the *last* exploration task!
    """)
    responses = render_questionnaire(POST_QUESTIONNAIRE, key_prefix="post")
    if st.button("Submit Final Questionnaire and Finish"):
        log_entry({"type": "post_survey", "responses": responses})
        #export_logs()  # locally
        export_logs_github()  # to github
        st.session_state.post_survey_done = True
        st.rerun()

def show_study_complete():
    """Generate Unique participation code and show study completion message"""
    participation_code = secrets.token_hex(3).upper()
    st.session_state["participation_code"] = participation_code
    save_participation_code(participation_code)
    st.success(f"Thank you for participating!\n\nYour confirmation code is: *`{participation_code}`*\n\n If you want to recieve VP hours, please save this code and send it to hopper@uni-osnabrueck.de along with your VP documentation paper. \n\nYou can now safely close this tab.")

# ----- Main Study Flow -----

def run_study_interface(pipeline, vectorstore):
    """Main function to run the study interface"""
    # Intro page
    if "intro_shown" not in st.session_state:
        show_intro()
        return

    # Pre-study questionnaire
    if "pre_survey_done" not in st.session_state:
        show_pre_questionnaire()
        return

    # Task feedback
    if st.session_state.task_ready_for_feedback:
        show_task_feedback()
        return

    st.session_state["questionnaire_active"] = (
        "pre_survey_done" not in st.session_state or
        ("post_survey_done" not in st.session_state and st.session_state.get("current_task") == "free")
    )

    # Handle free exploration phase independently
    if st.session_state.current_task == "free":
        if "free_exploration_done" not in st.session_state:
            show_free_exploration(pipeline, vectorstore)
            return
        if "post_survey_done" in st.session_state:
            show_study_complete()
        else:
            show_post_questionnaire()
            return
        return

    # Task + Chatbot section
    show_task_interface(pipeline, vectorstore)