import os
import shutil
import kagglehub

path = kagglehub.dataset_download("ayeshasiddiqa123/cars-pre")
src = os.path.join(path, "car_price_prediction_.csv")

os.makedirs("data", exist_ok=True)
dst = os.path.join("data", "car_price_prediction_.csv")

shutil.copyfile(src, dst)
print("Copied:", dst)
