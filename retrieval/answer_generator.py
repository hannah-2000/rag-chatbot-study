from langchain.prompts import PromptTemplate

class AnswerGenerator:
    '''
    Handles answer generation using an LLM based on retrieved documents.
    '''

    def __init__(self, llm):
        '''
        Initializes the AnswerGenerator with a language model.

        Parameters:
            llm (LLM): An instance of an LLM (e.g., OpenAI, HuggingFace).
        '''
        
        self.llm = llm

        self.prompt_template = PromptTemplate(
            input_variables=["query", "context"],
            template=(
                "You are a helpful assistant for students. Based on the following context, "
                "answer the query concisely and provide references to ALL the sources you used."
                "You must analyze the entire provided context and synthesize an answer using all relevant information. "
                "If the context includes multiple fragments, you should combine them into a complete answer rather than ignoring short segments."

                "- The references **must** be listed in their original format as provided in the metadata, except the semester."

                "- If multiple sources were used, list them all exactly as shown in the metadata."
                "- Do not replace sources with 'Provided context' or any other generalization."
                "- Use the **exact** pages, course name and lecture name from the metadata."
                "- Only! inclue course name, lecture name and pages for the sources!"


                "If you do not find useful or relevant information in the provided context, **DO NOT** make up an answer."
                "Simply respond with: 'I could not find any helpful information in the database.'"

                "Example:"
                "**Context:**"
                "- 'Neural networks are widely used in deep learning. (Source: ('pages': '10-12', 'course': 'Machine Learning', 'lecture': 'Neural Networks', 'semester': 'WiSe 2023'))'"
                "- 'Backpropagation is a key algorithm for training deep neural networks. (Source: ('pages': '30-42', 'course': 'Machine Learning', 'lecture': 'Deep Learning Fundamentals', 'semester': 'WiSe 2023'))'"

                "**Query:**"
                "'What is backpropagation?'"

                "**Answer:**"
                "'Backpropagation is a key algorithm for training deep neural networks by adjusting weights using gradient descent.'"

                "**Sources:**"
                "- Pages: 30-42, Course: Machine Learning, Lecture: Deep Learning Fundamentals"

                "---"

                "**Context:**"
                "{context}"

                "**Query:**"
                "{query}"
            )
        )
        self.chain = self.prompt_template | self.llm

    def generate_answer(self, query, retrieved_docs):
        '''
        Generates an answer based on the query and retrieved documents.

        Parameters:
            query (str): The user's query.
            retrieved_docs (List[Document]): List of retrieved documents.

        Returns:
            str: The generated answer with properly formatted sources.
        '''

        formatted_context = []

        for doc in retrieved_docs:
       
              formatted_context.append(f"- {doc.page_content} (Source: {doc.metadata})")
        context = "\n".join(formatted_context)

        # Generate answer 
        response = self.chain.invoke({"query": query, "context": context})

        return response
   