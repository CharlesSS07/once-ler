

from . import text_preprocessing
import config
import tools

import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from markdownify import markdownify
#import re
#import pandas as pd
import os
import glob
import json
#import math
#import time
from typing import Generator, List, Tuple, Optional
import numpy as np
#from tqdm.auto import tqdm
#import yaml
from threading import Thread
import subprocess
from datetime import datetime
import shutil
import tempfile

from sentence_transformers import SentenceTransformer
from sentence_transformers.util import cos_sim

# create necessary databases if they don't already exist
import psycopg2

cursor = config.database.cursor()
config.database.autocommit = True
try:
    cursor.execute('DROP DATABASE websites;') # temporary
    config.database.commit()
except Exception as e:
    config.database.rollback()
    print('no websites db found')
    print(e)

try:
    cursor.execute('CREATE DATABASE websites;')
    config.database.commit()
except psycopg2.errors.DuplicateDatabase:
    pass
del cursor

database = psycopg2.connect(
    database="websites")
cursor = database.cursor()

cursor.execute(
'''CREATE TABLE IF NOT EXISTS urls (
    id serial PRIMARY KEY,
    url VARCHAR(500) NOT NULL UNIQUE,
    cache_file VARCHAR(500),
    last_cache_timestamp TIMESTAMP
)''') # url VARCHAR(500) CHARACTER SET 'ascii' COLLATE 'ascii_general_ci' NOT NULL UNIQUE,

cursor.execute(
'''CREATE TABLE IF NOT EXISTS webpage_summaries (
    id INT NOT NULL PRIMARY KEY,
    summary VARCHAR(3000)
)''')

database.commit()
del database, cursor

# stole some ways from the only example of google gecko embedding I could find, good source https://colab.research.google.com/github/GoogleCloudPlatform/vertex-ai-samples/blob/main/notebooks/official/matching_engine/sdk_matching_engine_create_stack_overflow_embeddings_vertex.ipynb#scrollTo=9b01baa906b5

class CachedWebsite():

    class CachedWebpageLookupException(Exception):
        pass

    class WebpageNotCached(CachedWebpageLookupException):
        pass
    
    def __init__(self, hostname:str):
        self.hostname = hostname
        self.DEFAULT_DIRECTORY_INDEX_PAGE_FILENAME = 'direrctory-index-page.html'
        self.valid = False
#        if not os.path.exists(self.get_website_cache_dir()):
#            self.__scrape()
#        else:
#            self.valid = True
        
    def valid_cache(self):
        return self.valid # maybe check last cacheing time from database
    
    def get_website_cache_dir(self):
        return os.path.join(config.website_cache_dir, self.hostname)
    
    def get_cached_webpage(self, url:str, page_hash='abcd'):
        # TODO: look up urls, and their cache_file in a database, using a hash computed by client js
        # ^ much more robust than current approach
        # TODO: use page_hash to look up the page by content, and then url translation as backup
        URL = urlparse(url)
        if URL.hostname!=self.hostname:
            raise CachedWebsite.CachedWebpageLookupException(f'url hostname does not match website hostname: {URL.hostname}!={self.hostname}')
        
        page = None
        
        cache_file = os.path.join(config.website_cache_dir, url.lstrip('https://'))
        
        if os.path.isfile(cache_file):
            page = CachedWebpage(
                url,
                cache_file,
                self)
        
        cache_file = os.path.join(config.website_cache_dir, URL.hostname, URL.path[1:])
        
        if os.path.isdir(cache_file):
            if os.path.exists(os.path.join(cache_file, self.DEFAULT_DIRECTORY_INDEX_PAGE_FILENAME)):
                page = CachedWebpage(
                    url,
                    os.path.join(cache_file, self.DEFAULT_DIRECTORY_INDEX_PAGE_FILENAME),
                    self)
            if len(glob.glob(os.path.join(cache_file, '*')))==1:
                print('Cache file not easily identified!!!')
                print(url)
                print(cache_file)
                page = CachedWebpage(
                    url,
                    glob.glob(os.path.join(cache_file, '*'))[0],
                    self)
        
        if os.path.isfile(cache_file):
            page = CachedWebpage(url, cache_file, self)
        
        if page==None:
            print('No cache found for ' + url)
            print('Creating one')
            path, filename = os.path.split(cache_file)
            os.makedirs(path, exist_ok=True)
            # could use wget with --force-directories
            
            if os.path.isdir(cache_file):
                cache_file = os.path.join(cache_file, self.DEFAULT_DIRECTORY_INDEX_PAGE_FILENAME)
            
            with open(cache_file, 'w') as f:
                f.write(requests.get(url).text)
                f.flush()
            page = CachedWebpage(
                url,
                cache_file,
                self)
            self.valid = True
            return page # This just-in-time downloading was added to make things work for demo
