# boogle
The boogle browser assistant is a browser extension which allows the user to pull out their desired information from any given website using only a natural language query.
This is meant to replace the need for reading/skimming entire web pages for answers to simple questions.
For instance, the University of Utah hosts the residency web page for informing students of the rules behind attaining tuition for residency purposes.
The webpage is so big that the school also employs people on email systems to answer questions which are detailed on the webpage.
This expensive solution costs the student time since they must now wait an average of up to 3 weeks for this employee to respond.
The solution could be automated, saving the student time and reducing the need for an employee who reads web pages all day.
The automation would look something like a chatbot which interprets information directly from the website.
This is the inspiration for the boogle browser assistant.

## improvements
 - **Look & Feel:** improves look of chat interface
   - make style stay consistent across different webpages
   - add buttons for hiding chat window
   - add buttons for clearing chat, searching chat?
   - add buttons defined by response of language model
   - special formatting (underling links, phone numbers, names, currency amounts, etc.)
 - **Performance:** improve pre-parsing of page before it is embedded in database
   - remove more of the useless html
   - or just convert straight to markup...
 - **Scaleability, Usability:** put all services onto the render.com platform, or some other hosting service
   - speeds up calls, allows service to run 24/7, simplifies deployment of new services
   - makes things more scalable
 - **Look Around Corner of the Web:** leverage the links a webpage has as sources of additional information the user may be looking for
   - allows the chatbot to look around the corner of the web
 - **Learn about the User:** use AI to parse the response of the user to pick up on pieces of information they give away
 - **Legitimate Login Portal:** use wix or some other platform to manage user settings, and provided downloads to the browser extension
 - **Tools:** Add tools to the flowise chat setup to make the bot even more handy

## bugs
 1. **Data Leaks** database is not cleared between different domains. databases should only hold session pertaining to the user, the domain, and the conversation
   - this causes information from unrelated pages to leak across in conversation in unexpected ways
 2. **Chat History not Persistent** there's no database storing chat history so information stored in the chat is not persistent, including the users language, and name

## running
You will need nodejs. I'm not sure how nodejs will get the modules I installed but it has a list of the required ones.

Runs off of flowise server: `npx flowise start --LOG_LEVEL=debug --DEBUG=true`, which servers on port 3000, and allows us to modify the lang chain chat model that calls openai and such.

With the main server being `node index.json`, which serves on port 8000.

I am using an ngrok url which is hard coded into manifes.json, and scrip.json to access my api on port 8000.

Let me know what else you need to get it running.
