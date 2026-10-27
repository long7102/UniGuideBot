"""Prepare the same local UI assets for Vercel CDN serving."""
from pathlib import Path
import shutil
root=Path(__file__).resolve().parent
shutil.copytree(root/"static",root/"public/static",dirs_exist_ok=True)
print("Static assets copied to public/static")
