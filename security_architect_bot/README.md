# SecArchBot

A Zero Trust Security Architecture Analysis Bot for Slack that leverages multiple AI models to analyze system designs and architectures. The bot identifies security vulnerabilities through a zero trust lens, provides multiple solution approaches with detailed rationale, and generates secure architecture diagrams. It can process both text descriptions and visual architecture diagrams to deliver comprehensive security recommendations.

## Author

Created by Deriv Security Team

## Features

- Automated zero trust security architecture analysis
- Support for both text descriptions and architecture diagrams:
  - Text analysis using OpenAI GPT-4
  - Image analysis using Google Gemini
- Detailed security assessment reports including:
  - Multiple security solution approaches
  - Technical components for each solution
  - Implementation complexity assessment
  - Security posture scoring
  - Detailed security rationale
- Generation of secure architecture diagrams using Eraser.io
- Real-time Slack interaction with thread support

## Demo

![SecArchBot Demo](SecArchBot3.1.gif)

## Architecture

![SecArchBot Architecture](secarchbot_arch.png)

SecArchBot is built with a modular architecture that integrates multiple AI services:

### Core Components

1. **Slack Integration Layer** (`slack_analyzer.py`)
   - Handles Slack events and message processing
   - Manages Socket Mode connection
   - Formats and sends responses back to Slack

2. **Image Analysis Engine** (`image_analyzer.py`)
   - Processes uploaded architecture diagrams
   - Uses Google Gemini for image understanding
   - Extracts text and architectural elements from diagrams

3. **Security Analysis Engine** (`threat_analyzer.py`)
   - Creates specialized prompts for security analysis
   - Structures the security assessment format
   - Processes and formats analysis results

4. **AI Integration Services**
   - OpenAI API (`openai_api.py`): Handles text analysis and security recommendations
   - Eraser API (`eraser_api.py`): Generates secure architecture diagrams

### Data Flow

1. User sends a message or uploads an image to Slack
2. Slack events are captured by the bot
3. Text and/or images are processed by respective analysis engines
4. Security analysis is performed using OpenAI GPT-4
5. Results are formatted and returned to the user
6. A secure architecture diagram is generated using Eraser.io

## Prerequisites

- Python 3.8+ (for local installation)
- A Slack workspace with admin privileges
- OpenAI API key (for text analysis)
- Eraser.io API token (for diagram generation)
- Gemini API key (for image analysis)
- Docker and Docker Compose (optional, for containerized deployment)

## System Requirements

### For Local Installation
- Operating System: Windows 10/11, macOS, or Linux
- RAM: 4GB minimum (8GB recommended)
- Disk Space: 500MB for the application and dependencies
- Internet connection for API access

### For Docker Installation
- Docker Engine 19.03.0+
- Docker Compose 1.27.0+
- 2GB of available RAM for the container
- Internet connection for API access

## Installation

1. Clone the repository:
```bash
git clone https://github.com/deriv-com/security-tools.git
cd security_architect_bot
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Copy the environment template and fill in your credentials:
```bash
cp .env.template .env
```

## Configuration

Edit the `.env` file with your credentials:

```env
SLACK_BOT_TOKEN=your-slack-bot-token
SLACK_APP_TOKEN=your-slack-app-token
SLACK_SIGNING_SECRET=your-slack-signing-secret
OPENAI_API_KEY=your-openai-api-key
ERASER_API_TOKEN=your-eraser-api-token
GEMINI_API_KEY=your-gemini-api-key
```

### Obtaining API Keys

#### OpenAI API Key
1. Visit [OpenAI's platform](https://platform.openai.com/signup)
2. Create an account or sign in
3. Navigate to the API section
4. Create a new API key and copy it to your `.env` file

#### Eraser.io API Token
1. Sign up for an account at [Eraser.io](https://eraser.io)
2. Navigate to your account settings
3. Find the API section and generate a new token
4. Copy the token to your `.env` file

#### Gemini API Key
1. Visit [Google AI Studio](https://makersuite.google.com/app/apikey)
2. Sign in with your Google account
3. Create a new API key
4. Copy the key to your `.env` file

### Setting up Slack

1. Create a new Slack App:
   - Go to https://api.slack.com/apps
   - Click "Create New App"
   - Choose "From scratch"
   - Enter "SecArchBot" as the app name
   - Select your workspace and click "Create App"

2. Set up Bot Token Scopes:
   - In the left sidebar, click on "OAuth & Permissions"
   - Scroll down to "Scopes" > "Bot Token Scopes"
   - Add the following scopes:
     - app_mentions:read
     - channels:history
     - channels:read
     - chat:write
     - files:read
     - files:write
     - users:read

3. Enable Socket Mode:
   - In the left sidebar, click on "Socket Mode"
   - Toggle "Enable Socket Mode" to On
   - Create an app-level token with the `connections:write` scope
   - Copy the generated token (starts with `xapp-`) - this is your `SLACK_APP_TOKEN`

4. Install the app to your workspace:
   - In the left sidebar, click on "Install App"
   - Click "Install to Workspace"
   - Review the permissions and click "Allow"

5. Get your tokens:
   - Bot Token: Go to "OAuth & Permissions" and copy the "Bot User OAuth Token" (starts with `xoxb-`) - this is your `SLACK_BOT_TOKEN`
   - Signing Secret: Go to "Basic Information" > "App Credentials" and copy the "Signing Secret" - this is your `SLACK_SIGNING_SECRET`

6. Enable Event Subscriptions:
   - In the left sidebar, click on "Event Subscriptions"
   - Toggle "Enable Events" to On
   - Under "Subscribe to bot events", add:
     - app_mention
     - message.im

7. Copy all three tokens to your `.env` file:
   ```
   SLACK_BOT_TOKEN=xoxb-your-bot-token
   SLACK_APP_TOKEN=xapp-your-app-token
   SLACK_SIGNING_SECRET=your-signing-secret
   ```

## Usage

### Running Locally

1. Start the bot:
```bash
python slack_analyzer.py
```

### Running with Docker Compose

1. Start the bot:
```bash
docker-compose up -d
```

2. Check logs if needed:
```bash
docker-compose logs -f
```

### Interacting with the Bot

1. In Slack, you can:
   - Send a direct message to the bot
   - Mention @SecArchBot in a channel

2. Provide your system architecture details through:
   - Text description
   - Architecture diagram (upload an image)
   - Or both

3. The bot will analyze the architecture and provide:
   - Detailed security analysis with multiple solution approaches
   - Implementation complexity and security posture scores
   - Recommended security approach with technical rationale
   - A proposed secure architecture diagram generated by Eraser.io

Example:
```
@SecArchBot A team requires a secure method to exchange sensitive files with an external partner. They are considering setting up an SFTP server, utilizing AWS and a tunnel.
```


## Troubleshooting

### Common Issues

1. **Bot not responding in Slack**
   - Verify your Slack tokens are correct in the `.env` file
   - Ensure the bot is running (check logs)
   - Confirm the bot has been invited to the channel you're messaging in

2. **API Connection Issues**
   - Check that all API keys in your `.env` file are valid
   - Ensure your internet connection is working
   - Verify you haven't exceeded API rate limits

3. **Docker Issues**
   - Run `docker-compose ps` to check if the container is running
   - Check logs with `docker-compose logs -f`
   - Ensure Docker has enough resources allocated

4. **Image Analysis Not Working**
   - Verify Gemini API key is correct
   - Ensure the image is in a supported format (PNG, JPG)
   - Check that the image is clear and readable

### Logs

Logs are stored in the `logs/secarchbot.log` file. When running with Docker, logs are persisted in the mounted volume.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
