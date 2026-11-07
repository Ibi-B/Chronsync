import sqlite3
import os
import glob
from lxml import etree

DB_PATH = "public/timeline.sqlite3"

def init_db():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Tuned for HTTP Range Requests on GitHub Pages
    cursor.execute("PRAGMA page_size = 4096;")
    cursor.execute("PRAGMA journal_mode = OFF;")
    cursor.execute("PRAGMA synchronous = 0;")
    
    cursor.execute("""
        CREATE TABLE channels (
            id TEXT PRIMARY KEY,
            name TEXT,
            logo TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE programs (
            channel_id TEXT,
            title TEXT,
            desc TEXT,
            start_time TEXT,
            stop_time TEXT,
            FOREIGN KEY(channel_id) REFERENCES channels(id)
        )
    """)
    
    cursor.execute("CREATE INDEX idx_programs_channel ON programs(channel_id);")
    cursor.execute("CREATE INDEX idx_programs_time ON programs(start_time, stop_time);")
    return conn

def parse_xml_to_db(conn, xml_file):
    cursor = conn.cursor()
    context = etree.iterparse(xml_file, events=('end',), tag=['channel', 'programme'])
    
    channels = []
    programs = []
    
    for event, elem in context:
        if elem.tag == 'channel':
            ch_id = elem.get('id')
            name_elem = elem.find('display-name')
            name = name_elem.text if name_elem is not None else "Unknown"
            logo_elem = elem.find('icon')
            logo = logo_elem.get('src') if logo_elem is not None else ""
            channels.append((ch_id, name, logo))
            
        elif elem.tag == 'programme':
            ch_id = elem.get('channel')
            start = elem.get('start')
            stop = elem.get('stop')
            title_elem = elem.find('title')
            title = title_elem.text if title_elem is not None else "Unknown"
            desc_elem = elem.find('desc')
            desc = desc_elem.text if desc_elem is not None else ""
            programs.append((ch_id, title, desc, start, stop))
            
        # Hard memory wipe to prevent CI/CD out-of-memory crashes
        elem.clear()
        while elem.getprevious() is not None:
            del elem.getparent()[0]

    cursor.executemany("INSERT OR IGNORE INTO channels VALUES (?, ?, ?)", channels)
    cursor.executemany("INSERT INTO programs VALUES (?, ?, ?, ?, ?)", programs)
    conn.commit()

if __name__ == "__main__":
    os.makedirs("public", exist_ok=True)
    conn = init_db()
    
    for file in glob.glob("raw_data/*.xml"):
        parse_xml_to_db(conn, file)
        
    conn.execute("VACUUM;")
    conn.close()
    print("Database built and optimized successfully.")
