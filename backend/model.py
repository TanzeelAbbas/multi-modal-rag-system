import os
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough

load_dotenv()

class LangChainQAService:
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize LangChain QA Service with Gemini
        
        Args:
            api_key (Optional[str]): Google Generative AI API Key (default: from .env)
        """
        self.api_key = api_key or os.getenv('GOOGLE_API_KEY')
        if not self.api_key:
            raise ValueError("Google API Key is required. Please set GOOGLE_API_KEY in the .env file.")

        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            google_api_key=self.api_key,
            temperature=0.1, 
            max_output_tokens=512
        )

        self.qa_prompt = PromptTemplate.from_template("""
        You are a helpful AI assistant for document question-answering.
        
        Context:
        {context}
        
        Question: {question}
        
        Provide a comprehensive and precise answer based on the given context.
        If the context is insufficient, state that clearly.
        
        Helpful Answer:""")

        print("LangChain QA Service initialized successfully.")

    def generate_answer(
        self, 
        query: str, 
        context: List[Dict[str, Any]] = None
    ) -> str:
        """
        Generate answer using LangChain and Gemini
        
        Args:
            query (str): User's question
            context (List[Dict[str, Any]], optional): Context documents
        
        Returns:
            str: Generated answer
        """
        try:
            context_text = "\n\n".join([
                ctx.get('text', '') for ctx in (context or [])
            ])

            print(f"Context Text: {context_text}")

            rag_chain = (
                {"context": lambda x: context_text, "question": RunnablePassthrough()}
                | self.qa_prompt
                | self.llm
                | StrOutputParser()
            )

            response = rag_chain.invoke(query)
            return response

        except Exception as e:
            return f"Error generating answer: {str(e)}"

    def validate_api_key(self) -> bool:
        """
        Validate the Google API Key
        
        Returns:
            bool: True if API key is valid, False otherwise
        """
        try:
            test_response = self.llm.invoke("Hello, can you confirm the API is working?")
            return test_response is not None
        except Exception:
            return False