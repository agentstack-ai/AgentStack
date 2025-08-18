import os
import json
import requests
from typing import List, Dict, Optional, Union

class ChatPDFTool:
    def __init__(self):
        # Load config
        config_path = os.path.join(os.path.dirname(__file__), "config.json")
        with open(config_path) as f:
            self.config = json.load(f)
        
        self.api_key = self.config["env"]["CHATPDF_API_KEY"]
        if not self.api_key or self.api_key == "sec_xxxxxx":
            raise ValueError("Please set your ChatPDF API key in config.json")
        
        self.headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
        }
        self.base_url = self.config["url"] + "/v1"

    def add_pdf_from_url(self, url: str) -> str:
        """Add a PDF to ChatPDF using a URL.
        
        Args:
            url: Public URL of the PDF file
            
        Returns:
            source_id: The ID to use for chatting with this PDF
        """
        endpoint = f"{self.base_url}/sources/add-url"  # Fixed back to add-url
        response = requests.post(endpoint, headers=self.headers, json={"url": url})
        response.raise_for_status()
        return response.json()["sourceId"]

    def add_pdf_from_file(self, file_path: str) -> str:
        """Add a PDF to ChatPDF by uploading a file.
        
        Args:
            file_path: Path to the PDF file
            
        Returns:
            source_id: The ID to use for chatting with this PDF
        """
        endpoint = f"{self.base_url}/sources/add-file"  # Fixed back to add-file
        headers = {"x-api-key": self.api_key}  # Don't include Content-Type for multipart
        
        with open(file_path, 'rb') as file:
            files = {'file': ('document.pdf', file, 'application/pdf')}
            response = requests.post(endpoint, headers=headers, files=files)
        
        response.raise_for_status()
        return response.json()["sourceId"]

    def chat(
        self, 
        source_id: str, 
        question: str, 
        chat_history: Optional[List[Dict[str, str]]] = None,
        reference_sources: bool = True,
        stream: bool = False
    ) -> Dict[str, Union[str, List[Dict[str, int]]]]:
        """Chat with a PDF using its source ID.
        
        Args:
            source_id: The ID of the PDF to chat with
            question: The question to ask
            chat_history: Optional list of previous messages
            reference_sources: Whether to include page references
            stream: Whether to stream the response
            
        Returns:
            Dict containing the response content and optional references
        """
        endpoint = f"{self.base_url}/chats/message"
        
        # Build messages array
        messages = []
        if chat_history:
            messages.extend(chat_history)
        messages.append({
            "role": "user",
            "content": question
        })
        
        data = {
            "sourceId": source_id,
            "messages": messages
        }
        
        # Only add optional parameters if they're different from defaults
        if reference_sources:
            data["referenceSources"] = reference_sources
        if stream:
            data["stream"] = stream
        
        response = requests.post(endpoint, headers=self.headers, json=data)
        response.raise_for_status()
        return response.json()

def ask_pdf_url(url: str, question: str) -> str:
    """Quick function to ask a question about a PDF from a URL.
    
    Args:
        url: Public URL of the PDF
        question: Question to ask about the PDF
        
    Returns:
        Answer from ChatPDF
    """
    tool = ChatPDFTool()
    source_id = tool.add_pdf_from_url(url)
    response = tool.chat(source_id, question)
    return response["content"]

def ask_pdf_file(file_path: str, question: str) -> str:
    """Quick function to ask a question about a PDF file.
    
    Args:
        file_path: Path to the PDF file
        question: Question to ask about the PDF
        
    Returns:
        Answer from ChatPDF
    """
    tool = ChatPDFTool()
    source_id = tool.add_pdf_from_file(file_path)
    response = tool.chat(source_id, question)
    return response["content"]

if __name__ == "__main__":
    # Example usage
    pdf_url = "https://uscode.house.gov/static/constitution.pdf"
    question = "What are the first three articles about?"
    
    try:
        print(f"Adding PDF from URL: {pdf_url}")
        tool = ChatPDFTool()
        source_id = tool.add_pdf_from_url(pdf_url)
        print(f"Got source ID: {source_id}")
        
        print(f"\nAsking question: {question}")
        response = tool.chat(source_id, question)
        print(f"Answer: {response['content']}")
    except Exception as e:
        print(f"Error: {str(e)}")