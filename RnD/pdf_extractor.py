import PyPDF2
import os

pdf_path = "pdfcoffee.com_joe-dinapoli-trading-with-dinapoli-levels-pdf-free.pdf"
output_dir = "extracted_text"

# Create output directory
os.makedirs(output_dir, exist_ok=True)

with open(pdf_path, "rb") as file:
    reader = PyPDF2.PdfReader(file)
    total_pages = len(reader.pages)
    print(f"Total pages: {total_pages}")

    # Extract text page by page and save in chunks
    chunk_size = 20  # pages per file
    all_text = []

    for i, page in enumerate(reader.pages):
        text = page.extract_text()
        all_text.append(f"\n\n=== PAGE {i+1} ===\n\n{text}")
        print(f"Extracted page {i+1}/{total_pages}")

    # Save all text to one file
    with open(os.path.join(output_dir, "full_text.txt"), "w", encoding="utf-8") as f:
        f.write("".join(all_text))

    # Also save in chunks for easier reading
    for chunk_num in range(0, total_pages, chunk_size):
        chunk_end = min(chunk_num + chunk_size, total_pages)
        chunk_text = "".join(all_text[chunk_num:chunk_end])
        filename = f"pages_{chunk_num+1}_to_{chunk_end}.txt"
        with open(os.path.join(output_dir, filename), "w", encoding="utf-8") as f:
            f.write(chunk_text)
        print(f"Saved {filename}")

print(f"\nDone! Text files saved to '{output_dir}' folder")