#            raise CachedWebsite.WebpageNotCached('No cache found for ' + url)
        
        if not page.get_page_hash()==page_hash:
            self.valid = False
        
        return page
    
    def __scrape(self):
        try:
            shutil.rmtree(self.get_website_cache_dir())
        except OSError as e:
            print("Error: %s - %s." % (e.filename, e.strerror))
        p = subprocess.run([
            'wget',
            '--recursive', # wget should have a default max recusion level of 5 i think
            '--default-page', self.DEFAULT_DIRECTORY_INDEX_PAGE_FILENAME,
            '--adjust-extension', # make sure html files have a .html suffix
            '--convert-links', # make sure links in the files now point to the local cloned files
            '--directory-prefix', config.website_cache_dir,
            '--follow-tags=a', # avoid downloading images, css, etc.
            '--ignore-tags=img,link,script',
            '--reject', "'*.js,*.css,*.ico,*.gif,*.jpg,*.jpeg,*.png,*.mp3,*.tgz,*.flv,*.avi,*.mpeg,*.iso'",
            'https://'+self.hostname+'/'
        ])
        if p.returncode!=0 and p.returncode!=8:
            raise subprocess.CalledProcessError(p.returncode, p.cmd)
        self.valid = True
        
        self.__cache(self.get_website_cache_dir())
    
    def __cache(self, dir):
        # DFS run through whole website scrape directory recursivley, and cache the page
        for path, dirs, files in os.walk(dir):
            page_path = path.replace(self.get_website_cache_dir(), '')
            for file in files:
                url = f'https://{"/".join([self.hostname.strip("/"), page_path.strip("/"), file.strip("/")])}'.replace('//', '/') # TODO: fix this up...
                print(url, os.path.join(path, file))
                webpage = CachedWebpage(url, os.path.join(path, file), self)
            for directory in dirs:
                self.__cache(directory)

class CachedWebpage():
    
    class CachedWebpageHasOldHash(Exception):
        pass
    
    def __init__(self, url:str, cache_file:str, parent_site:CachedWebsite):
        self.url = url
        self.cache_file = cache_file
        self.parent_site = parent_site
        
        self.websites_connection = psycopg2.connect(
            database="websites")
        self.cursor = self.websites_connection.cursor()
        
        self.cursor.execute(
            '''INSERT INTO urls(url, cache_file, last_cache_timestamp) VALUES (%s, %s, %s)
ON CONFLICT (url) DO UPDATE
SET last_cache_timestamp=%s, cache_file=%s
WHERE urls.url=%s;''',
            (
                self.url,
                self.get_website_cache_file(),
                datetime.now(),
                datetime.now(),
                self.get_website_cache_file(),
                self.url
            )
        )
        self.websites_connection.commit()
    
    def get_website_cache_file(self):
        return self.cache_file
    
    def get_raw_html(self):
        if hasattr(self, 'raw_html'):
            return self.raw_html
            
        with open(self.get_website_cache_file(), 'rb') as f:
            self.raw_html = f.read()
        return self.get_raw_html()
    
    def get_page_hash(self):
        return 'abcd' # TODO: fix this
    
    def get_markdown(self):
        if hasattr(self, 'html_markdown'):
            return self.html_markdown
        self.html_markdown = text_preprocessing.clean_markdown(
            markdownify(str(self.get_bs4_html_object().find('body')))
        )
        return self.get_markdown()
    
    def get_bs4_html_object(self):
        if hasattr(self, 'document'):
            return self.document
        
        self.document = BeautifulSoup(self.get_raw_html(), features="lxml")
        if not self.document.find(id='chatinterface')==None:
            self.document.find(id='chatinterface').decompose() # remove the chat interface
        
        for element in self.document.find_all('script'):
            element.decompose()
        for element in self.document.find_all('noscript'):
            element.decompose()
        for element in self.document.find_all('style'):
            element.decompose()
        
        return self.get_bs4_html_object()
    
    def get_metadata(self):
        if hasattr(self, 'metadata'):
            return self.metadata
        document = self.get_bs4_html_object()
        # parse out links, buttons, etc.
        metas =   list(sorted(set([ meta.attrs['content'].strip() for meta in document.find_all('meta') if 'name' in meta.attrs and 'description' in meta.attrs['name'] ])))
        titles =  list(sorted(set([ e.get_text().strip() for e in document.find_all('title') ])))
        links =   { l['href']:str(l) for l in document.find_all('a', href=True) }
        buttons = list(sorted(set([ b.text.strip() for b in document.find_all('button') ]))) # maybe get the surrounding text too?
        
        self.metadata = {
            'titles': titles,
            'descriptions': metas,
            'links': links
        }
        
        return self.get_metadata()

