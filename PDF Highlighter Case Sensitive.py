import pymupdf
import os
import shutil
import sys
from pathlib import Path

def highlight_keywords_in_pdf(input_pdf, output_pdf, keywords, highlight_color=(1, 1, 0)):
    """
    Highlights specified keywords in a PDF file with case-sensitive matching.
    
    Args:
        input_pdf: Path to the input PDF file
        output_pdf: Path to save the highlighted PDF
        keywords: List of keywords to highlight
        highlight_color: RGB tuple (values 0-1), default is yellow
    """
    box_shrink = 3  # Amount to shrink the box to avoid get_textbox from capturing words from adjacent lines
    common_punctuation = "\"',.()[]{}!?;:-"  # Common punctuation to strip from words for matching
    # Open the PDF
    doc = pymupdf.open(input_pdf)
    
    # Track total highlights made
    total_highlights = 0
    truncated = False
    # Iterate through each page
    for page in doc:
        
        for keyword in keywords:

            boxes = page.search_for(keyword)

            for box_no, box in enumerate(boxes):

                if truncated:
                    truncated = False
                    continue
                
                shrunk_box = pymupdf.Rect(box[0], box[1]+box_shrink, box[2], box[3]-box_shrink)  
                word = page.get_textbox(shrunk_box)

                # the hyphen is only able to capture truncated english words, but not Chinese
                """
                Page.search_for() behaves differently for Chinese and English text. 
                1. For English, "words" are separated by whitespaces, so if the "needle" found is not a complete word,
                but within a word, search_for() will return the needle with one character before and after it. This 
                means we have to worry about things like apostrophes, parentheses, commas etc. 
                2. For Chinese, there seems to be no such "word" separation, so search_for() will return the exact needle

                In order to capture truncated Chinese words, since our keywords only have two characters, for now 
                I'm simply checking if the length of the word is 1 and if it's a Chinese character. In the future,
                this may need to be changed, but for now it works. 
                """

                word = word.strip(common_punctuation)  # Remove common punctuation from start and end of word
                keyword_len = len(keyword)
                word_len = len(word)

                truncated = (word_len < keyword_len)

                if truncated:
                    
                    next_box = boxes[box_no+1]
                    shrunk_next_box = pymupdf.Rect(next_box[0], next_box[1]+box_shrink, next_box[2], next_box[3]-box_shrink)
                    next_word = page.get_textbox(shrunk_next_box).strip(common_punctuation)

                    if is_chinese_char(word):
                        word = word + '\n' + next_word
                    else:
                        word = word + next_word

                if keyword in word:

                    highlight = page.add_highlight_annot(box)
                
                    if truncated:
                        
                        next_box = boxes[box_no+1]

                        highlight = page.add_highlight_annot(next_box)

                    highlight.set_colors(stroke=highlight_color)
                    highlight.update()
                    total_highlights += 1
            
    # Save the modified PDF
    doc.save(output_pdf)
    doc.close()
    
    return total_highlights

def is_chinese_char(ch):
    return '\u4e00' <= ch <= '\u9fff'

def process_multiple_pdfs(input_folder, output_folder, keywords, highlight_color=(1, 1, 0)):
    """
    Process multiple PDF files in a folder.
    
    Args:
        input_folder: Folder containing input PDF files
        output_folder: Folder to save highlighted PDFs
        keywords: List of keywords to highlight
        highlight_color: RGB tuple (values 0-1)
    """
    # Create output folder if it doesn't exist
    Path(output_folder).mkdir(parents=True, exist_ok=True)
    
    # Clear existing files in output folder
    if os.path.exists(output_folder):
        for filename in os.listdir(output_folder):
            file_path = os.path.join(output_folder, filename)
            try:
                if os.path.isfile(file_path):
                    os.remove(file_path)
                elif os.path.isdir(file_path):
                    shutil.rmtree(file_path)
            except Exception as e:
                print(f"Warning: Could not delete {filename}: {str(e)}")
        print(f"Cleared existing files in {output_folder}\n")
    
    # Get all PDF files in input folder
    pdf_files = [f for f in os.listdir(input_folder) if f.lower().endswith('.pdf')]
    
    if not pdf_files:
        print(f"No PDF files found in {input_folder}")
        return
    
    print(f"Found {len(pdf_files)} PDF file(s) to process")
    print(repr(f"Keywords to highlight: {', '.join(keywords)}"))
    
    # Process each PDF
    for pdf_file in pdf_files:
        input_path = os.path.join(input_folder, pdf_file)
        output_path = os.path.join(output_folder, pdf_file)  # Save with same name
        
        try:
            highlights = highlight_keywords_in_pdf(
                input_path, 
                output_path, 
                keywords, 
                highlight_color
            )
            print(f"✓ {pdf_file}: {highlights} highlight(s) made")
        except Exception as e:
            print(f"✗ {pdf_file}: Error - {str(e)}")
    
    print(f"\nProcessing complete! Highlighted PDFs saved to: {output_folder}")

