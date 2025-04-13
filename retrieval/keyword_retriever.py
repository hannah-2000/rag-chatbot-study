from whoosh.qparser import MultifieldParser, OrGroup
from whoosh.index import open_dir
from whoosh.query import And, Term
from textblob import TextBlob  
from langchain.schema import Document 



class KeywordRetriever:
    """
    Handles keyword-based retrieval from the Whoosh index.
    """
    def __init__(self, index_dir):
        """Opens the existing Whoosh index for searching."""
        self.ix = open_dir(index_dir)
        
    def correct_spelling(self,query):
        """Uses TextBlob to correct spelling in the query before searching."""
        return str(TextBlob(query).correct())

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
            corrected_query = self.correct_spelling(query)

            parser = MultifieldParser(
                ["content", "course", "lecture", "header"],  
                schema=self.ix.schema,
                group=OrGroup.factory(0.9)  # Allows partial matches, prioritizes more matches
            )
            parser.fieldboosts = { 
                "content": 3.0,  # Prioritize content matches
                "course": 1.5,  
                "lecture": 1.2,  
                "header": 1.0  
            }

            parsed_query = parser.parse(corrected_query)  

            #Apply metadata filters
            filters = []
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

            #  Perform search
            results = searcher.search(parsed_query, filter=filter_query, limit=top_k)

            # Format and return results
            formatted_results = []
            for hit in results:
                metadata = {
                "course": hit.get("course", "Unknown Course"),
                "lecture": hit.get("lecture", "Unknown Lecture"),
                "semester": hit.get("semester", "Unknown Semester"),
                "page": hit.get("page", "Unknown Page"),
                "header": hit.get("header", "")
                }

                formatted_results.append(Document(
                    page_content=hit["content"], 
                    metadata=metadata
                ))

        return formatted_results