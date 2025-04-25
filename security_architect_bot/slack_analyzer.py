import os
import sys
import re
import signal
import atexit
import traceback
import requests
import json
from datetime import datetime, timezone
from PIL import Image
from eraser_api import EraserAPI
from openai_api import OpenAIAPI
from image_analyzer import ImageAnalyzer
from logger import logger

def test_slack_connection(token):
    """Test connection to Slack API"""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    try:
        response = requests.post(
            "https://slack.com/api/auth.test",
            headers=headers,
            verify=True
        )
        if response.status_code != 200:
            raise Exception(f"API test failed with status {response.status_code}: {response.text}")
        return True
    except Exception as e:
        raise Exception(f"Failed to connect to Slack API: {str(e)}")

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler
from dotenv import load_dotenv
from threat_analyzer import create_analysis_prompt

# Global variables for connection management
active_handler = None
should_exit = False

def cleanup():
    """Cleanup function to be called on exit"""
    global active_handler
    if active_handler:
        try:
            active_handler.close()
            # Remove PID file
            if os.path.exists("/tmp/slack_analyzer.pid"):
                os.remove("/tmp/slack_analyzer.pid")
        except:
            pass

def signal_handler(_signum, _frame):
    """Handle shutdown signals"""
    global should_exit
    should_exit = True
    cleanup()
    sys.exit(0)

# Register cleanup functions
atexit.register(cleanup)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

# Load environment variables
load_dotenv()

# Verify environment variables
required_vars = ["SLACK_BOT_TOKEN", "SLACK_APP_TOKEN", "SLACK_SIGNING_SECRET", "OPENAI_API_KEY", "ERASER_API_TOKEN"]
missing_vars = [var for var in required_vars if not os.environ.get(var)]
if missing_vars:
    logger.error(f"Missing required environment variables: {', '.join(missing_vars)}")
    sys.exit(1)

sys.stdout.write("\n=== Starting SecArchBot ===\n")
sys.stdout.write("Initializing Slack app...\n")
sys.stdout.flush()
try:
    # Initialize the Slack app
    app = App(
        token=os.environ.get("SLACK_BOT_TOKEN"),
        signing_secret=os.environ.get("SLACK_SIGNING_SECRET")
    )
    sys.stdout.write("✓ Slack app initialized successfully\n")
    sys.stdout.flush()
    logger.info("Slack app initialized successfully")
except Exception as e:
    error_msg = f"Failed to initialize Slack app: {str(e)}"
    print(f"✗ {error_msg}")
    logger.error(error_msg)
    raise

def extract_image_text(image_url):
    """Extract text from image using OCR"""
    try:
        logger.info(f"Starting image analysis for URL: {image_url}")
        
        # Get headers for Slack API request
        headers = {
            "Authorization": f"Bearer {os.environ.get('SLACK_BOT_TOKEN')}",
        }
        
        # Download image from Slack
        logger.info("Downloading image from Slack...")
        image_data = ImageAnalyzer.download_image(image_url, headers=headers)
        logger.info(f"Successfully downloaded image ({len(image_data)} bytes)")
        
        # Attempt text extraction using Gemini first
        extracted_text = ""
        try:
            logger.info("Attempting text extraction using Gemini...")
            extracted_text = ImageAnalyzer.extract_text_from_image_gemini(image_data)
            logger.info(f"Successfully extracted text using Gemini ({len(extracted_text)} chars)")
        except Exception as gemini_error:
            logger.warning(f"Gemini OCR failed: {gemini_error}. Attempting fallback with Tesseract...")
            # Fallback to Tesseract OCR
            try:
                extracted_text = ImageAnalyzer.extract_text_from_image(image_data)
                logger.info(f"Successfully extracted text using Tesseract fallback ({len(extracted_text)} chars)")
            except Exception as tesseract_error:
                logger.error(f"Tesseract OCR fallback also failed: {tesseract_error}")
                # Re-raise the original Gemini error or a combined error if preferred
                raise ValueError(f"Image analysis failed with both Gemini and Tesseract. Gemini error: {gemini_error}, Tesseract error: {tesseract_error}") from tesseract_error

        return extracted_text
                
    except Exception as e:
        logger.error(f"Error in image analysis: {str(e)}")
        logger.error(traceback.format_exc())
        raise ValueError(f"Image analysis failed: {str(e)}")

