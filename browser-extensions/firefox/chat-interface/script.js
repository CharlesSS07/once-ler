
const user_id = 'neo';

async function parsePage() {
    
    const documentClone = document.cloneNode(true);
    documentClone.body.removeChild(documentClone.getElementById('chatinterface'));
    
    var article = new Readability(documentClone).parse();
    let postProcessedHTML = await article.content;
//    .textContent
//    .replace(/\\\\n/g, '\n')
//    .replace(/\\\\t/g, '\n')
//    .replace(/\\n/g, '\t')
//    .replace(/\\t/g, '\t')
//    .replace(/\n\n\n[\n]+/g, '')
//    .replace(/\t\t\t[\t]+/g, '')
//    .replace(/  [ ]+/g, ' ');

    fetch(
        'https://1f49-155-98-131-2.ngrok-free.app/parse_page', {
            method: "POST",
            mode: "cors",
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(
                {
                    user_id: user_id,
                    document: document.documentElement.outerHTML,
                    text: postProcessedHTML,
                    url: window.location.href
                }
            )
        }
    );
}

parsePage();

// chat interface stolen from: https://codepen.io/sajadhsm/pen/odaBdd

const msgerForm = document.querySelector(".msger-inputarea");
const msgerInput = document.querySelector(".msger-input");
const msgerChat = document.querySelector(".msger-chat");

msgerForm.addEventListener("submit", event => {
    event.preventDefault();

    const msgText = msgerInput.value;
    if (!msgText) return;

    appendMessage("You", "https://media.istockphoto.com/id/1298261537/vector/blank-man-profile-head-icon-placeholder.jpg?s=170667a&w=is&k=20&c=OySd4zJilw82P4k-sQ72kYckL122oUiy5Z5VTnFQi90=", "right", msgText);
    msgerInput.value = "";

    const documentClone = document.cloneNode(true);
    documentClone.body.removeChild(documentClone.getElementById('chatinterface'));
    //documentClone.querySelectorAll('style').forEach((element) => {
    //element.remove();
    //});
    //documentClone.querySelectorAll('script').forEach((element) => {
    //element.remove();
    //});
    //
    //// remove all class=... and style= ... from HTML before sending off
    //// this gets rid of lots of nearly useless text
    //// we want to remove as much as possibile to speed up GPT call, and transfer speeds
    //let postProcessedHTML = documentClone.body.innerHTML;
    //console.log(postProcessedHTML.length);
    //postProcessedHTML = postProcessedHTML.replaceAll(/(<[a-z]+.*?)(class=".*?")(.*?>)/g, // to remove all class=...
    //(_, g1, g2, g3) => {
    //return `${g1.trim()} ${g3.trim()}`;
    //})
    //.replaceAll(/(<[a-z]+.*?)(style=".*?")(.*?>)/g, // to remove all style=...
    //(_, g1, g2, g3) => {
    //return `${g1.trim()} ${g3.trim()}`;
    //})
    //.replaceAll('\t', '').replace('\n\r', '').replace('\r', '').replace('\n', '');

    var article = new Readability(documentClone).parse();
    let postProcessedHTML = article.textContent;
    console.log(postProcessedHTML);
    console.log(postProcessedHTML.length);

    fetch(
        'https://1f49-155-98-131-2.ngrok-free.app/on_user_message', {
            method: "POST",
            mode: "cors",
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(
                {
                    user_id: user_id,
                    message: msgText,
                    page: window.location.href
                }
            )
        }
    ).then(async (chatCompletion) => {
        const messages = (await chatCompletion.json()).messages;
        console.log(messages);
        for (const i in messages) {
            const message = messages[i];
            console.log(message);
            if (message.name=="User") {
                // maybe mark as processed?
                continue;
            }
            appendMessage(
                message.name,
                "https://admissions.utah.edu/wp-content/themes/umctheme3/favicon-32x32.png",
                "left",
                message.content.replace(/\\n/g, '<br>').replace(/\n/g, '<br>')
            );
        }
    }).catch(err => {
        console.error(err);
    });
    
});

function appendMessage(name, img, side, text) {
    //   Simple solution for small apps
    let imgHTML = `<div class="msg-img" style="background-image: url(${img})"></div>`;
    if (side=='right') {
        imgHTML = '';
    }
    const msgHTML = `<div class="msg ${side}-msg">
    ${imgHTML}

    <div class="msg-bubble">

    <div class="msg-info">
    <div class="msg-info-name">${name}</div>
    <div class="msg-info-time">${formatDate(new Date())}</div>
    </div>

    <div class="msg-text">${text}</div>
    </div>
    </div>`;

    msgerChat.insertAdjacentHTML("beforeend", msgHTML);
    msgerChat.scrollTop += 500;
}

function formatDate(date) {
    const h = "0" + date.getHours();
    const m = "0" + date.getMinutes();

    return `${h.slice(-2)}:${m.slice(-2)}`;
}

// Dragging code stolen from: https://www.w3schools.com/howto/howto_js_draggable.asp

function dragElement(elmnt, handle) {
  var pos1 = 0, pos2 = 0, pos3 = 0, pos4 =0;
  handle.onmousedown = dragMouseDown;

  function dragMouseDown(e) {
    // console.log('dragMouseDown fired');
    e = e || window.event;
    e.preventDefault();
    // get the mouse cursor position at startup:
    pos3 = e.clientX;
    pos4 = e.clientY;
    document.onmouseup = closeDragElement;
    // call a function whenever the cursor moves:
    document.onmousemove = elementDrag;
    // console.log('dragMouseDown exited');
  }

  function elementDrag(e) {
    // console.log('elementDrag fired');
    e = e || window.event;
    e.preventDefault();
    // calculate the new cursor position:
    pos1 = pos3 - e.clientX;
    pos2 = pos4 - e.clientY;
    pos3 = e.clientX;
    pos4 = e.clientY;
    // set the element's new position:
    elmnt.style.top = (elmnt.offsetTop - pos2) + "px";
    elmnt.style.left = (elmnt.offsetLeft - pos1) + "px";
  }

  function closeDragElement() {
    // console.log('closeDragElement fired');
    // stop moving when mouse button is released:
    document.onmouseup = null;
    document.onmousemove = null;
  }
}

dragElement(document.querySelector(".msger").parentElement, document.querySelector(".msger-header"));

