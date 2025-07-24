from config import SERPER_API_KEY, OPENROUTER_API_KEY  # Changed import
import requests
from bs4 import BeautifulSoup
import json
import os
import time
from typing import List, Dict

class ZeroSearch:
    def __init__(self):
        self.serper_key = SERPER_API_KEY  # Changed key
        self.openrouter_key = OPENROUTER_API_KEY
        self.model = "tngtech/deepseek-r1t2-chimera:free"
        self.queries_file = "querries.json"
        self.results_file = "results.json"
        self.report_file = "report.json"

        # Initialize storage files (unchanged)
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
                "Authorization": f"Bearer {self.openrouter_key}",
                "Content-Type": "application/json"
            },
            json={
                "model": self.model,
                "messages": [{"role": "user", "content": prompt}],
                "temperature": 0.7
            }
        )

        # Extract and clean queries (unchanged)
        raw_queries = response.json()['choices'][0]['message']['content'].strip()
        queries = [q.strip() for q in raw_queries.split('\n') if q.strip()]

        # Save to file (unchanged)
        with open(self.queries_file, 'w') as f:
            json.dump(queries, f, indent=2)

        return queries

    def search(self, query: str) -> None:
        """Pull full-text top-10 results via Serper API + BeautifulSoup"""
        # Serper API call (modified section)
        serper_response = requests.post(
            url="https://google.serper.dev/search",
            headers={
                "X-API-KEY": self.serper_key,
                "Content-Type": "application/json"
            },
            json={"q": query, "num": 10}
        ).json()

        results = []
        organic_results = serper_response.get("organic", [])

        for res in organic_results:
            url = res.get('link', '')
            if not url:
                continue

            try:
                # Fetch and parse webpage (unchanged)
                page = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
                soup = BeautifulSoup(page.content, 'html.parser')

                # Extract title - use Serper's title first
                title = res.get('title', '')
                if not title and soup.title:
                    title = soup.title.string

                # Extract and clean main text (unchanged)
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

        # Append to existing results (unchanged)
        existing_results = []
        if os.path.exists(self.results_file) and os.path.getsize(self.results_file) > 0:
            with open(self.results_file, 'r') as f:
                existing_results = json.load(f)

        existing_results.extend(results)

        with open(self.results_file, 'w') as f:
            json.dump(existing_results, f, indent=2)

    # report() and _get_ai_summary() remain unchanged below
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

import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading

class ZeroSearchGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("ZeroSearch Research Assistant")
        self.zs = ZeroSearch()
        
        # Configure main window
        self.root.geometry("800x600")
        self.root.minsize(700, 500)
        
        # Create main frame
        main_frame = ttk.Frame(root, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Theme input section
        theme_frame = ttk.LabelFrame(main_frame, text="Research Theme", padding=10)
        theme_frame.pack(fill=tk.X, pady=(0, 10))
        
        ttk.Label(theme_frame, text="Enter research topic:").pack(side=tk.LEFT, padx=(0, 10))
        self.theme_entry = ttk.Entry(theme_frame, width=50)
        self.theme_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.theme_entry.bind("<Return>", lambda e: self.generate_queries())
        
        # Action buttons
        btn_frame = ttk.Frame(main_frame)
        btn_frame.pack(fill=tk.X, pady=(0, 10))
        
        self.generate_btn = ttk.Button(btn_frame, text="1. Generate Queries", 
                                      command=self.generate_queries)
        self.generate_btn.pack(side=tk.LEFT, padx=5)
        
        self.search_btn = ttk.Button(btn_frame, text="2. Run Searches", 
                                    command=self.run_searches, state=tk.DISABLED)
        self.search_btn.pack(side=tk.LEFT, padx=5)
        
        self.report_btn = ttk.Button(btn_frame, text="3. Generate Report", 
                                    command=self.generate_report, state=tk.DISABLED)
        self.report_btn.pack(side=tk.LEFT, padx=5)
        
        # Progress bar
        self.progress = ttk.Progressbar(btn_frame, mode='determinate')
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        self.progress.pack_forget()  # Hide initially
        
        # Output area
        output_frame = ttk.LabelFrame(main_frame, text="Research Output", padding=10)
        output_frame.pack(fill=tk.BOTH, expand=True)
        
        self.output_area = scrolledtext.ScrolledText(output_frame, wrap=tk.WORD)
        self.output_area.pack(fill=tk.BOTH, expand=True)
        self.output_area.configure(state=tk.DISABLED, font=("Arial", 10))
        
        # Status bar
        self.status_var = tk.StringVar(value="Ready")
        status_bar = ttk.Label(root, textvariable=self.status_var, relief=tk.SUNKEN, anchor=tk.W)
        status_bar.pack(side=tk.BOTTOM, fill=tk.X)
    
    def log_message(self, message, clear=False):
        """Add message to output area"""
        self.output_area.configure(state=tk.NORMAL)
        if clear:
            self.output_area.delete(1.0, tk.END)
        self.output_area.insert(tk.END, message + "\n")
        self.output_area.configure(state=tk.DISABLED)
        self.output_area.see(tk.END)
        self.root.update_idletasks()
    
    def update_status(self, message):
        """Update status bar"""
        self.status_var.set(message)
        self.root.update_idletasks()
    
    def generate_queries(self):
        """Generate research queries from theme"""
        theme = self.theme_entry.get().strip()
        if not theme:
            messagebox.showerror("Input Error", "Please enter a research theme")
            return
            
        # Disable button during operation
        self.generate_btn.config(state=tk.DISABLED)
        self.update_status("Generating research queries...")
        self.log_message(f"Generating queries for theme: {theme}", clear=True)
        
        def worker():
            try:
                queries = self.zs.get_querries(theme)
                self.log_message(f"\nGenerated {len(queries)} queries:")
                for i, q in enumerate(queries, 1):
                    self.log_message(f"{i}. {q}")
                
                # Enable next steps
                self.search_btn.config(state=tk.NORMAL)
                self.report_btn.config(state=tk.DISABLED)
                messagebox.showinfo("Success", "Queries generated successfully!")
            except Exception as e:
                self.log_message(f"\nERROR: {str(e)}")
                messagebox.showerror("Error", f"Query generation failed: {str(e)}")
            finally:
                self.generate_btn.config(state=tk.NORMAL)
                self.update_status("Ready")
        
        threading.Thread(target=worker, daemon=True).start()
    
    def run_searches(self):
        """Execute all searches from generated queries"""
        # Show progress bar
        self.progress.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        self.search_btn.config(state=tk.DISABLED)
        self.update_status("Running web searches...")
        self.log_message("\nStarting web searches...")
        
        def worker():
            try:
                with open(self.zs.queries_file) as f:
                    queries = json.load(f)
                
                total = len(queries)
                for i, query in enumerate(queries, 1):
                    self.log_message(f"\nSearch {i}/{total}: {query}")
                    self.update_status(f"Searching: {query[:50]}...")
                    self.zs.search(query)
                    
                    # Update progress
                    progress = int((i / total) * 100)
                    self.progress['value'] = progress
                    self.root.update_idletasks()
                
                self.log_message("\nAll searches completed!")
                self.report_btn.config(state=tk.NORMAL)
                messagebox.showinfo("Success", "All web searches completed!")
            except Exception as e:
                self.log_message(f"\nERROR: {str(e)}")
                messagebox.showerror("Error", f"Search failed: {str(e)}")
            finally:
                self.search_btn.config(state=tk.NORMAL)
                self.progress.pack_forget()
                self.update_status("Ready")
        
        threading.Thread(target=worker, daemon=True).start()
    
    def generate_report(self):
        """Generate final research report"""
        self.report_btn.config(state=tk.DISABLED)
        self.update_status("Generating research report...")
        self.log_message("\nGenerating final research report...")
        
        def worker():
            try:
                report = self.zs.report()
                self.log_message("\n" + "="*50)
                self.log_message("FINAL RESEARCH REPORT")
                self.log_message("="*50 + "\n")
                self.log_message(report)
                self.log_message("\n" + "="*50)
                messagebox.showinfo("Success", "Research report generated!")
            except Exception as e:
                self.log_message(f"\nERROR: {str(e)}")
                messagebox.showerror("Error", f"Report generation failed: {str(e)}")
            finally:
                self.report_btn.config(state=tk.NORMAL)
                self.update_status("Ready")
        
        threading.Thread(target=worker, daemon=True).start()

# Add this at the bottom of your file to run the GUI
if __name__ == "__main__":
    root = tk.Tk()
    app = ZeroSearchGUI(root)
    root.mainloop()