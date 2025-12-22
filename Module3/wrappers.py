from langchain_core.messages import AIMessage
from langchain_core.runnables import Runnable, RunnableConfig
import weaviate
import weaviate.classes as wvc
from weaviate.util import generate_uuid5
from sentence_transformers import SentenceTransformer
from transformers import pipeline
import torch
import numpy as np

# --- Wrapper class for the local Embeddings model ---
class LocalHuggingFaceEmbeddings:
    """
    This class adapts a local SentenceTransformer model
    to the LangChain interface, which expects the methods embed_documents and embed_query.
    """
    def __init__(self, model_name):
        print(f"📥 Loading local embedding model: {model_name}...")
        try:
            self.model = SentenceTransformer(model_name)
            print("✅ Local embedding model loaded successfully.")
        except Exception as e:
            print(f"❌ Error loading {model_name}. Falling back to 'all-MiniLM-L6-v2'.")
            print(f"Error details: {e}")
            self.model = SentenceTransformer("sentence-transformers/all-MiniLM-L6-v2")

    def embed_documents(self, texts):
        # Returns a list of lists
        embeddings = self.model.encode(texts, convert_to_numpy=True)
        return embeddings.tolist()

    def embed_query(self, text):
        # Returns a single list
        embedding = self.model.encode(text, convert_to_numpy=True)
        return embedding.tolist()


# --- Wrapper class for the local LLM ---
class LocalHuggingFaceChatModel(Runnable):
    """
    A simple wrapper around the Transformers Pipeline to make it compatible
    with LangChain's 'invoke' method and the pipe '|' operator.
    """
    def __init__(self, model_name):
        print(f"📥 Loading local LLM: {model_name}...")
        # This is the 'Automatic Transmission' setup we discussed:
        # 1. device=-1 forces CPU usage.
        # 2. torch_dtype=torch.float32 is the fastest format for CPU.
        self.pipe = pipeline(
            "text-generation",
            model=model_name,
            device=-1,
            torch_dtype=torch.float32
        )
        print("✅ Local LLM loaded successfully.")

    def invoke(self, input_data, config: RunnableConfig = None, **kwargs):
        """
        Adapts LangChain inputs (PromptValue or Messages) to the pipeline format.
        """
        # 1. Convert LangChain input to the list-of-dicts format expected by the pipeline
        messages = []

        # Handle LangChain PromptValue (which has .to_messages())
        if hasattr(input_data, 'to_messages'):
            lc_messages = input_data.to_messages()
            for msg in lc_messages:
                # Map LangChain message types to role strings
                role = "user"
                if msg.type == "system": role = "system"
                elif msg.type == "ai": role = "assistant"

                # Gemma pipeline expects content as a list of dicts or string.
                messages.append({"role": role, "content": [{"type": "text", "text": msg.content}]})

        # Handle raw string input (fallback)
        elif isinstance(input_data, str):
            messages = [{"role": "user", "content": [{"type": "text", "text": input_data}]}]

        # 2. Run the pipeline ("Automatic Transmission")
        # We set max_new_tokens to limit the answer length
        outputs = self.pipe(messages, max_new_tokens=512)

        # 3. Extract the generated text
        # The pipeline returns a list of dicts. The last message is the assistant's reply.
        generated_text = outputs[0]['generated_text'][-1]['content']

        # 4. Return as an AIMessage to satisfy LangChain's StrOutputParser
        return AIMessage(content=generated_text)
