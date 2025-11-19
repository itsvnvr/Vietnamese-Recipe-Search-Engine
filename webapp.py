from flask import Flask, render_template, request
import json
import os
import glob
import sys
import math
import re

# Import search engine module - use simplified version if underthesea not available
try:
    from src.search_engine import search, load_data, preprocess_query
    print("✅ Successfully imported search_engine with underthesea")
except ImportError as e:
    print(f"⚠️  Could not import search_engine: {e}")
    print("🔄 Using simplified search engine without underthesea...")
    
    from collections import defaultdict
    
    # Simplified Vietnamese stopwords
    VIETNAMESE_STOPWORDS = {
        "và", "của", "là", "cho", "với", "những", "các", "được", "trong", "khi",
        "một", "bằng", "thì", "ở", "rồi", "để", "ra", "có", "này", "nên", "đến",
        "cũng", "như", "nhưng", "vào", "vì", "từ", "đó", "đang", "lúc"
    }
    
    # Field weights from original search_engine.py
    FIELD_WEIGHTS = {
        "title": 3.0,
        "ingredients": 2.0,
        "instructions": 1.0
    }
    
    def expand_compound_tokens(tokens):
        """
        Mở rộng token ghép (vd: 'cà rốt' hoặc 'cà_rốt') thành cả token ghép và các token đơn.
        """
        expanded = []
        for token in tokens:
            expanded.append(token)  # Giữ token gốc
            # Tách token ghép (có dấu gạch dưới HOẶC khoảng trắng)
            if '_' in token or ' ' in token:
                parts = token.replace('_', ' ').split()
                for part in parts:
                    if part and part not in VIETNAMESE_STOPWORDS and len(part) > 1:
                        expanded.append(part)
        return expanded
    
    def simple_preprocess_query(query):
        """Simplified query preprocessing without underthesea"""
        query = query.lower().strip()
        # Simple split by space and punctuation
        import re
        tokens = re.findall(r'\b\w+\b', query)
        tokens = [t for t in tokens if t and t not in VIETNAMESE_STOPWORDS and len(t) > 1]
        # Mở rộng token ghép
        tokens = expand_compound_tokens(tokens)
        return tokens
    
    def compute_tfidf(freq, df, N):
        """Compute TF-IDF weight with logarithmic TF."""
        if freq == 0 or df == 0:
            return 0.0
        tf = 1 + math.log10(freq)
        idf = math.log10(N / df)
        return tf * idf
    
    def simple_search(query, data, recipes, mode="OR"):
        """Simplified search function using real inverted index data"""
        try:
            inverted_index = data["index"]
            df_map = data.get("df", {})
            N = data.get("N", len(recipes))
            if not inverted_index or not df_map or N == 0:
                print("ERROR: Index data is missing (N, df, or index).", file=sys.stderr)
                return []
        except KeyError:
            print("ERROR: Invalid index structure.", file=sys.stderr)
            return []

        tokens = simple_preprocess_query(query)
        if not tokens:
            return []

        doc_scores = defaultdict(float)
        doc_sets = []
        found_tokens_count = 0

        # Score calculation with field weights
        for token in tokens:
            if token not in inverted_index:
                continue
                
            found_tokens_count += 1
            postings = inverted_index[token]
            doc_sets.append(set(map(int, postings.keys())))
            
            token_df = df_map.get(token, 1)

            for doc_id_str, field_freqs in postings.items():
                doc_id = int(doc_id_str)

                freq_title = field_freqs.get("freq_title", 0)
                freq_ingredients = field_freqs.get("freq_ingredients", 0)
                freq_instructions = field_freqs.get("freq_instructions", 0)

                score_title = compute_tfidf(freq_title, token_df, N)
                score_ingredients = compute_tfidf(freq_ingredients, token_df, N)
                score_instructions = compute_tfidf(freq_instructions, token_df, N)
                
                weighted_score = (score_title * FIELD_WEIGHTS["title"]) + \
                                 (score_ingredients * FIELD_WEIGHTS["ingredients"]) + \
                                 (score_instructions * FIELD_WEIGHTS["instructions"])
                
                doc_scores[doc_id] += weighted_score

        if not doc_sets:
            return []

        if mode == "AND" and found_tokens_count != len(tokens):
            return []

        matched_docs = set.intersection(*doc_sets) if mode.upper() == "AND" else set.union(*doc_sets)
        ranked = [(doc_id, doc_scores[doc_id]) for doc_id in matched_docs if doc_scores[doc_id] > 0]
        ranked.sort(key=lambda x: x[1], reverse=True)

        results = []
        for doc_id, score in ranked:
            r = recipes[doc_id]
            results.append({
                "docID": doc_id,
                "score": round(score, 3),
                "title": r.get("title", "Không có tiêu đề"),
                "ingredients": r.get("ingredients", []),
                "instructions": r.get("instructions", []),
                "url": r.get("url", ""),
                "image_url": r.get("image_url", None)  # Include real image URLs
            })
        return results
    
    def simple_load_data(files):
        """Load data from JSON files"""
        recipes = []
        for fp in files:
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    recipes.extend(json.load(f))
            except Exception as e:
                print(f"Error reading file {fp}: {e}", file=sys.stderr)
        return recipes
    
    # Use simplified functions
    search = simple_search
    load_data = simple_load_data
    preprocess_query = simple_preprocess_query

