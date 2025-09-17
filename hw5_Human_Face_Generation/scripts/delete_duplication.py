import os
from PIL import Image
import imagehash
from tqdm import tqdm

input_dir = "filtered_sharp_images"  # Your folder
hash_map = {}  # hash -> list of filenames

# Step 1: Build hash map
print("[INFO] Scanning image hashes...")
for fname in tqdm(os.listdir(input_dir)):
    if not fname.lower().endswith((".png", ".jpg", ".jpeg")):
        continue
    try:
        img_path = os.path.join(input_dir, fname)
        img = Image.open(img_path).convert("RGB")
        h = str(imagehash.phash(img))  # You can also use dhash or ahash

        if h not in hash_map:
            hash_map[h] = []
        hash_map[h].append(img_path)

    except Exception as e:
        print(f"[ERROR] Failed to process {fname}: {e}")

# Step 2: Delete all entries that are not unique
deleted = 0
for h, files in hash_map.items():
    if len(files) > 1:
        for path in files:
            try:
                os.remove(path)
                deleted += 1
            except Exception as e:
                print(f"[ERROR] Failed to delete {path}: {e}")

print(f"[DONE] Deleted {deleted} duplicated images.")
