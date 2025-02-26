import requests
import sqlite3
import hashlib
import datetime
from bs4 import BeautifulSoup
from urllib.parse import urlparse

# Set up SQLite database
conn = sqlite3.connect('sitemap.db')
cursor = conn.cursor()

# Define schema
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

# Define a function to scan a source
def scan_source(page_url):
    if page_url.endswith('/'):
        page_url = page_url[:-1]
    print('Scan url: {}'.format(page_url))
    # Use requests to fetch the page
    response = requests.get(page_url)
    # Parse the HTML content using BeautifulSoup
    soup = BeautifulSoup(response.content, 'html5lib')
    # Extract URLs from the page
    for link in soup.find_all('a', href=True):
        url = link['href']
        # Clean the URL using the clean function from SiteMapGen.py
        url = clean_url(url)
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
    
    # remove current url from temp_url
    skip_url.append(page_url)
    temp_url.remove(page_url)
    # check temp_url is this empty if it is not empty then scan the first url
    if len(temp_url) > 0:
        scan_source(temp_url[0])

def clean_url(url):
    # print(' {} | {}'.format(url,base_url))
    # print(' {} | {}'.format(url,base_url))
    # base_url = get_base_url(base_url)
    print('{}'.format(url))

    # This function is copied from SiteMapGen.py
    if url.startswith('#') or url.startswith('mailto:') or url.startswith('javascript:') or url.startswith('tel:') or url.startswith('sms:') or url.startswith('callto:') or url.startswith('mms:') or url.startswith('fax:') or url.startswith('skype:') or url.startswith('whatsapp:') or url == '/':
        return None
    if url.startswith('/'):
        url = '{}{}'.format(base_url, url)
    if url.startswith('http://') != True and url.startswith('https://') != True:
        url = '{}/{}'.format(base_url, url)
    if url.startswith(base_url) is False:
        return None
    return url

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


# Define a function to generate the sitemap XML
def generate_sitemap_xml():
    # Query the database for all pages
    cursor.execute('SELECT * FROM pages ORDER BY url')
    pages = cursor.fetchall()
    # Generate the sitemap XML
    sitemap_xml = '<?xml version="1.0" encoding="UTF-8"?>\n'
    sitemap_xml += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    for page in pages:
        sitemap_xml += f'  <url>\n'
        sitemap_xml += f'    <loc>{page[2]}</loc>\n'
        sitemap_xml += f'    <lastmod>{page[5]}</lastmod>\n'
        sitemap_xml += f'  </url>\n'
    sitemap_xml += '</urlset>\n'
    return sitemap_xml

# Define a variable to store the temp url
temp_url = []
skip_url = []
base_url = ''

# Scan a few sources
sources = ['https://homester.hk', 'https://homester.hk/blog', 'https://homester.hk/page/team']
for source in sources:
    temp_url.append(source)
    base_url = source
    scan_source(source)

# Generate the sitemap
sitemap_xml = generate_sitemap_xml()
print(sitemap_xml)

# Save the sitemap XML to a file
with open('sitemap.xml', 'w') as f:
    f.write(sitemap_xml)

print('Sitemap generated and saved to sitemap.xml')
conn.commit()