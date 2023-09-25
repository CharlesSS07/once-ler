
import falcon

import assistant

class ChatQueryEndpoint:

    def on_post(self, req, resp):

#        resp.set_header('Access-Control-Allow-Origin', '*')
#        resp.set_header('Access-Control-Allow-Methods', '*')
#        resp.set_header('Access-Control-Allow-Headers', '*')
        
        user_id = req.media['user_id']
        message = req.media['message']
        html_document = req.media['document']
        page = req.media['page']
        
        resp.media = {'messages': assistant.on_message(user_id, message, html_document, page)}
        
        resp.status = falcon.HTTP_200
        resp.complete = True

app = falcon.App(
    cors_enable=True # allows any endpoint to be accessed by the browser, could be insecure if that's not what we want
)
app.add_route('/query', ChatQueryEndpoint())


