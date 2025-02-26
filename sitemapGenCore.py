import requests
import sqlite3
import hashlib
import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# Constants
SQLITE_NAME = 'sitemap.db'
XML_EXPORT_NAME = 'sitemap.xml'
SOURCES = ['https://www.w3schools.com/']

# Database setup
conn = sqlite3.connect(SQLITE_NAME)
cursor = conn.cursor()

# Create tables if not exist
cursor.execute('''
    CREATE TABLE IF NOT EXISTS sources (
        id INTEGER PRIMARY KEY,
        url TEXT NOT NULL
    );
''')

cursor.execute('''
    CREATE TABLE IF NOT EXISTS pages (
        id INTEGER PRIMARY KEY,
        source_id INTEGER NOT NULL,
        url TEXT NOT NULL,
        content_hash TEXT NOT NULL,
        createat TEXT NOT NULL,
        lastmod TEXT NOT NULL,
        FOREIGN KEY (source_id) REFERENCES sources (id)
    );
''')

# Function to extract base URL from a given URL
def get_base_url(url):
    """
    Extracts the base URL from a given URL.

    Args:
        url (str): The URL to extract the base URL from.

    Returns:
        str: The base URL.
    """
    parsed_url = urlparse(url)
    return f"{parsed_url.scheme}://{parsed_url.netloc}"

# Function to clean a URL
def clean_url(url, base_url):
    """
    Cleans a URL by removing unnecessary characters and adding the base URL if necessary.

    Args:
        url (str): The URL to clean.
        base_url (str): The base URL to use.

    Returns:
        str: The cleaned URL or None if the URL is invalid.
    """
    if url.startswith('#') or url.startswith('mailto:') or url.startswith('javascript:') or url.startswith('tel:') or url.startswith('sms:') or url.startswith('callto:') or url.startswith('mms:') or url.startswith('fax:') or url.startswith('skype:') or url.startswith('whatsapp:') or url == '/':
        return None
    if url.startswith('//'):
        url = f"{"https:"}{url}"
    if url.startswith('/'):
        url = f"{base_url}{url}"
    if not url.startswith('http://') and not url.startswith('https://'):
        url = f"{base_url}/{url}"
    if not url.startswith(base_url):
        return None
    return url

# Function to scan a source
def scan_source(page_url, base_url):
    """
    Scans a source URL and extracts URLs from the page.

    Args:
        page_url (str): The URL to scan.
        base_url (str): The base URL to use.

    Returns:
        None
    """
    if page_url.endswith('/'):
        page_url = page_url[:-1]
    print(f"Scan url: {page_url}")
    response = requests.get(page_url)
    soup = BeautifulSoup(response.content, 'html5lib')
    for link in soup.find_all('a', href=True):
        url = link['href']
        print(f"Raw url: {url}")
        url = clean_url(url, base_url)
        print(f"Formatted url: {url}")
        if url and url not in temp_url and url not in skip_url:
            if url.endswith('/'):
                temp_url.append(url[:-1])
            else:
                temp_url.append(url)

    # Hash the page content
    content_hash = hashlib.sha256(response.content).hexdigest()
    # Check if the page already exists in the database
    cursor.execute('SELECT * FROM pages WHERE url = ?', (page_url,))
    page = cursor.fetchone()
    if page is None:
        # Insert the page into the database with the current date as lastmod
        cursor.execute('INSERT INTO pages (source_id, url, content_hash, createat, lastmod) VALUES (?, ?, ?, ?, ?)', (1, page_url, content_hash, datetime.datetime.now().strftime("%Y-%m-%d"), datetime.datetime.now().strftime("%Y-%m-%d")))
    else:
        # If the hash value has changed, update the lastmod value
        if page[3] != content_hash:
            cursor.execute('UPDATE pages SET content_hash = ?, lastmod = ? WHERE url = ?', (content_hash, datetime.datetime.now().strftime("%Y-%m-%d"), page_url))

    # Remove current URL from temp_url
    skip_url.append(page_url)
    if page_url in temp_url:
        temp_url.remove(page_url)
    # Check if temp_url is not empty, then scan the first URL
    if temp_url:
        scan_source(temp_url[0], base_url)

# Function to generate the sitemap XML
def generate_sitemap_xml():
    """
    Generates the sitemap XML file.

    Returns:
        str: The sitemap XML content.
    """
    cursor.execute('SELECT * FROM pages ORDER BY url')
    pages = cursor.fetchall()
    sitemap_xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap_xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for page in pages:
        sitemap_xml += '  <url>\n'
        sitemap_xml += '    <loc>' + page[2] + '</loc>\n'
        sitemap_xml += '    <lastmod>' + page[5] + '</lastmod>\n'
        sitemap_xml += '  </url>\n'
    sitemap_xml += '</urlset>\n'
    return sitemap_xml

# Main program
if __name__ == '__main__':
    # Initialize temp_url and skip_url
    temp_url = []
    skip_url = []

    # Scan sources
    for source in SOURCES:
        base_url = get_base_url(source)
        scan_source(source, base_url)

    # Generate sitemap XML
    sitemap_xml = generate_sitemap_xml()

    # Save sitemap XML to file
    with open(XML_EXPORT_NAME, 'w') as f:
        f.write(sitemap_xml)

    # Close database connection
    conn.close()

    print("Sitemap generated successfully!")