app = Flask(__name__)

# Global variables for data - load once at startup
data = None
recipes = None

def load_search_data():
    """Load search index and recipe data once at startup"""
    global data, recipes
    
    # Load index
    INDEX_FILE = os.path.join("data", "index", "inverted_index.json")
    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"Loaded search index: {INDEX_FILE}")
    except FileNotFoundError:
        print(f"ERROR: Index file not found at '{INDEX_FILE}'", file=sys.stderr)
        print("You need to run 'src/build_index.py' first.", file=sys.stderr)
        return False
    except Exception as e:
        print(f"Error loading index: {e}", file=sys.stderr)
        return False
    
    # Load recipe data
    data_path = "data/raw/*.json"
    recipe_files = sorted(glob.glob(data_path))
    
    if not recipe_files:
        print(f"No recipe files found in '{data_path}'", file=sys.stderr)
        return False
    
    recipes = load_data(recipe_files)
    if not recipes:
        print("No recipes loaded", file=sys.stderr)
        return False
    
    print(f"Loaded {len(recipes)} recipes")
    return True

def highlight_query_in_text(text, query_tokens):
    """Highlight search terms in text with HTML bold tags"""
    if not text or not query_tokens:
        return text
    
    # Sort keywords by length (longest first) to avoid partial matching issues
    sorted_tokens = sorted(query_tokens, key=len, reverse=True)
    
    for token in sorted_tokens:
        # Replace underscores with spaces for display
        visible_token = token.replace("_", " ")
        try:
            # Use word boundary for Vietnamese text
            pattern = re.compile(r'\b' + re.escape(visible_token) + r'\b', re.IGNORECASE)
            text = pattern.sub(lambda m: f"<b>{m.group(0)}</b>", text)
        except re.error:
            pass
    
    return text

@app.route("/")
def index():
    """Home page with search form"""
    return render_template("index.html")

@app.route("/search")
def search_results():
    """Search results page with pagination"""
    query = request.args.get("query", "").strip()
    method = request.args.get("method", "OR").upper()
    page = int(request.args.get("page", 1))
    
    if not query:
        return render_template("results.html", 
                             results_list=[], 
                             query="", 
                             method=method, 
                             current_page=1, 
                             total_pages=0,
                             has_prev=False,
                             has_next=False)
    
    # Ensure method is valid
    if method not in ["AND", "OR"]:
        method = "OR"
    
    # Get search results
    all_results = search(query, data, recipes, method)
    
    # Pagination logic
    results_per_page = 10
    total_results = len(all_results)
    total_pages = math.ceil(total_results / results_per_page) if total_results > 0 else 0
    
    # Ensure page is valid
    if page < 1:
        page = 1
    if page > total_pages and total_pages > 0:
        page = total_pages
    
    # Get results for current page
    start_idx = (page - 1) * results_per_page
    end_idx = start_idx + results_per_page
    page_results = all_results[start_idx:end_idx]
    
    # Process results for display
    query_tokens = preprocess_query(query)
    processed_results = []
    
    for result in page_results:
        # Create snippet from ingredients and instructions
        snippet_parts = []
        
        # Add some ingredients to snippet
        if result.get("ingredients"):
            ingredients_text = ", ".join(result["ingredients"][:3])  # First 3 ingredients
            snippet_parts.append(f"Nguyên liệu: {ingredients_text}")
        
        # Add first instruction step
        if result.get("instructions"):
            first_instruction = result["instructions"][0] if result["instructions"] else ""
            if first_instruction:
                snippet_parts.append(f"Cách làm: {first_instruction}")
        
        snippet = ". ".join(snippet_parts)
        
        # Highlight query terms in snippet and title
        highlighted_snippet = highlight_query_in_text(snippet, query_tokens)
        highlighted_title = highlight_query_in_text(result["title"], query_tokens)
        
        processed_result = {
            "id": result["docID"],
            "title": highlighted_title,
            "original_title": result["title"],  # Keep original for display
            "url": result.get("url", "#"),
            "snippet": highlighted_snippet,
            "snippet_short": highlighted_snippet[:150] + "..." if len(highlighted_snippet) > 150 else highlighted_snippet,
            "snippet_full": highlighted_snippet,
            "image_url": result.get("image_url", None),  # Use real image URLs from data
            "score": result["score"],
            # Add full details for modal
            "ingredients": result.get("ingredients", []),
            "instructions": result.get("instructions", [])
        }
        processed_results.append(processed_result)
    
    # Pagination info
    has_prev = page > 1
    has_next = page < total_pages
    
    return render_template("results.html",
                         results_list=processed_results,
                         query=query,
                         method=method,
                         current_page=page,
                         total_pages=total_pages,
                         has_prev=has_prev,
                         has_next=has_next,
                         total_results=total_results)

if __name__ == "__main__":
    # Load data at startup
    if load_search_data():
        print("Starting Flask app...")
        app.run(debug=True, host="0.0.0.0", port=5000)
    else:
        print("Failed to load search data. Exiting.")
        sys.exit(1)
