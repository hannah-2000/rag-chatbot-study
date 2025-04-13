
import sys
sys.path.append("../")
import os
from retrieval.rag_retriever import Retriever
from retrieval.answer_generator import AnswerGenerator
from retrieval.keyword_retriever import KeywordRetriever

#from key import openAIkey #TODO andere lösung
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.cross_encoders.huggingface import HuggingFaceCrossEncoder

#from langchain.retrievers.document_compressors import CrossEncoderReranker
import streamlit as st #TODO delete, only for local testing
import time
#os.environ["OPENAI_API_KEY"] = st.secrets["OPENAI_API_KEY"] #TODO delete, only for local testing
# Check if MPS (Metal Performance Shaders) is available
#device = "mps" if torch.backends.mps.is_available() else "cpu"
openai_api_key = st.secrets["openAI"]["open_ai_key"]

class Pipeline:
    def __init__(self, chroma_path, keyword_index_path):
        """
        Initialize the pipeline with paths for both RAG (ChromaDB) and keyword search (Whoosh).

        Parameters:
            chroma_path (str): Path to the Chroma database for RAG.
            keyword_index_path (str): Path to the Whoosh index for keyword search.
        """
        #os.environ["OPENAI_API_KEY"] = openAIkey
        self.chroma_path = chroma_path
        self.keyword_index_path = keyword_index_path  # Store both retrieval paths
        
        #self.embedding_model_OA = OpenAIEmbeddings(model="text-embedding-ada-002")
        self.embedding_model_OA = OpenAIEmbeddings(model="text-embedding-3-large", openai_api_key= openai_api_key) #use best embedding model in bechmarks
        print("embedding model loaded")
        #self.model = ChatOpenAI(model="gpt-3.5-turbo")
        self.model = ChatOpenAI(model="gpt-4o", openai_api_key=openai_api_key) #use best model in benchmarks
        print("model loaded")
        # Initialize Reranker
        #self.reranker_model =HuggingFaceCrossEncoder(model_name= "BAAI/bge-reranker-small")#"BAAI/bge-reranker-base")
        # local_model_path = "retrieval/reranker_model"  # Path to saved model
        # self.reranker_model = HuggingFaceCrossEncoder(model_name=local_model_path)
        #self.reranker = None
        print("reranker model loaded")
        # Initialize retrievers
        self.keyword_retriever = KeywordRetriever(index_dir=keyword_index_path)  
        print("keyword retriever loaded")
        self.rag_retriever = None  # Will be initialized dynamically to avoid redundant computation


    def get_rag_retriever(self, query):
        """
        Lazily initializes the Retriever instance only when needed.
        """
        #if self.rag_retriever is None:
            
        self.rag_retriever = Retriever(
            chroma_path=self.chroma_path,
            embedding_model=self.embedding_model_OA,
            multiquery_llm=self.model,
            reranker_model= None,#self.reranker_model,
            query=query
        )
        return self.rag_retriever

    def retrieve_rag(self, query, filters=None, multiquery=True, rerank=False, k=5):
        """
        Retrieve documents using RAG (ChromaDB + embeddings).
        """
        print("Using RAG retrieval...")
        retriever = self.get_rag_retriever(query)
        print("retriever intitialized")
        retrieved_docs = retriever.retrieve(
            rerank=rerank,
            multiquery=multiquery,
            filters=filters,
            search_type="similarity",
            k=k
        )
        print(f"RAG retrieval complete. Retrieved {len(retrieved_docs)} documents.")
        print("retrieved docs: ", retrieved_docs)
        return retrieved_docs

    def retrieve_keyword(self, query, filters=None, k=5):
        """
        Retrieve documents using Keyword Search (Whoosh index).
        """
        print("Using Keyword retrieval...")
        return self.keyword_retriever.search(query, **(filters or {}), top_k=k)

    def retrieve(self, query, search_mode="rag", filters=None, multiquery=True, rerank=False, k=5):
        """
        Dynamically chooses between RAG or keyword search based on `search_mode`.
        """
        if search_mode == "rag":
            return self.retrieve_rag(query, filters, multiquery, rerank, k)
        elif search_mode == "keyword":
            return self.retrieve_keyword(query, filters, k)
        else:
            raise ValueError("Invalid search mode. Choose 'rag' or 'keyword'.")

    def answer(self, query, retrieved_docs):
        """
        Generate an answer using retrieved documents.
        """
        if not retrieved_docs:
            return "No relevant documents found."
        print("***********RETRIEVED DOCUMENTS************")
        print(retrieved_docs)
        print("***********RETRIEVED DOCUMENTS ENDE************")
        answer_generator = AnswerGenerator(self.model)
        return answer_generator.generate_answer(query=query, retrieved_docs=retrieved_docs)

    def process_query(self, query, search_mode="rag", filters=None, multiquery=True, rerank=False, k=5):
        """
        Process the query using the selected retrieval method.

        Parameters:
            query (str): The user's search query.
            search_mode (str): Either "rag" or "keyword".
            filters (dict, optional): Filters for metadata-based retrieval.
            multiquery (bool): Whether to use multiquery retrieval.
            selfquery (bool): Whether to use self-query retrieval.
            rerank (bool): Whether to apply reranking.
            k (int): Number of top documents to return.

        Returns:
            str or list: The final answer if RAG is used, or retrieved documents if keyword search is used.
        """
        print(f"Processing query with {search_mode.upper()} retrieval...")
        retrieval_start = time.time()
        retrieved_docs = self.retrieve(query, search_mode, filters, multiquery, rerank, k)
        retrieval_end = time.time()
        retrieval_time = retrieval_end - retrieval_start
        print(f"Retrieval complete in {retrieval_time:.2f}")

        # Generate an answer only for RAG retrieval
        answer_start = time.time()
        answer = self.answer(query, retrieved_docs)
        answer_end = time.time()
        answer_time = answer_end - answer_start
        print(f"Answer generation complete in {answer_time:.2f}")
        return answer


if __name__ == "__main__":
    chroma_path = "../data/data_embedded"  
    keyword_index_path = "../data/data_indexed"  

    pipeline = Pipeline(chroma_path, keyword_index_path)

    print("\n📥 Ready to take questions! Type 'exit' to quit.\n")
    while True:
        query = input("🔍 Enter your query: ")
        if query.lower() in ["exit", "quit"]:
            print("👋 Exiting.")
            break

        search_mode = input("💡 Retrieval mode (rag/keyword)? [default: rag]: ").strip().lower() or "rag"

        try:
            answer = pipeline.process_query(query, search_mode=search_mode)
            print("\n🧠 Answer:\n", answer)
            print("-" * 50)
        except Exception as e:
            print("❌ Error while processing query:", e)