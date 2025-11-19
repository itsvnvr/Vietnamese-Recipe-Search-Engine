import json
import re
import math
from collections import defaultdict
from underthesea import word_tokenize
import os
import glob
import sys

# --- PHẦN 1: STOPWORDS VÀ TRỌNG SỐ ---

VIETNAMESE_STOPWORDS = {
    "và", "của", "là", "cho", "với", "những", "các", "được", "trong", "khi",
    "một", "bằng", "thì", "ở", "rồi", "để", "ra", "có", "này", "nên", "đến",
    "cũng", "như", "nhưng", "vào", "vì", "từ", "đó", "đang", "lúc"
}

# [LOGIC MỚI] Định nghĩa trọng số cho từng trường
FIELD_WEIGHTS = {
    "title": 3.0,
    "ingredients": 2.0,
    "instructions": 1.0
}

# --- PHẦN 2: XỬ LÝ VĂN BẢN (ĐÃ CẬP NHẬT) ---

def expand_compound_tokens(tokens):
    """
    Mở rộng token ghép (vd: 'cà rốt' hoặc 'cà_rốt') thành cả token ghép và các token đơn.
    Ví dụ: ['cà rốt'] -> ['cà rốt', 'cà', 'rốt']
           ['cà_rốt'] -> ['cà_rốt', 'cà', 'rốt']
    Điều này đảm bảo search với bất kỳ dạng nào đều match được.
    """
    expanded = []
    for token in tokens:
        expanded.append(token)  # Giữ token gốc
        # Tách token ghép (có dấu gạch dưới HOẶC khoảng trắng)
        if '_' in token or ' ' in token:
            # Thử tách bằng cả hai cách
            parts = token.replace('_', ' ').split()
            # Chỉ thêm các phần không phải stopword
            for part in parts:
                if part and part not in VIETNAMESE_STOPWORDS and len(part) > 1:
                    expanded.append(part)
    return expanded

def preprocess_query(query):
    """Chuyển truy vấn thành dạng chuẩn, đồng bộ với build_index."""
    query = query.lower().strip()
    tokens = word_tokenize(query)
    tokens = [t for t in tokens if t.strip() and t not in VIETNAMESE_STOPWORDS and any(c.isalnum() for c in t)]
    # Mở rộng token ghép để đồng bộ với index
    tokens = expand_compound_tokens(tokens)
    return tokens

def highlight_text(text, keywords):
    """Chèn mã màu làm nổi bật (hỗ trợ 'cà_rốt' -> 'cà rốt')."""
    if not text:
        return ""
    
    # Sắp xếp từ khóa, từ dài nhất trước, để highlight "thịt bò" trước "bò"
    sorted_keywords = sorted(keywords, key=len, reverse=True)
    
    for kw in sorted_keywords:
        visible_kw = kw.replace("_", " ")
        try:
            # --- [SỬA LỖI LOGIC] ---
            # Dùng \b (word boundary) để xử lý ranh giới từ (bao gồm tiếng Việt)
            # một cách chính xác, thay vì logic (?<!) phức tạp và sai.
            pattern = re.compile(r"\b" + re.escape(visible_kw) + r"\b", re.IGNORECASE)
            
            # Dùng \033[1;33m (Vàng đậm) \033[0m (Reset)
            text = pattern.sub(lambda m: f"\033[1;33m{m.group(0)}\033[0m", text)
        except re.error as e:
            print(f"Lỗi regex với từ khóa '{kw}': {e}", file=sys.stderr)
            pass
    return text

# --- PHẦN 3: TÍNH TOÁN (Không thay đổi) ---

def compute_tfidf(freq, df, N):
    """Tính trọng số TF-IDF với TF dạng logarit."""
    if freq == 0 or df == 0:
        return 0.0
    tf = 1 + math.log10(freq)
    idf = math.log10(N / df) # df không bao giờ = 0 nếu freq > 0
    return tf * idf

# --- PHẦN 4: HÀM TÌM KIẾM (ĐÃ VIẾT LẠI LOGIC CHẤM ĐIỂM) ---

