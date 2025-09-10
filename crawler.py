import requests
import html2text
import json
import os
import re
from bs4 import BeautifulSoup
from datetime import datetime

# The API endpoint for the OpenRouter API
API_URL = "https://openrouter.ai/api/v1/chat/completions"

def get_summary_from_openrouter(text_to_summarize, api_key):
    """
    Calls the OpenRouter API to generate a summary (tl;dr) of the provided text.
    """
    if not api_key:
        print("Error: OpenRouter API key not found.")
        return "Summary could not be generated due to missing API key."

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    # The user query and system prompt are combined into a 'messages' array
    payload = {
        "model": "mistralai/mistral-7b-instruct",  # A good, fast model for summarization
        "messages": [
            {"role": "system", "content": "You are a world-class summarizer. Provide a concise, single-paragraph tl;dr of the following technical article. Do not include any titles or introductory phrases like 'In this article' or 'This article discusses'. Just provide the summary."},
            {"role": "user", "content": text_to_summarize}
        ]
    }

    try:
        response = requests.post(API_URL, headers=headers, data=json.dumps(payload))
        response.raise_for_status()  # Raise an exception for bad status codes
        
        result = response.json()
        
        # Check if the generated text part exists
        if 'choices' in result and len(result['choices']) > 0 and 'content' in result['choices'][0]['message']:
            summary = result['choices'][0]['message']['content']
            return summary.strip()
        else:
            print("Warning: No summary text found in the API response.")
            return "Summary could not be generated."

    except requests.exceptions.RequestException as e:
        print(f"Error calling OpenRouter API: {e}")
        return "Summary could not be generated due to a network or API error."


def crawl_and_save(url):
    """
    Crawls a given URL, scrapes the main article content, gets an OpenRouter summary,
    and saves the result to a Markdown file in a 'daily-digest' folder.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()

        soup = BeautifulSoup(response.content, 'html.parser')

        # Heuristics to find the main article content
        main_content = None
        for tag in ['article', 'main']:
            main_content = soup.find(tag)
            if main_content:
                break
        
        # If no main content found, try to use a common class name for articles
        if not main_content:
            main_content = soup.find(class_=re.compile(r'article|post|content', re.I))

        if not main_content:
            print(f"Could not find main article content on {url}")
            return

        # Convert the content to Markdown for a clean, readable format
        h = html2text.HTML2Text()
        h.ignore_links = False
        markdown_content = h.handle(str(main_content))

        # Get the page title for the filename
        title_tag = soup.find('title')
        title = title_tag.get_text(strip=True) if title_tag else 'Untitled'
        
        # Call the new function to get the summary
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        summary = get_summary_from_openrouter(markdown_content, openrouter_api_key)

        # Sanitize the title to use as a filename
        sanitized_title = re.sub(r'[\\/*?:"<>|]', "", title).strip()
        filename = f"{sanitized_title}.md"
        
        # Create the daily-digest directory if it doesn't exist
        directory = "daily-digest"
        if not os.path.exists(directory):
            os.makedirs(directory)

        # Prepare the final markdown output with the summary
        final_markdown = f"""# {title}
*Source: {url}*
*Published: {datetime.now().strftime('%Y-%m-%d')}*

## TL;DR:
{summary}

---

{markdown_content}
"""

        filepath = os.path.join(directory, filename)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(final_markdown)

        print(f"Successfully crawled '{title}' and saved to {filepath}")

    except requests.exceptions.RequestException as e:
        print(f"Error: Could not retrieve URL {url}. Reason: {e}")

if __name__ == "__main__":
    # Example usage: crawl a popular tech news site.
    example_url = "https://www.theverge.com/2025/9/10/24857432/apple-watch-s10-chip-rumor-health-features"
    crawl_and_save(example_url)
