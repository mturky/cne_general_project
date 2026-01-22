import os
from PyPDF2 import PdfMerger  # or: from pypdf import PdfMerger

# Folder containing PDF files
folder_path = "./pdfs"

# Get all PDF files in the folder
pdf_files = [f for f in os.listdir(folder_path) if f.lower().endswith(".pdf")]

# Dictionary to group files by the middle number
groups = {}

for pdf in pdf_files:
    parts = pdf.split("_")
    if len(parts) >= 3:
        group = parts[1]  # "11", "22", etc.
        groups.setdefault(group, []).append(pdf)

# Merge files for each group
for group, files in groups.items():
    merger = PdfMerger()
    # Sort files by the last part (e.g., 01, 02, 03)
    for pdf in sorted(files, key=lambda x: int(x.split("_")[2].split(".")[0])):
        merger.append(os.path.join(folder_path, pdf))
    
    output_file = os.path.join(folder_path, f"{group}.pdf")
    merger.write(output_file)
    merger.close()
    print(f"Created: {output_file}")