def search(query, data, recipes, mode="OR"):
    """Tìm tài liệu theo truy vấn và xếp hạng dựa trên TF-IDF theo từng trường."""
    
    # 1. Trích xuất dữ liệu từ file index (Không thay đổi)
    try:
        inverted_index = data["index"]
        df_map = data.get("df", {})
        N = data.get("N", len(recipes))
        if not inverted_index or not df_map or N == 0:
            print("LỖI: File index bị thiếu dữ liệu (N, df, hoặc index).", file=sys.stderr)
            return []
    except KeyError:
        print("LỖI: Cấu trúc file index không hợp lệ. Đang mong đợi {'N', 'df', 'index'}.", file=sys.stderr)
        return []

    # 2. Xử lý truy vấn (Không thay đổi)
    tokens = preprocess_query(query)
    if not tokens:
        return []

    doc_scores = defaultdict(float)
    doc_sets = []
    found_tokens_count = 0

    # 3. [LOGIC MỚI] Tính điểm theo trọng số trường
    for token in tokens:
        if token not in inverted_index:
            continue
            
        found_tokens_count += 1
        
        # Lấy danh sách tài liệu chứa token này
        postings = inverted_index[token]
        doc_sets.append(set(map(int, postings.keys())))
        
        # Lấy document frequency (df) của token
        token_df = df_map.get(token, 1) # Mặc định là 1 để tránh lỗi chia cho 0

        # Lặp qua từng tài liệu (doc_id) chứa token này
        for doc_id_str, field_freqs in postings.items():
            doc_id = int(doc_id_str)

            # Lấy tần suất (freq) từ từng trường
            freq_title = field_freqs.get("freq_title", 0)
            freq_ingredients = field_freqs.get("freq_ingredients", 0)
            freq_instructions = field_freqs.get("freq_instructions", 0)

            # Tính điểm TF-IDF cho từng trường
            score_title = compute_tfidf(freq_title, token_df, N)
            score_ingredients = compute_tfidf(freq_ingredients, token_df, N)
            score_instructions = compute_tfidf(freq_instructions, token_df, N)
            
            # Tính tổng điểm có trọng số cho token này
            weighted_score = (score_title * FIELD_WEIGHTS["title"]) + \
                             (score_ingredients * FIELD_WEIGHTS["ingredients"]) + \
                             (score_instructions * FIELD_WEIGHTS["instructions"])
            
            # Cộng dồn điểm vào tổng điểm của tài liệu
            doc_scores[doc_id] += weighted_score

    # 4. Lọc và Sắp xếp kết quả (Giữ nguyên logic)
    if not doc_sets:
        return []

    # Sửa lỗi logic AND: chỉ trả về kết quả nếu TẤT CẢ token đều được tìm thấy
    if mode == "AND" and found_tokens_count != len(tokens):
        return [] 

    # Lấy danh sách docID khớp (Union cho OR, Intersection cho AND)
    matched_docs = set.intersection(*doc_sets) if mode.upper() == "AND" else set.union(*doc_sets)

    # Lọc ra các tài liệu có điểm > 0
    ranked = [(doc_id, doc_scores[doc_id]) for doc_id in matched_docs if doc_scores[doc_id] > 0]
    
    # Sắp xếp theo điểm, từ cao đến thấp
    ranked.sort(key=lambda x: x[1], reverse=True)

    # 5. Trả về kết quả
    results = []
    for doc_id, score in ranked:
        r = recipes[doc_id] # r là dictionary công thức gốc
        results.append({
            "docID": doc_id,
            "score": round(score, 3),
            "title": r.get("title", "Không có tiêu đề"),
            "ingredients": r.get("ingredients", []),
            "instructions": r.get("instructions", []),
            "url": r.get("url", ""),
            "image_url": r.get("image_url", None)  # Thêm image URL
        })
    return results

