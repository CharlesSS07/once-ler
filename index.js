
import * as boogleai from './boogleai.js';

import express from 'express';

const app = express ();

const maxRequestBodySize = '9mb';
app.use(express.json({limit: maxRequestBodySize}));

const PORT = 8000;

app.listen(PORT, () => {
  console.log("Server Listening on PORT:", PORT);
});

app.options('/query', (request, response) => {
  response.header('Access-Control-Allow-Origin', '*');
  response.header('Access-Control-Allow-Methods', 'POST, OPTIONS');
  response.header('Access-Control-Allow-Headers', '*');
  response.sendStatus(200);
});

app.post("/query", async (request, response) => {
  try {
    response.header('Access-Control-Allow-Origin', '*');
    response.header('Access-Control-Allow-Methods', 'POST, OPTIONS');
    response.header('Access-Control-Allow-Headers', '*');
    
    // hack soloution to stand in for a database and real user managment system for now, while testing
    const user_id = 'neo';
    const website_domain = request.get('origin');
    
    const query_message = request.body.message;
    const query_document = request.body.document;

    boogleai.get_boogle_reply(user_id, website_domain, query_message, query_document)
    .then((new_message) => {
      response.send({message: new_message});
    }).catch((error) => {
      console.log(error.message);
      response.send(error);
    });
  } catch(error) {
    console.log(error.message);
    response.send(error);
  }
});
