import json
import re
from collections import defaultdict
from underthesea import word_tokenize
import os
import glob
import sys

# --- PHẦN 1: STOPWORDS (Không thay đổi) ---
VIETNAMESE_STOPWORDS = {
    "và", "của", "là", "cho", "với", "những", "các", "được", "trong", "khi",
    "một", "bằng", "thì", "ở", "rồi", "để", "ra", "có", "này", "nên", "đến",
    "cũng", "như", "nhưng", "vào", "vì", "từ", "đó", "đang", "lúc"
}

# --- PHẦN 2: CLEAN & TOKENIZE (ĐÃ CẬP NHẬT) ---
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

def clean_text(text):
    """
    Chuẩn bị nội dung văn bản để đưa vào chỉ mục:
    - Viết thường.
    - Tách từ bằng underthesea.
    - Bỏ stopwords.
    - Mở rộng token ghép thành cả token đơn.
    """
    text = text.lower()
    # KHÔNG dùng re.sub, để underthesea xử lý token phức (vd: cà_rốt)
    tokens = word_tokenize(text)
    # Lọc stopwords VÀ các token rác (chỉ là dấu câu)
    tokens = [t for t in tokens if t.strip() and t not in VIETNAMESE_STOPWORDS and any(c.isalnum() for c in t)]
    # Mở rộng token ghép
    tokens = expand_compound_tokens(tokens)
    return tokens

# --- PHẦN 3: NẠP DATA (Không thay đổi) ---
def load_data(files):
    """
    Đọc nội dung từ danh sách file JSON và gom tất cả công thức lại thành một list duy nhất.
    """
    recipes = []
    for fpath in files:
        try:
            with open(fpath, "r", encoding="utf-8") as f:
                data = json.load(f)
                recipes.extend(data)
        except Exception as e:
            print(f"Lỗi khi đọc file {fpath}: {e}", file=sys.stderr)
            pass
            
    print(f"Đã nhập vào tổng số {len(recipes)} công thức từ {len(files)} tệp dữ liệu.")
    return recipes


# --- PHẦN 4: XÂY DỰNG CHỈ MỤC (ĐÃ VIẾT LẠI HOÀN TOÀN) ---
def build_inverted_index(recipes):
    """
    Tạo index dạng:
    từ -> {docID: {freq_title: N, freq_ingredients: M, freq_instructions: K}}
    Đồng thời tính toán N (tổng số tài liệu) và df (document frequency) cho mỗi từ.
    """
    inverted_index = {}
    doc_freq = defaultdict(int)  # Dùng để đếm document frequency (df)
    N = len(recipes) # Tổng số tài liệu

    print(f"Bắt đầu xây dựng chỉ mục cho {N} công thức...")

    for doc_id, recipe in enumerate(recipes):
        
        # 1. Xử lý từng trường (field) riêng biệt
        title_text = recipe.get("title", "")
        ingredients_text = " ".join(recipe.get("ingredients", []))
        instructions_text = " ".join(recipe.get("instructions", []))

        title_tokens = clean_text(title_text)
        ingredients_tokens = clean_text(ingredients_text)
        instructions_tokens = clean_text(instructions_text)

        # 2. Đếm tần suất (freq) cho mỗi trường
        field_token_counts = {
            "freq_title": defaultdict(int),
            "freq_ingredients": defaultdict(int),
            "freq_instructions": defaultdict(int)
        }
        for tok in title_tokens:
            field_token_counts["freq_title"][tok] += 1
        for tok in ingredients_tokens:
            field_token_counts["freq_ingredients"][tok] += 1
        for tok in instructions_tokens:
            field_token_counts["freq_instructions"][tok] += 1

        # 3. Lấy tất cả token duy nhất trong tài liệu này
        all_doc_tokens = set(title_tokens) | set(ingredients_tokens) | set(instructions_tokens)

        # 4. Cập nhật Inverted Index và Document Frequency (df)
        for tok in all_doc_tokens:
            # Cập nhật df
            doc_freq[tok] += 1
            
            # Cập nhật inverted_index
            if tok not in inverted_index:
                inverted_index[tok] = {}

            # Lưu trữ tần suất của từng trường
            inverted_index[tok][doc_id] = {
                "freq_title": field_token_counts["freq_title"].get(tok, 0),
                "freq_ingredients": field_token_counts["freq_ingredients"].get(tok, 0),
                "freq_instructions": field_token_counts["freq_instructions"].get(tok, 0)
            }
            
        if (doc_id + 1) % 1000 == 0:
            print(f"  ... đã xử lý {doc_id + 1} / {N} công thức ...")

    print(f"Hoàn tất xây dựng index. Tổng số từ khóa được lưu: {len(inverted_index)}.")

    # 5. Trả về một đối tượng dict hoàn chỉnh
    # Chuyển df từ defaultdict sang dict thường để lưu JSON
    df_dict = dict(doc_freq)
    
    return {
        "N": N,               # Tổng số tài liệu
        "df": df_dict,        # Document Frequency cho mỗi từ
        "index": inverted_index # Chỉ mục ngược với freq theo trường
    }


# --- PHẦN 5: GHI CHỈ MỤC (Không thay đổi) ---
def save_index(data_to_save, filename="inverted_index.json"):
    """
    Ghi toàn bộ dữ liệu (N, df, index) vào thư mục data/index.
    """
    INDEX_DIR = os.path.join("data", "index")
    os.makedirs(INDEX_DIR, exist_ok=True)

    filepath = os.path.join(INDEX_DIR, filename)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            # Dùng indent=2 để file dễ đọc hơn, bỏ indent=None nếu muốn file nhỏ nhất
            json.dump(data_to_save, f, ensure_ascii=False, indent=2)
        print(f"Chỉ mục đã được lưu thành công tại: {filepath}")
    except Exception as e:
        print(f"LỖI NGHIÊM TRỌNG: Không thể ghi file index: {e}", file=sys.stderr)


# --- PHẦN 6: CHƯƠNG TRÌNH ĐIỀU KHIỂN (Không thay đổi) ---
def main():
    data_path = "data/raw/*.json"
    recipe_files = sorted(glob.glob(data_path))

    if not recipe_files:
        print(f"Không phát hiện dữ liệu tại đường dẫn '{data_path}'.", file=sys.stderr)
        return

    recipes = load_data(recipe_files)
    if not recipes:
        print("Không nạp được công thức nào, dừng chương trình.", file=sys.stderr)
        return

    # Build_inverted_index giờ trả về một dict lớn
    index_data = build_inverted_index(recipes)

    save_index(index_data)


if __name__ == "__main__":
    main()