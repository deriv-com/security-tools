import io
import pytesseract
from PIL import Image
import requests
import os
from google import genai
from dotenv import load_dotenv
import sys
from logger import logger # Import the centralized logger

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

class ImageAnalyzer:
    @staticmethod
    def extract_text_from_image(image_data: bytes) -> str:
        """
        Extract text from image using OCR
        
        Args:
            image_data (bytes): Raw image data
            
        Returns:
            str: Extracted text from the image
        """
        try:
            logger.info("Starting OCR text extraction")
            
            # Convert bytes to PIL Image
            image = Image.open(io.BytesIO(image_data))
            
            # Extract text using pytesseract
            text = pytesseract.image_to_string(image)
            
            logger.info(f"Successfully extracted {len(text)} characters from image")
            
            # Clean up the text
            cleaned_text = text.strip()
            
            # Add some context about the text being from an architecture diagram
            formatted_text = f"""Architecture Diagram Analysis:

Components and Connections Identified:
{cleaned_text}

Note: This text was extracted from an architecture diagram using OCR. The structure and layout of components may provide additional context beyond the extracted text."""
            
            return formatted_text
            
        except Exception as e:
            logger.error(f"Error extracting text from image: {str(e)}")
            raise ValueError(f"Failed to extract text from image: {str(e)}")
        
    @staticmethod
    def extract_text_from_image_gemini(image_data: bytes) -> str:
        """
        Analyze image content using the Gemini API.

        Args:
            image_data (bytes): Raw image data

        Returns:
            str: Gemini's analysis of the image.
        """
        try:
            logger.info("Starting Gemini image analysis")

            # Detect image format using PIL
            try:
                image = Image.open(io.BytesIO(image_data))
                # mime_type = Image.MIME[image.format] # Unused variable removed
            except Exception as e:  # Handle invalid image data
                logger.error(f"Invalid image data: {e}")
                raise ValueError("Could not determine image format. Please provide a valid image.")


            client = genai.Client(api_key=GEMINI_API_KEY) # replace w/ your API key
            response = client.models.generate_content(
                model="gemini-2.0-flash",  # Or -exp if necessary
                contents=[
                    '''
                        "Act as a Security Analyst specializing in Zero Trust Architecture. Your first task is to meticulously analyze the provided architecture diagram. Provide an **extremely detailed description and inventory** of all components, connections, and zones. As you describe each element, **immediately identify and note any aspects that appear potentially problematic or misaligned with core Zero Trust principles** ('never trust, always verify', least privilege, assume breach, micro-segmentation, explicit verification).

                        **Do not provide comprehensive solutions or recommendations yet.** Focus on description combined with flagging initial Zero Trust concerns based *only* on the visual evidence. Structure your analysis like this:

                        1.  **Overall System Context:** Briefly describe the likely purpose/type of system shown.
                        2.  **Component Inventory & Initial ZT Notes:** List *every* identifiable component (servers, databases, firewalls, load balancers, user endpoints, cloud services, APIs, etc.). For each:
                            * Identify its type and likely function.
                            * Describe its *implied security role or context*.
                            * **Initial ZT Observation:** Note if its placement, connections, or nature raises potential Zero Trust concerns (e.g., 'Database: Located in a broad 'internal' zone, potentially accessible by multiple services without apparent granular controls, raising concerns about least privilege.', 'Web Server: Public-facing, standard component. Note if connections bypass expected security controls like a WAF if one isn't shown.').
                        3.  **Connections, Flows, & Initial ZT Notes:** Describe all visible connections and data flow paths (mention direction if possible).
                            * **Initial ZT Observation:** Note if flows imply excessive trust, lack obvious verification points, or cross boundaries without clear mediation (e.g., 'Flow - App Server to Database: Direct connection within the same zone shown. This might represent implicit trust; verification mechanism unclear from diagram.', 'Flow - User to Web Server: Appears to go through perimeter firewall only. Need to later verify if additional layers like WAF, authentication exist.').
                        4.  **Boundaries, Zones, & Initial ZT Notes:** Identify visual or implied zones (DMZ, Internal, Trusted, Untrusted, VPCs, Subnets). Describe their apparent purpose.
                            * **Initial ZT Observation:** Note if zones seem overly large ('flat network'), suggesting significant implicit trust and potential for lateral movement, contrary to micro-segmentation goals. Note lack of internal segmentation if apparent (e.g., 'Internal Zone: Appears monolithic, containing diverse services. Lack of internal segmentation could be a key Zero Trust gap.').
                        5.  **Summary of Potential ZT Gaps:** Briefly list the 2-4 most prominent potential Zero Trust issues flagged during the description (e.g., 'Apparent large implicit trust zones', 'Lack of visible internal segmentation', 'Unclear verification points for internal service communication')."
                    ''',  # Your prompt
                    image
                ])

            gemini_analysis = response.text

            # Optional: Add context or reformatting if desired.  Example:
            formatted_text = f"""Architecture Diagram Analysis (Gemini):

    {gemini_analysis}
    Note: This text was extracted from an architecture diagram using OCR. The structure and layout of components may provide additional context beyond the extracted text.
    """

            logger.info(f"Gemini analysis complete, formatted text {formatted_text}")
            return formatted_text


        except Exception as e:
            logger.error(f"Error analyzing image with Gemini: {str(e)}")
            raise ValueError(f"Failed to analyze image: {str(e)}")

    @staticmethod
    def download_image(url: str, headers: dict = None) -> bytes:
        """
        Download image from URL
        
        Args:
            url (str): Image URL
            headers (dict): Optional headers for the request
            
        Returns:
            bytes: Raw image data
        """
        try:
            logger.info(f"Downloading image from URL: {url}")
            
            response = requests.get(url, headers=headers)
            response.raise_for_status()
            
            logger.info(f"Successfully downloaded {len(response.content)} bytes")
            return response.content
            
        except Exception as e:
            logger.error(f"Error downloading image: {str(e)}")
            raise ValueError(f"Failed to download image: {str(e)}")
