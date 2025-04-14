from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import random
import time


def setup_driver():
    # Cấu hình Selenium
    options = Options()
    options.add_argument("--headless")  # Chạy ẩn
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    driver = webdriver.Chrome(options=options)
    return driver


def crawl_banggood_products(category_url):
    driver = setup_driver()
    products = []

    try:
        # Truy cập trang danh mục
        print(f"Accessing category page: {category_url}")
        driver.get(category_url)
        time.sleep(random.uniform(3, 5))  # Chờ trang tải

        # Tìm tất cả thẻ <li> có thuộc tính data-product-id
        wait = WebDriverWait(driver, 10)
        product_list_items = wait.until(
            EC.presence_of_all_elements_located((By.XPATH, "//li[@data-product-id]"))
        )
        print(f"Found {len(product_list_items)} product list items")

        # Giới hạn tối đa 20 sản phẩm
        product_list_items = product_list_items[:30]

        for index, li_tag in enumerate(product_list_items, 1):
            product_url = None
            title = None
            try:
                # Try to find the URL using the "exclick" class
                a_tag_url = li_tag.find_element(By.XPATH, './/a[@class="exclick"]')
                product_url = a_tag_url.get_attribute("href")
            except Exception:
                print(
                    f"Link {index}: Could not find URL using class 'exclick'. Trying other methods."
                )
                try:
                    # Try to find any <a> tag within the li and get its href
                    a_tag_url_fallback = li_tag.find_element(By.XPATH, ".//a[@href]")
                    product_url = a_tag_url_fallback.get_attribute("href")
                except Exception as e:
                    print(f"Link {index}: Could not find URL using fallback - {e}")

            try:
                # Find the <a> tag with class="title" to get the title
                title_tag = li_tag.find_element(By.XPATH, './/a[@class="title"]')
                title = title_tag.text.strip()
            except Exception as e:
                print(f"Link {index}: Could not find product title - {e}")

            if product_url and title:
                print(f"Link {index}: Product Title: {title} - URL: {product_url}")
                products.append({"url": product_url, "title": title})
            elif product_url:
                print(f"Link {index}: Found URL but not title - URL: {product_url}")
                products.append({"url": product_url, "title": "No Title Found"})
            else:
                print(f"Link {index}: Could not extract URL or title.")

        return products

    except Exception as e:
        print(f"Error on category page: {e}")
        return None
    finally:
        driver.quit()


# URL danh mục Banggood
category_url = (
    "https://sea.banggood.com/Wholesale-RC-Helicopter-ca-7003.html?bid=2107010101"
)
results = crawl_banggood_products(category_url)

if results:
    print("\nFinal Results:")
    for i, product in enumerate(results, 1):
        print(f"Product {i}: {product['title']} ({product['url']})")
else:
    print("Failed to retrieve products")
