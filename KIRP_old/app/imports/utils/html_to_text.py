from bs4 import BeautifulSoup

def html_to_text(html: str):
    soup = BeautifulSoup(html, "html.parser")
    return soup.get_text(separator="\n")
