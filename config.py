

import vertexai
vertexai.init(project="stone-botany-397219", location="us-central1")

import os
home, _ = os.path.split(__file__)

website_cache_dir = os.path.join(home, 'website-cache')
os.makedirs(website_cache_dir, exist_ok=True)

import psycopg2
database = psycopg2.connect(
    database="postgres")