def analyze_architecture(text, image_text=""):
    """Process the text and generate zero trust security analysis"""
    try:
        logger.info("Starting architecture analysis")
        # Extract system name (use first line or default)
        system_name = text.split('\n')[0] if text else "Unnamed System"
        
        # Combine text and image analysis if available
        combined_input = f"{text}\n\nArchitecture Diagram Analysis:\n{image_text}" if image_text else text
        
        # Create the analysis prompt
        logger.info("Creating analysis prompt")
        prompt = create_analysis_prompt(
            system_name=system_name,
            app_input=combined_input
        )

        # Get the analysis using OpenAI
        logger.info("Getting analysis from OpenAI")
        client = OpenAIAPI(api_key=os.environ.get("OPENAI_API_KEY"))
        response = client.chat_completion(
            prompt=prompt,
            prompt_sys="You are a zero trust security architect. Always respond with syntactically valid JSON, including all necessary commas between properties and array items."
        )
        
        # Clean up response and parse JSON
        if "```json" in response:
            content = response.split("```json")[1].split("```")[0]
        elif "```" in response:
            content = response.split("```")[1].split("```")[0]
        else:
            content = response
            
        content = content.replace('\n', '').replace('  ', ' ').strip()
        # Return both the parsed JSON content and the prompt used
        return json.loads(content), prompt
        
    except Exception as e:
        logger.error(f"Error analyzing architecture: {str(e)}")
        logger.error(traceback.format_exc())
        return None

