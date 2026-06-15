import os
import re 
from typing import Dict, Any 

def process_markdown(file_path: str) -> Dict[str, Any]:
    """
     Reads, sanitizes, and analyzes a markdown text file.
     Returns a dictionary containing the clean text and metasata.
    """

    if not os.path.exists(file_path):
        raise FileNotFoundError(f"Text file not found at {file_path}")

    with open(file_path, "r", encoding="utf-8") as f:
        raw_text = f.read()

    clean_text = raw_text.strip().replace("\r\n", "\n").replace("\r", "\n")
    # Strip leading/trailing whitespace and normalize Windows/Mac line break to Unix Standard (\n)
    clean_text = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', clean_text)
    # Remove hidden/zero-width unicode characters that can break JSON serialization
 
    # Remove URLs.
    markdown_link_pattern = r'\[([^\]]+)\]\(https?://[^\s)]+\)'
    clean_text = re.sub(markdown_link_pattern, r'\1', clean_text)
    naked_url_pattern = r'https?://\S+|www\.\S+'
    clean_text = re.sub(naked_url_pattern, '', clean_text)

    # Structural cleanup. 
    clean_text = re.sub(r'\n{3,}', '\n\n', clean_text)
    clean_text = re.sub(r' {2,}', ' ', clean_text)
    clean_text = clean_text.strip()

    word_count = len(clean_text.split())
    has_headers = bool(re.search(r'^#+\s+', clean_text, re.MULTILINE))

    return {
        "status" : "success",
        "filename" : os.path.basename(file_path), 
        "metrics" : {
            "word_count" : word_count,
            "has_markdwon_header" : has_headers,
            "char_length" : len(clean_text)
        },
        "content" : clean_text
    }

