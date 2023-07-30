
import fetch, {
  //Blob,
  FormData,
  //blobFrom,
  //blobFromSync,
  File,
  //fileFrom,
  //fileFromSync,
} from 'node-fetch'

async function get_boogle_reply(user_id, website_domain, query_message, query_document_html_text) {
  
  const formData = new FormData()
  formData.append("files", new File([query_document_html_text], 'tmp.txt', { type: 'text/plain'}), 'tmp.txt');
  formData.append("question", query_message);
  //formData.append("sessionId", user_id+"/"+website_domain);
  formData.append("pineconeNamespace", website_domain);
  
  async function query(formData) {
    const response = await fetch(
      "http://localhost:3000/api/v1/prediction/f2824a3b-11e9-4991-8556-363c0a79e2cd",
      {
        method: "POST",
        body: formData
      }
    );
    const result = await response.json();
    return result;
  }
  
  return query(formData);
}
export { get_boogle_reply };
