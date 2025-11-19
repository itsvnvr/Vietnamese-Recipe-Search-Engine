import requests
from bs4 import BeautifulSoup
import json
import re
import os # Thêm thư viện os

def clean_text(element):
    """Hàm trợ giúp để lấy text sạch, xóa các khoảng trắng thừa"""
    
    # SỬA Ở ĐÂY: Thêm separator=" " để tránh dính từ
    text = element.get_text(" ", strip=True) 
    
    # Thay thế nhiều khoảng trắng, tab, xuống dòng bằng một dấu cách
    return re.sub(r'\s+', ' ', text)

def parse_recipe_detail(recipe_url):
    """
    Hàm này truy cập trang chi tiết món ăn và bóc tách dữ liệu.
    """
    try:
        print(f"  -> Đang lấy chi tiết: {recipe_url}")
        session = requests.Session()
        session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        response = session.get(recipe_url, timeout=10)
        response.raise_for_status() # Báo lỗi nếu request hỏng
        
        soup = BeautifulSoup(response.text, 'html.parser')

        # 1. Lấy Tiêu đề
        title_tag = soup.select_one('h1 span.title')
        
        # SỬA Ở ĐÂY: Dùng get_text(" ", strip=True) hoặc dùng clean_text
        title = title_tag.get_text(" ", strip=True) if title_tag else None
        # Hoặc cách khác: title = clean_text(title_tag) if title_tag else None

        # 2. Lấy Hình ảnh
        img_tag = soup.select_one('div.aspect-video img')
        image_url = None
        if img_tag:
            image_url = img_tag.get('data-src') or img_tag.get('src')
        
        # 3. Lấy Video
        video_div = soup.select_one('div.youtube')
        video_url = None
        if video_div and video_div.get('data-embed'):
            video_id = video_div.get('data-embed')
            video_url = f'https://www.youtube.com/watch?v={video_id}'

        # 4. Lấy Nguyên liệu (Hàm clean_text đã sửa nên ở đây sẽ đúng)
        ingredient_elements = soup.select('div#tab-muong ul li')
        ingredients = [clean_text(el) for el in ingredient_elements]

        # 5. Lấy Hướng dẫn (Hàm clean_text đã sửa nên ở đây sẽ đúng)
        instruction_elements = soup.select('div#section-soche li, div#section-thuchien p, div#section-thuchien li')
        instructions = [clean_text(el) for el in instruction_elements if clean_text(el)] # Chỉ lấy nếu có text

        return {
            'title': title,
            'url': recipe_url,
            'image_url': image_url,
            'video_url': video_url,
            'ingredients': ingredients,
            'instructions': instructions,
        }

    except requests.RequestException as e:
        print(f"    Lỗi khi lấy chi tiết {recipe_url}: {e}")
        return None
    except Exception as e:
        print(f"    Lỗi khi xử lý {recipe_url}: {e}")
        return None

def main_crawl():
    """
    Hàm chính điều khiển việc crawl qua các trang danh sách.
    """
    start_url = 'https://monngonmoingay.com/tim-kiem-mon-ngon/'
    
    pages_to_crawl = [start_url]
    crawled_list_pages = set()
    all_recipes_data = []

    # Tạo một session để gửi request, giả lập trình duyệt
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    })

    while pages_to_crawl:
        current_list_url = pages_to_crawl.pop(0)
        
        if current_list_url in crawled_list_pages:
            continue
        
        print(f"\nĐang crawl trang danh sách: {current_list_url}")
        crawled_list_pages.add(current_list_url)

        try:
            # Tải trang danh sách
            response = session.get(current_list_url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, 'html.parser')

            # --- Bước 1: Thu thập tất cả link món ăn trên trang này (ĐÃ SỬA) ---
            recipe_links = soup.select('h3.font-bold > a[title]') 
            
            if not recipe_links:
                print("Không tìm thấy link món ăn nào trên trang này.")
            
            for link_tag in recipe_links:
                recipe_url = link_tag.get('href')
                if recipe_url:
                    # Lấy dữ liệu chi tiết
                    recipe_data = parse_recipe_detail(recipe_url)
                    if recipe_data:
                        all_recipes_data.append(recipe_data)

            # --- Bước 2: Tìm link "Trang Kế Tiếp" ---
            next_page_tag = soup.select_one('a.next.page-numbers')
            if next_page_tag and next_page_tag.get('href'):
                next_page_url = next_page_tag.get('href')
                if next_page_url not in crawled_list_pages:
                    pages_to_crawl.append(next_page_url)
                    print(f"Đã tìm thấy trang kế tiếp: {next_page_url}")
            else:
                # Trang cuối cùng sẽ không có nút "next"
                print("Không tìm thấy trang kế tiếp. Dừng crawl.")

        except requests.RequestException as e:
            print(f"Lỗi khi tải trang danh sách {current_list_url}: {e}")
            continue

    # --- Bước 3: Lưu tất cả dữ liệu ra file JSON vào thư mục data/raw ---
    print(f"\nHoàn thành! Đã crawl được {len(all_recipes_data)} công thức.")
    if len(all_recipes_data) > 0:
        
        # === PHẦN SỬA ĐỔI ĐỂ LƯU VÀO data/raw ===
        output_dir = "data/raw"
        output_file = os.path.join(output_dir, "monngonmoingay_raw.json") # Tạo đường dẫn đầy đủ

        # Kiểm tra và tạo thư mục nếu chưa tồn tại
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)
            print(f"Đã tạo thư mục: {output_dir}")
        
        print(f"Đang lưu ra file {output_file}...")
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(all_recipes_data, f, ensure_ascii=False, indent=4)
        print("Đã lưu file thành công!")
        # =========================================
    else:
        print("Không có dữ liệu để lưu. Vui lòng kiểm tra lại selector.")

# Chạy chương trình
if __name__ == "__main__":
    main_crawl()