class SummarizedCachedWebpage():
    
    def __init__(self, cached_webpage: CachedWebpage):
        self.cached_webpage = cached_webpage
    
    def __generate_summary(self):
        metadata = self.cached_webpage.get_metadata()
        chunks = list(text_preprocessing.overlap_chunk(self.cached_webpage.get_markdown(), 312, 100))
        self.page_summary = tools.summarize_chunks_collapsing([
            'This is a webpage located at: ' + self.cached_webpage.url,
            *metadata['descriptions'],
            *metadata['titles'],
            *chunks
        ])
        return self.page_summary
    
    def get_summary(self):
        
        # see if summary is cached in memory
        if hasattr(self, 'page_summary'):
            return self.page_summary
        
        # get the summary from the database IF it has been cached there
        self.cached_webpage.cursor.execute(
            'SELECT * FROM webpage_summaries WHERE id IN (SELECT id FROM urls WHERE urls.url=%s)', (self.cached_webpage.url,))
        summary_row = self.cached_webpage.cursor.fetchone()
        self.cached_webpage.websites_connection.commit()
        
        if not summary_row is None:
            # summary exists, cache in memory and return
            self.page_summary = summary_row[1]
            return self.get_summary()
        
        # generate the sumary since it has not been cached
        self.__generate_summary()
        
        # save the summary to the database in table webpage_summaries with same id as in urls table
        self.cached_webpage.cursor.execute(
            'INSERT INTO webpage_summaries (id, summary) SELECT id, %s FROM urls WHERE urls.url=%s', (self.page_summary, self.cached_webpage.url))
        self.cached_webpage.websites_connection.commit()
        
        return self.get_summary()

class EmbeddedCachedWebpage():
    
    def __init__(self, cached_webpage: CachedWebpage):
        self.cached_webpage = cached_webpage
        self.embedding_model = SentenceTransformer('thenlper/gte-large')
        self.embedding_simality_metric = lambda a,b: np.array(cos_sim(a, b))[0]
    
    def vector_search(self, text, n=4, thresh=0.65):
        if hasattr(self, 'embeddings') and hasattr(self, 'chunks'):
            chunk_embedding = self.embedding_model.encode([text])[0].astype(np.float64)
            # brute force check distance from every other chunk to this text
            print(chunk_embedding.dtype, self.embeddings[0].dtype)
            chunk_simularity = self.embedding_simality_metric(
                chunk_embedding.astype(np.float32),
                self.embeddings
            )
            chunk_rank_order = np.argsort(chunk_simularity)
            return np.array(self.chunks)[chunk_rank_order][len(chunk_rank_order)-n:][::-1]
        
        chunks = list(text_preprocessing.overlap_chunk(self.cached_webpage.get_markdown(), 312, 100))
              
        self.embeddings = []
        self.chunks = []
        for c, e in zip(chunks, self.embedding_model.encode(chunks)):
            self.embeddings.append(e)
            self.chunks.append(c)
        
        return self.vector_search(text)

class EmbeddedCachedWebsite():

    def __init__(self, cached_site:CachedWebsite):
        self.cached_site = cached_site

    def embed_site(self):
        pass

    def vector_search(self, text):
        pass


import pandas as pd
from tqdm.auto import tqdm
import traceback
import threading
import collections
import concurrent.futures
import gc

class LocalCustomEmbeddedCachedWebsite():

    def __init__(self, cached_site:CachedWebsite):
        self.cached_site = cached_site
        
        self.embedding_model = SentenceTransformer('thenlper/gte-large')
        self.embedding_simality_metric = lambda a,b: np.array(cos_sim(a, b))[0]
    
    def get_embedding_file(self):
        return os.path.join(config.website_cache_dir, self.cached_site.hostname+'.embedding.csv')
    
    def get_metadata_file(self):
        return os.path.join(config.website_cache_dir, self.cached_site.hostname+'.metadata.csv')
    
    def embed_site(self):
        
        if hasattr(self, 'embedding') or os.path.exists(self.get_embedding_file()):
            return
        
        metadata = pd.DataFrame(columns=['chunk', 'url'])
#        embedding = pd.DataFrame(columns=[*list(range(1, 1024+1))])
        
        def embed_page(url):
            
            results = []
            try:
                
                webpage = self.cached_site.get_cached_webpage(url)
