import os
import numpy as np
import torch
from torchvision.models import inception_v3, Inception_V3_Weights
from torchvision import transforms
from PIL import Image
from tqdm import tqdm
from scipy.spatial import distance
import shutil

# --- CONFIG ---

input_dir = "FID/selected_10000"
output_dir = "selected_1000"
ref_mu_path = "FID/test_mu.npy"
ref_sigma_path = "FID/test_sigma.npy"
top_k = 1000

# --- Load reference distribution ---
ref_mu = np.load(ref_mu_path)
ref_sigma = np.load(ref_sigma_path)
ref_sigma_inv = np.linalg.inv(ref_sigma)

# --- Load InceptionV3 model ---
weights = Inception_V3_Weights.IMAGENET1K_V1
model = inception_v3(weights=weights, transform_input=False)
model.fc = torch.nn.Identity()
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
print(f"[INFO] Using device: {device}")
model.to(device).eval()


# --- Define transform ---
transform = transforms.Compose([
    transforms.Resize((299, 299)),
    transforms.ToTensor(),
    transforms.Normalize([0.5] * 3, [0.5] * 3)
])

# --- Score images ---
image_scores = []

print("[INFO] Scanning and scoring images...")
with torch.no_grad():
    for fname in tqdm(os.listdir(input_dir)):
        if not fname.lower().endswith((".png", ".jpg", ".jpeg")):
            continue
        try:
            path = os.path.join(input_dir, fname)
            img = Image.open(path).convert("RGB")
            img_tensor = transform(img).unsqueeze(0).to(device)

            features = model(img_tensor).squeeze().cpu().numpy()
            m_dist = distance.mahalanobis(features, ref_mu, ref_sigma_inv)

            image_scores.append((m_dist, path))
        except Exception as e:
            print(f"[ERROR] Failed on {fname}: {e}")

# --- Sort and copy top K ---
print(f"[INFO] Found {len(image_scores)} images. Sorting...")
image_scores.sort()
os.makedirs(output_dir, exist_ok=True)

print(f"[INFO] Copying top {top_k} images to '{output_dir}'...")
for i, (_, src_path) in enumerate(image_scores[:top_k]):
    dst_path = os.path.join(output_dir, f"{i:05d}.png")
    shutil.copy(src_path, dst_path)

print("[DONE] Top 1000 images selected and copied.")
