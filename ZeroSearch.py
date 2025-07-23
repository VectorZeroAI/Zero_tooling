import requests
from bs4 import BeautifulSoup
import json
import os
import time
from typing import List, Dict

class ZeroSearch:
    def __init__(self, brave_api_key: str, openrouter_api_key: str):
        self.brave_api_key = brave_api_key
        self.openrouter_api_key = openrouter_api_key
        self.model = "tngtech/deepseek-r1t2-chimera:free"
        self.queries_file = "querries.json"
        self.results_file = "results.json"
        self.report_file = "report.json"
        
        # Initialize storage files
        for file in [self.queries_file, self.results_file, self.report_file]:
            if not os.path.exists(file):
                with open(file, 'w') as f:
                    if file == self.results_file:
                        json.dump([], f)
                    else:
                        f.write('')

    def get_querries(self, theme: str) -> List[str]:
        """Generate 10 deep research queries for a given theme"""
        prompt = f"Compile 10 prompts for comprehensive web research of this theme: {theme}. Answer ONLY with the queries."
        
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7
            }
        )
        
        # Extract and clean queries
        raw_queries = response.json()['choices'][0]['message']['content'].strip()
        queries = [q.strip() for q in raw_queries.split('\n') if q.strip()]
        
        # Save to file
        with open(self.queries_file, 'w') as f:
            json.dump(queries, f, indent=2)
            
        return queries

    def search(self, query: str) -> None:
        """Pull full-text top-10 results via Brave Search + BeautifulSoup"""
        # Call Brave Search API
        brave_response = requests.get(
            url="https://api.search.brave.com/res/v1/web/search",
            headers={"Accept": "application/json", "X-Subscription-Token": self.brave_api_key},
            params={
                "q": query,
                "safesearch": "off",
                "count": 10,
                "text_deep": True
            }
        ).json()
        
        results = []
        web_results = brave_response.get('web', {}).get('results', [])
        
        for res in web_results:
            url = res['url']
            try:
                # Fetch and parse webpage
                page = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                soup = BeautifulSoup(page.content, 'html.parser')
                
                # Extract title
                title = res.get('title', '')
                if not title and soup.title:
                    title = soup.title.string
                
                # Extract and clean main text
                if soup.body:
                    for element in soup.body.select('script, style, noscript, footer, nav'):
                        element.decompose()
                    text = ' '.join(soup.body.get_text().split())
                else:
                    text = ''
                
                results.append({
                    "url": url,
                    "title": title,
                    "text": text[:100000]  # Limit text size
                })
                
                # Be polite between requests
                time.sleep(1)
                
            except Exception as e:
                print(f"Error processing {url}: {str(e)}")
                continue
        
        # Append to existing results
        existing_results = []
        if os.path.exists(self.results_file) and os.path.getsize(self.results_file) > 0:
            with open(self.results_file, 'r') as f:
                existing_results = json.load(f)
                
        existing_results.extend(results)
        
        with open(self.results_file, 'w') as f:
            json.dump(existing_results, f, indent=2)

    def report(self) -> str:
        """Generate detailed report from all gathered texts"""
        # Load all results
        if not os.path.exists(self.results_file) or os.path.getsize(self.results_file) == 0:
            return "No results available for reporting"
            
        with open(self.results_file, 'r') as f:
            results = json.load(f)
        
        # Concatenate all text
        full_text = "\n\n".join([f"Source: {res['url']}\n{res['text']}" for res in results])
        
        # Prepare chunking parameters
        MAX_TOKENS = 100000  # Conservative token limit
        CHUNK_SIZE = int(MAX_TOKENS * 2.5)  # Approximate character count
        
        # Process in chunks if needed
        if len(full_text) > CHUNK_SIZE:
            chunks = [full_text[i:i+CHUNK_SIZE] for i in range(0, len(full_text), CHUNK_SIZE)]
            summaries = []
            
            for chunk in chunks:
                response = self._get_ai_summary(chunk)
                summaries.append(response)
                
            combined_summary = "\n\n".join(summaries)
            final_report = self._get_ai_summary(combined_summary)
        else:
            final_report = self._get_ai_summary(full_text)
        
        # Save and return report
        with open(self.report_file, 'w') as f:
            f.write(final_report)
            
        return final_report

    def _get_ai_summary(self, text: str) -> str:
        """Helper function to get AI summary for text chunks"""
        prompt = (
            "You are a web researcher AI. Analyze the following text and create a detailed report "
            "capturing all important themes, patterns, and data points. Include specific facts, "
            "statistics, and insights. Organize findings logically:\n\n"
            f"{text}"
        )
        
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.3
            }
        )
        
        return response.json()['choices'][0]['message']['content'].strip()