#                    metadata = self.get_metadata()
                chunks = list(text_preprocessing.overlap_chunk(webpage.get_markdown(), 312, 100))
                
                for c, e in zip(chunks, self.embedding_model.encode(chunks)):
                    results.append({
                        "embedding": list(e.astype(float)),
                        "chunk": c,
                        'url': url
                    })
                
            except Exception as e:
                traceback.print_exc()
            
            return results
        
        idx = 0
        
        with open(self.get_embedding_file(), 'a') as e:
            for path, dirs, files in tqdm(
                    list(os.walk(self.cached_site.get_website_cache_dir())),
                    desc='Pages ==> Embedded Pages'
                ):
                
                try:
                    page_path = path.replace(self.cached_site.get_website_cache_dir(), '')
                    
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        futures = []
                        for file in files:
                            url = 'https://'+f'{"/".join([self.cached_site.hostname.strip("/"), page_path.strip("/"), file.strip("/")])}'.replace('//', '/') # TODO: fix this up...
                            futures.append(executor.submit(embed_page, url))
                        
                        for future in concurrent.futures.as_completed(futures):
                            lines = []
                            for row in future.result():
    #                            embedding.loc[idx] = {i:ei for i,ei in enumerate(row['embedding'])}
                                lines.append(','.join([str(i) for i in row['embedding']])+'\n')
                                metadata.loc[idx] = {'chunk': row['chunk'], 'url':row['url']}
                                idx+=1
                            
                            e.writelines(lines)
                            e.flush()
                            del row, future, lines
                            gc.collect()
                        
                        del futures
                        gc.collect()
                except Exception as e:
                    traceback.print_exc()
        
#        embedding.to_csv(self.get_embedding_file()) # same format google uses: id,1,2,3,...,N
        metadata.to_csv(self.get_metadata_file()) # column oriented database. same index

    def vector_search(self, text, n=4, thresh=0.65):
        if hasattr(self, 'embedding'):
            chunk_embedding = self.embedding_model.encode([text])[0].astype(np.float64)
            # brute force check distance from every other chunk to this text
            chunk_simularity = self.embedding_simality_metric(
                chunk_embedding,
                self.embedding
            )
            chunk_rank_order = np.argsort(chunk_simularity)
            return np.array(self.metadata.chunk)[chunk_rank_order][len(chunk_rank_order)-n:][::-1]
        
        self.embedding = []
        with open(self.get_embedding_file(), 'r') as e:
            for line in e.readlines():
                self.embedding.append(np.array(line.split(',')).astype(float))
        
        self.metadata = pd.read_csv(self.get_metadata_file())
        
        return self.vector_search(text, n, thresh)

#def gecko_embedding_generator(text_iterator):
#

#class GoogleCloudEmbeddedCachedWebpage(EmbeddedCachedWebpage):
#
#    def __init__(self, cached_site:CachedWebsite):
#        super(GoogleCloudEmbeddedCachedWebpage, self).__init__(cached_site, embedding_generator)
#
#        # embedding_funciton should be a callable which takes a iterable of strings to embed, and returns a list/generator of corresponding embeddings. it might batch/split up/call apis/do whatever
#        self.embedding_generator = embedding_generator
#
#    def embed_pages(self):
#
#        for path, dirs, files in os.walk(dir):
#            page_path = path.replace(self.get_website_cache_dir(), '')
#            for file in files:
#                url = f'https://{"/".join([self.hostname.strip("/"), page_path.strip("/"), file.strip("/")])}'.replace('//', '/') # TODO: fix this up...
#                print(url, os.path.join(path, file))
#                webpage = CachedWebpage(url, os.path.join(path, file), self)
##                metadata = self.get_metadata()
#                chunks = text_preprocessing.overlap_chunk(webpage.get_markdown(), 312, 100)
#
#                with tempfile.NamedTemporaryFile(suffix='.json') as fh:
#                    for i in self.embedding_generator(chunks):
#                        # save to google vector store
#                        fh.writelines([
#                            json.dumps(
#                                {
#                                    "id": f'{i:03d}:'+self.get_website_cache_file(),
#                                    "embedding": [ str(ei) for ei in e.astype(float)]
#                                }
#                            ) + '\n'
#                        ])
#
#                    fh.flush()
#
#                    # upload page embeddings json to remote google cloud bucket
#                    print(' '.join(['gsutil', '-m', 'cp', '-r', os.path.join(fh.name.strip('/'), '*'), os.path.join('gs:vectorized_websites', fh.name.strip('/')).strip('/')+'/'])
#                    subprocess.run([
#                        'gsutil', '-m', 'cp', '-r', os.path.join(fh.name.strip('/'), '*'), os.path.join('gs:vectorized_websites', fh.name.strip('/')).strip('/')+'/'
#                    ], check=True)
#
#        DISPLAY_NAME = "uu_webpages"
#        DESCRIPTION = "embeddings of the uu web pages"
#
#        DIMENSIONS = 768
#
#        tree_ah_index = aiplatform.MatchingEngineIndex.create_tree_ah_index(
#            display_name=DISPLAY_NAME,
#            contents_delta_uri=remote_folder,
#            dimensions=DIMENSIONS,
#            approximate_neighbors_count=150,
#            distance_measure_type="DOT_PRODUCT_DISTANCE",
#            leaf_node_embedding_count=500,
#            leaf_nodes_to_search_percent=80,
#            description=DESCRIPTION,
#        )
#
#
#    def vector_search(self, text):
#        pass

