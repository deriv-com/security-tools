from openai import OpenAI
from logger import logger # Import the centralized logger

class OpenAIAPI:
    def __init__(self, api_key):
        self.api_key = api_key
        self.client = OpenAI(api_key=api_key)
        
    def chat_completion(self, prompt, prompt_sys=None, temperature=0.7, max_tokens=4000):
        """
        Send a chat completion request to OpenAI API using the official client
        """
        messages = []
        if prompt_sys:
            messages.append({"role": "system", "content": prompt_sys})
        messages.append({"role": "user", "content": prompt})
        
        try:
            logger.info("Sending chat completion request to OpenAI API")
            response = self.client.chat.completions.create(
                model="gpt-4",
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            logger.info("Successfully received response from OpenAI API")
            
            if response.choices and response.choices[0].message.content:
                return response.choices[0].message.content
            else:
                logger.error("No valid response content in API response")
                raise Exception("No valid response content")
                
        except Exception as e:
            logger.error(f"OpenAI API request failed: {str(e)}")
            raise Exception(f"API request failed: {str(e)}")
