from langchain_chroma import Chroma  # old: from langchain.vectorstores import Chroma
from langchain.retrievers.document_compressors import CrossEncoderReranker
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain.prompts import PromptTemplate
import streamlit as st
# Check if MPS (Metal Performance Shaders) is available


class Retriever:
    """
    Handles document retrieval with optional multiquery expansion, self-query, and reranking.
    """


    def __init__(self, chroma_path, embedding_model, multiquery_llm, reranker_model, query):
        """
        Initializes the Retriever with RAG and reranking capabilities.

        Parameters:
            chroma_path (str): Path to the Chroma vector database.
            embedding_model (Embeddings): The embedding model used for similarity search.
            multiquery_llm (LLM): The LLM used for multiquery retrieval.
            query (str): The user query.
        """
        self.embeddings = embedding_model
        self.vectorstore = Chroma(persist_directory=chroma_path, embedding_function=embedding_model)
        self.query = query
        self.llm = multiquery_llm
        print("before reranker model initialization")
        # Use HuggingFaceCrossEncoder for LangChain compatibility
        #self.reranker_model = HuggingFaceCrossEncoder(model_name="BAAI/bge-reranker-base")
        self.reranker_model = reranker_model
        #self.reranker = self.load_reranker() #TODO-> works?
        # Wrap it inside LangChain's CrossEncoderReranker
        #self.reranker = CrossEncoderReranker(model=self.reranker_model, top_n=5)  # Adjust `top_n` if needed

    def create_retriever(self, filters=None, search_type="similarity", multiquery=True, k=5):
        """
        Creates a retriever from the Chroma vector store.

        Parameters:
            filters (dict): Metadata filters.
            search_type (str): The retrieval method (e.g., "similarity").
            selfquery (bool): Whether to use a self-query retriever.
            multiquery (bool): Whether to use a multiquery retriever.
            k (int): Number of documents to retrieve.

        Returns:
            retriever: A LangChain retriever object.
        """
        retriever = self.vectorstore.as_retriever(
            search_type=search_type,
            search_kwargs={"k": k, "filter": filters}
        )

        # # Use self-query retriever if enabled
        # if selfquery:
        #     retriever = self.self_query_retriever()

        # Use MultiQueryRetriever if enabled
        if multiquery:
            retriever = self.multiquery_retriever(retriever, self.llm)

        return retriever

    def retrieve(self, filters=None, search_type="similarity", rerank=False, multiquery=True, k=5):#HERE reranker!!
        """
        Retrieves and optionally reranks documents based on user settings.

        Parameters:
            filters (dict): Metadata filters for narrowing down the search.
            search_type (str): Type of retrieval method (e.g., "similarity").
            rerank (bool): Whether to apply reranking after retrieval.
            selfquery (bool): Whether to use a self-query retriever.
            multiquery (bool): Whether to use a multiquery retriever.
            k (int): Number of top documents to retrieve.

        Returns:
            List[Document]: A list of retrieved (and optionally reranked) documents.
        """
        adjusted_k = k * 4 #if not multiquery else k  # If not using multiquery, retrieve more docs
        
        retriever = self.create_retriever(filters=filters, search_type=search_type,  multiquery=multiquery, k=adjusted_k)
        print("retriever", retriever)
        retrieved_docs = retriever.invoke(self.query)
        print(f"Retrieved {len(retrieved_docs)} docs with filters: {filters}")  

        # Apply reranking if enabled
        if rerank:
            print("RERANNNNNNK")
            retrieved_docs = self.apply_reranking(retrieved_docs, k)

        return retrieved_docs[:k]  # Keep only top-k results

    def apply_reranking(self, retrieved_docs, k):
        """
        Applies reranking to the retrieved documents using the preloaded reranker.

        Parameters:
            retrieved_docs (List[Document]): Documents retrieved from the vector database.
            k (int): The number of top documents to return after reranking.

        Returns:
            List[Document]: The reranked list of top k documents.
        """
        # Apply reranking directly on the retrieved documents
        reranked_docs = self.reranker.compress_documents(retrieved_docs, self.query)
        print("WHYYYY")
        return reranked_docs[:k]  # ✅ Keep only top-k results

    def multiquery_retriever(self, retriever, llm):
        """
        Applies multiquery retrieval by generating variations of the query.

        Parameters:
            retriever: The base retriever object that fetches documents.
            llm (LLM): The language model used for query expansion.

        Returns:
            MultiQueryRetriever: A retriever that expands the query into multiple versions.
        """
        multiquery_prompt = PromptTemplate.from_template(
            partial_variables={"query": self.query},
            template="""You are a precise AI language model assistant. Your task is to generate exactly 4 
                different variations of the given user query without adding or expanding its meaning.
                - DO NOT add additional context.
                - DO NOT assume or infer missing information.
                - DO NOT include location, specific institutions, or implicit assumptions.
                - Maintain the same length as the original query.
                - Respond with ONLY the 4 reformulated queries, each on a separate line, with NO extra text.

                Original query: {query}"""
        )

        retriever = MultiQueryRetriever.from_llm(
            retriever=retriever,
            llm=llm,
            prompt=multiquery_prompt
        )
        return retriever

