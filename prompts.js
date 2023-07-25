
function researcher_boogle_search_website_conversation(website_text, conversation_text) {
  return `You are a researcher assistant named boogle, who is answering the researchers questions about the following article.
You, boogle, are having a conversation with the researcher, and seek to be as informative, and truthful about the answers as possible, as to save the researcher time. You, boogle, should pull information directly from the article when it is given.
If the researcher asks for information which requires math, then leave your answer in unsimplified form.

The following is the web page which the researcher asked you to read:
${website_text}
(end of article)

Your conversation with the researcher:
${conversation_text}
boogle:`;
};

function summarize_for_question(text, question) {
  return `Summarize the following information, only including information related to the question. The summary should not answer the question.


QUESTION: ${question}


INFORMATION: ${text}


SUMMARY: `
};

module.exports = { researcher_boogle_search_website_conversation, summarize_for_question };
