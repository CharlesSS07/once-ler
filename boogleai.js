const tmp = require('tmp');
// tmp.setGracefulCleanup();
const fs = require('fs');

const { Blob, blobFrom, blobFromSync, File, fileFrom, fileFromSync } = require('node-fetch');

function get_boogle_reply(user_id, website_domain, query_message, query_document_html_text) {
  
  const tmpFileObject = tmp.fileSync({prefix: 'webpage-', postfix: '.txt' });
  const tmpPath = tmpFileObject.name;
  fs.writeFileSync(tmpPath, Buffer.from(query_document_html_text, 'utf8'));
  console.log(tmpPath);

  let formData = new FormData();
  formData.append("files", new Buffer.File(query_document_html_text, tmpPath));
  formData.append("question", query_message);
  
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
  
  return query(formData).then((response) => {
    console.log(response);
    // tmpFileObject.removeCallback();
    return response;
  });
}
module.exports = { get_boogle_reply };