def process_message(event, say, client, thread_ts=None):
    """Common message processing logic"""
    request_time = datetime.now(timezone.utc) # Capture request time
    user_id = None
    channel_id = None
    
    try:
        # --- Extract Event Details ---
        # Handle different event structures (direct message vs mention vs payload)
        if isinstance(event, dict) and 'payload' in event and 'event' in event['payload']:
            event_data = event['payload']['event']
        elif isinstance(event, dict) and 'type' in event: # Standard event structure
             event_data = event
        else:
             logger.warning(f"Unexpected event structure: {event}")
             event_data = {} # Fallback to empty dict

        user_id = event_data.get('user')
        channel_id = event_data.get('channel')
        thread_ts = event_data.get('thread_ts', thread_ts or event_data.get('ts')) # Ensure thread_ts is captured

        logger.info(f"Processing message event for user {user_id} in channel {channel_id}, thread {thread_ts}")
        logger.debug(f"Full event data: {event_data}")

        # Extract text from the message
        text = ''
        if event.get('text'):
            # Remove bot mention if present
            text = re.sub(r'<@[A-Z0-9]+>', '', event['text']).strip()
            logger.info(f"Extracted text: {text}")
        
        # Check for files (images)
        files = event.get('files', [])
        if isinstance(event, dict) and 'payload' in event:
            event_data = event['payload'].get('event', {})
            files = event_data.get('files', []) # Use extracted event_data
            logger.debug(f"Files found in event: {files}")
        image_files = [f for f in files if f and f.get('mimetype', '').startswith('image/')] # Added check for f existence
        logger.info(f"Found {len(image_files)} image files")

        # input_attachments_log = [...] # Removed unused variable assignment

        # If no text and no images, ask for input
        if not text and not image_files:
            say("Please provide a description of the system architecture to analyze (text, image, or both).", thread_ts=thread_ts)
            return
        
        # Extract text from image if available
        image_text = ""
        if image_files:
            # Extract text from each image file
            image_texts = []
            for image_file in image_files:
                image_url = image_file.get('url_private')
                if image_url:
                    # Get image text using OCR
                    extracted_text = extract_image_text(image_url)
                    if extracted_text:
                        image_texts.append(extracted_text)
            
            image_text = "\n".join(image_texts)
            logger.info(f"Image detected: Architecture diagram analyzed")
        
        # Combine text from message and image
        combined_text = f"{text}\n{image_text}".strip()
        if not combined_text:
            combined_text = "Unnamed System"
            
        # Send initial response
        say("Analyzing your architecture... This may take a minute.", thread_ts=thread_ts)
        
        # Generate the analysis
        logger.info("Starting analysis")
        # Unpack result and prompt
        analysis_data = analyze_architecture(text, image_text) 
        
        if not analysis_data:
            logger.error("Analysis function returned None")
            say("Failed to analyze architecture. Please try again.", thread_ts=thread_ts)
            return

        # Unpack the results
        analysis_result, system_prompt = analysis_data

        if not analysis_result:
            logger.error("Analysis failed to produce results (analysis_result is None/empty)")
            say("Failed to analyze architecture. Please try again.", thread_ts=thread_ts)
            return
            
        try:
            logger.info("Processing analysis results")
            # Create blocks for better Slack formatting
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "🔒 Security Architecture Analysis",
                        "emoji": True
                    }
                },
                {"type": "divider"}
            ]

            # Add solutions
            for idx, solution in enumerate(analysis_result["solutions"], 1):
                blocks.extend([
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*Solution {idx}: {solution['name']}*\n_{solution['approach']}_"
                        }
                    },
                    {
                        "type": "section",
                        "fields": [
                            {
                                "type": "mrkdwn",
                                "text": "*Key Components*\n• Identity: " + ", ".join(solution['technical_components']['identity_provider'][:2]) + "\n• Network: " + ", ".join(solution['technical_components']['network_architecture'][:2])
                            },
                            {
                                "type": "mrkdwn",
                                "text": "*Security Rationale*\n" + solution['technical_components']['security_rationale']
                            }
                        ]
                    },
                    {
                        "type": "context",
                        "elements": [
                            {
                                "type": "mrkdwn",
                                "text": f"*Complexity:* {solution['implementation_complexity']} | *Security Score:* {solution['security_posture_score']}"
                            }
                        ]
                    },
                    {"type": "divider"}
                ])

            # Add recommendation if available
            if "recommendation" in analysis_result:
                blocks.extend([
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "🎯 Recommended Approach",
                            "emoji": True
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"*{analysis_result['recommendation']['selected_solution']}*"
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*Technical Rationale*\n" + "\n".join(f"• {reason}" for reason in analysis_result["recommendation"]["technical_reasons"][:3])
                        }
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*Implementation Steps*\n" + "\n".join(f"• {step}" for step in analysis_result["recommendation"]["implementation_steps"][:3])
                        }
                    }
                ])

            # Send the formatted message using blocks
            say(blocks=blocks, thread_ts=thread_ts)

            # --- Generate and send diagram ---
            # output_attachments_log = None # Removed unused variable initialization
            diagram_upload_response = None # Initialize response variable
            try:
                logger.info("Generating architecture diagram using Eraser.io")

                # Initialize Eraser API client
                eraser = EraserAPI(os.environ.get("ERASER_API_TOKEN"))
                
                # Create the diagram prompt based on selected solution
                selected_solution = analysis_result["recommendation"]["selected_solution"]
                solution_details = next(
                    (s for s in analysis_result["solutions"] if s["name"] == selected_solution),
                    None
                )
                
                if not solution_details:
                    raise Exception("Selected solution details not found")
                
                # Create a focused diagram prompt for the selected solution
                diagram_prompt = f"""
Generate a detailed zero trust architecture diagram for the recommended solution:

System: {combined_text}

Approach: {solution_details['approach']}

Key Components to Visualize:

1. Identity & Authentication:
{chr(10).join(f'- {item}' for item in solution_details['technical_components']['identity_provider'])}

2. Network Security:
{chr(10).join(f'- {item}' for item in solution_details['technical_components']['network_architecture'])}

3. Security Rationale:
{solution_details['technical_components']['security_rationale']}

Required Elements:
1. Authentication & Authorization Flow
2. Network Segmentation Boundaries
3. Data Encryption Points
4. Security Control Checkpoints
5. Trust Boundaries

Style Guidelines:
- Use clear visual separation between security zones
- Highlight authentication/authorization checkpoints
- Show data flow with encryption indicators
- Include security control labels
- Use a color scheme that emphasizes security boundaries
"""
                
                # Generate the diagram
                diagram_response = eraser.generate_diagram_from_prompt(diagram_prompt)
                
                if 'url' in diagram_response:
                    # Download the image from URL
                    logger.debug("Downloading diagram from URL...")
                    image_url = diagram_response['url']
                    image_response = requests.get(image_url)
                    image_response.raise_for_status()
                    
                    # Save image temporarily
                    temp_image_path = "/tmp/architecture_diagram.png"
                    with open(temp_image_path, "wb") as f:
                        f.write(image_response.content)
                    
                    # Remove transparency
                    img = Image.open(temp_image_path)
                    if img.mode in ('RGBA', 'LA') or (img.mode == 'P' and 'transparency' in img.info):
                        # Create new image with white background
                        background = Image.new('RGBA', img.size, (255, 255, 255, 255))
                        if img.mode == 'P':
                            img = img.convert('RGBA')
                        # Composite the image onto the background
                        img = Image.alpha_composite(background, img)
                        # Convert back to RGB (no alpha)
                        img = img.convert('RGB')
                        # Save the modified image
                        img.save(temp_image_path, 'PNG')
                    
                    try:
                        # Upload the local image file to Slack
                        # Use channel_id extracted earlier
                        diagram_upload_response = client.files_upload_v2(
                            channel=channel_id,
                            title="secure_architecture_diagram",
                            file=temp_image_path,
                            initial_comment="Proposed Secure Architecture Diagram",
                            thread_ts=thread_ts
                        )
                        logger.info("Architecture diagram upload successful")
                        # Removed block for formatting unused output_attachments_log

                    finally:
                        # Clean up temp file
                        if os.path.exists(temp_image_path):
                            os.remove(temp_image_path)
                else:
                    raise Exception("No diagram URL in Eraser.io response")
                    
            except Exception as diagram_error:
                logger.error(f"Error generating diagram with Eraser.io: {str(diagram_error)}")
                say(f"Failed to generate architecture diagram: {str(diagram_error)}", thread_ts=thread_ts)

        except Exception as e:
            logger.error(f"Error processing analysis results or logging: {str(e)}")
            logger.error(traceback.format_exc())
            # Send error message with key details
            say("Failed to process security analysis. Please check the logs for details.", thread_ts=thread_ts)
        
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        logger.error(traceback.format_exc())
        say(f"Sorry, I encountered an error: {str(e)}", thread_ts=thread_ts)

