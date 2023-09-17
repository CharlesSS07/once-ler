
import falcon
import falcon.asgi

class ChatQueryEndpoint:

    async def on_post(self, req, resp):

        resp.set_header('Access-Control-Allow-Origin', '*')
        resp.set_header('Access-Control-Allow-Methods', '*')
        resp.set_header('Access-Control-Allow-Headers', '*')
        
        user_id = 'neo'
        
        message = req.media['message']
        
        html_document = req.media['document']
        
        page = req.media['page']
        
        print(req)
        
        # resp.body = 

    async def process_request(self, req, resp):
        print(resp.headers)
        resp.set_header('Access-Control-Allow-Origin', '*')
        resp.set_header('Access-Control-Allow-Methods', '*')
        resp.set_header('Access-Control-Allow-Headers', '*')
        resp.status = falcon.HTTP_200
        # resp.set_header('Access-Control-Max-Age', 1728000)  # 20 days
        if req.method == 'OPTIONS':
            print('recieved options')
            return
            # raise falcon.http_status.HTTPStatus(falcon.HTTP_200, body='\n')

app = falcon.asgi.App(
    cors_enable=True # allows any endpoint to be accessed by the browser, could be insecure if that's not what we want
)
app.add_route('/query', ChatQueryEndpoint())


