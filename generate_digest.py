import os
import sys
import openai
from datetime import datetime
import json

# Configure the Openrouter client using the API key from environment variables
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    print("Error: OPENROUTER_API_KEY environment variable not set.", file=sys.stderr)
    sys.exit(1)

client = openai.OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# Use Gemini 2.5 Flash for a balance of performance and cost.
MODEL = "google/gemini-2.5-flash"

def generate_tech_news_digest():
    """
    Intelligently searches the web for the latest tech news and generates a TL;DR summary.
    """
    messages = [
        {"role": "system", "content": "You are an automated agent for a GitHub Actions workflow. Your ONLY task is to search the web for the latest tech news and provide a concise summary. You MUST execute this task without any user interaction or follow-up questions. NEVER ask for clarifying information. Based on your best-effort search, you will produce a summary."},
        {"role": "user", "content": "Perform a web search for the most recent and significant tech news from the past 24 hours. Focus on major announcements, product releases, or industry shifts from top sources like CNET, The Verge, and TechCrunch. Provide a summary with key headlines in a plain text, easy-to-read, TL;DR format."}
    ]
    
    # Define the web search tool for the model to use
    tools = [
        {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Searches the web for information."
            }
        }
    ]
    
    print("Starting intelligent web search for latest tech news...")
    
    try:
        # Loop to handle tool calls until a final response is received
        while True:
            response = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=tools,
                tool_choice="auto",
                max_tokens=1024,
                stream=False
            )
            
            response_message = response.choices[0].message
            
            # Check for tool calls
            if response_message.tool_calls:
                for tool_call in response_message.tool_calls:
                    if tool_call.function.name == "web_search":
                        print("LLM requested a web search. Executing tool call...")
                        
                        messages.append(response_message)
                        messages.append(
                            {
                                "tool_call_id": tool_call.id,
                                "role": "tool",
                                "name": "web_search",
                                "content": json.dumps({"search_query": response_message.tool_calls[0].function.arguments})
                            }
                        )
                        continue
            else:
                # No tool calls, this is the final response
                summary = response_message.content.strip()
                if not summary:
                    print("Warning: The LLM returned an empty summary.", file=sys.stderr)
                    return "No significant tech news found in the latest search."
                return summary

    except openai.APIConnectionError as e:
        print(f"Failed to connect to Openrouter API: {e}", file=sys.stderr)
        return "An error occurred while connecting to the API."
    except openai.APIError as e:
        print(f"Openrouter API returned an error: {e}", file=sys.stderr)
        return "An API-related error occurred while fetching news."
    except Exception as e:
        print(f"An unexpected error occurred during news generation: {e}", file=sys.stderr)
        return "An unexpected error occurred."


if __name__ == "__main__":
    digest = generate_tech_news_digest()

    current_time = datetime.now()
    log_timestamp = current_time.strftime("%Y-%m-%d %I:%M %p")
    file_timestamp = current_time.strftime("%Y-%m-%d_%H-%M")
    
    output_directory = "news_digests"
    try:
        os.makedirs(output_directory, exist_ok=True)
    except IOError as e:
        print(f"Error creating output directory: {e}", file=sys.stderr)
        sys.exit(1)
    
    output_content = f"Tech News Digest - {log_timestamp}\n\n{digest}\n"

    print("\n--- Generating Tech News Digest ---")
    print(output_content)
    print("-----------------------------------")

    output_filename = os.path.join(output_directory, f"digest_{file_timestamp}.txt")
    try:
        with open(output_filename, "w", encoding="utf-8") as file:
            file.write(output_content)
        print(f"\nSuccessfully wrote the digest to {output_filename}")
    except IOError as e:
        print(f"Error writing to file: {e}", file=sys.stderr)
        sys.exit(1)
    
    if "error occurred" in digest:
        sys.exit(1)
