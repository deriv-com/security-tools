import requests
from logger import logger  # Import the centralized logger

class EraserAPI:
    def __init__(self, api_token: str):
        self.api_token = api_token
        self.headers = {
            "Authorization": f"Bearer {api_token}",
            "Accept": "application/json",
            "Content-Type": "application/json"
        }

    def generate_diagram_from_prompt(self, prompt: str) -> dict:
        """
        Generate a diagram using Eraser's AI diagram generation endpoint.
        
        Args:
            prompt (str): The text description of the diagram to generate
            
        Returns:
            dict: The response from Eraser's API containing the diagram data
        """
        endpoint = "https://app.eraser.io/api/render/prompt"
        
        # Prepare the request payload according to API spec
        payload = {
            "text": prompt,  # Required field
            "type": "architecture",  # Specify diagram type
            "options": {
                "theme": "light",
                "format": "png",
                "layout": "vertical",
                "width": 1600,
                "height": 1200,
                "padding": 20,
                "scale": 1.5,
                "spacing": {
                    "horizontal": 80,
                    "vertical": 80
                }
            }
        }
        
        try:
            response = requests.post(
                endpoint,
                headers=self.headers,
                json=payload,
                timeout=180  # Increased timeout for diagram generation
            )

            logger.debug(f"Eraser API request sent to {endpoint}. Status Code: {response.status_code}") # Use logger

            # Add retries for timeouts
            retries = 3
            while retries > 0 and response.status_code >= 500:
                logger.warning(f"Eraser API returned {response.status_code}. Retrying request... {retries} attempts left") # Use logger
                response = requests.post(
                    endpoint,
                    headers=self.headers,
                    json=payload,
                    timeout=180
                )
                retries -= 1
            
            # Handle specific error cases after retries
            if response.status_code == 400:
                error_msg = response.text
                logger.error(f"Eraser API Bad Request (400): {error_msg}")
                raise ValueError(f"Invalid request: {error_msg}")
            elif response.status_code == 401:
                logger.error("Eraser API Unauthorized (401): Invalid API token.")
                raise ValueError("Invalid API token. Please check your token.")
            elif response.status_code == 422:
                logger.error(f"Eraser API Unprocessable Entity (422): Invalid prompt or parameters. Response: {response.text}")
                raise ValueError("Invalid prompt or parameters. Please check your input.")

            # Raise HTTPError for other bad responses (4xx or 5xx) after retries
            response.raise_for_status()

            # Try to parse JSON response
            try:
                json_response = response.json()
                # Extract image URL if available
                if 'imageUrl' in json_response:
                    logger.info(f"Successfully generated diagram. Image URL: {json_response['imageUrl']}")
                    return {'url': json_response['imageUrl']}  # Convert to expected format
                else:
                    logger.error(f"Eraser API response missing 'imageUrl'. Response: {json_response}")
                    raise ValueError("No image URL in response")
            except ValueError as json_error: # Catch JSON decoding errors specifically
                logger.error(f"Failed to parse JSON response from Eraser API. Status: {response.status_code}, Response: {response.text}", exc_info=True)
                raise ValueError(f"Invalid JSON response: {response.text}") from json_error

        except requests.exceptions.Timeout as timeout_error:
            logger.error(f"Timeout calling Eraser API at {endpoint}", exc_info=True)
            raise ValueError(f"Timeout calling Eraser.io API: {str(timeout_error)}") from timeout_error
        except requests.exceptions.RequestException as req_error:
            logger.error(f"Error calling Eraser API at {endpoint}", exc_info=True)
            raise ValueError(f"Error calling Eraser.io API: {str(req_error)}") from req_error
        except Exception as e: # Catch any other unexpected errors
            logger.error(f"Unexpected error in EraserAPI.generate_diagram_from_prompt", exc_info=True)
            raise # Re-raise the original exception
