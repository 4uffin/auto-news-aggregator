import os
import sys
import openai
from datetime import datetime
import json
import feedparser
import requests
from bs4 import BeautifulSoup

# Configure the Openrouter client using the API key from environment variables
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
if not OPENROUTER_API_KEY:
    print("Error: OPENROUTER_API_KEY environment variable not set.", file=sys.stderr)
    sys.exit(1)

client = openai.OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

MODEL = "google/gemini-2.5-flash"

def get_rss_headlines():
    """
    Fetches recent headlines from major tech news RSS feeds.
    """
    feeds = [
        ("The Verge", "https://www.theverge.com/rss/index.xml"),
        ("TechCrunch", "https://techcrunch.com/feed/"),
        ("CNET", "https://www.cnet.com/rss/news/"),
        ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
        ("Engadget", "https://www.engadget.com/rss.xml"),
    ]
    
    all_headlines = []
    
    for source_name, feed_url in feeds:
        try:
            print(f"Fetching headlines from {source_name}...")
            feed = feedparser.parse(feed_url)
            
            if hasattr(feed, 'entries') and feed.entries:
                source_headlines = []
                for entry in feed.entries[:5]:  # Get top 5 from each source
                    title = entry.title.strip()
                    published = getattr(entry, 'published', 'Recent')
                    source_headlines.append(f"- {title}")
                
                if source_headlines:
                    all_headlines.append(f"**{source_name}:**")
                    all_headlines.extend(source_headlines)
                    all_headlines.append("")  # Add blank line between sources
                    
        except Exception as e:
            print(f"Error fetching from {source_name}: {e}", file=sys.stderr)
            continue
    
    return all_headlines

def scrape_tech_headlines_fallback():
    """
    Fallback web scraping if RSS feeds fail.
    """
    tech_sources = [
        ("The Verge", "https://www.theverge.com/tech"),
        ("TechCrunch", "https://techcrunch.com/"),
        ("CNET", "https://www.cnet.com/tech/"),
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    all_headlines = []
    
    for source_name, source_url in tech_sources:
        try:
            print(f"Scraping headlines from {source_name}...")
            response = requests.get(source_url, headers=headers, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Extract headlines based on common patterns
                headlines = []
                selectors = [
                    'h1', 'h2', 'h3',
                    '.headline', '.title', '.entry-title',
                    '[data-testid*="headline"]',
                    'article h2', 'article h3',
                    '.post-title', '.article-title'
                ]
                
                for selector in selectors:
                    elements = soup.select(selector)
                    for element in elements:
                        text = element.get_text().strip()
                        # Filter for reasonable headline length and content
                        if 20 <= len(text) <= 200 and not text.lower().startswith(('advertisement', 'sponsored')):
                            headlines.append(text)
                            if len(headlines) >= 5:  # Limit per source
                                break
                    if len(headlines) >= 5:
                        break
                
                if headlines:
                    all_headlines.append(f"**{source_name}:**")
                    all_headlines.extend([f"- {h}" for h in headlines[:5]])
                    all_headlines.append("")  # Add blank line between sources
                    
        except Exception as e:
            print(f"Error scraping {source_name}: {e}", file=sys.stderr)
            continue
    
    return all_headlines

def fetch_current_tech_news():
    """
    Fetches current tech news using RSS feeds with web scraping fallback.
    """
    print("Fetching current tech news...")
    
    # Try RSS feeds first
    headlines = get_rss_headlines()
    
    # If RSS feeds didn't work well, try web scraping
    if len(headlines) < 10:  # Not enough content from RSS
        print("RSS feeds provided limited results, trying web scraping...")
        scraped_headlines = scrape_tech_headlines_fallback()
        headlines.extend(scraped_headlines)
    
    if not headlines or len(headlines) < 5:
        return None
    
    return "\n".join(headlines)

def generate_tech_news_digest():
    """
    Fetches the latest tech news and generates a TL;DR summary.
    """
    # Fetch current tech news
    current_news = fetch_current_tech_news()
    
    if not current_news:
        return "Unable to fetch current tech news from available sources. Please check your internet connection or try again later."
    
    # Get current date for context
    current_date = datetime.now().strftime("%Y-%m-%d")
    current_time = datetime.now().strftime("%I:%M %p")
    
    # Generate summary using the LLM
    messages = [
        {
            "role": "system", 
            "content": f"""You are a tech news summarizer. Today is {current_date} at {current_time}. 
            Create a concise, well-organized TL;DR summary of the provided tech news headlines. 
            Focus on the most significant and interesting stories. Present them in a clear, readable format with proper categorization.
            Avoid redundant stories and focus on major announcements, product releases, industry shifts, or breaking news.
            Keep the summary engaging but professional."""
        },
        {
            "role": "user", 
            "content": f"""Based on these current tech news headlines I just fetched:

{current_news}

Please create a well-organized TL;DR summary highlighting the most important and interesting tech news stories from today. 

Format requirements:
- Use clear headings or categories when appropriate
- Use bullet points or short paragraphs for readability  
- Focus on major announcements, product releases, or significant industry developments
- Eliminate duplicate or very similar stories
- Keep it concise but informative
- Aim for 200-400 words total"""
        }
    ]
    
    try:
        print("Generating summary with LLM...")
        response = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            max_tokens=1024,
            temperature=0.3,
            stream=False
        )
        
        summary = response.choices[0].message.content.strip()
        
        if not summary:
            return "Unable to generate a meaningful summary from the available news sources."
            
        return summary

    except openai.APIConnectionError as e:
        print(f"Failed to connect to Openrouter API: {e}", file=sys.stderr)
        return "An error occurred while connecting to the API for summary generation."
    except openai.APIError as e:
        print(f"Openrouter API returned an error: {e}", file=sys.stderr)
        return "An API-related error occurred while generating the summary."
    except Exception as e:
        print(f"An unexpected error occurred during summary generation: {e}", file=sys.stderr)
        return "An unexpected error occurred while generating the summary."


if __name__ == "__main__":
    print("Starting tech news digest generation...")
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
    
    output_content = f"Tech News Digest - {log_timestamp}\n{'='*50}\n\n{digest}\n"

    print("\n" + "="*50)
    print("TECH NEWS DIGEST GENERATED")
    print("="*50)
    print(output_content)
    print("="*50)

    output_filename = os.path.join(output_directory, f"digest_{file_timestamp}.txt")
    try:
        with open(output_filename, "w", encoding="utf-8") as file:
            file.write(output_content)
        print(f"\nSuccessfully wrote the digest to {output_filename}")
    except IOError as e:
        print(f"Error writing to file: {e}", file=sys.stderr)
        sys.exit(1)
    
    # Check for error conditions
    error_indicators = ["unable to", "error occurred", "check your internet", "try again later"]
    if any(indicator in digest.lower() for indicator in error_indicators):
        print("Warning: Digest generation encountered issues.", file=sys.stderr)
        sys.exit(1)
    
    print("Tech news digest generation completed successfully!")
