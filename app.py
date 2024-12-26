import os
from flask import Flask, render_template, request, jsonify
from google.cloud import dialogflow_v2 as dialogflow
from transformers import pipeline
from PyPDF2 import PdfReader
from fuzzywuzzy import process

app = Flask(__name__)

# Predefined rule-based responses
responses = {
    "what are the library hours?": "The library is open from 8 AM to 8 PM.",
    "how can i access my grades?": "You can access your grades via the student portal.",
    "who is the dean of the college?": "The current dean is Dr. Smith.",
    "thank you": "You're welcome! How else can I assist you?",
    "hello": "Hello! How can I help you today?",
    "who are you": "I am your friendly student assistant chatbot, here to help you with college-related queries!",
}

# Initialize the Hugging Face summarizer
summarizer = pipeline("summarization", model="sshleifer/distilbart-cnn-12-6")

# Define the base directory for files
FILES_DIR = os.path.join(os.getcwd(), "static", "files")

# Dialogflow configuration
os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = "D:/studentassistantbot-yeng-44fdaa81eab9.json"

# Intent detection using predefined responses
def detect_intent(user_query):
    user_query = user_query.lower()
    if user_query in responses:
        return responses[user_query]
    return None

# Intent detection using Dialogflow
def detect_dialogflow_intent(user_query):
    project_id = 'studentassistantbot-yeng'
    session_client = dialogflow.SessionsClient()
    session = session_client.session_path(project_id, 'unique-session-id')

    text_input = dialogflow.TextInput(text=user_query, language_code='en')
    query_input = dialogflow.QueryInput(text=text_input)

    try:
        response = session_client.detect_intent(session=session, query_input=query_input)
        return response.query_result.fulfillment_text
    except Exception as e:
        return f"Error: {str(e)}"

# Context tracking and chat history
chat_history = []

# Home route
@app.route("/")
def home():
    modules = {}
    for module in os.listdir(FILES_DIR):
        module_path = os.path.join(FILES_DIR, module)
        if os.path.isdir(module_path):
            modules[module] = os.listdir(module_path)
    return render_template("index.html", modules=modules)

# Chatbot response route
@app.route("/get", methods=["POST"])
def chatbot_response():
    user_query = request.json.get("query", "").lower()
    chat_history.append(f"You: {user_query}")

    # Check for rule-based response
    rule_based_response = detect_intent(user_query)
    if rule_based_response:
        chat_history.append(f"Bot: {rule_based_response}")
        return jsonify({"response": rule_based_response})

    # Check for course-related response
    course_response = search_course_material(user_query)
    if course_response:
        chat_history.append(f"Bot: {course_response}")
        return jsonify({"response": course_response})

    # Fallback to Dialogflow
    dialogflow_response = detect_dialogflow_intent(user_query)
    chat_history.append(f"Bot: {dialogflow_response}")
    return jsonify({"response": dialogflow_response})

# Search course material
def search_course_material(query):
    for module in os.listdir(FILES_DIR):
        module_path = os.path.join(FILES_DIR, module)
        if os.path.isdir(module_path):
            for subject_file in os.listdir(module_path):
                subject_path = os.path.join(module_path, subject_file)
                if subject_file.endswith(('.txt', '.pdf')):
                    content = extract_file_content(subject_path)
                    if content:
                        best_match = process.extractOne(query, [content])
                        if best_match and best_match[1] > 60:
                            return best_match[0]
    return None

# Extract content from files
def extract_file_content(file_path):
    try:
        if file_path.lower().endswith('.pdf'):
            reader = PdfReader(file_path)
            content = "".join(page.extract_text() for page in reader.pages)
        else:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()
        return content
    except Exception as e:
        return None

# Route to read a file
@app.route("/read", methods=["POST"])
def read_file():
    data = request.json
    module = data.get("module")
    subject = data.get("subject")
    file_path = os.path.join(FILES_DIR, module, subject)

    if not os.path.exists(file_path):
        return jsonify({"response": f"File '{subject}' not found in '{module}'."})

    content = extract_file_content(file_path)
    if content:
        return jsonify({"response": content})
    return jsonify({"response": "Error reading file."})

# Route to summarize a file
@app.route("/summarize", methods=["POST"])
def summarize_file():
    data = request.json
    module = data.get("module")
    subject = data.get("subject")
    file_path = os.path.join(FILES_DIR, module, subject)

    if not os.path.exists(file_path):
        return jsonify({"response": f"File '{subject}' not found in '{module}'."})

    content = extract_file_content(file_path)
    if content:
        try:
            summary = summarizer(content, max_length=150, min_length=50, do_sample=False)[0]['summary_text']
            return jsonify({"response": summary})
        except Exception as e:
            return jsonify({"response": f"Error summarizing file: {str(e)}"})
    return jsonify({"response": "Error reading file."})

# Route for the history page
@app.route("/history")
def history():
    return render_template("history.html", chat_history=chat_history)

# Route for the account page
@app.route("/account")
def account():
    return render_template("account.html")

@app.route('/quiz')
def some_view():
    modules = {
        'Module 1': ['Subject 1', 'Subject 2'],
        'Module 2': ['Subject 3', 'Subject 4']
    }
    return render_template('quiz.html', modules=modules)

@app.route("/hmi3")
def hmi3():
    return render_template("hmi3.html")

@app.route("/hmi5")
def hmi5():
    return render_template("hmi5.html")

@app.route("/hmi6")
def hmi6():
    return render_template("hmi6.html")

@app.route("/ml1")
def ml1():
    return render_template("ml1.html")

@app.route("/ml2")
def ml2():
    return render_template("ml2.html")



if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
