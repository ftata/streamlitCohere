import streamlit as st
import cohere
import io
import fitz  # For PDF processing
import docx  # For DOCX processing
import os

# Function to read CSS file and return as string
def load_css(file_name):
    with open(file_name, "r") as f:
        return f.read()

# Load and inject CSS styles
css_styles = load_css("styles/control-styles.css")
st.markdown(f"<style>{css_styles}</style>", unsafe_allow_html=True)

# Initialize Cohere client with your API key from an environment variable
cohere_api_key = os.getenv('CO_KEY')
if not cohere_api_key:
    st.error("Cohere API key not found. Please set the CO_KEY environment variable.")
    st.stop()
co = cohere.Client(cohere_api_key)

st.sidebar.title('Upload and Ask')

# File uploader widget in the sidebar
uploaded_files = st.sidebar.file_uploader("Upload your documents:", type=['pdf', 'txt', 'docx'], accept_multiple_files=True)

# Text input for the question in the sidebar
question = st.sidebar.text_input("Enter your question:")

# ADDED: Temperature slider for model generation
temperature = st.sidebar.slider("Adjust Temperature:", min_value=0.0, max_value=1.0, value=0.5, step=0.05)

# ADDED: Slider for max tokens
max_tokens = st.sidebar.slider("Max Tokens:", min_value=10, max_value=1000, value=50, step=10)

# Button to submit the question in the sidebar
submit_button = st.sidebar.button('Get Answer')

# Initialize session state for conversation history if it doesn't exist
if 'conversation_history' not in st.session_state:
    st.session_state['conversation_history'] = []

def extract_text(uploaded_file):
    text = ""
    if uploaded_file is not None:
        if uploaded_file.type == "text/plain":
            text = str(uploaded_file.read(), "utf-8")
        elif uploaded_file.type == "application/pdf":
            try:
                file_bytes = io.BytesIO(uploaded_file.read())
                pdf = fitz.open(stream=file_bytes, filetype="pdf")
                text = ""
                for page in pdf:
                    text += page.get_text("text")
            except Exception as e:
                st.error(f"Error processing PDF file: {e}")
        elif uploaded_file.type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
            try:
                doc = docx.Document(io.BytesIO(uploaded_file.read()))
                text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
            except Exception as e:
                st.error(f"Error processing DOCX file: {e}")
    return text

def truncate_documents(doc_texts, max_total_length=4000):
    truncated_texts = []
    remaining_length = max_total_length
    for text in doc_texts:
        if remaining_length <= 0:
            break
        truncated_text = text[:remaining_length]
        truncated_texts.append(truncated_text)
        remaining_length -= len(truncated_text.encode('utf-8'))
    return "\n".join(truncated_texts)

if submit_button:
    if uploaded_files and question:
        with st.spinner('Processing...'):
            document_texts = [extract_text(uploaded_file) for uploaded_file in uploaded_files]
            truncated_document_text = truncate_documents(document_texts, 4000)
            try:
                # UPDATED: Use the selected temperature and max tokens for model generation
                response = co.generate(
                    model='command',  # Model Name
                    prompt=f"Documents: {truncated_document_text}\nQuestion: {question}\nAnswer:",
                    max_tokens=max_tokens,
                    temperature=temperature,
                    stop_sequences=["\n"],
                )
                answer = response.generations[0].text.strip()
                
                # Update conversation history in session state
                st.session_state['conversation_history'].append((question, answer))
                
            except Exception as e:
                st.error(f"Error generating answer: {e}")
    else:
        st.error("Please upload documents and enter a question.")

# Display conversation history in the main area
st.title("Conversation History:")
for idx, (q, a) in enumerate(st.session_state['conversation_history']):
    st.text(f"Question {idx+1}: {q}")
    st.text_area(f"Answer {idx+1}", a, height=150, key=f"a_{idx}")
