# Tech News Digest 📰🤖

An automated tech news aggregation and summarization tool that fetches headlines from major tech publications and generates concise TL;DR summaries using AI.

## Features

- **Multi-source news aggregation**: Fetches headlines from The Verge, TechCrunch, CNET, Ars Technica, and Engadget
- **Intelligent summarization**: Uses Google's Gemini 2.5 Flash model via OpenRouter to generate concise summaries
- **Fallback mechanisms**: RSS feeds with web scraping fallback for reliability
- **Automated scheduling**: Runs every 12 hours via GitHub Actions
- **File organization**: Saves timestamped digests to organized directories

## How It Works

1. **News Collection**: The script fetches recent headlines from RSS feeds of major tech publications
2. **Fallback Scraping**: If RSS feeds fail or provide insufficient content, it falls back to web scraping
3. **AI Summarization**: Headlines are processed by Google's Gemini model to create organized summaries
4. **Output Generation**: Creates timestamped digest files with formatted summaries
5. **Automation**: GitHub Actions runs the process every 12 hours and commits new digests

## Prerequisites

- Python 3.12+
- OpenRouter API key
- Internet connection for fetching news

## Installation

1. Clone the repository:
```bash
git clone <your-repository-url>
cd tech-news-digest
```

2. Install required dependencies:
```bash
pip install openai feedparser requests beautifulsoup4
```

3. Set up your OpenRouter API key:
```bash
export OPENROUTER_API_KEY="your-api-key-here"
```

## Usage

### Manual Execution

Run the script directly:
```bash
python generate_digest.py
```

The script will:
- Fetch current tech news headlines
- Generate an AI-powered summary
- Save the digest to `news_digests/digest_YYYY-MM-DD_HH-MM.txt`
- Display the summary in the terminal

### Automated Execution

The GitHub Actions workflow runs automatically:
- **Schedule**: Every 12 hours (00:00 and 12:00 UTC)
- **Manual trigger**: Available from the GitHub Actions tab
- **Auto-commit**: Automatically commits new digest files

## Configuration

### News Sources

The script fetches from these sources by default:
- The Verge
- TechCrunch
- CNET
- Ars Technica
- Engadget

To modify sources, edit the `feeds` list in the `get_rss_headlines()` function.

### AI Model

Currently uses Google's Gemini 2.5 Flash via OpenRouter. To change models, modify the `MODEL` variable:
```python
MODEL = "google/gemini-2.5-flash"  # Change to your preferred model
```

### Summary Parameters

Adjust AI summarization by modifying the prompt in `generate_tech_news_digest()`:
- Word count target (currently 200-400 words)
- Formatting requirements
- Content focus areas

## GitHub Actions Setup

1. Add your OpenRouter API key to repository secrets:
   - Go to Settings → Secrets and variables → Actions
   - Add `OPENROUTER_API_KEY` with your API key

2. The workflow will automatically:
   - Run on schedule (every 12 hours)
   - Install dependencies
   - Execute the digest generation
   - Commit new files to the repository

## Output Format

Generated digests include:
- Timestamp header with generation time
- Organized summary with clear headings
- Major tech announcements and developments
- Product releases and industry shifts
- Clean, readable formatting

Example output location: `news_digests/digest_2024-01-15_14-30.txt`

## Error Handling

The script includes robust error handling:
- **Connection failures**: Graceful fallback between RSS and web scraping
- **API errors**: Detailed error messages and appropriate exit codes
- **File I/O issues**: Safe directory creation and file writing
- **GitHub Actions integration**: Automatic failure prevention for incomplete runs

## Troubleshooting

### Common Issues

**"OPENROUTER_API_KEY environment variable not set"**
- Ensure your API key is properly set in environment variables
- For GitHub Actions, verify the secret is added to repository settings

**"Unable to fetch current tech news"**
- Check internet connection
- Verify RSS feed URLs are accessible
- Web scraping fallback should activate automatically

**"API-related error occurred"**
- Verify OpenRouter API key is valid
- Check API quota and billing status
- Ensure the specified model is available

### Debug Mode

For troubleshooting, the script outputs detailed progress information:
- Source fetching status
- Headline counts per source
- API request status
- File writing confirmation

## Contributing

1. Fork the repository
2. Create a feature branch
3. Test your changes thoroughly
4. Submit a pull request with clear description

## License

This project is open source. Please check the repository for specific license terms.

## Acknowledgments

- **News Sources**: The Verge, TechCrunch, CNET, Ars Technica, Engladget
- **AI Provider**: Google Gemini via OpenRouter
- **Automation**: GitHub Actions
- **Dependencies**: OpenAI Python client, feedparser, requests, BeautifulSoup4
