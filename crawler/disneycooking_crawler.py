import requests
from bs4 import BeautifulSoup
import json
import time 
import re
import os 

# Khai báo HEADERS đầy đủ để mô phỏng trình duyệt, giúp tăng tính ổn định kết nối
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7',
    'DNT': '1', 
    'Connection': 'keep-alive',
    'Upgrade-Insecure-Requests': '1',
}

# Cấu hình API cho Gemini
# API_KEY để trống (""), Canvas sẽ tự động cung cấp
API_KEY = "AIzaSyBLSxkT73PbY97mG8d_p44bSS7QBEuqd3g" # <-- SỬA LẠI
API_URL = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.5-flash-preview-09-2025:generateContent?key={API_KEY}"
MAX_RETRIES = 5

def fetch_with_backoff(url, payload):
    """
    Thực hiện POST request với Exponential Backoff.
    """
    for attempt in range(MAX_RETRIES):
        try:
            response = requests.post(
                url, 
                headers={'Content-Type': 'application/json'},
                data=json.dumps(payload),
                timeout=30 # Tăng timeout cho các tác vụ nặng hơn
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if attempt < MAX_RETRIES - 1:
                delay = 2 ** attempt
                # print(f"API attempt {attempt + 1} failed, retrying in {delay}s...")
                time.sleep(delay) # Giữ nguyên sleep
            else:
                print(f"LỖI API sau {MAX_RETRIES} lần thử: {e}")
                return None
    return None

def process_dish_details_with_gemini(raw_text):
    """
    Sử dụng Gemini API để trích xuất (title, ingredients, instructions).
    """
    system_prompt = (
        "Bạn là một chuyên gia trích xuất dữ liệu công thức nấu ăn. "
        "Nhiệm vụ của bạn là phân tích văn bản thô được cung cấp, trích xuất Tiêu đề món ăn, Nguyên liệu, và Hướng dẫn thực hiện. "
        "Hãy đảm bảo:\n"
        "1. Tiêu đề phải là chuỗi văn bản thuần túy.\n"
        "2. Nguyên liệu (ingredients) phải là một danh sách các chuỗi (list of strings).\n"
        "3. Hướng dẫn (instructions) phải là một danh sách các chuỗi (list of strings).\n"
        "4. Loại bỏ tất cả các nội dung không phải công thức như quảng cáo, mô tả hình ảnh, v.v."
        "5. Nếu không thể tìm thấy, trả về mảng rỗng."
    )
    
    user_query = f"""
    Trích xuất Tiêu đề, Nguyên liệu, và Hướng dẫn từ văn bản thô sau (bằng tiếng Việt):
    ---
    {raw_text}
    ---
    
    Vui lòng trả về đầu ra DẠNG JSON OBJECT theo cấu trúc sau:
    {{
        "title": "Tiêu đề món ăn",
        "ingredients": ["Nguyên liệu 1", "Nguyên liệu 2", ...],
        "instructions": ["Bước 1 thực hiện", "Bước 2 thực hiện", ...]
    }}
    """
    
    payload = {
        "contents": [{"parts": [{"text": user_query}]}],
        "systemInstruction": {"parts": [{"text": system_prompt}]},
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseSchema": {
                "type": "OBJECT",
                "properties": {
                    "title": {"type": "STRING"},
                    "ingredients": {"type": "ARRAY", "items": {"type": "STRING"}},
                    "instructions": {"type": "ARRAY", "items": {"type": "STRING"}}
                },
                "propertyOrdering": ["title", "ingredients", "instructions"]
            }
        }
    }
    
    result = fetch_with_backoff(API_URL, payload)

    if result and result.get('candidates'):
        try:
            json_text = result['candidates'][0]['content']['parts'][0]['text']
            extracted_data = json.loads(json_text)
            return extracted_data
            
        except Exception as e:
            print(f"LỖI parse JSON từ Gemini: {e}")
            return None
    
    return None

