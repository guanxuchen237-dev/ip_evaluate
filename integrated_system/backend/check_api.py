
import urllib.request
import json

def check_api():
    try:
        url = "http://localhost:5000/api/charts/ticket_top?limit=10"
        with urllib.request.urlopen(url) as response:
            data = json.loads(response.read().decode())
            print(f"API returned {len(data)} items:")
            titles = [item['title'] for item in data]
            for i, t in enumerate(titles):
                print(f"{i+1}. {t} ({data[i].get('platform', '?')}) - {data[i].get('monthly_tickets', '?')}")
            
            unique_titles = set(titles)
            if len(unique_titles) < len(titles):
                print("\nDUPLICATES FOUND!")
            else:
                print("\nNO DUPLICATES.")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_api()
