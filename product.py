from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import random
import time
import pandas as pd
import csv
import os


def setup_driver():
    options = Options()
    options.add_argument("--headless")  # Uncomment for headless mode
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
    driver = webdriver.Chrome(options=options)
    return driver


def save_product_to_csv(product, output_csv_file, fieldnames):
    mode = "a" if os.path.isfile(output_csv_file) else "w"
    with open(output_csv_file, mode=mode, newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if mode == "w":
            writer.writeheader()
        writer.writerow(product)


def crawl_banggood_products(
    driver,
    category_url,
    lv3_title,
    output_csv_file,
    max_products=20,
    existing_products=0,
):
    products_collected = existing_products
    fieldnames = [
        "lv3_title",
        "lv3_href",
        "product_url",
        "title",
        "price",
        "sku_properties",
        "description",
        "image_urls",
        "option_details",
    ]

    try:
        # Access the category page
        print(f"Accessing category page: {category_url}")
        driver.get(category_url)
        time.sleep(random.uniform(3, 5))  # Wait for page load

        while products_collected < max_products:
            # Find all <li> tags with data-product-id
            wait = WebDriverWait(driver, 10)
            product_list_items = wait.until(
                EC.presence_of_all_elements_located(
                    (By.XPATH, "//li[@data-product-id]")
                )
            )
            print(f"Found {len(product_list_items)} product list items")

            # Process up to remaining products needed
            for i, li_tag in enumerate(product_list_items):
                if products_collected >= max_products:
                    break

                # Skip products already processed
                if i < existing_products:
                    continue

                product_url = None
                title = None
                price = "Price not found"
                sku_properties = []
                description = None
                image_urls = []
                option_details = []

                # Extract product URL
                try:
                    a_tag_url = li_tag.find_element(By.XPATH, './/a[@class="exclick"]')
                    product_url = a_tag_url.get_attribute("href")
                except Exception:
                    try:
                        a_tag_url_fallback = li_tag.find_element(
                            By.XPATH, ".//a[@href]"
                        )
                        product_url = a_tag_url_fallback.get_attribute("href")
                    except Exception as e:
                        print(f"Could not find URL: {e}")
                        continue

                # Navigate to the product page
                if product_url:
                    print(f"Accessing product page: {product_url}")
                    driver.get(product_url)
                    time.sleep(random.uniform(2, 4))

                    # Extract title
                    try:
                        title_tag = wait.until(
                            EC.presence_of_element_located(
                                (
                                    By.XPATH,
                                    '//h1[@class="product-title"]//span[@class="product-title-text"]',
                                )
                            )
                        )
                        title = title_tag.text.strip()
                    except Exception as e:
                        print(f"Could not find product title: {e}")

                    # Extract SKU properties and iterate through options
                    try:
                        product_blocks = driver.find_elements(
                            By.XPATH, '//div[contains(@class, "product-block")]'
                        )
                        for block in product_blocks:
                            try:
                                property_name_tag = block.find_element(
                                    By.XPATH,
                                    './/div[contains(@class, "block-title")]//em',
                                )
                                property_name = property_name_tag.text.replace(
                                    ":", ""
                                ).strip()

                                img_tags = block.find_elements(
                                    By.XPATH, './/a[contains(@class, "imgtag")]'
                                )
                                option_elements = (
                                    img_tags
                                    if img_tags
                                    else block.find_elements(
                                        By.XPATH, './/a[@href="javascript:;"]'
                                    )
                                )

                                sku_values = [
                                    el.get_attribute("title").strip()
                                    for el in option_elements
                                    if el.get_attribute("title")
                                ]
                                active_value = next(
                                    (
                                        el.get_attribute("title").strip()
                                        for el in option_elements
                                        if "active" in el.get_attribute("class")
                                    ),
                                    sku_values[0] if sku_values else "Unknown",
                                )
                                sku_properties.append(
                                    {
                                        "sku_property": property_name,
                                        "sku_values": sku_values,
                                        "active_value": active_value,
                                    }
                                )

                                # Click through each option to get price and stock
                                for el in option_elements:
                                    option_name = el.get_attribute("title").strip()
                                    if not option_name:
                                        continue
                                    try:
                                        driver.execute_script(
                                            "arguments[0].click();", el
                                        )
                                        time.sleep(random.uniform(1, 2))

                                        # Extract price for this option
                                        try:
                                            price_tag = wait.until(
                                                EC.presence_of_element_located(
                                                    (
                                                        By.XPATH,
                                                        '//div[@class="product-newbie-price"]//div[@class="newbie-price"]',
                                                    )
                                                )
                                            )
                                            option_price = price_tag.text.strip()
                                        except Exception:
                                            try:
                                                price_tag = driver.find_element(
                                                    By.XPATH,
                                                    '//span[contains(@class, "main-price")]',
                                                )
                                                option_price = price_tag.text.strip()
                                            except Exception:
                                                option_price = "Price not found"

                                        # Extract stock for this option
                                        try:
                                            stock_tag = wait.until(
                                                EC.presence_of_element_located(
                                                    (
                                                        By.XPATH,
                                                        '//div[@data-spm="0000000Cr" and contains(@class, "pcs")]//em',
                                                    )
                                                )
                                            )
                                            stock = stock_tag.text.strip()
                                        except Exception:
                                            stock = "Stock not found"

                                        option_details.append(
                                            {
                                                "option_name": option_name,
                                                "price": option_price,
                                                "stock": stock,
                                            }
                                        )
                                        print(
                                            f"Extracted option: {option_name}, Price: {option_price}, Stock: {stock}"
                                        )
                                    except Exception as e:
                                        print(
                                            f"Error clicking option {option_name}: {e}"
                                        )
                                        continue

                            except Exception as e:
                                print(f"Error processing product block: {e}")
                                continue

                        # Extract warehouse
                        try:
                            warehouse_block = driver.find_element(
                                By.XPATH, '//div[contains(@class, "product-warehouse")]'
                            )
                            warehouse_name = warehouse_block.find_element(
                                By.XPATH,
                                './/div[contains(@class, "block-title")]//span[@class="text-name"]',
                            ).text.strip()
                            warehouse_values = [
                                a_tag.text.strip()
                                for a_tag in warehouse_block.find_elements(
                                    By.XPATH, ".//a[@data-warehouse]"
                                )
                            ]
                            active_warehouse = next(
                                (
                                    a_tag.text.strip()
                                    for a_tag in warehouse_block.find_elements(
                                        By.XPATH, ".//a[@data-warehouse]"
                                    )
                                    if "active" in a_tag.get_attribute("class")
                                ),
                                (
                                    warehouse_values[0]
                                    if warehouse_values
                                    else warehouse_name
                                ),
                            )
                            sku_properties.append(
                                {
                                    "sku_property": "Ship From",
                                    "sku_values": warehouse_values,
                                    "active_value": active_warehouse,
                                }
                            )
                        except Exception as e:
                            print(f"Could not extract warehouse info: {e}")

                    except Exception as e:
                        print(f"Error extracting SKU properties: {e}")

                    # Use default price if no options were processed
                    if not option_details:
                        try:
                            price_tag = wait.until(
                                EC.presence_of_element_located(
                                    (
                                        By.XPATH,
                                        '//div[@class="product-newbie-price"]//div[@class="newbie-price"]',
                                    )
                                )
                            )
                            price = price_tag.text.strip()
                        except Exception:
                            try:
                                price_tag = driver.find_element(
                                    By.XPATH, '//span[contains(@class, "main-price")]'
                                )
                                price = price_tag.text.strip()
                            except Exception:
                                print("Could not find any price element.")

                    # Extract product description
                    try:
                        # Scroll to tab-cnt
                        try:
                            tab_section = wait.until(
                                EC.presence_of_element_located(
                                    (
                                        By.XPATH,
                                        '//div[@data-spm="0000000UL" and contains(@class, "tab-cnt")]',
                                    )
                                )
                            )
                            driver.execute_script(
                                "arguments[0].scrollIntoView({behavior: 'smooth', block: 'center'});",
                                tab_section,
                            )
                            print("Scrolled to description section")
                            time.sleep(random.uniform(1, 2))
                        except Exception as e:
                            print(f"Could not scroll to tab-cnt: {e}")

                        # Activate Description tab
                        try:
                            description_tab = wait.until(
                                EC.element_to_be_clickable(
                                    (
                                        By.XPATH,
                                        '//a[contains(@class, "tab-nav-item") and contains(text(), "Description")]',
                                    )
                                )
                            )
                            driver.execute_script(
                                "arguments[0].click();", description_tab
                            )
                            print("Clicked 'Description' tab")
                            time.sleep(random.uniform(1, 2))
                        except Exception:
                            print("No 'Description' tab found or already active")

                        # Click "Show More" button
                        try:
                            more_button = wait.until(
                                EC.element_to_be_clickable(
                                    (
                                        By.XPATH,
                                        '//div[@data-spm="0000000UL" and contains(@class, "tab-cnt")]//a[contains(@class, "product-description-main-more")]',
                                    )
                                )
                            )
                            driver.execute_script("arguments[0].click();", more_button)
                            print("Clicked 'Show More' button")
                            time.sleep(random.uniform(1, 2))
                        except Exception:
                            print("No 'Show More' button found or not clickable")

                        # Extract description HTML
                        description_div = wait.until(
                            EC.presence_of_element_located(
                                (
                                    By.XPATH,
                                    '//div[@data-spm="0000000UL" and contains(@class, "tab-cnt")]//div[contains(@class, "product-description-main-box")]',
                                )
                            )
                        )
                        description = description_div.get_attribute("innerHTML").strip()
                        print("Successfully extracted product description")
                    except Exception as e:
                        print(f"Error extracting product description: {e}")
                        description = "Description not found"

                    # Extract all image URLs from img src
                    try:
                        image_elements = wait.until(
                            EC.presence_of_all_elements_located(
                                (
                                    By.XPATH,
                                    '//ul[@data-spm="0000000W4" and contains(@class, "list cf")]//img[@data-spm="0000000Wa"]',
                                )
                            )
                        )
                        image_urls = [
                            img.get_attribute("src").strip()
                            for img in image_elements
                            if img.get_attribute("src")
                        ]
                        print(f"Extracted {len(image_urls)} image URLs")
                    except Exception as e:
                        print(f"Error extracting image URLs: {e}")
                        image_urls = []

                    product_info = {
                        "lv3_title": lv3_title,
                        "lv3_href": category_url,
                        "product_url": product_url,
                        "title": title,
                        "price": price,
                        "sku_properties": str(
                            sku_properties
                        ),  # Convert to string for CSV
                        "description": description,
                        "image_urls": str(image_urls),  # Convert to string for CSV
                        "option_details": str(
                            option_details
                        ),  # Convert to string for CSV
                    }
                    # Save product immediately
                    save_product_to_csv(product_info, output_csv_file, fieldnames)
                    products_collected += 1
                    print(
                        f"Collected and saved product {products_collected}/{max_products} for {category_url}"
                    )

                    # Return to category page
                    driver.get(category_url)
                    time.sleep(random.uniform(2, 4))

            # Check for next page if needed
            if products_collected < max_products:
                try:
                    next_button = driver.find_element(
                        By.XPATH, '//a[contains(@class, "next")]'
                    )
                    if next_button.is_enabled():
                        driver.execute_script("arguments[0].click();", next_button)
                        print("Navigated to next page")
                        time.sleep(random.uniform(3, 5))
                        existing_products = products_collected
                    else:
                        print("No more pages available")
                        break
                except Exception:
                    print("No next page button found or end of pages")
                    break
            else:
                break

    except Exception as e:
        print(f"Error on category page {category_url}: {e}")

    return products_collected


def check_existing_products(output_csv_file):
    processed_urls = {}
    if os.path.isfile(output_csv_file):
        try:
            df = pd.read_csv(output_csv_file)
            if "lv3_href" in df.columns:
                url_counts = df.groupby("lv3_href").size().to_dict()
                processed_urls = {url: count for url, count in url_counts.items()}
        except Exception as e:
            print(f"Error reading {output_csv_file}: {e}")
    return processed_urls


def main():
    csv_file = "aliexpress_categories.csv"
    output_csv_file = "banggood_product_details.csv"
    max_products_per_url = 20

    if not os.path.isfile(csv_file):
        print(f"Error: File '{csv_file}' not found.")
        return

    try:
        df = pd.read_csv(csv_file)
        if "lv3" not in df.columns or "lv3_href" not in df.columns:
            print(
                f"Error: File '{csv_file}' is missing required columns: 'lv3' or 'lv3_href'."
            )
            return
    except Exception as e:
        print(f"Error reading CSV file '{csv_file}': {e}")
        return

    # Check existing products
    processed_urls = check_existing_products(output_csv_file)
    driver = setup_driver()

    for index, row in df.iterrows():
        lv3_title = row["lv3"]
        lv3_href = row["lv3_href"]

        if pd.isna(lv3_href):
            print(f"Skipping row {index + 1} due to missing lv3_href.")
            continue

        if "banggood.com" not in lv3_href:
            print(f"Skipping URL '{lv3_href}' as it's not a Banggood URL.")
            continue

        # Check existing products for this URL
        existing_count = processed_urls.get(lv3_href, 0)
        if existing_count >= max_products_per_url:
            print(f"Skipping {lv3_href}: Already collected {existing_count} products.")
            continue

        print(
            f"\nProcessing category: {lv3_title} - URL: {lv3_href} (Need {max_products_per_url - existing_count} more products)"
        )
        products_collected = crawl_banggood_products(
            driver,
            lv3_href,
            lv3_title,
            output_csv_file,
            max_products_per_url,
            existing_count,
        )

        # Update processed_urls
        processed_urls[lv3_href] = products_collected
        print(
            f"Total collected {products_collected}/{max_products_per_url} products for {lv3_href}"
        )

    driver.quit()
    print(f"\nProduct details saved to '{output_csv_file}'")


if __name__ == "__main__":
    main()
