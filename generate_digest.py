import os
import sys
import openai
from datetime import datetime

# Configure the Openrouter client using the API key from environment variables
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    print("Error: OPENROUTER_API_KEY environment variable not set.", file=sys.stderr)
    sys.exit(1)

client = openai.OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# Use a model that supports the 'online' web search capability
MODEL = "mistralai/mixtral-8x7b-instruct-v0.1"
SEARCH_MODEL = f"{MODEL}:online"

def generate_tech_news_digest():
    """
    Intelligently searches the web for the latest tech news and generates a TL;DR summary.
    """
    try:
        print("Starting intelligent web search for latest tech news...")
        
        # Initial prompt to the LLM to perform a web search
        response = client.chat.completions.create(
            model=SEARCH_MODEL,
            messages=[
                {"role": "system", "content": "You are a professional tech journalist. Your task is to find the most recent and significant news from top tech sources like CNET, The Verge, and TechCrunch. Summarize the key developments in a concise, plain text TL;DR format."},
                {"role": "user", "content": "Find the latest tech news from the past 24 hours. Focus on major announcements, product releases, or industry shifts. Provide a summary with key headlines in a plain text, easy-to-read format."}
            ],
            stream=False
        )

        # The model should respond with a direct summary after performing the web search
        summary = response.choices[0].message.content.strip()

        if not summary:
            print("Warning: The LLM returned an empty summary.", file=sys.stderr)
            return "No significant tech news found in the latest search."

        return summary

    except openai.APIConnectionError as e:
        print(f"Failed to connect to Openrouter API: {e}", file=sys.stderr)
        return "An error occurred while connecting to the API."
    except openai.APIError as e:
        # Catches other API errors like authentication, rate limits, etc.
        print(f"Openrouter API returned an error: {e}", file=sys.stderr)
        return "An API-related error occurred while fetching news."
    except Exception as e:
        # Catches any other unexpected errors
        print(f"An unexpected error occurred during news generation: {e}", file=sys.stderr)
        return "An unexpected error occurred."


if __name__ == "__main__":
    digest = generate_tech_news_digest()

    # Get the current date and time for the file and log output
    current_time = datetime.now()
    log_timestamp = current_time.strftime("%Y-%m-%d %I:%M %p")
    file_timestamp = current_time.strftime("%Y-%m-%d_%H-%M")
    
    # Create the output directory if it doesn't exist
    output_directory = "news_digests"
    try:
        os.makedirs(output_directory, exist_ok=True)
    except IOError as e:
        print(f"Error creating output directory: {e}", file=sys.stderr)
        sys.exit(1)
    
    output_content = f"Tech News Digest - {log_timestamp}\n\n{digest}\n"

    # Print to workflow logs
    print("\n--- Generating Tech News Digest ---")
    print(output_content)
    print("-----------------------------------")

    # Write to a plain text file in the repository with a timestamped filename
    output_filename = os.path.join(output_directory, f"digest_{file_timestamp}.txt")
    try:
        with open(output_filename, "w", encoding="utf-8") as file:
            file.write(output_content)
        print(f"\nSuccessfully wrote the digest to {output_filename}")
    except IOError as e:
        print(f"Error writing to file: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Check if a digest was generated before a successful exit
    if "error occurred" in digest:
        sys.exit(1)
