import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import time

# Đọc file CSV
try:
    product_links_df = pd.read_csv("banggood_product_links.csv")
    categories_df = pd.read_csv("banggood_categories.csv")
except FileNotFoundError as e:
    print(f"Lỗi: Không tìm thấy file CSV - {e}")
    exit()

# Lấy link lv3_href cuối cùng từ product_links_df
try:
    last_lv3_href = product_links_df["lv3_href"].iloc[-1]
except IndexError:
    print("Lỗi: File banggood_product_links.csv rỗng hoặc không có cột lv3_href")
    exit()

# Tìm vị trí của last_lv3_href trong categories_df
try:
    current_index = categories_df[categories_df["lv3_href"] == last_lv3_href].index[0]
except IndexError:
    print(f"Lỗi: Không tìm thấy {last_lv3_href} trong banggood_categories.csv")
    exit()

# Lấy link tiếp theo từ categories_df
next_index = current_index + 1
if next_index >= len(categories_df):
    print("Đã xử lý hết các danh mục!")
    exit()

# Cấu hình Selenium
chrome_options = Options()
chrome_options.add_argument("--headless")  # Chạy không giao diện
chrome_options.add_argument("--disable-gpu")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")
chrome_options.add_argument("--disable-blink-features=AutomationControlled")
chrome_options.add_argument(
    "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
)

# Khởi tạo driver
driver = webdriver.Chrome(
    service=Service(ChromeDriverManager().install()), options=chrome_options
)

# Danh sách để lưu link sản phẩm mới
new_products = []


# Hàm cào link sản phẩm từ một danh mục
def scrape_products(category_row, max_products=20):
    lv3_href = category_row["lv3_href"]
    lv3 = category_row.get("lv3", "")  # Lấy lv3, để rỗng nếu không có

    print(f"Đang cào danh mục: {lv3} - {lv3_href}")

    try:
        # Load trang với Selenium
        driver.get(lv3_href)
        time.sleep(3)  # Đợi trang load ban đầu

        # Scroll để load thêm sản phẩm
        max_scroll_attempts = 10  # Giới hạn số lần thử scroll
        scroll_count = 0
        last_item_count = 0

        while scroll_count < max_scroll_attempts:
            # Scroll xuống cuối trang
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(1)  # Đợi 3 giây để load sản phẩm mới

            # Kiểm tra số lượng li hiện tại
            soup = BeautifulSoup(driver.page_source, "html.parser")
            goodlist = soup.find("ul", class_="goodlist")
            if goodlist:
                items = goodlist.find_all("li")
                current_item_count = len(items)
                print(
                    f"Scroll {scroll_count + 1}: Tìm thấy {current_item_count} sản phẩm"
                )
                if current_item_count >= max_products:
                    break  # Đủ sản phẩm
                if current_item_count == last_item_count and current_item_count > 0:
                    print("Không load thêm sản phẩm mới, dừng scroll")
                    break  # Không load thêm được
                last_item_count = current_item_count

            scroll_count += 1

        # Phân tích HTML cuối cùng
        soup = BeautifulSoup(driver.page_source, "html.parser")
        goodlist = soup.find("ul", class_="goodlist")
        if not goodlist:
            print(f"Không tìm thấy ul class='goodlist' trong {lv3_href}")
            print(f"Nội dung HTML mẫu: {str(soup)[:500]}...")
            return

        # Tìm tất cả li trong goodlist
        items = goodlist.find_all("li")
        print(f"Tổng số sản phẩm tìm thấy: {len(items)}")
        count = 0

        for item in items:
            # Tìm thẻ a với data-spm="0000001WJ"
            a_tag = item.find("a", attrs={"data-spm": "0000001WJ"})
            if a_tag and "href" in a_tag.attrs:
                product_url = a_tag["href"]
                # Đảm bảo link bắt đầu bằng https://sea.banggood.com
                if not product_url.startswith("http"):
                    product_url = "https://sea.banggood.com" + product_url
                new_products.append(
                    {"lv3_href": lv3_href, "lv3": lv3, "product_url": product_url}
                )
                count += 1
                if count >= max_products:
                    break

        print(f"Đã lấy {count} sản phẩm từ {lv3}")

    except Exception as e:
        print(f"Lỗi khi cào {lv3_href}: {e}")


# Bắt đầu từ danh mục tiếp theo
try:
    for index in range(next_index, len(categories_df)):
        category_row = categories_df.iloc[index]
        scrape_products(category_row)

        # Ghi vào file sau mỗi danh mục
        if new_products:
            try:
                new_df = pd.DataFrame(new_products)
                new_df.to_csv(
                    "banggood_product_links.csv", mode="a", header=False, index=False
                )
                print(
                    f"Đã ghi {len(new_products)} sản phẩm vào banggood_product_links.csv"
                )
                new_products = []  # Reset danh sách
            except Exception as e:
                print(f"Lỗi khi ghi file CSV: {e}")

        # Nghỉ 2 giây giữa các danh mục
finally:
    driver.quit()

print("Hoàn thành!")