#class ProcessedWebpageCache():
#
#    def __init__(self, page:CachedWebpage):
#
#        self.page = page
#
#        self.embedding_model = SentenceTransformer('thenlper/gte-large')
#        self.embedding_simality_metric = lambda a,b: np.array(cos_sim(a, b))[0]
#
#    def load(self):
#        if not os.path.exists(self.cache_file):
#            raise ProcessedWebpageCache.WebpageNotCached('No cache for ' + self.url)
#        with open(self.cache_file, 'r') as f:
#            self.raw_html = f.read()
#
#        # check if url is in urls db
#        cursor.execute('SELECT count(1) > 0 FROM urls WHERE url = %s', (self.url,))
#        result = cursor.fetchone()
#        cursor.commit()
#        if not result:
#            raise ProcessedWebpageCache.WebpageNotCached('No cache for ' + self.url)
#        return self
#
##    def get_chunks(self):
##        if hasattr(self, 'chunks'):
##            return self.chunks
##        max_chunk_size = 312 # make sure things add up to 512, which is the window size of embedding model...
##        self.chunks = list(text_preprocessing.overlap_chunk(self.get_markdown(), max_chunk_size, 100)) # 100 + 312 + 100 = 512
##        return self.get_chunks()
#
#
#
#    def get_chunk_embeddings(self):
#        if hasattr(self, 'chunk_embeddings'):
#            return self.chunk_embeddings
#        chunks = self.get_chunks()
#        self.chunk_embeddings = [] # TODO: store in google cloud
#        with open(self.get_filepath('content.md.embeddings.json'), 'a') as f:
#            for i, (c, e) in tqdm(
#                enumerate(zip(chunks, self.embedding_model.encode(chunks))),
#                total=len(chunks),
#                desc="Chunk --> Embedding"
#            ):
#                self.chunk_embeddings.append(e)
#                f.writelines([
#                    json.dumps(
#                        {
#                            'i':i,
#                            "embedding": [ str(ei) for ei in e.astype(float)],
#                            "chunk": c
#                        }
#                    ) + '\n'
#                ])
#        return self.get_chunk_embeddings()
#
#    def get_similar_chunks(self, chunk, n=4, thresh=0.65):
#        # should check chunk is < 512 tokens, etc.
#        embeddings = self.get_chunk_embeddings()
#        chunk_embedding = self.embedding_model.encode([chunk])[0].astype(float)
#        chunk_rank = self.embedding_simality_metric(chunk_embedding, np.array(embeddings).astype(np.float64))
#        chunk_rank_order = np.argsort(chunk_rank)[len(chunk_rank)-n:][::-1]
#        return np.array(self.chunks)[chunk_rank_order[chunk_rank[chunk_rank_order]>thresh]]

#def cache(url:str):
#
#    try:
#        cache = ProcessedWebpageCache(url).load()
#    except ProcessedWebpageCache.WebpageNotCached:
#        cache = ProcessedWebpageCache(url).setup(page_readability_html, page_document_html)
#
#    cache.get_summary()
#    cache.get_chunk_embeddings()

def load(url: str):
    
    # check if website_dir exists...
    
    embeddings = pd.DataFrame(columns=['embedding', 'chunk'])
    with open(get_website_cache_file(url, 'content.readability.md.embeddings.json'), 'r') as f:
        for i, line in enumerate(f.readlines()):
            embeddings.loc[i] = json.loads(line)
            embeddings.loc[i].embedding = np.array(embeddings.loc[i].embedding).astype(float)
    return embeddings
#    return pd.read_pickle(os.path.join(get_website_cache(url), 'embeddings.pkl'))
    
