import cv2
import os
import shutil
from tqdm import tqdm

# --- CONFIGURATION ---
input_dir = "filtered_sharp_images"            # Your current dataset folder
output_dir = "filtered_sharp_images_v2"   # Where to save sharp ones
threshold = 150.0                      # Tune this: higher = stricter filtering

os.makedirs(output_dir, exist_ok=True)

# --- Function to detect blurriness ---
def is_blurry(image_path, threshold=100.0):
    image = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)
    if image is None:
        return True  # treat unreadable as blurry
    laplacian_var = cv2.Laplacian(image, cv2.CV_64F).var()
    return laplacian_var < threshold

# --- Run through dataset ---
all_files = [f for f in os.listdir(input_dir) if f.lower().endswith((".png", ".jpg", ".jpeg"))]
print(f"[INFO] Found {len(all_files)} files.")

kept = 0
for filename in tqdm(all_files, desc="Filtering"):
    path = os.path.join(input_dir, filename)
    if not is_blurry(path, threshold=threshold):
        shutil.copy(path, os.path.join(output_dir, filename))
        kept += 1

print(f"[DONE] Kept {kept} sharp images out of {len(all_files)}.")
