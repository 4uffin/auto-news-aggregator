import os
import sys
import openai
from datetime import datetime
import json
import feedparser
import requests
from bs4 import BeautifulSoup
import re

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
    Fetches recent headlines from major tech news RSS feeds with URLs.
    Returns a list of dictionaries with title, url, source, and published info.
    """
    feeds = [
        ("The Verge", "https://www.theverge.com/rss/index.xml"),
        ("TechCrunch", "https://techcrunch.com/feed/"),
        ("CNET", "https://www.cnet.com/rss/news/"),
        ("Ars Technica", "https://feeds.arstechnica.com/arstechnica/index"),
        ("Engadget", "https://www.engadget.com/rss.xml"),
    ]
    
    all_articles = []
    
    for source_name, feed_url in feeds:
        try:
            print(f"Fetching headlines from {source_name}...")
            feed = feedparser.parse(feed_url)
            
            if hasattr(feed, 'entries') and feed.entries:
                for entry in feed.entries[:5]:  # Get top 5 from each source
                    article = {
                        'title': entry.title.strip(),
                        'url': getattr(entry, 'link', ''),
                        'source': source_name,
                        'published': getattr(entry, 'published', 'Recent'),
                        'id': len(all_articles)  # Simple ID for tracking
                    }
                    all_articles.append(article)
                    
        except Exception as e:
            print(f"Error fetching from {source_name}: {e}", file=sys.stderr)
            continue
    
    return all_articles

def scrape_tech_headlines_fallback():
    """
    Fallback web scraping if RSS feeds fail.
    Returns a list of dictionaries with title, url, source info.
    """
    tech_sources = [
        ("The Verge", "https://www.theverge.com/tech"),
        ("TechCrunch", "https://techcrunch.com/"),
        ("CNET", "https://www.cnet.com/tech/"),
    ]
    
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }
    
    all_articles = []
    
    for source_name, source_url in tech_sources:
        try:
            print(f"Scraping headlines from {source_name}...")
            response = requests.get(source_url, headers=headers, timeout=15)
            if response.status_code == 200:
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Find article links with headlines
                article_selectors = [
                    'article a[href]',
                    '.headline a[href]',
                    '.title a[href]',
                    '.entry-title a[href]',
                    'h2 a[href]',
                    'h3 a[href]'
                ]
                
                found_articles = []
                for selector in article_selectors:
                    elements = soup.select(selector)
                    for element in elements:
                        title = element.get_text().strip()
                        url = element.get('href', '')
                        
                        # Make relative URLs absolute
                        if url.startswith('/'):
                            url = f"{source_url.rstrip('/')}{url}"
                        elif not url.startswith('http'):
                            continue
                        
                        # Filter for reasonable headline length and content
                        if 20 <= len(title) <= 200 and not title.lower().startswith(('advertisement', 'sponsored')):
                            article = {
                                'title': title,
                                'url': url,
                                'source': source_name,
                                'published': 'Recent',
                                'id': len(all_articles) + len(found_articles)
                            }
                            found_articles.append(article)
                            
                            if len(found_articles) >= 5:  # Limit per source
                                break
                    
                    if len(found_articles) >= 5:
                        break
                
                all_articles.extend(found_articles)
                    
        except Exception as e:
            print(f"Error scraping {source_name}: {e}", file=sys.stderr)
            continue
    
    return all_articles

def fetch_current_tech_news():
    """
    Fetches current tech news using RSS feeds with web scraping fallback.
    Returns both formatted text for the LLM and the articles list for source tracking.
    """
    print("Fetching current tech news...")
    
    # Try RSS feeds first
    articles = get_rss_headlines()
    
    # If RSS feeds didn't work well, try web scraping
    if len(articles) < 10:  # Not enough content from RSS
        print("RSS feeds provided limited results, trying web scraping...")
        scraped_articles = scrape_tech_headlines_fallback()
        articles.extend(scraped_articles)
    
    if not articles or len(articles) < 5:
        return None, []
    
    # Format articles for LLM processing with IDs
    formatted_headlines = []
    by_source = {}
    
    for article in articles:
        source = article['source']
        if source not in by_source:
            by_source[source] = []
        by_source[source].append(article)
    
    for source, source_articles in by_source.items():
        formatted_headlines.append(f"**{source}:**")
        for article in source_articles:
            formatted_headlines.append(f"- [ID:{article['id']}] {article['title']}")
        formatted_headlines.append("")  # Add blank line between sources
    
    return "\n".join(formatted_headlines), articles

def extract_referenced_ids(summary_text):
    """
    Extracts article IDs that were referenced in the summary.
    Looks for patterns like [ID:5] in the text.
    """
    id_pattern = r'\[ID:(\d+)\]'
    matches = re.findall(id_pattern, summary_text)
    return [int(match) for match in matches]

def generate_tech_news_digest():
    """
    Fetches the latest tech news and generates a TL;DR summary with sources.
    """
    # Fetch current tech news
    current_news, articles = fetch_current_tech_news()
    
    if not current_news or not articles:
        return "Unable to fetch current tech news from available sources. Please check your internet connection or try again later."
    
    # Create articles lookup by ID
    articles_by_id = {article['id']: article for article in articles}
    
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
            
            IMPORTANT: When you reference a specific article in your summary, include its ID number in brackets like [ID:5] 
            immediately after mentioning that story. This helps track which sources were used.
            
            Avoid redundant stories and focus on major announcements, product releases, industry shifts, or breaking news.
            Keep the summary engaging but professional."""
        },
        {
            "role": "user", 
            "content": f"""Based on these current tech news headlines I just fetched:

{current_news}

Please create a well-organized TL;DR summary highlighting the most important and interesting tech news stories from today. 

CRITICAL FORMATTING REQUIREMENTS:
- Start each major section with a ## heading (like "## Apple & Mobile Tech")
- Use proper line breaks - DO NOT put everything in one paragraph
- Use bullet points (-) for individual news items within each section
- Leave blank lines between sections
- Each news item should be on its own line
- When you mention a specific story, include its ID in brackets like [ID:X] right after the reference

CONTENT REQUIREMENTS:
- Group similar stories into logical categories
- Focus on major announcements, product releases, or significant industry developments
- Eliminate duplicate or very similar stories
- Keep it concise but informative
- Aim for 200-400 words total

EXAMPLE FORMAT:
## Apple & Mobile Tech

- Apple announced new iPhone features [ID:X] with improved battery life
- iOS updates are rolling out with enhanced security [ID:Y]

## Artificial Intelligence

- OpenAI released new model capabilities [ID:Z]
- AI regulation discussions continue in Europe

Remember to include the [ID:X] tags so I can create a sources section with links!"""
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
        
        # Extract referenced article IDs and build sources section
        referenced_ids = extract_referenced_ids(summary)
        
        if referenced_ids:
            sources_section = "\n\n" + "="*30 + "\n"
            sources_section += "SOURCES\n"
            sources_section += "="*30 + "\n\n"
            
            for article_id in sorted(set(referenced_ids)):
                if article_id in articles_by_id:
                    article = articles_by_id[article_id]
                    sources_section += f"[{article_id}] {article['title']}\n"
                    sources_section += f"    Source: {article['source']}\n"
                    if article['url']:
                        sources_section += f"    Link: {article['url']}\n"
                    sources_section += "\n"
            
            # Clean up the summary by removing ID tags for final output
            clean_summary = re.sub(r'\[ID:\d+\]', '', summary).strip()
            clean_summary = re.sub(r'\s+', ' ', clean_summary)  # Clean up extra spaces
            
            final_digest = clean_summary + sources_section
        else:
            final_digest = summary + "\n\nNote: No specific articles were directly referenced in this summary."
            
        return final_digest

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