@app.event("app_mention")
def handle_mention(event, say, client):
    """Handle when the bot is mentioned"""
    try:
        logger.info(f"Received mention event: {event}")
        # Get thread_ts from the event, fallback to event ts if not in a thread
        thread_ts = event.get('thread_ts', event.get('ts'))
        process_message(event, say, client, thread_ts=thread_ts)
    except Exception as e:
        logger.error(f"Error handling mention: {str(e)}")
        logger.error(traceback.format_exc())
        thread_ts = event.get('thread_ts', event.get('ts'))
        say(f"Sorry, I encountered an error: {str(e)}", thread_ts=thread_ts)

@app.message()
def handle_message(message, say, client):
    """Handle direct messages to the bot"""
    try:
        logger.info(f"Received message event: {message}")
        
        # Skip messages from the bot itself
        if message.get('bot_id'):
            logger.info("Skipping bot message")
            return
            
        # Extract the actual message from payload if needed
        if isinstance(message, dict) and 'payload' in message:
            message = message['payload'].get('event', message)
            
        # Only process direct messages
        is_dm = message.get('channel_type') == 'im'
        
        logger.info(f"Message type - DM: {is_dm}")
        
        # Process only direct messages
        if is_dm:
            logger.info("Processing direct message")
            # Get thread_ts from the message, fallback to message ts if not in a thread
            thread_ts = message.get('thread_ts', message.get('ts'))
            process_message(message, say, client, thread_ts=thread_ts)
        else:
            logger.info(f"Skipping message - not a DM. Channel type: {message.get('channel_type')}")
        
    except Exception as e:
        logger.error(f"Error handling message: {str(e)}")
        logger.error(traceback.format_exc())
        thread_ts = message.get('thread_ts', message.get('ts'))
        say(f"Sorry, I encountered an error: {str(e)}", thread_ts=thread_ts)

def main():
    """Main entry point"""
    global active_handler
    
    try:
        # Test Slack connection first
        sys.stdout.write("\nTesting Slack connection...\n")
        sys.stdout.flush()
        if test_slack_connection(os.environ.get("SLACK_BOT_TOKEN")):
            sys.stdout.write("✓ Slack connection test successful\n")
            sys.stdout.flush()
        
        # Check for existing lock file
        pid_file = "/tmp/slack_analyzer.pid"
        if os.path.exists(pid_file):
            with open(pid_file, 'r') as f:
                old_pid = int(f.read().strip())
                try:
                    # Check if process is still running
                    os.kill(old_pid, 0)
                    logger.error(f"Another instance is already running with PID {old_pid}")
                    sys.exit(1)
                except OSError:
                    # Process not running, we can proceed
                    pass
        
        # Write our PID
        with open(pid_file, 'w') as f:
            f.write(str(os.getpid()))

        # Initialize the handler with custom session
        active_handler = SocketModeHandler(
            app=app,
            app_token=os.environ.get("SLACK_APP_TOKEN")
        )
        
        sys.stdout.write("\nStarting Slack bot...\n")
        sys.stdout.write("Connecting to Slack (this may take a few seconds)...\n")
        sys.stdout.flush()
        try:
            active_handler.start()  # Start the Socket Mode handler
        except KeyboardInterrupt:
            logger.info("Exiting gracefully due to keyboard interrupt.")
        except Exception as e:
            logger.error(f"Error during bot execution: {e}")

        # Check should_exit flag after handler completion
        if should_exit:
            logger.info("Exiting due to signal handler.")
            sys.exit(0)

        sys.stdout.write("\n✓ Bot is running! Ready to analyze architecture diagrams.\n")
        sys.stdout.write("You can now mention @SecArchBot in your Slack channels.\n")
        sys.stdout.flush()

    except Exception as e:
        logger.error(f"Error starting bot: {str(e)}")
        logger.error(traceback.format_exc())
        cleanup()
        raise

if __name__ == "__main__":
    main()
