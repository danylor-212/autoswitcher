
import requests
import os

def download_dictionary():
    url = "https://raw.githubusercontent.com/dwyl/english-words/master/words_alpha.txt"
    target_file = "words_alpha.txt"
    
    # Save in the same directory as this script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    file_path = os.path.join(script_dir, target_file)
    
    print(f"Downloading dictionary from {url}...")
    try:
        response = requests.get(url)
        response.raise_for_status()
        
        with open(file_path, 'wb') as f:
            f.write(response.content)
            
        print(f"Dictionary saved to {file_path}")
    except Exception as e:
        print(f"Failed to download dictionary: {e}")

if __name__ == "__main__":
    download_dictionary()
