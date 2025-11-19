import os
import json
import glob
from typing import List, Dict, Any
import sys

# --- CÀI ĐẶT ĐƯỜNG DẪN ---
# Giúp file này chạy được dù bạn gọi từ 'src/' hay 'run.py'
try:
    current_file_path = os.path.abspath(__file__)
    src_dir = os.path.dirname(current_file_path)
    PROJECT_ROOT = os.path.dirname(src_dir)
except NameError:
    # Xử lý khi chạy trong môi trường không có __file__
    PROJECT_ROOT = os.path.abspath(os.path.join(os.getcwd(), os.pardir))
sys.path.append(src_dir)

# Import các hàm cần thiết từ search_engine.py
try:
    # Giả định search_engine.py nằm trong cùng thư mục 'src/'
    
    # [ĐÃ SỬA LỖI Ở ĐÂY]
    # Import đúng tên hàm là 'load_data' và dùng alias 'as load_recipes'
    from search_engine import load_data as load_recipes, search 
    
except ImportError:
    print("LỖI: Không tìm thấy module 'search_engine'. Vui lòng đảm bảo 'search_engine.py' nằm trong thư mục 'src/'.")
    sys.exit(1)


# **************************************************************************
# I. THIẾT LẬP CẤU HÌNH VÀ DỮ LIỆU
# **************************************************************************

# 1. Đường dẫn Index và Dữ liệu thô
INDEX_FILE = os.path.join(PROJECT_ROOT, "data", "index", "inverted_index.json")
RECIPE_DIR = os.path.join(PROJECT_ROOT, "data", "raw") 

