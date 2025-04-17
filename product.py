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
import re
from selenium.common.exceptions import WebDriverException, NoSuchElementException


def setup_driver():
    options = Options()
    options.add_argument("--headless")  # Uncomment for headless mode
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-webgl")  # Disable WebGL to avoid SwiftShader errors
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--ignore-certificate-errors")  # Bypass SSL certificate issues
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


def save_description_to_csv(description_data, description_csv_file):
    fieldnames = ["product_url", "product_id", "description"]
    mode = "a" if os.path.isfile(description_csv_file) else "w"
    with open(description_csv_file, mode=mode, newline="", encoding="utf-8") as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
        if mode == "w":
            writer.writeheader()
        writer.writerow(description_data)


def get_product_id_from_url(url):
    match = re.search(r"-p-(\d+)\.html", url)
    return match.group(1) if match else None


def get_crawled_urls(output_csv_file):
    crawled_urls = set()
    if os.path.isfile(output_csv_file):
        try:
            df = pd.read_csv(output_csv_file)
            if "product_url" in df.columns:
                crawled_urls = set(df["product_url"].astype(str))
        except Exception as e:
            print(f"Error reading {output_csv_file}: {e}")
    return crawled_urls


def crawl_product(
    driver, product_url, lv3_title, category_url, output_csv_file, description_csv_file
):
    fieldnames = [
        "lv3_title",
        "lv3_href",
        "product_url",
        "product_id",
        "title",
        "price",
        "sku_properties",
        "image_urls",
        "option_details",
    ]
    product_id = get_product_id_from_url(product_url)
    title = None
    price = "Price not found"
    sku_properties = []
    description = None
    image_urls = []
    option_details = []

    try:
        print(f"Crawling product: {product_url}")
        driver.get(product_url)

        # Extract title
        try:
            wait = WebDriverWait(driver, 1)
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
                    try:
                        property_name_tag = block.find_element(
                            By.XPATH,
                            './/div[contains(@class, "block-title")]//em',
                        )
                        property_name = property_name_tag.text.replace(":", "").strip()
                    except NoSuchElementException:
                        print("No block-title em found, skipping this block")
                        continue

                    img_tags = block.find_elements(
                        By.XPATH, './/a[contains(@class, "imgtag")]'
                    )
                    option_elements = (
                        img_tags
                        if img_tags
                        else block.find_elements(By.XPATH, './/a[@href="javascript:;"]')
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

                    for el in option_elements:
                        option_name = el.get_attribute("title").strip()
                        if not option_name:
                            continue
                        try:
                            driver.execute_script("arguments[0].click();", el)

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
                                    price_tag = wait.until(
                                        EC.presence_of_element_located(
                                            (
                                                By.XPATH,
                                                '//span[contains(@class, "main-price")]',
                                            )
                                        )
                                    )
                                    option_price = price_tag.text.strip()
                                except Exception:
                                    option_price = "Price not found"

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
                            print(f"Error clicking option {option_name}: {e}")
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
                    (warehouse_values[0] if warehouse_values else warehouse_name),
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

        # Extract default price if no options were processed
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
                    price_tag = wait.until(
                        EC.presence_of_element_located(
                            (
                                By.XPATH,
                                '//span[contains(@class, "main-price")]',
                            )
                        )
                    )
                    price = price_tag.text.strip()
                except Exception:
                    print("Could not find newbie-price or main-price element.")
                    price = "Price not found"

        # Extract product description
        try:
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

            try:
                description_tab = wait.until(
                    EC.element_to_be_clickable(
                        (
                            By.XPATH,
                            '//a[contains(@class, "tab-nav-item") and contains(text(), "Description")]',
                        )
                    )
                )
                driver.execute_script("arguments[0].click();", description_tab)
                print("Clicked 'Description' tab")
            except Exception:
                print("No 'Description' tab found or already active")

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

        # Save description to separate CSV
        if description:
            description_data = {
                "product_url": product_url,
                "product_id": product_id,
                "description": description,
            }
            save_description_to_csv(description_data, description_csv_file)

        # Extract all image URLs
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

        product_info = {
            "lv3_title": lv3_title,
            "lv3_href": category_url,
            "product_url": product_url,
            "product_id": product_id,
            "title": title,
            "price": price,
            "sku_properties": str(sku_properties),
            "image_urls": str(image_urls),
            "option_details": str(option_details),
        }
        save_product_to_csv(product_info, output_csv_file, fieldnames)
        print(f"Saved product data for {product_url}")

    except Exception as e:
        print(f"Error crawling product {product_url}: {e}")


def main():
    product_links_csv_file = "banggood_product_links.csv"
    output_csv_file = "banggood_product_details.csv"
    description_csv_file = "banggood_product_descriptions.csv"
    max_retries = 3

    if not os.path.isfile(product_links_csv_file):
        print(f"Error: File '{product_links_csv_file}' not found.")
        return

    try:
        df_links = pd.read_csv(product_links_csv_file)
        if not all(
            col in df_links.columns for col in ["lv3_href", "lv3", "product_url"]
        ):
            print(f"Error: '{product_links_csv_file}' missing required columns.")
            return
    except Exception as e:
        print(f"Error reading CSV file '{product_links_csv_file}': {e}")
        return

    # Get set of already crawled URLs
    crawled_urls = get_crawled_urls(output_csv_file)
    print(f"Found {len(crawled_urls)} already crawled URLs")

    driver = None
    products_collected = 0

    for index, row in df_links.iterrows():
        product_url = row["product_url"]
        lv3_title = row["lv3"]
        lv3_href = row["lv3_href"]

        if product_url in crawled_urls:
            print(f"Product {product_url} already crawled, skipping.")
            continue

        retries = 0
        while retries < max_retries:
            try:
                if driver is None:
                    driver = setup_driver()

                crawl_product(
                    driver,
                    product_url,
                    lv3_title,
                    lv3_href,
                    output_csv_file,
                    description_csv_file,
                )
                products_collected += 1
                print(f"Processed product {products_collected}: {product_url}")
                break

            except WebDriverException as e:
                print(f"WebDriverException for {product_url}: {e}")
                retries += 1
                if retries < max_retries:
                    print(
                        f"Retrying {product_url} (Attempt {retries + 1}/{max_retries})"
                    )
                    try:
                        driver.quit()
                    except:
                        pass
                    driver = None
                    time.sleep(random.uniform(1, 2))
                else:
                    print(f"Max retries reached for {product_url}. Skipping.")
                    break

    if driver is None:
        try:
            driver.quit()
        except:
            pass
    print(f"\nTotal crawled {products_collected} new products")
    print(f"Product details saved to '{output_csv_file}'")
    print(f"Product descriptions saved to '{description_csv_file}'")


if __name__ == "__main__":
    main()
