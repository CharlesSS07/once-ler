

from . import text_preprocessing

import config
import tools

import requests
from urllib.parse import urlparse
from bs4 import BeautifulSoup
from markdownify import markdownify
import re
import pandas as pd
import os
import glob
import json
import math
import time
from typing import Generator, List, Tuple, Optional
import numpy as np
from tqdm.auto import tqdm
import yaml
from threading import Thread

from sentence_transformers import SentenceTransformer
embedding_model = SentenceTransformer('thenlper/gte-large')


def get_website_cache_file(url:str, filename):
    
    URL = urlparse(url)
    
    sep = '|'
    
    path = [URL.hostname, *[ f for f in URL.path.split('/') if len(f)!=0 ], '.'+filename]
    
    website_dir = os.path.join(config.website_db_dir, sep.join(path)) # strip leading / off of path
    
    return website_dir

# stole some ways from the only example of google gecko embedding I could find, good source https://colab.research.google.com/github/GoogleCloudPlatform/vertex-ai-samples/blob/main/notebooks/official/matching_engine/sdk_matching_engine_create_stack_overflow_embeddings_vertex.ipynb#scrollTo=9b01baa906b5


class ProcessedWebpageCache():

    class WebpageNotCached(Exception):
        pass
    
    def __init__(self, url:str):
        self.url = url
        
    def get_filepath(self, filename:str):
        return get_website_cache_file(self.url, filename)
    
    def get_file_content(self, filename:str):
        with open(self.get_filepath(filename), 'r') as f:
            return f.read()
    
    def setup(self, page_readability_html:str, page_document_html:str):
        
        self.page_readability_html = page_readability_html
        self.page_document_html = page_document_html
            
        with open(self.get_filepath('content.html'), 'w') as f:
            f.write(page_document_html)
        
        with open(self.get_filepath('content.readability.html'), 'w') as f:
            f.write(page_readability_html)
        
        return self
    
    def load(self):
        if len(glob.glob(self.get_filepath('*')))==0:
            raise ProcessedWebpageCache.WebpageNotCached(self.url)
        return self
    
    def get_raw_html(self):
        if hasattr(self, 'page_document_html'):
            return self.page_document_html
        self.page_document_html = self.get_file_content('content.html')
        return self.get_raw_html()
    
    def get_raw_html_markdown(self):
        if hasattr(self, 'page_document_html_markdown'):
            return self.page_document_html_markdown
        with open(self.get_filepath('content.html.md'), 'w') as f:
            f.write(text_preprocessing.clean_markdown(
                markdownify(str(self.get_bs4_html_object().find('body')))
            ))
        self.page_document_html_markdown = self.get_file_content('content.html.md')
        return self.get_raw_html()
    
    def get_bs4_html_object(self):
        if hasattr(self, 'document'):
            return self.document
        
        self.document = BeautifulSoup(self.get_raw_html(), features="lxml")
        self.document.find(id='chatinterface').decompose() # remove the chat interface
        
        for element in self.document.find_all('script'):
            element.decompose()
        for element in self.document.find_all('noscript'):
            element.decompose()
        for element in self.document.find_all('style'):
            element.decompose()
        
        return self.get_bs4_html_object()
        
    def get_readability_html(self):
        if hasattr(self, 'page_readability_html'):
            return self.page_readability_html
        self.page_readability_html = self.get_file_content('content.readability.html')
        return self.get_readability_html()
        
    def get_readability_html_markdown(self):
        if hasattr(self, 'page_readability_html_markdown'):
            return self.page_readability_html_markdown
        with open(self.get_filepath('content.readability.html.md'), 'w') as f:
            f.write(text_preprocessing.clean_markdown(
                markdownify(str(self.get_readability_html()))
            ))
        self.page_readability_html_markdown = self.get_file_content('content.readability.html.md')
        return self.get_readability_html_markdown()
        
    def get_metadata(self):
        if hasattr(self, 'metadata'):
            return self.metadata
        document = self.get_bs4_html_object()
        # parse out links, buttons, etc.
        # use pythonic types so that yaml acts nicley
        metas =   list(sorted(set([ meta.attrs['content'].strip() for meta in document.find_all('meta') if 'name' in meta.attrs and 'description' in meta.attrs['name'] ])))
        titles =  list(sorted(set([ e.get_text().strip() for e in document.find_all('title') ])))
        links =   { l['href']:str(l) for l in document.find_all('a', href=True) }
        buttons = list(sorted(set([ b.text.strip() for b in document.find_all('button') ]))) # maybe get the surrounding text too?
        
        self.metadata = {
            'titles': titles,
            'descriptions': metas,
            'links': links
        }
        with open(self.get_filepath('meta.yaml'), 'w') as f:
            yaml.dump(self.metadata, f)
        
        return self.get_metadata()
    
    def get_chunks(self):
        if hasattr(self, 'chunks'):
            return self.chunks
        max_chunk_size = 312 # make sure things add up to 512, which is the window size of embedding model...
        self.chunks = list(text_preprocessing.overlap_chunk(self.get_readability_html_markdown(), max_chunk_size, 100)) # 100 + 312 + 100 = 512
        return self.get_chunks()
        
    def get_summary(self):
        if hasattr(self, 'page_summary'):
            return self.page_summary
        metadata = self.get_metadata()
        self.page_summary = tools.summarize_chunks([
            'Page location: ' + self.url,
            *metadata['descriptions'],
            *metadata['titles'],
            *self.get_chunks()
        ])
        with open(self.get_filepath('content.readability.chunked.md.summary.txt'), 'w') as f:
            f.write(self.page_summary)
        return self.get_summary()
    
    def get_chunk_embeddings(self):
        if hasattr(self, 'chunk_embeddings'):
            return self.chunk_embeddings
        chunks = self.get_chunks()
        self.chunk_embeddings = []
        with open(self.get_filepath('content.readability.md.embeddings.json'), 'a') as f:
            for i, (c, e) in tqdm(
                enumerate(zip(chunks, embedding_model.encode(chunks))),
                total=len(chunks),
                desc="Chunk --> Embedding"
            ):
                self.chunk_embeddings.append(e)
                f.writelines([
                    json.dumps(
                        {
                            'i':i,
                            "embedding": [ str(ei) for ei in e.astype(float)],
                            "chunk": c
                        }
                    ) + '\n'
                ])
        return self.get_chunk_embeddings()

def cache(url:str, page_readability_html: str, page_document_html: str):
    
    try:
        cache = ProcessedWebpageCache(url).load()
    except ProcessedWebpageCache.WebpageNotCached:
        cache = ProcessedWebpageCache(url).setup(page_readability_html, page_document_html)
    
    cache.get_summary()
    cache.get_chunk_embeddings()

def load(url: str):
    
    # check if website_dir exists...
    
    embeddings = pd.DataFrame(columns=['embedding', 'chunk'])
    with open(get_website_cache_file(url, 'content.readability.md.embeddings.json'), 'r') as f:
        for i, line in enumerate(f.readlines()):
            embeddings.loc[i] = json.loads(line)
            embeddings.loc[i].embedding = np.array(embeddings.loc[i].embedding).astype(float)
    return embeddings
#    return pd.read_pickle(os.path.join(get_website_cache(url), 'embeddings.pkl'))