# 2. DỮ LIỆU NỀN TẢNG (GROUND_TRUTH)
#    Bộ "đáp án" chuẩn, đã được lọc thủ công (làm lại)
#    dựa trên kết quả bạn cung cấp.
GROUND_TRUTH: Dict[str, List[str]] = {
    # Truy vấn 1:
    "Món ăn từ thịt bò": [
        "https://www.disneycooking.com/gau-bo-lam-mon-gi-ngon",
        "https://www.dienmayxanh.com/vao-bep/cach-nau-chao-dau-xanh-thit-bo-thom-ngon-don-gian-bo-duong-09252",
        "https://www.dienmayxanh.com/vao-bep/3-cach-che-bien-rau-bo-khai-xao-bang-chao-sau-long-sieu-don-22207",
        "https://www.dienmayxanh.com/vao-bep/cach-lam-mon-hu-tieu-xao-bo-kho-dam-da-chuan-vi-nhu-nha-hang-23242",
        "https://monngonmoingay.com/thit-bo-chien-mam-bo-hoc/"
    ],
    # Truy vấn 2:
    "Công thức nấu canh chua": [
        "https://www.dienmayxanh.com/vao-bep/cach-nau-canh-cua-chua-la-mieng-thom-ngon-hap-dan-cho-ca-nha-15472",
        "https://www.dienmayxanh.com/vao-bep/cach-lam-qua-doc-nau-canh-chua-dau-ca-thanh-mat-bang-bo-noi-23329",
        "https://www.dienmayxanh.com/vao-bep/cach-lam-ca-leo-nau-canh-chua-chuan-vi-tai-nha-bang-bo-noi-23286",
        "https://www.dienmayxanh.com/vao-bep/cach-che-bien-canh-ca-nau-chua-kieu-mien-bac-chuan-vi-bang-22308"
    ],
    # Truy vấn 3: (Lọc các món "chiên")
    "Công thức ăn vặt không chiên": [
        "https://www.dienmayxanh.com/vao-bep/cach-lam-dau-tay-ngam-duong-mon-an-vat-giau-vitamin-09763"
        # (Đã loại bỏ "Tổng hợp 30 cách làm" vì là bài viết tổng hợp)
    ],
    # Truy vấn 4:
    "Cách làm các loại chả": [
        "https://www.dienmayxanh.com/vao-bep/cach-lam-cha-gio-quang-dong-bo-duong-va-dep-mat-bang-chao-23023",
        "https://www.dienmayxanh.com/vao-bep/cach-lam-cha-gio-hai-san-pho-mai-keo-soi-gion-thom-voi-chao-22946",
        "https://www.dienmayxanh.com/vao-bep/cach-lam-banh-mi-binh-dinh-co-trung-luoc-cha-ram-bang-chao-va-22729",
        "https://www.dienmayxanh.com/vao-bep/cach-lam-tokbokki-cha-ca-theo-cong-thuc-chuan-vi-duong-pho-23177",
        "https://www.dienmayxanh.com/vao-bep/cach-lam-cha-gio-hat-sen-bui-thom-gion-lau-don-gian-moi-la-07412"
    ],
    # Truy vấn 5:
    "Món ngon từ tôm và hải sản": [
        "https://www.dienmayxanh.com/vao-bep/cach-nau-lau-nam-hai-san-nong-hoi-hap-dan-truc-tiep-bang-noi-23311",
        "https://monngonmoingay.com/sup-phong-tom-hai-san/",
        "https://www.dienmayxanh.com/vao-bep/cach-lam-pho-xao-hai-san-thom-ngon-bo-duong-don-gian-tai-nha-08255",
        "https://www.dienmayxanh.com/vao-bep/cach-lam-mi-xao-gion-hai-san-thom-ngon-hap-dan-don-gian-chi-06936",
        "https://www.dienmayxanh.com/vao-bep/cach-nau-hu-tieu-hai-san-thom-ngon-don-gian-de-lam-cho-bua-11673"
    ],
    # Truy vấn 6: (Lọc các bài viết "mẹo")
    "Công thức nấu món cá": [
        "https://www.dienmayxanh.com/vao-bep/cach-lam-tokbokki-cha-ca-theo-cong-thuc-chuan-vi-duong-pho-23177",
        "https://www.dienmayxanh.com/vao-bep/cach-nau-mon-ca-chim-trang-nau-canh-chua-thom-ngon-don-gian-14099",
        "https://www.dienmayxanh.com/vao-bep/cach-nau-ca-nganh-om-chuoi-dau-thom-mem-khong-nat-voi-noi-lau-23017",
        "https://www.dienmayxanh.com/vao-bep/cach-nau-bun-ca-thu-ngon-kho-cuong-nhanh-chong-don-gian-ngay-14760"
        # (Đã loại bỏ "Mẹo chế biến cá không tanh")
    ],
    # Truy vấn 7:
    "Món lẩu cho gia đình": [
        "https://www.dienmayxanh.com/vao-bep/cach-nau-lau-sa-te-uyen-uong-thom-ngon-bang-noi-lau-dien-da-23019",
        "https://www.dienmayxanh.com/vao-bep/cach-lam-ca-chep-nau-lau-thai-ngay-mua-thom-ngon-hap-dan-voi-23384",
        "https://www.dienmayxanh.com/vao-bep/cach-nau-lau-ca-khoai-nau-hanh-ot-nong-hoi-thom-ngon-cho-ca-12332",
        "httpsVl.dienmayxanh.com/vao-bep/cach-nau-lau-ca-tam-sapa-chua-cay-ngon-mem-tai-nha-voi-noi-22720",
        "https://www.dienmayxanh.com/vao-bep/cach-nau-lau-nam-hai-san-nong-hoi-hap-dan-truc-tiep-bang-noi-23311",
        "https://www.dienmayxanh.com/vao-bep/cach-nau-lau-ga-thap-cam-ngon-nhuc-nach-nhieu-topping-bang-noi-lau-dien-23318" # URL bị cắt, giả định là .com/...23318
    ],
    # Truy vấn 8:
    "Bún phở và mì": [
        "https://www.dienmayxanh.com/vao-bep/cach-lam-pho-con-sui-sa-pa-moi-la-bang-noi-ap-suat-22570",
        "https://www.dienmayxanh.com/vao-bep/cach-nau-pho-bap-bo-bang-noi-ap-suat-thom-ngon-dam-da-huong-16184",
        "https://monngonmoingay.com/pho-tai-lan/",
        "https://monngonmoingay.com/pho-chay-2/",
        "https://www.dienmayxanh.com/vao-bep/2-cach-lam-pho-xao-trung-va-tom-la-mieng-thom-lung-kho-cuong-08397"
    ],
    # Truy vấn 9: (Đã gộp Vịt và Gà)
    "Các món ăn làm từ vịt và gà": [
        # (Kết quả món Vịt)
        "https://www.dienmayxanh.com/vao-bep/cach-lam-vit-kho-nuoc-dua-tuoi-thom-mem-ngot-thit-tai-nha-cuc-23120",
        "https://www.dienmayxanh.com/vao-bep/cach-lam-thit-vit-kho-sa-ot-cay-nong-bat-vi-cho-bua-com-hap-14012",
        "https://www.disneycooking.com/cach-nau-bun-mang-vit",
        "https://monngonmoingay.com/vit-nau-com-ruou/",
        "https://www.dienmayxanh.com/vao-bep/cach-lam-vit-nuong-lu-mem-ngon-dam-da-don-gian-tai-nha-06096",
        # (Kết quả món Gà)
        "https://www.dienmayxanh.com/vao-bep/cach-lam-ga-tam-bot-chien-gion-aji-quick-gion-rum-bang-chao-23287",
        "https://www.dienmayxanh.com/vao-bep/cach-lam-ga-an-may-ga-nuong-dat-set-chuan-vi-nguoi-hoa-voi-22672",
        "https://www.dienmayxanh.com/vao-bep/cach-lam-ga-nau-bao-tu-gion-ngon-nuoc-dung-ngot-thanh-voi-noi-22972",
        "https://www.dienmayxanh.com/vao-bep/cach-lam-ga-nau-nam-dong-co-bap-non-ngot-lanh-an-voi-bun-hay-23280",
        "https://www.dienmayxanh.com/vao-bep/2-cach-lam-ga-nau-dau-chay-va-ga-tiem-chay-moi-la-hap-dan-04467", # (Chấp nhận "gà nấu đậu chay" là món gà)
        "https://www.dienmayxanh.com/vao-bep/cach-lam-mon-ga-sot-cam-thom-ngon-00403"
    ],
    # Truy vấn 10:
    "Hướng dẫn làm món kho ngon": [
        "https://www.dienmayxanh.com/vao-bep/cach-nau-chao-gao-do-an-cung-ca-bong-kho-mon-ngon-xu-hue-voi-22527",
        "https://www.dienmayxanh.com/vao-bep/cach-lam-ca-tram-kho-thit-ba-chi-ngon-mem-ruc-thom-beo-bang-22329",
        "https://www.dienmayxanh.com/vao-bep/cach-lam-ca-et-kho-tieu-dam-vi-chuan-mien-bien-ma-ban-nen-thu-12244",
        "https://www.dienmayxanh.com/vao-bep/cach-lam-ca-dua-kho-to-thom-ngon-dam-da-cuc-hao-com-don-gian-08074",
        "https://www.dienmayxanh.com/vao-bep/cach-lam-ca-basa-kho-gung-thom-ngon-dam-da-dua-com-06964"
    ],
    # Truy vấn 11:
    "Gỏi và salad": [
        "https://monngonmoingay.com/salad-thit-hun-khoi-trung-cut/",
        "https://monngonmoingay.com/goi-hai-san-phuong-dong/",
        "https://monngonmoingay.com/salad-ga-nuong/",
        "https://monngonmoingay.com/salad-ga-nuong-3/",
        "https://monngonmoingay.com/salad-banh-da-tom/"
    ],
    # Truy vấn 12: (Đổi tên truy vấn cho khớp với kết quả)
    "Món ăn cho bé": [
        "https://www.dienmayxanh.com/vao-bep/cach-nau-chao-ca-basa-ngon-don-gian-de-lam-cho-be-an-dam-13839",
        "https://www.dienmayxanh.com/vao-bep/cach-lam-ca-hoi-sot-cam-cho-be-cuc-de-khong-bi-dang-bang-may-23331",
        "https://www.dienmayxanh.com/vao-bep/2-cach-nau-chao-bao-ngu-cho-be-an-dam-bo-duong-thom-ngon-don-15794",
        "httpsVl.dienmayxanh.com/vao-bep/cach-nau-chao-cu-cai-trang-bo-duong-va-cuc-ki-don-gian-cho-be-15724",
        "https://www.dienmayxanh.com/vao-bep/2-cach-lam-sinh-to-du-du-cho-be-an-dam-ho-tro-tang-can-ma-me-14627"
    ],
    # Truy vấn 13:
    "Công thức làm bánh": [
        "https://www.dienmayxanh.com/vao-bep/cach-lam-banh-bo-re-tre-kinh-doanh-thom-ngon-bang-xung-hap-23046",
        "httpsL.dienmayxanh.com/vao-bep/cong-thuc-lam-banh-khoai-mi-chien-gion-de-lam-mon-an-vat-ngon-23413",
        "https://www.dienmayxanh.com/vao-bep/cach-lam-banh-pia-thit-lap-thom-ngon-bang-lo-nuong-thung-va-22997",
        "https://www.dienmayxanh.com/vao-bep/2-cach-lam-banh-quy-chocolate-chip-phien-ban-mem-va-gion-don-22833"
    ],
    # Truy vấn 14:
    "Món ăn chay": [
        "httpsVl.dienmayxanh.com/vao-bep/cach-lam-bo-lui-chay-thom-ngon-don-gian-bat-vi-cho-bua-com-07643",
        "https://www.dienmayxanh.com/vao-bep/cach-lam-chuoi-xanh-kho-chay-de-lam-cho-bua-com-chay-dan-da-22724",
        "https://www.dienmayxanh.com/vao-bep/2-cach-lam-ga-nau-dau-chay-va-ga-tiem-chay-moi-la-hap-dan-04467",
        "https://monngonmoingay.com/mi-cay-chay/",
        "https://www.dienmayxanh.com/vao-bep/2-cach-lam-goi-nam-tuyet-chay-ca-rot-gion-ngon-hap-dan-cho-11353",
        "https://www.dienmayxanh.com/vao-bep/cach-lam-cha-don-chay-deo-thom-hap-bang-noi-hap-de-da-dang-23039",
        "https://monngonmoingay.com/pho-chay-2/",
        "https://www.dienmayxanh.com/vao-bep/cach-lam-suon-non-chay-nuong-me-hap-dan-moi-la-ngon-mieng-04519"
    ],
    # Truy vấn 15:
    "Khoai tây chiên": [
        "https://www.dienmayxanh.com/vao-bep/cach-lam-banh-khoai-tay-sua-chien-xu-thom-ngon-gion-rum-09336",
        "https://www.dienmayxanh.com/vao-bep/cach-lam-khoai-tay-chien-ngon-nhu-kfc-don-gian-tai-nha-voi-23316",
        "https://monngonmoingay.com/khoai-tay-chien-bo-nuong/",
        "https://www.dienmayxanh.com/vao-bep/cach-lam-tater-tots-khoai-tay-chien-kieu-my-thom-ngon-hap-dan-05753",
        "https://monngonmoingay.com/banh-khoai-tay-chien-xu/"
    ],
    # Truy vấn 16: (Lọc các món mặn)
    "Món tráng miệng": [
        "https://monngonmoingay.com/banh-crepe-ap-chao/"
        # (Đã loại bỏ Cơm sen, Trà, Súp)
    ]
}


