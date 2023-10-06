
#import falcon
import falcon.asgi

import asyncio

import assistant

import VectorizedWebsites

class NewPageLoadedEndpoint:

    async def on_post(self, req, resp):
        
        media = await req.get_media()
        
        user_id = media['user_id']
        html_document = media['document']
        text_document = media['text']
        url = media['url']
        
        VectorizedWebsites.cache(url, text_document, html_document)
        
        resp.status = falcon.HTTP_200
        resp.complete = True

class OnUserMessageEndpoint:

    async def on_post(self, req, resp):
    
        media = await req.get_media()
        
        user_id = media['user_id']
        message = media['message']
        page = media['page']
        
        resp.media = {'messages': assistant.on_user_message(user_id, message, page)}
        
        resp.status = falcon.HTTP_200
        resp.complete = True

app = falcon.asgi.App(
    cors_enable=True # allows any endpoint to be accessed by the browser, could be insecure if that's not what we want
)
app.add_route('/on_user_message', OnUserMessageEndpoint())
app.add_route('/on_page_load', NewPageLoadedEndpoint())

async def custom_handle_uncaught_exception(req, resp, ex, params, ws=None):
    print('Error on:', req)
    raise ex

app.add_error_handler(Exception, custom_handle_uncaught_exception)
