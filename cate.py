from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
import time
import csv
import os
import psutil


def cleanup_chromedriver():
    for proc in psutil.process_iter(["name"]):
        if proc.info["name"] in ["chromedriver.exe", "chromedriver"]:
            try:
                proc.kill()
                print(f"Killed existing chromedriver process: {proc.pid}")
            except:
                pass


def setup_driver():
    chrome_options = Options()
    chrome_options.add_argument(
        "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    )
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
    chrome_options.add_argument("--start-maximized")  # Open browser in full-screen
    # chrome_options.add_argument("--headless")  # Uncomment to run headless
    try:
        cleanup_chromedriver()
        driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), options=chrome_options
        )
        print("Chrome driver initialized successfully!")
        return driver
    except Exception as e:
        print(f"Error initializing Chrome driver: {e}")
        raise


def get_crawled_urls(filename):
    crawled_urls = set()
    if os.path.isfile(filename):
        try:
            with open(filename, mode="r", encoding="utf-8") as csvfile:
                reader = csv.DictReader(csvfile)
                for row in reader:
                    if "lv3_href" in row and row["lv3_href"]:
                        crawled_urls.add(row["lv3_href"])
        except Exception as e:
            print(f"Error reading {filename}: {e}")
    return crawled_urls


def crawl_categories(driver, url, filename="banggood_categories.csv"):
    driver.get(url)
    time.sleep(5)

    all_category_data = []
    crawled_urls = get_crawled_urls(filename)
    print(f"Found {len(crawled_urls)} already crawled category URLs")

    try:
        # Adjust selector for Banggood's category menu
        header_category_list = WebDriverWait(driver, 30).until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, "ul.nav-menu-list")  # Updated for Banggood
            )
        )
        cate_items = header_category_list.find_elements(
            By.CSS_SELECTOR, "li.nav-menu-item"
        )
        print(f"Found {len(cate_items)} level 1 categories.")

        for lv1_item in cate_items:
            try:
                lv1_a_tag = lv1_item.find_element(By.CSS_SELECTOR, "a.nav-menu-link")
                lv1_title = lv1_a_tag.text.strip()

                # Hover over the lv1 item to reveal lv2 and lv3 categories
                webdriver.ActionChains(driver).move_to_element(lv1_item).perform()
                time.sleep(2)  # Wait for the dropdown to appear

                try:
                    cate_cnt = WebDriverWait(lv1_item, 5).until(
                        EC.presence_of_element_located(
                            (By.CSS_SELECTOR, "div.submenu")  # Updated for Banggood
                        )
                    )
                    exclick_dls = cate_cnt.find_elements(
                        By.CSS_SELECTOR, "dl.submenu-dl"
                    )

                    for lv2_dl in exclick_dls:
                        try:
                            lv2_a_tag = lv2_dl.find_element(By.CSS_SELECTOR, "dt > a")
                            lv2_title = lv2_a_tag.text.strip()

                            lv3_dds = lv2_dl.find_elements(By.CSS_SELECTOR, "dd > a")
                            for lv3_a_tag in lv3_dds:
                                lv3_title = lv3_a_tag.text.strip()
                                lv3_href = lv3_a_tag.get_attribute("href")
                                if lv3_href and lv3_href not in crawled_urls:
                                    category_data = {
                                        "lv1": lv1_title,
                                        "lv2": lv2_title,
                                        "lv3": lv3_title,
                                        "lv3_href": lv3_href,
                                    }
                                    all_category_data.append(category_data)
                                    print(
                                        f"LV1: {lv1_title}, LV2: {lv2_title}, LV3: {lv3_title}, Link: {lv3_href}"
                                    )
                                else:
                                    print(f"Skipping already crawled LV3: {lv3_href}")
                        except Exception as e:
                            print(f"Error processing LV2 categories: {e}")

                except:
                    print(f"No sub-categories found for {lv1_title}")

            except Exception as e:
                print(f"Error processing LV1 category: {e}")

    except Exception as e:
        print(f"Error finding header categories: {e}")

    # Save to CSV
    if all_category_data:
        fieldnames = ["lv1", "lv2", "lv3", "lv3_href"]
        with open(filename, mode="a", newline="", encoding="utf-8") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not os.path.isfile(filename):
                writer.writeheader()
            writer.writerows(all_category_data)
        print(f"Saved {len(all_category_data)} new categories to {filename}")
    else:
        print("No new categories to save")


def main():
    url = "https://www.banggood.com"
    filename = "banggood_categories.csv"
    driver = None
    try:
        driver = setup_driver()
        crawl_categories(driver, url, filename)
    except Exception as e:
        print(f"An error occurred in main: {e}")
    finally:
        if driver:
            driver.quit()
        cleanup_chromedriver()


if __name__ == "__main__":
    main()
