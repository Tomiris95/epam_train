#python
import streamlit as st
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import AIMessage
import weaviate
import weaviate.classes as wvc

from wrappers import LocalHuggingFaceEmbeddings, LocalHuggingFaceChatModel  

# STREAMLIT UI CONFIG
st.set_page_config(page_title="Smart Toddler RAG Assistant", layout="centered")

st.title("🧠 Smart Toddler Care Assistant (1–3 Years)")
st.markdown("Ask any question about toddler health, feeding, sleep, development, and Montessori activities.")

# Config
WEAVIATE_HTTP_PORT = 8080
WEAVIATE_GRPC_PORT = 50051
COLLECTION_NAME = "SimpleRAG"

# Initialize embeddings and chat model
embeddings_model = LocalHuggingFaceEmbeddings("google/embeddinggemma-300m")
chat_model = LocalHuggingFaceChatModel("google/gemma-3-1b-it")

# Connect to Weaviate
weaviate_client = weaviate.connect_to_local(
    host="localhost",
    port=WEAVIATE_HTTP_PORT,
    grpc_port=WEAVIATE_GRPC_PORT
)
rag_collection = weaviate_client.collections.get(COLLECTION_NAME)

# Define prompts
expansion_prompt = ChatPromptTemplate.from_template(
    "You are an expert in information retrieval. "
    "Rephrase the following user query to be detailed and suitable for vector search. "
    "Return only the rephrased query.\n\nOriginal Query: '{query}'\n\nRephrased Query:"
)
query_expansion_chain = expansion_prompt | chat_model | StrOutputParser()

generation_prompt = ChatPromptTemplate.from_template(
    "You are a factual assistant. "
    "Answer the user's question only based on the provided context. "
    "Do not use external knowledge. Provide a concise summary with 2-3 sentences. Do not use bullet points. "
    "If the answer is not in the context, say: 'The provided context does not contain the answer to this question.'\n\n"
    "Context:\n{context}\n\nQuestion: {question}"
)
answer_generation_chain = generation_prompt | chat_model | StrOutputParser()

user_query = st.text_input("Enter your question:")

if user_query:
    # Expand query
    expanded_query = query_expansion_chain.invoke({"query": user_query})

    st.write("**Expanded Query for Search:**", expanded_query)

    # Embed query
    query_embedding = embeddings_model.embed_query(expanded_query)

    # Retrieve documents from Weaviate
    retrieved_objects = rag_collection.query.near_vector(
        near_vector=query_embedding,
        limit=5,
        return_metadata=wvc.query.MetadataQuery(distance=True)
    )

    retrieved_docs_content = [obj.properties['content'] for obj in retrieved_objects.objects]
    context_for_llm = "\n\n---\n\n".join(retrieved_docs_content)

    # Generate final answer
    final_answer = answer_generation_chain.invoke({
        "context": context_for_llm,
        "question": user_query
    })

    st.text_area("Answer:", value=final_answer, height=300)

# FOOTER
st.markdown("---")
st.markdown("🧠 Smart Toddler RAG System")
