import argparse
import sys
import os

# --- BƯỚC 1: THIẾT LẬP ĐƯỜNG DẪN (QUAN TRỌNG) ---
# Lấy đường dẫn tuyệt đối đến thư mục gốc của dự án (nơi chứa file run.py)
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

# [ĐÃ SỬA] Xóa bỏ các dòng sys.path.append(SRC_DIR) và sys.path.append(CRAWLER_DIR).
# Python sẽ tự động nhận 'src' và 'crawler' là các package (gói)
# khi bạn chạy 'python run.py ...' từ thư mục gốc PROJECT_ROOT.


# --- BƯỚC 2: IMPORT CÁC MODULE CỦA DỰ ÁN ---
# (Phải import SAU khi đã thiết lập đường dẫn)
try:
    # [ĐÃ SỬA] Import tường minh từ package 'src'
    from src.build_index import main as build_main
    from src.search_engine import main as search_main
    from src.evaluate_ranking import evaluate_system as evaluate_main
    
    # [ĐÃ SỬA] Import tường minh từ package 'crawler'
    from crawler import dienmayxanh_crawler
    from crawler import monngonmoingay_crawler
    from crawler import disneycooking_crawler

    # [ĐÃ SỬA] Xử lý webapp.py (nằm trong 'src')
    webapp_main = None
    try:
        # Giờ nó sẽ tìm 'webapp.py' bên trong thư mục 'src'
        from webapp import main as webapp_main
    except ImportError:
        # Lỗi này là bình thường vì file webapp.py chưa tồn tại
        pass 

except ImportError as e:
    print(f"LỖI: Không thể import các module chính.", file=sys.stderr)
    print(f"Chi tiết: {e}", file=sys.stderr)
    print("Hãy đảm bảo bạn đã cài đặt tất cả thư viện trong 'requirements.txt'", file=sys.stderr)
    print(f"Và các thư mục 'src', 'crawler' tồn tại đúng vị trí.", file=sys.stderr)
    sys.exit(1)

# --- BƯỚC 3: HÀM HỖ TRỢ (Wrapper Functions) ---
# (Không cần thay đổi ở đây)
def run_all_crawlers():
    """(MODULE 1) Chạy tuần tự tất cả các crawler."""
    print("--- Bắt đầu Module 1: Thu thập dữ liệu ---")
    
    try:
        print("\n[1/3] Đang chạy dienmayxanh_crawler...")
        dienmayxanh_crawler.main() 
    except Exception as e:
        print(f"Lỗi khi chạy dienmayxanh_crawler: {e}", file=sys.stderr)

    try:
        print("\n[2/3] Đang chạy monngonmoingay_crawler...")
        monngonmoingay_crawler.main()
    except Exception as e:
        print(f"Lỗi khi chạy monngonmoingay_crawler: {e}", file=sys.stderr)

    try:
        print("\n[3/3] Đang chạy disneycooking_crawler...")
        disneycooking_crawler.main()
    except Exception as e:
        print(f"Lỗi khi chạy disneycooking_crawler: {e}", file=sys.stderr)
        
    print("\n--- Hoàn tất Module 1 ---")

# --- BƯỚC 4: HÀM ĐIỀU KHIỂN CHÍNH (với argparse) ---
# (Không cần thay đổi ở đây)
def main():
    # Tạo parser chính
    parser = argparse.ArgumentParser(
        description="Trình chạy chính cho Hệ thống Tìm kiếm Công thức Việt Nam.",
        formatter_class=argparse.RawTextHelpFormatter # Giữ định dạng help text
    )
    
    # Tạo các "lệnh" con (subparsers)
    subparsers = parser.add_subparsers(dest='action', required=True, 
                                        help='Các hành động có thể thực hiện')

    # 1. Lệnh 'crawl' (Module 1)
    parser_crawl = subparsers.add_parser('crawl', 
                                            help='(Module 1) Chạy tất cả crawler để thu thập dữ liệu thô (raw).')
    parser_crawl.set_defaults(func=run_all_crawlers) # Gán với hàm hỗ trợ

    # 2. Lệnh 'build' (Module 2)
    parser_build = subparsers.add_parser('build', 
                                            help='(Module 2) Xây dựng inverted index từ dữ liệu thô.')
    parser_build.set_defaults(func=build_main)

    # 3. Lệnh 'search' (Module 3)
    parser_search = subparsers.add_parser('search', 
                                            help='(Module 3) Chạy công cụ tìm kiếm (chế độ dòng lệnh).')
    parser_search.set_defaults(func=search_main)
    
    # 4. Lệnh 'webapp' (Module 4) 
    parser_webapp = subparsers.add_parser('webapp', 
                                            help='(Module 4) Khởi động giao diện web (HIỆN CHƯA CÓ).')
    
    if webapp_main:
        # Nếu import webapp.main thành công, gán lệnh
        parser_webapp.set_defaults(func=webapp_main) 
    else:
        # Nếu import thất bại, gán một hàm báo lỗi
        parser_webapp.set_defaults(func=lambda: print(
            "LỖI: Module 'webapp.py' chưa được triển khai. Bỏ qua."
        ))

    # 5. Lệnh 'evaluate' (Module 5)
    parser_evaluate = subparsers.add_parser('evaluate', 
                                            help='(Module 5) Chạy đánh giá (MAP, P@10) cho hệ thống.')
    # Gán với hàm evaluate_system() (mà chúng ta đã import as evaluate_main)
    parser_evaluate.set_defaults(func=evaluate_main) 

    # 6. Phân tích các đối số từ dòng lệnh
    try:
        args = parser.parse_args()
    except Exception as e:
        print(f"Lỗi khi phân tích đối số: {e}")
        parser.print_help()
        sys.exit(1)

    # 7. Chạy hàm tương ứng với lệnh đã chọn
    print(f"\n--- [run.py] Đang thực thi hành động: '{args.action}' ---")
    args.func() # Chạy hàm main() hoặc evaluate_system() của module được chọn
    print(f"--- [run.py] Hoàn thành hành động: '{args.action}' ---")

if __name__ == "__main__":
    main()