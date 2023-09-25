
import os
home, _ = os.path.split(__file__)

website_vectordb_cache_dir = os.path.join(home, 'website_vectordb_cache')
os.makedirs(website_vectordb_cache_dir, exist_ok=True)


