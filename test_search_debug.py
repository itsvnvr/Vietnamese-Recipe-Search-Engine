#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script kiểm tra và debug search queries
Sử dụng: python test_search_debug.py
"""

import json
import sys
import os
import glob

# Fix Windows console encoding for Unicode
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Import search engine
from src.search_engine import search, load_data, preprocess_query

def main():
    print("=" * 70)
    print("VIETNAMESE RECIPE SEARCH - DEBUG MODE")
    print("=" * 70)
    
    # Load index
    INDEX_FILE = os.path.join("data", "index", "inverted_index.json")
    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"[OK] Loaded index: {INDEX_FILE}")
    except FileNotFoundError:
        print(f"[ERROR] Index file not found at '{INDEX_FILE}'", file=sys.stderr)
        print("   -> Run 'python src/build_index.py' first.", file=sys.stderr)
        return
    except Exception as e:
        print(f"[ERROR] Error loading index: {e}", file=sys.stderr)
        return
    
    # Load recipe data
    data_path = "data/raw/*.json"
    recipe_files = sorted(glob.glob(data_path))
    
    if not recipe_files:
        print(f"[ERROR] No recipe files found in '{data_path}'", file=sys.stderr)
        return
    
    recipes = load_data(recipe_files)
    if not recipes:
        print("[ERROR] No recipes loaded", file=sys.stderr)
        return
    
    print(f"[OK] Loaded {len(recipes)} recipes")
    print(f"[OK] Index contains {len(data.get('index', {}))} unique tokens")
    print()
    
    # Test queries
    test_queries = [
        ("canh chua", "OR"),
        ("công thức nấu canh chua", "OR"),
        ("công thức nấu canh chua", "AND"),
    ]
    
    for query, mode in test_queries:
        print("\n" + "=" * 70)
        print(f"[SEARCH] Testing query: '{query}' [Mode: {mode}]")
        print("=" * 70)
        
        # Show processed tokens
        tokens = preprocess_query(query)
        print(f"\n[TOKENS] Query tokens after preprocessing: {tokens}")
        print(f"         Total: {len(tokens)} tokens")
        
        # Check which tokens are in index
        print("\n[CHECK] Checking tokens in index:")
        inverted_index = data["index"]
        for token in tokens:
            if token in inverted_index:
                doc_count = len(inverted_index[token])
                print(f"   [FOUND] '{token}' -> found in {doc_count} documents")
            else:
                print(f"   [MISSING] '{token}' -> NOT in index")
        
        # Run search with debug enabled
        print(f"\n[RUN] Running search...")
        results = search(query, data, recipes, mode, debug=True)
        
        print(f"\n[RESULTS] {len(results)} recipes found")
        if results:
            print("\n[TOP 5]:")
            for i, r in enumerate(results[:5], 1):
                print(f"   {i}. {r['title']} (score: {r['score']})")
        else:
            print("   [NONE] No results")
        
        print()
    
    print("\n" + "=" * 70)
    print("[DONE] Debug session complete!")
    print("=" * 70)

if __name__ == "__main__":
    main()

