import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Retrieve variables
API_KEY = os.getenv("OPENAI_API_KEY")
KB_VECTOR_STORE_ID = os.getenv("VECTOR_STORE_ID")

# Validate variable configurations
if not API_KEY:
    raise ValueError("OPENAI_API_KEY is missing from the .env file.")
if not KB_VECTOR_STORE_ID:
    raise ValueError("VECTOR_STORE_ID is missing from the .env file.")

# Model Configuration
PRIMARY_AGENT_MODEL = "gpt-5-mini"