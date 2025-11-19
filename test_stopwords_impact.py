#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test để hiển thị impact của stopwords lên search results
"""

import json
import sys
import os
import glob

# Fix Windows console encoding
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

from src.search_engine import search, load_data, preprocess_query

def main():
    print("=" * 80)
    print("TEST: IMPACT CỦA STOPWORDS LÊN SEARCH RESULTS")
    print("=" * 80)
    
    # Load data
    INDEX_FILE = os.path.join("data", "index", "inverted_index.json")
    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        print(f"[ERROR] {e}")
        return
    
    recipe_files = sorted(glob.glob("data/raw/*.json"))
    recipes = load_data(recipe_files)
    
    print(f"[OK] Loaded {len(recipes)} recipes\n")
    
    # Test query
    query = "công thức nấu canh chua"
    
    print(f"Query gốc: '{query}'")
    tokens = preprocess_query(query)
    print(f"Tokens sau khi loại stopwords: {tokens}")
    print()
    
    print("=" * 80)
    print("VẤN ĐỀ:")
    print("=" * 80)
    print("• Các từ 'công thức', 'nấu' đã bị LOẠI BỎ hoàn toàn")
    print("• Mode AND chỉ áp dụng cho tokens còn lại: ['canh', 'chua']")
    print("• Kết quả sẽ là documents chứa BOTH 'canh' AND 'chua'")
    print("• Nhưng KHÔNG yêu cầu phải có 'công thức' hay 'nấu'")
    print()
    
    # Run search AND
    results_and = search(query, data, recipes, mode="AND", debug=False)
    
    print("=" * 80)
    print(f"KẾT QUẢ MODE AND: {len(results_and)} recipes")
    print("=" * 80)
    
    # Check top 5 results - do they contain "công thức"?
    print("\nKiểm tra xem TOP 5 có chứa từ 'công thức' không:\n")
    
    for i, r in enumerate(results_and[:5], 1):
        title = r['title']
        has_cong_thuc = "công thức" in title.lower()
        has_nau = "nấu" in title.lower()
        
        marker_ct = "✅" if has_cong_thuc else "❌"
        marker_nau = "✅" if has_nau else "❌"
        
        print(f"{i}. {title}")
        print(f"   {marker_ct} Có 'công thức'? {has_cong_thuc}")
        print(f"   {marker_nau} Có 'nấu'? {has_nau}")
        print(f"   Score: {r['score']}")
        print()
    
    print("=" * 80)
    print("GIẢI THÍCH:")
    print("=" * 80)
    print("Mode AND đang yêu cầu: documents phải chứa 'canh' AND 'chua'")
    print("KHÔNG yêu cầu: phải có 'công thức' hoặc 'nấu'")
    print("→ Đây là do chúng đã bị loại khỏi query khi preprocessing")
    print()
    
    print("=" * 80)
    print("HAI LỰA CHỌN:")
    print("=" * 80)
    print("1. [HIỆN TẠI] Loại bỏ từ generic → Focus vào keywords chính")
    print("   Ưu điểm: User gõ 'công thức nấu X' hay 'X' đều cho kết quả giống nhau")
    print("   Nhược điểm: Không thể search documents có chứa 'công thức'")
    print()
    print("2. [TUY CHỌN] Giữ từ generic nhưng giảm weight")
    print("   Ưu điểm: Vẫn có thể filter documents có 'công thức'")
    print("   Nhược điểm: 'canh chua' vs 'công thức nấu canh chua' cho kết quả khác nhau")
    print()

if __name__ == "__main__":
    main()

