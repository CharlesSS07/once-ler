
import falcon.asgi

import traceback
import asyncio
import collections
import threading

import config
import tools
import websitedata
import assistant

#class NewPageLoadedEndpoint:
#
#    async def on_post(self, req, resp):
#
#        media = await req.get_media()
#
#        user_id = media['user_id']
#        html_document = media['document']
#        text_document = media['text']
#        url = media['url']
#
#        websitedata.cache(url, text_document, html_document)
#
#        resp.status = falcon.HTTP_200
#        resp.complete = True

class OnUserMessageEndpoint:

    async def on_get(self, req, resp):
        pass

    async def on_websocket(self, req, ws):
        try:
            await ws.accept()
        except falcon.WebSocketDisconnected:
            return
        media = await ws.receive_media()
        user_id = media['user_id']

        message_buffer = collections.deque()

        async def sink():
            while True:
                try:
                    message = await ws.receive_media()
                    content = message['message']
                    page = message['page']
                    threading.Thread(
                        target=assistant.events.on_user_message, args=(user_id, content, page, message_buffer)
                    ).start()
                except falcon.WebSocketDisconnected:
                    break

        sink_task = falcon.create_task(sink())

        while not sink_task.done():
            while ws.ready and not message_buffer and not sink_task.done():
                await asyncio.sleep(0)
            if not ws.ready or sink_task.done():
                break
            try:
                await ws.send_media(message_buffer.popleft())
            except falcon.WebSocketDisconnected: # might have no messages left in buffer, so catch index error
                print('disconnected')
                break

        sink_task.cancel()
        try:
            await sink_task
        except asyncio.CancelledError:
            pass

app = falcon.asgi.App(
    cors_enable=True # allows any endpoint to be accessed by the browser, could be insecure if that's not what we want
)
app.add_route('/user_message_socketserver', OnUserMessageEndpoint())
#app.add_route('/on_page_load', NewPageLoadedEndpoint())

async def custom_handle_uncaught_exception(req, resp, ex, params, ws=None):
    print('Error on:', req)
    raise ex

app.add_error_handler(Exception, custom_handle_uncaught_exception)
