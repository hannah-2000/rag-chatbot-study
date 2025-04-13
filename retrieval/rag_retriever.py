from langchain_chroma import Chroma  
from langchain.retrievers.multi_query import MultiQueryRetriever
from langchain.prompts import PromptTemplate


class Retriever:
    """
    Handles document retrieval with optional multiquery expansion.
    """


    def __init__(self, chroma_path, embedding_model, multiquery_llm, query):
        """
        Initializes the Retriever.

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
        
    def create_retriever(self, filters=None, search_type="similarity", multiquery=True, k=5):
        """
        Creates a retriever from the Chroma vector store.

        Parameters:
            filters (dict): Metadata filters.
            search_type (str): The retrieval method (e.g., "similarity").
            multiquery (bool): Whether to use a multiquery retriever.
            k (int): Number of documents to retrieve.

        Returns:
            retriever: A LangChain retriever object.
        """
        retriever = self.vectorstore.as_retriever(
            search_type=search_type,
            search_kwargs={"k": k, "filter": filters}
        )

        if multiquery:
            retriever = self.multiquery_retriever(retriever, self.llm)

        return retriever

    def retrieve(self, filters=None, search_type="similarity", multiquery=True, k=5):
        """
        Retrieves documents based on user settings.

        Parameters:
            filters (dict): Metadata filters for narrowing down the search.
            search_type (str): Type of retrieval method (e.g., "similarity").
            multiquery (bool): Whether to use a multiquery retriever.
            k (int): Number of top documents to retrieve.

        Returns:
            List[Document]: A list of retrieved documents.
        """
        adjusted_k = k * 4 
        
        retriever = self.create_retriever(filters=filters, search_type=search_type,  multiquery=multiquery, k=adjusted_k)
        retrieved_docs = retriever.invoke(self.query)

        return retrieved_docs[:k]  # Keep only top-k results

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

