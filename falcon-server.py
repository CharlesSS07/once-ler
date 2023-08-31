
import falcon

class EnglishQueryEndpoint:
    def on_post(self, req, resp):
        
        user_id = 'neo'
        
        message = req.media['message']
        
        html_document = req.media['document']
        
        page = req.media['page']
        
        # resp.body = 


app = falcon.App(
    cors_enable=True # allows any endpoint to be accessed by the browser, could be insecure if that's not what we want
)
app.add_route('/query', EnglishQueryEndpoint())


