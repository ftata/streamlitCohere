import streamlit as st
import cohere
import io
import fitz  # For PDF processing
import docx  # For DOCX processing
import os

# Initialize Cohere client with your API key from an environment variable
cohere_api_key = os.getenv('CO_KEY')
if not cohere_api_key:
    st.error("Cohere API key not found. Please set the CO_KEY environment variable.")
    st.stop()
co = cohere.Client(cohere_api_key)

st.title('Document Question Answering System')

# File uploader widget to accept multiple files
uploaded_files = st.file_uploader("Upload your documents:", type=['pdf', 'txt', 'docx'], accept_multiple_files=True)

question = st.text_input("Enter your question:")

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
                    text += page.get_text()
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
        remaining_length -= len(truncated_text)
    return "\n".join(truncated_texts)

if st.button('Get Answer'):
    if uploaded_files and question:
        with st.spinner('Processing...'):
            document_texts = [extract_text(uploaded_file) for uploaded_file in uploaded_files]
            truncated_document_text = truncate_documents(document_texts, 4000)
            try:
                response = co.generate(
                    model='command',  # cohere model name
                    prompt=f"Documents: {truncated_document_text}\nQuestion: {question}\nAnswer:",
                    max_tokens=50,
                    temperature=0.5,
                    stop_sequences=["\n"],
                )
                answer = response.generations[0].text.strip()
                
                # update conversation history in session state
                st.session_state['conversation_history'].append((question, answer))
                
            except Exception as e:
                st.error(f"Error generating answer: {e}")
    else:
        st.write("Please upload documents and enter a question.")

# Display conversation history
st.write("Conversation History:")
for idx, (q, a) in enumerate(st.session_state['conversation_history']):
    st.text_area(f"Question {idx+1}", q, height=75, key=f"q_{idx}")
    st.text_area(f"Answer {idx+1}", a, height=150, key=f"a_{idx}")
