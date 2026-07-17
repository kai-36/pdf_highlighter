import pymupdf
import argparse
import os
import sys
from pathlib import Path
from concurrent.futures import ProcessPoolExecutor
from tqdm import tqdm

# global variables for worker processes
_worker_keywords = None
_worker_color = None

def highlight_keywords_in_pdf(input_pdf_path, output_pdf_path, keywords, highlight_color=(1, 1, 0)):
    """
    Highlights specified keywords in a PDF file with case-sensitive matching.
    
    Args:
        input_pdf_path: Path to the input PDF file
        output_pdf_path: Path to save the highlighted PDF
        keywords: List of keywords to highlight
        highlight_color: RGB tuple (values 0-1), default is yellow

    Return:
        Total number of highlighted keywords
    """
    shrink_proportion = 0.3  # Amount to shrink the box to avoid get_textbox from capturing words from adjacent lines
    common_punctuation = "\"',.()[]{}!?;:-"  # Common punctuation to strip from words for matching
    # Open the PDF
    doc = pymupdf.open(input_pdf_path)
    
    # Track total highlights made
    total_highlights = 0
    truncated = False
    # Iterate through each page
    for page in doc:

        """
        Page.search_for() internally creates a TextPage everytime it is called. We can reduce execution
        time by creating the TextPage first and then passing it to Page.search_for() so that it doesn't
        have to recreate the same TextPage for each keyword
        """

        textpage = page.get_textpage(flags=pymupdf.TEXTFLAGS_SEARCH)

        for keyword in keywords:

            boxes = page.search_for(keyword, textpage=textpage)

            for box_no, box in enumerate(boxes):
            
                if truncated:
                    truncated = False
                    continue
                
                box_height = box[3] - box[1]
                box_shrink = box_height * shrink_proportion / 2

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
                    highlight.set_colors(stroke=highlight_color)
                    highlight.update()
                
                    if truncated:
                        
                        next_box = boxes[box_no+1]

                        highlight = page.add_highlight_annot(next_box)
                        highlight.set_colors(stroke=highlight_color)
                        highlight.update()
    
                    total_highlights += 1
            
    # Save the modified PDF
    doc.save(output_pdf_path)
    doc.close()
    
    return total_highlights

def is_chinese_char(ch):
    return '\u4e00' <= ch <= '\u9fff'

def parse_arguments():
    parser = argparse.ArgumentParser(description="Highlight keywords across all PDFs in a folder tree.")
    parser.add_argument("input_folder", help="Path to the folder containing subfolders of PDFs")
    parser.add_argument("-v", "--verbose", action="store_true", help="Print per-file results")
    return parser.parse_args()

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
        sys.exit(1)

    with open(path, "r", encoding="utf-8") as f:
        keywords = [
            line.rstrip('\n').replace("\\n", "\n")
            for line in f
            if line.rstrip('\n')
        ]

    return keywords

def init_worker(keywords, highlight_color):
    global _worker_keywords, _worker_color

    _worker_keywords, _worker_color = keywords, highlight_color

def extract_tasks(input_folder_path, output_folder_path):
    # returns the input and output path for each PDF 
    tasks = []

    input_folders = [f for f in input_folder_path.iterdir() if f.is_dir()]
    
    for folder in input_folders:

        output_subfolder = output_folder_path / folder.name
        output_subfolder.mkdir(parents=True, exist_ok=True)

        pdf_files = [f for f in folder.iterdir() if f.suffix == ".pdf"]
        
        for pdf_file in pdf_files:
            
            input_pdf_path = pdf_file
            output_pdf_path = output_subfolder / pdf_file.name
            tasks.append((input_pdf_path, output_pdf_path))

    return tasks

def process_pdf(args):
    input_pdf_path, output_pdf_path = args

    try:
        highlights = highlight_keywords_in_pdf(
            input_pdf_path, 
            output_pdf_path, 
            _worker_keywords, 
            _worker_color
        )
        
        return (input_pdf_path, highlights, None)
    
    except Exception as e:
        return(input_pdf, None, str(e))


# Example usage
if __name__ == "__main__":
    print(pymupdf.__doc__)  # Print the docstring of the pymupdf module to check version and info
    
    keywords = load_keywords("keywords.txt")

    args = parse_arguments()
    
    input_folder_path = Path(args.input_folder)
    
    verbose = args.verbose

    # Define folders
    # input_folder = "testing_input_pdfs"
    script_dir = Path(__file__).resolve().parent
    output_folder_path = script_dir / ("highlighted_" + input_folder_path.name)

    # Change highlight color
    # Yellow: (1, 1, 0)
    # Green: (0, 1, 0)
    # Blue: (0, 0.5, 1)
    # Pink: (1, 0.75, 0.8)
    highlight_color = (0, 1, 0) # Green

    tasks = extract_tasks(input_folder_path, output_folder_path)
    
    max_workers = max(1, os.cpu_count() - 2)
    error_count = 0
    problematic_pdfs = []

    with ProcessPoolExecutor(initializer=init_worker, initargs=(keywords, highlight_color), max_workers=max_workers) as executor:

        results = executor.map(process_pdf, tasks)

        for input_pdf, highlights, error in tqdm(results, total=len(tasks), desc="Highlighting PDFs", unit="pdf"):
            
            if error:
                if verbose:
                    tqdm.write(f"✗ {input_pdf}: Error - {error}")

                error_count += 1
                problematic_pdfs.append((input_pdf, error))

            elif highlights == 0:
                if verbose:
                    tqdm.write(f"✗ {input_pdf}: Error - {highlights} highlight(s) made")

                error_count += 1

                error = f"{highlights} highlight(s) made"
                problematic_pdfs.append((input_pdf, error))

            elif verbose:
                tqdm.write(f"✓ {input_pdf}: {highlights} highlight(s) made")

    print(f"\nProcessing complete! Highlighted PDFs saved to: {output_folder_path}")
    print(f"\nSuccessfully processed {len(tasks)-error_count}/ {len(tasks)} PDFs")

    if problematic_pdfs:
        print("\nProblematic PDFs: ")

        for pdf, error in problematic_pdfs:
            print(f"\n{pdf}: {error}")