def get_input_folder():
    # 1. Check if user provided an argument
    if len(sys.argv) != 2:
        print("Error: Please provide the input folder path.")
        print("Usage: python script.py <input_folder>")
        sys.exit(1)

    folder = Path(sys.argv[1])

    # 2. Check if path exists
    if not folder.exists():
        print(f"Error: Path does not exist -> {folder}")
        sys.exit(1)

    # 3. Check if it's a folder
    if not folder.is_dir():
        print(f"Error: Path is not a folder -> {folder}")
        sys.exit(1)

    return folder

def load_keywords(file_path):
    path = Path(file_path)

    if not path.exists():
        print(f"Error: Keyword file not found -> {path}")
        return []

    with open(path, "r", encoding="utf-8") as f:
        keywords = [
            line.rstrip('\n').replace("\\n", "\n")
            for line in f
            if line.rstrip('\n')
        ]

    return keywords


# Example usage
if __name__ == "__main__":
    print(pymupdf.__doc__)  # Print the docstring of the pymupdf module to check version and info
    # Define your keywords (supports English, Chinese, and other s)
    # keywords = [  
    #     "NTU",
    #     "NBS",
    #     "Nanyang",
    #     "NIE",
    #     "RSIS",
    #     "Rajaratnam",
    #     "NUS",
    #     "National",
    #     "SMU", 
    #     "Management",
    #     "Ho Teck Hua",
    #     "Tan Eng Chye",
    #     "Lily Kong",
    #     "Christian Wolfrum",
    #     "Aaron Thean",
    #     "Alan Chan",
    #     "Kuipers", # Ernst J. Kuipers
    #     "Liu Bin",
    #     "Archan Misra",
    #     # Malay keywords
    #     "Teknologi",
    #     "Nasional",
    #     "Pengurusan",     
    #     # Chinese keywords
    #     "南洋",
    #     "南\n洋",
    #     "南大",
    #     "南\n大",
    #     "拉惹",  # RSIS
    #     "拉\n惹", # doesn't work
    #     "国际",
    #     "国\n际",
    #     "国立",  # NIE, NUS
    #     "国\n立",
    #     "国大",
    #     "国\n大",
    #     "管理",
    #     "管\n理",
    #     "管大",
    #     "管\n大"
    # ]
    
    keywords = load_keywords("keywords.txt")

    input_folder =  get_input_folder()
    # Define folders
    # Option 1: Relative paths (folders in same directory as script)
    # input_folder = "testing_input_pdfs"
    output_folder = "highlighted_pdfs"
    
    # Option 2: Absolute paths (specify full path to folders)
    # input_folder = r"C:\Users\YourName\Documents\PDFs"
    # output_folder = r"C:\Users\YourName\Documents\Highlighted_PDFs"
    
    # Option 3: Use home directory
    # input_folder = os.path.expanduser("~/Documents/input_pdfs")
    # output_folder = os.path.expanduser("~/Documents/highlighted_pdfs")
    
    # Optional: Change highlight color
    # Yellow: (1, 1, 0)
    # Green: (0, 1, 0)
    # Blue: (0, 0.5, 1)
    # Pink: (1, 0.75, 0.8)
    highlight_color = (1, 1, 0)  # Yellow
    
    
    # Process all PDFs
    process_multiple_pdfs(input_folder, output_folder, keywords, highlight_color)

