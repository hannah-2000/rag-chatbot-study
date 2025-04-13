from whoosh.qparser import MultifieldParser, OrGroup
from whoosh.index import open_dir
from whoosh.query import And, Term
from textblob import TextBlob  #Simple spell checker
from langchain.schema import Document  # fro answer generator
print("✅ keyword_retriever.py was loaded")
class KeywordRetriever:
    """
    Handles keyword-based retrieval from the Whoosh index.
    """


    def __init__(self, index_dir):
        """Opens the existing Whoosh index for searching."""
        #self.ix = open_dir(index_dir)
        import os
        print("INDEX DIR:", index_dir)
        print("FILES:", os.listdir(index_dir))
        try:
            self.ix = open_dir(index_dir, indexname="MAIN_463")
        except Exception as e:
            print("FAILED TO OPEN INDEX:", e)
            raise
        #self.ix = open_dir(index_dir, indexname="MAIN_463")
    #OLD without heading as metadata
    # def search(self, query, semester=None, course=None, lecture=None, top_k=5, return_snippets=True):
    #     """
    #     Performs a keyword-based search with optional filtering.

    #     Args:
    #         query (str): The search query.
    #         semester (str, optional): Filter by semester.
    #         course (str, optional): Filter by course.
    #         lecture (str, optional): Filter by lecture.
    #         top_k (int): Number of results to return.
    #         return_snippets (bool): If True, return text snippets instead of full content.

    #     Returns:
    #         List[Dict]: Retrieved documents in a structured format.
    #     """
    #     with self.ix.searcher() as searcher:
    #         parser = MultifieldParser(["content", "title", "course", "lecture"], schema=self.ix.schema)
    #         #TODO weighting of content!!
    #         parsed_query = parser.parse(query)

    #         # Apply Whoosh filtering directly instead of manual filtering
    #         filters = []
    #         if semester:
    #             filters.append(Term("semester", semester))
    #         if course:
    #             filters.append(Term("course", course))
    #         if lecture:
    #             filters.append(Term("lecture", lecture))

    #         filter_query = And(filters) if filters else None
    #         results = searcher.search(parsed_query, limit=top_k, filter=filter_query)

    #         formatted_results = []
    #         for hit in results:
    #             formatted_results.append({
    #                 "title": hit["title"],
    #                 "semester": hit["semester"],
    #                 "course": hit["course"],
    #                 "lecture": hit["lecture"],
    #                 "page": hit["page"],
    #                 #"content": hit.highlights("content") if return_snippets else hit["content"],
    #                 "content": hit["content"]
    #             })

    #     return formatted_results
    #OLD ende
    #new
    def correct_spelling(self,query):
        """Uses TextBlob to correct spelling in the query before searching."""
        return str(TextBlob(query).correct())  # Returns the corrected query as a string

    def search(self, query, semester=None, course=None, lecture=None, top_k=5):
        """
        Performs a keyword-based search with:
        - Spelling correction
        - OR-based query parsing (allows partial matches)
        - Field weighting for ranking
        - BM25F scoring for relevance

        Args:
            query (str): The search query.
            semester (str, optional): Filter by semester.
            course (str, optional): Filter by course.
            lecture (str, optional): Filter by lecture.
            top_k (int): Number of results to return.

        Returns:
            List[Dict]: Retrieved documents in a structured format.
        """
        with self.ix.searcher() as searcher: 
            # Step 1: Correct the query
            corrected_query = self.correct_spelling(query)
            print(f"🔍 Corrected Query: {corrected_query}")

            # Step 2: Use OR-based query parsing with field weighting
            parser = MultifieldParser(
                ["content", "course", "lecture", "header"],  # Fields to search
                schema=self.ix.schema,
                group=OrGroup.factory(0.9)  # Allows partial matches, prioritizes more matches
            )
            parser.fieldboosts = {  # Apply field weighting
                "content": 3.0,  # Prioritize content matches
                "course": 1.5,  # Course matches matter, but less
                "lecture": 1.2,  # Lecture names have some weight
                "header": 1.0  # Header matches are the weakest
            }

            parsed_query = parser.parse(corrected_query)  # Parse the corrected query

            # Step 3: Apply metadata filters
            filters = []
            # Unpack $in filters if present
            if isinstance(semester, dict) and "$in" in semester:
                semester = semester["$in"][0] if semester["$in"] else None
            if isinstance(course, dict) and "$in" in course:
                course = course["$in"][0] if course["$in"] else None
            if isinstance(lecture, dict) and "$in" in lecture:
                lecture = lecture["$in"][0] if lecture["$in"] else None

            if semester:
                filters.append(Term("semester", semester))
            if course:
                filters.append(Term("course", course))
            if lecture:
                filters.append(Term("lecture", lecture))

            filter_query = And(filters) if filters else None

            # Step 4: Perform the search
            results = searcher.search(parsed_query, filter=filter_query, limit=top_k)

            # Step 5: Format and return results
            formatted_results = []
            for hit in results:
                #NEW
                metadata = {
                "course": hit.get("course", "Unknown Course"),
                "lecture": hit.get("lecture", "Unknown Lecture"),
                "semester": hit.get("semester", "Unknown Semester"),
                "page": hit.get("page", "Unknown Page"),
                "header": hit.get("header", "")
                }

                # formatted_results.append({
                #     "title": hit["title"],
                #     "semester": hit["semester"],
                #     "course": hit["course"],
                #     "lecture": hit["lecture"],
                #     "page": hit["page"],
                #     "header": hit.get("header", ""),
                #     "content": hit["content"],
                #     "score": hit.score  # Include score for ranking verification
                # })
                #NEW
                # formatted_results.append({
                # "page_content": hit["content"],  # ✅ Matches RAG retrieval structure
                # "metadata": metadata
                # })
                formatted_results.append(Document(
                    page_content=hit["content"], 
                    metadata=metadata
                ))

        return formatted_results
        #new ende

# # Example usage
# if __name__ == "__main__":
#     retriever = KeywordRetriever()
#     search_results = retriever.search("machine learning", semester="SoSe 2023", course="AI", top_k=3)
#     for res in search_results:
#         print(f"Title: {res['title']}, Content: {res['content']}")