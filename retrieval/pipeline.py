
from retrieval.rag_retriever import Retriever
from retrieval.answer_generator import AnswerGenerator
from retrieval.keyword_retriever import KeywordRetriever
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
import streamlit as st 
openai_api_key = st.secrets["openAI"]["open_ai_key"]

class Pipeline:
    def __init__(self, chroma_path, keyword_index_path):
        """
        Initialize the pipeline with paths for both RAG (ChromaDB) and keyword search (Whoosh).

        Parameters:
            chroma_path (str): Path to the Chroma database for RAG.
            keyword_index_path (str): Path to the Whoosh index for keyword search.
        """
        self.chroma_path = chroma_path
        self.keyword_index_path = keyword_index_path 
        
        self.embedding_model_OA = OpenAIEmbeddings(model="text-embedding-3-large", openai_api_key= openai_api_key) 
        self.model = ChatOpenAI(model="gpt-4o", openai_api_key=openai_api_key) 
        self.keyword_retriever = KeywordRetriever(index_dir=keyword_index_path)  
        self.rag_retriever = None  

    def get_rag_retriever(self, query):
        """
        Lazily initializes the Retriever instance only when needed.
        """
            
        self.rag_retriever = Retriever(
            chroma_path=self.chroma_path,
            embedding_model=self.embedding_model_OA,
            multiquery_llm=self.model,
            query=query
        )
        return self.rag_retriever

    def retrieve_rag(self, query, filters=None, multiquery=True, k=5):
        """
        Retrieve documents using RAG (ChromaDB + embeddings).
        """
        retriever = self.get_rag_retriever(query)
        retrieved_docs = retriever.retrieve(
            multiquery=multiquery,
            filters=filters,
            search_type="similarity",
            k=k
        )
        return retrieved_docs

    def retrieve_keyword(self, query, filters=None, k=5):
        """
        Retrieve documents using Keyword Search (Whoosh index).
        """
        return self.keyword_retriever.search(query, **(filters or {}), top_k=k)

    def retrieve(self, query, search_mode="rag", filters=None, multiquery=True, k=5):
        """
        Dynamically chooses between RAG or keyword search based on `search_mode`.
        """
        if search_mode == "rag":
            return self.retrieve_rag(query, filters, multiquery, k)
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
        answer_generator = AnswerGenerator(self.model)
        return answer_generator.generate_answer(query=query, retrieved_docs=retrieved_docs)

    def process_query(self, query, search_mode="rag", filters=None, multiquery=True, k=5):
        """
        Process the query using the selected retrieval method.

        Parameters:
            query (str): The user's search query.
            search_mode (str): Either "rag" or "keyword".
            filters (dict, optional): Filters for metadata-based retrieval.
            multiquery (bool): Whether to use multiquery retrieval.
            k (int): Number of top documents to return.

        Returns:
            str or list: The final answer if RAG is used, or retrieved documents if keyword search is used.
        """
        retrieved_docs = self.retrieve(query, search_mode, filters, multiquery, k)

        answer = self.answer(query, retrieved_docs)
        return answer