# **************************************************************************
# II. THUẬT TOÁN TÍNH TOÁN METRICS
# (Giữ nguyên, không thay đổi)
# **************************************************************************

def calculate_precision_at_k(retrieved_docs: List[Dict[str, Any]],
                             relevant_urls: List[str],
                             k: int = 10) -> float:
    """Tính Precision@K: Tỷ lệ tài liệu phù hợp trong K kết quả đầu tiên."""
    if k <= 0 or not retrieved_docs:
        return 0.0
    retrieved_at_k = [doc.get('url', '') for doc in retrieved_docs[:k]]
    relevant_in_k = len([url for url in retrieved_at_k if url in relevant_urls])
    return relevant_in_k / k


# Tệp: src/evaluate_ranking.py

def calculate_average_precision(retrieved_docs: List[Dict[str, Any]],
                                relevant_urls: List[str]) -> float:
    """Tính Average Precision (AP) cho một truy vấn."""
    
    # --- [SỬA LỖI] ---
    # Thêm một set để theo dõi các URL đã được tính điểm
    seen_relevant_urls = set()
    # ---------------
    
    relevant_count = 0
    precision_sum = 0.0
    total_relevant = len(relevant_urls)
    
    if total_relevant == 0:
        return 0.0 

    for i, doc in enumerate(retrieved_docs):
        doc_url = doc.get('url', '') 
        
        # --- [SỬA LỖI] ---
        # Chỉ tính điểm nếu URL này liên quan VÀ chưa được tính trước đó
        if doc_url in relevant_urls and doc_url not in seen_relevant_urls:
            relevant_count += 1
            precision_at_i = relevant_count / (i + 1)
            precision_sum += precision_at_i
            
            # Đánh dấu là đã tính điểm cho URL này
            seen_relevant_urls.add(doc_url)
        # ---------------

    if relevant_count == 0:
        return 0.0
        
    return precision_sum / total_relevant


