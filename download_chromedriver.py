import requests
import zipfile
import io
import os
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

version = "145.0.7632.77"
url = f"https://storage.googleapis.com/chrome-for-testing-public/{version}/win64/chromedriver-win64.zip"

print(f"Downloading ChromeDriver {version} from API...")
try:
    resp = requests.get(url, proxies={"http": None, "https": None}, verify=False, timeout=60)
    resp.raise_for_status()
    print("Download successful. Extracting...")

    with zipfile.ZipFile(io.BytesIO(resp.content)) as z:
        # The zip contains a folder like "chromedriver-win64/chromedriver.exe"
        driver_content = z.read("chromedriver-win64/chromedriver.exe")
        
        target_path = r"D:\spider_code\chromedriver.exe"
        if os.path.exists(target_path):
            try:
                os.remove(target_path)
            except Exception as e:
                print(f"Failed to remove old driver (it might be in use): {e}")
                
        with open(target_path, "wb") as f:
            f.write(driver_content)
            
    print(f"Success! ChromeDriver is now updated at {target_path}")
except Exception as e:
    print(f"Failed: {e}")
