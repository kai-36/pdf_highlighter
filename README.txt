This script is used to highlight specified keywords from PDF files using the PyMuPDF library
- As of writing this (27/5/2026), PyMuPDF 1.26.7 is used, as Page.search_for(needle) in newer versions is unable to capture truncated alphabetical words due to a bug

- Page.search_for(needle) scans the PDF file for a specified needle and returns a bounding box for each occurence of the needle, in the form of a Rect object. 
- For truncated words, Page.search_for(needle) will return two bounding boxes, each corresponding to one half of the word. 
- Page.search_for(needle) returns bounding boxes that are reasonably precise, which is relevant for highlighting
- Page.search_for(needle) is case-insensitive, and this is behaviour cannot be changed. It has to be used with Page.get_textbox(Rect) in order to filter the search results

- Page.get_textbox(Rect) returns the text from a specified Rect bounding box. Any text with a bounding box that intersects with the specified box will also be returned,
meaning the function will sometimes return adjacent characters, including punctuation. Sometimes, it will also return text from adjacent lines
- To deal with this, the box obtained from Page.search_for(needle) is made smaller by an arbitrary value {box_shrink}.
- Fow now, only the height is made smaller so that Page.get_textbox(Rect) doesn't get text from adjacent lines. The width could possibly be made smaller
so that adjacent characters do not get extracted as well. 
- Note that the box is only made smaller for Page.get_textbox(Rect). The original box obtained from Page.search_for(needle) is used for highlighting.


------------------------------------------------------------------

The keywords to highlight are specified in keywords.txt
- BE CAREFUL of leaving any whitespaces, the script will treat it as an intentional choice and it may affect the search 