# --- PHẦN 5: HIỂN THỊ (ĐÃ SỬA) ---
def display_results(results, query, mode):
    """Trình bày danh sách kết quả (đã có tô vàng)."""
    tokens = preprocess_query(query)

    if not results:
        print("\nKhông có món nào phù hợp với yêu cầu.")
        return

    print(f"\nSố công thức tìm được: {len(results)}\n")

    for i, r in enumerate(results[:10], 1):
        marked_title = highlight_text(r["title"], tokens)
        print(f"[{i}] {marked_title}  |  Điểm phù hợp: {r['score']}")

        print("\n    Thành phần:")
        if r["ingredients"]:
            for ing in r["ingredients"]:
                print(f"    + {highlight_text(ing, tokens)}")
        else:
            print("    (Không có thông tin)")

        print("\n    Cách làm:")
        if r["instructions"]:
            # --- [SỬA LỖI Ở ĐÂY] ---
            # Xóa bỏ giới hạn [ :3 ] để hiển thị tất cả các bước
            for step in r["instructions"]:
                print(f"    * {highlight_text(step, tokens)}")
            # ---------------------
        else:
            print("    (Không có thông tin)")
            
        print("\n" + "-" * 70 + "\n")


# --- PHẦN 6: NẠP DATA (Không thay đổi) ---
def load_data(files):
    """Đọc dữ liệu công thức từ nhiều tệp JSON."""
    recipes = []
    for fp in files:
        try:
            with open(fp, "r", encoding="utf-8") as f:
                recipes.extend(json.load(f))
        except Exception as e:
            print(f"Lỗi khi đọc file {fp}: {e}", file=sys.stderr)
            pass
    return recipes

# --- PHẦN 7: CHƯƠNG TRÌNH CHÍNH (Đã cập nhật) ---
def main():
    # Đường dẫn đúng theo cấu trúc thư mục mới
    INDEX_FILE = os.path.join("data", "index", "inverted_index.json")
    
    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
        print(f"Đã nạp chỉ mục: {INDEX_FILE}")
    except FileNotFoundError: 
        print(f"LỖI: Không tìm thấy tệp chỉ mục tại '{INDEX_FILE}'.", file=sys.stderr)
        print("Bạn cần chạy script 'src/build_index.py' để tạo tệp này trước.", file=sys.stderr)
        return
    except json.JSONDecodeError:
        print(f"LỖI: File index '{INDEX_FILE}' bị hỏng (không phải JSON).", file=sys.stderr)
        print("Vui lòng XÓA file này và chạy lại 'src/build_index.py'.", file=sys.stderr)
        return
    except Exception as e:
        print(f"Lỗi không xác định khi đọc chỉ mục: {e}", file=sys.stderr)
        return

    # Nạp dữ liệu công thức
    data_path = "data/raw/*.json"
    recipe_files = sorted(glob.glob(data_path))
    
    if not recipe_files:
        print(f"Không tìm thấy dữ liệu công thức trong thư mục '{data_path}'.", file=sys.stderr) 
        return

    recipes = load_data(recipe_files)
    if not recipes:
        print("Không nạp được công thức nào, dừng chương trình.", file=sys.stderr)
        return

    # Kiểm tra xem N trong index có khớp với số lượng công thức đã nạp không
    if "N" in data and data["N"] != len(recipes):
        print(f"CẢNH BÁO: Số lượng công thức trong index ({data.get('N')})", file=sys.stderr)
        print(f"không khớp với số lượng file nạp được ({len(recipes)}).", file=sys.stderr)
        print("File index có thể đã cũ. Vui lòng chạy lại 'src/build_index.py'.", file=sys.stderr)
        # Cập nhật N để chương trình chạy tiếp
        data["N"] = len(recipes)
    
    while True: 
        query = input("\nNhập món ăn bạn muốn tra cứu (hoặc gõ 'q' để thoát): ").strip()
        if query.lower() == 'q':
            break
        
        if not query:
            continue

        mode = input(
            "Kiểu tìm kiếm:\n"
            "  AND = kết quả phải chứa TẤT CẢ từ khóa\n"
            "  OR  = kết quả chỉ cần chứa ÍT NHẤT 1 từ khóa\n"
            "Chọn chế độ lọc kết quả (AND / OR, mặc định: OR): "
        ).strip().upper() or "OR"

        results = search(query, data, recipes, mode)
        display_results(results, query, mode)

if __name__ == "__main__":
    main()