def get_dish_details(url, referer_url):
    """
    HÀM NÀY ĐÃ ĐƯỢC SỬA ĐỔI:
    1. Dùng BeautifulSoup (BS4) để lấy image_url và video_url.
    2. Dùng Gemini để lấy title, ingredients, instructions.
    3. Gộp kết quả lại.
    """
    # Dừng 1.5 giây để lịch sự với server, tránh bị chặn
    time.sleep(1.5) 
    
    detail_headers = HEADERS.copy()
    detail_headers['Referer'] = referer_url 
    
    try:
        response = requests.get(url, headers=detail_headers, timeout=15)
        response.raise_for_status() 
        soup = BeautifulSoup(response.content, 'html.parser')
    except requests.exceptions.RequestException as e:
        print(f"LỖI HTTP khi truy cập chi tiết {url}: {e}")
        return None

    # === PHẦN SỬA ĐỔI: DÙNG BEAUTIFULSOUP ===
    # 1. Lấy Image URL bằng BeautifulSoup
    
    # Thử selector mới của bạn trước:
    image_tag = soup.select_one("div > div.post-container.cf > div > div > p:nth-child(2) > img") # <-- SỬA ĐỔI THEO YÊU CẦU
    
    # Nếu không tìm thấy, thử selector "ảnh đại diện" (featured image) cũ làm dự phòng:
    if not image_tag:
        image_tag = soup.select_one("div.post-image img") # <-- PHƯƠNG ÁN DỰ PHÒNG

    image_url = image_tag.get('src') if image_tag else None

    # 2. Lấy Video URL bằng BeautifulSoup
    # (Selector: tìm iframe youtube bên trong div nội dung bài viết)
    video_tag = soup.select_one("div.post-content iframe[src*='youtube']")
    video_url = video_tag.get('src') if video_tag else None
    # === KẾT THÚC SỬA ĐỔI ===

    # Lấy TOÀN BỘ nội dung chính của bài viết để gửi cho Gemini
    post_content_div = soup.find('div', class_='post-content')
    
    if not post_content_div:
        # print("Không tìm thấy div.post-content.")
        return None
    
    # Lấy text thô để Gemini xử lý
    raw_text = post_content_div.get_text(separator=' ', strip=True)

    print(f"   -> Đang gửi nội dung ({len(raw_text)} ký tự) tới Gemini để trích xuất text...")
    
    # 3. BƯỚC MỚI: Dùng Gemini để trích xuất (title, ingredients, instructions)
    dish_data_gemini = process_dish_details_with_gemini(raw_text)
    
    # Kiểm tra tính hợp lệ
    if dish_data_gemini and dish_data_gemini.get('title') and (dish_data_gemini.get('ingredients') or dish_data_gemini.get('instructions')):
        
        # 4. Gộp kết quả từ BeautifulSoup (ảnh/video) và Gemini (text)
        final_data = {
            "title": dish_data_gemini.get('title'),
            "url": url,
            "image_url": image_url,
            "video_url": video_url,
            "ingredients": [item.strip() for item in dish_data_gemini.get('ingredients', []) if item.strip()],
            "instructions": [item.strip() for item in dish_data_gemini.get('instructions', []) if item.strip()]
        }
        
        # Chỉ coi là thành công nếu có ít nhất nguyên liệu HOẶC hướng dẫn
        if final_data['ingredients'] or final_data['instructions']:
            return final_data
    
    print("   -> Gemini không trích xuất được đủ thông tin (Title/Ingredients/Instructions) -> Bỏ qua món này.")
    return None

def crawl_disneycooking(output_filename="data/raw/disneycooking_raw.json"): 
    """
    (Hàm này giữ nguyên, không cần thay đổi)
    Crawling trang danh sách món ăn, lấy chi tiết tất cả món, dùng Gemini để trích xuất cấu trúc và lưu vào file JSON.
    """
    base_url = "https://www.disneycooking.com/mon-ngon-moi-ngay"
    all_recipes = []

    print(f"Bắt đầu crawl danh sách từ: {base_url}")
    try:
        response = requests.get(base_url, headers=HEADERS, timeout=15) 
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'html.parser')
    except requests.exceptions.RequestException as e:
        print(f"LỖI KẾT NỐI TRANG DANH SÁCH, KHÔNG THỂ TIẾP TỤC: {e}")
        return

    # Bộ chọn: tìm thẻ a nằm trong div có class 'catItemView2'
    recipe_links = []
    link_elements = soup.select('div.catItemView2 a[href][title]')
    
    for link in link_elements:
        href = link.get('href')
        # Lọc liên kết món ăn hợp lệ
        if href and href.startswith(base_url.replace('/mon-ngon-moi-ngay', '')) and len(href.split('/')) == 4:
            if href not in recipe_links:
                recipe_links.append(href)

    print(f"Tìm thấy TỔNG CỘNG {len(recipe_links)} liên kết món ăn. Bắt đầu trích xuất cấu trúc...")
    
    if not recipe_links:
        print("Không có liên kết nào để crawl. Dừng chương trình.")
        return

    total_recipes = len(recipe_links)
    extracted_count = 0
    for i, link_url in enumerate(recipe_links): 
        print(f"[{i+1}/{total_recipes}] Đang xử lý: {link_url}")
        dish_data = get_dish_details(link_url, base_url)
        if dish_data:
            all_recipes.append(dish_data)
            extracted_count += 1

    # Lưu kết quả vào file JSON
    print(f"\n--- Đã trích xuất cấu trúc thành công cho {extracted_count} món ăn.")
    try:
        # --- PHẦN BỔ SUNG: Tạo thư mục nếu chưa tồn tại ---
        output_dir = os.path.dirname(output_filename)
        if output_dir: # Đảm bảo output_dir không rỗng (nếu file ở thư mục gốc)
            os.makedirs(output_dir, exist_ok=True)
        # --- KẾT THÚC PHẦN BỔ SUNG ---
        
        with open(output_filename, 'w', encoding='utf-8') as f:
            json.dump(all_recipes, f, indent=4, ensure_ascii=False)
        print(f" Dữ liệu đã được lưu thành công vào file: **{output_filename}**")
    except Exception as e:
        print(f"LỖI khi lưu file JSON: {e}")

# Thực thi hàm crawl
if __name__ == "__main__":
    crawl_disneycooking()