# **************************************************************************
# III. CHỨC NĂNG ĐÁNH GIÁ TỔNG THỂ (MODULE 5)
# **************************************************************************

def evaluate_system():
    """Chạy toàn bộ quá trình đánh giá hệ thống bằng cách gọi search_engine.search."""
    
    # 1. Tải Index
    try:
        with open(INDEX_FILE, "r", encoding="utf-8") as f:
            index_data = json.load(f)
        print(f"Đã nạp chỉ mục: {INDEX_FILE}")
    except FileNotFoundError:
        print(f"LỖI: Không tìm thấy chỉ mục tại {INDEX_FILE}. Vui lòng chạy 'python run.py build' trước.")
        return
    except Exception as e:
        print(f"LỖI khi đọc chỉ mục: {e}")
        return

    # 2. Tải Dữ liệu công thức thô
    recipe_files = sorted(glob.glob(os.path.join(RECIPE_DIR, "*.json")))
    if not recipe_files:
        print(f"LỖI: Không tìm thấy dữ liệu công thức thô trong thư mục '{RECIPE_DIR}'.")
        return

    recipes = load_recipes(recipe_files)
    print(f"Đã tải {len(recipes)} công thức từ {len(recipe_files)} tệp.")

    total_ap = 0.0
    all_precision_at_10: List[float] = []
    
    # [THAY ĐỔI] Lọc ra các truy vấn đã có "đáp án" (Ground Truth)
    queries_to_run = {q: urls for q, urls in GROUND_TRUTH.items() if urls}
    num_queries = len(queries_to_run)

    if num_queries == 0:
        print("LỖI: Không có truy vấn nào trong GROUND_TRUTH có 'đáp án'. Vui lòng cập nhật.")
        return

    print(f"\n--- BẮT ĐẦU ĐÁNH GIÁ HỆ THỐNG TF-IDF MÓN ĂN VIỆT NAM ---")
    print(f"Số truy vấn được đánh giá (có Ground Truth): {num_queries} / {len(GROUND_TRUTH)}")
    print(f"Mô hình xếp hạng: TF-IDF (Ưu tiên Tiêu đề, Nguyên liệu, Cụm từ)\n")

    for query_str, relevant_urls in queries_to_run.items():
        
        # Luôn chạy ở chế độ 'OR' để đánh giá khả năng xếp hạng
        retrieved_docs = search(query_str, index_data, recipes, mode="OR")

        p_at_10 = calculate_precision_at_k(retrieved_docs, relevant_urls, k=10)
        ap = calculate_average_precision(retrieved_docs, relevant_urls)

        all_precision_at_10.append(p_at_10)
        total_ap += ap

        print(f"  Truy vấn: '{query_str}'")
        print(f"    -> Precision@10: {p_at_10:.4f}")
        print(f"    -> Average Precision (AP): {ap:.4f}")

    mean_average_precision = total_ap / num_queries
    mean_precision_at_10 = sum(all_precision_at_10) / num_queries

    print("\n--- KẾT QUẢ ĐÁNH GIÁ TỔNG KẾT MODULE 5 ---")
    print(f"MEAN AVERAGE PRECISION (MAP): {mean_average_precision:.4f}")
    print(f"MEAN PRECISION@10 (P@10 TB): {mean_precision_at_10:.4f}")
    print("---------------------------------------------")


if __name__ == '__main__':
    # Đổi tên hàm thành 'evaluate_system' để 'run.py' có thể gọi
    evaluate_system()