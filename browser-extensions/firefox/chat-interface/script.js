
const user_id = 'neo';

const chatServerEndpoint = 'https://6155-155-98-131-2.ngrok-free.app';

async function on_page_load() {
    
    const documentClone = document.cloneNode(true);
    documentClone.body.removeChild(documentClone.getElementById('chatinterface'));
    
    var article = new Readability(documentClone).parse();
    let postProcessedHTML = await article.content;

    fetch(
        `${chatServerEndpoint}/on_page_load`, {
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

on_page_load();

function trimAny(str, chars) { // stolen from https://stackoverflow.com/questions/26156292/trim-specific-character-from-a-string
    var start = 0,
        end = str.length;

    while(start < end && chars.indexOf(str[start]) >= 0)
        ++start;

    while(end > start && chars.indexOf(str[end - 1]) >= 0)
        --end;

    return (start > 0 || end < str.length) ? str.substring(start, end) : str;
}

function datetimeLink(datetimeString, summary) {
    /**
     Checks if event is in future or past. Makes link to a search engine if in past, and calendar for future.
     
     AddEvent is a good Universal "Add to Calendar" solution, but requires money. Enable later if needed.
     AddEvent: https://www.addevent.com/c/documentation/add-to-calendar-button
     Themes of buttons can also be customized.
     */
    // todo get timezone from js, use here
    const date = Date.parse(trimAny(datetimeString, ',.?!<>;:\'"[]{}-_=+@#$%^&*()'));
    console.log(datetimeString);
    if (date.compareTo(Date.today().setTimeToNow()) > 0) { // future
        // stand in for now because AddEvent will not work yet
        return `<a href=example.com target="_blank"><time>${datetimeString}</time></a>`;
    } else { // past //${date.toString("MM/dd/yyyy hh:mm tt")}
        return `<form action="http://google.com/search" target="_blank">
<input name="q" value="${datetimeString}" hidden=true>
<button type="submit" class='button.link'>${datetimeString}</button>
</form>`;
    }
    
    // AddEvent button:
//    const start = date.toString("MM/dd/yyyy hh:mm tt");
////        const stop = date.toString("MM/dd/yyyy hh:mm tt")
//    return `<div title="Add to Calendar" class="addeventatc" data-styling="none">
//Add to Calendar
//<span class="start">${start}</span>
//<span class="timezone">America/Los_Angeles</span>
//<span class="title">Event from UU-GPT</span>
//<span class="description">${summary}</span>
//</div>`;
}

function formatDates(text) {
    /**
     "Convoludes" the text by running a date parsing function over every group of 1-4 words.
     */
    
    const words = text.split(' ');
    let formattedWords = [];
    const wordCount = words.length;
    let previousWindowWasDate = false;
    let previousWindow = '';
    
    for (let i = 0;i < wordCount;i++) {
        
        let j = i+1;
        const window = '';
        for (;j < wordCount+1;j++) {
            const window = words.slice(i, Math.min(j, wordCount)).join(' ');
            // console.log(`Window ${window} at ${i}, ${j}, ${Date.parse(window)}`);
            
            if (window.length>3 && Date.parse(
                trimAny(window, ',.?!<>;:\'"[]{}-_=+@#$%^&*()'))!=null) { // valid date
                previousWindowWasDate = true;
            } else { // not valid date
                if (previousWindowWasDate) { // if previous window had a valid date register it
                    previousWindowWasDate = false;
                    formattedWords.push(datetimeLink(previousWindow, text));
                    i = j-1;
                    break; // found the date so add it to formattedWords, and skip out of here
                }
            }
            
            previousWindow = window;
            
        }
        
        if (previousWindowWasDate) { // whole entire substring ^ was a date so add it, formatted
            previousWindowWasDate = false;
            formattedWords.push(datetimeLink(previousWindow, text));
            i = j-1;
        } else {
            formattedWords.push(words[i]); // found no dates so add whole window
        }
        
    }
    
    return formattedWords.join(' ');
}

var md2HTMLconverter = new showdown.Converter({
    tasklists: true,
    encodeEmails: true,
    emoji: true,
    openLinksInNewWindow: true
});
md2HTMLconverter.setFlavor('github');
function markup(text) {
    try {
        console.log(text);
        let html = '<h3>' + formatDates(text) + '</h3>';
        console.log(html);
        html = md2HTMLconverter.makeHtml(html);
        // do markdown in-browser. this makes ui elements for links, code, emails, time/date, etc.
        console.log(html);
        return $('<div>')
        .html(html)
        .linkify()
        .html();
    } catch (e) {
        console.log('could not markup.');
        console.error(e);
        return text;
    }
}


// chat interface stolen from: https://codepen.io/sajadhsm/pen/odaBdd

const msgerForm = document.querySelector(".msger-inputarea");
const msgerInput = document.querySelector(".msger-input");
const msgerChat = document.querySelector(".msger-chat");
msgerForm.addEventListener("submit", event => {
    event.preventDefault();

    const msgText = msgerInput.value;
    if (!msgText) return;

    appendMessage(
        "You",
        "https://media.istockphoto.com/id/1298261537/vector/blank-man-profile-head-icon-placeholder.jpg?s=170667a&w=is&k=20&c=OySd4zJilw82P4k-sQ72kYckL122oUiy5Z5VTnFQi90=",
        "right",
        markup(msgText)
    );
    msgerInput.value = "";

    fetch(
        `${chatServerEndpoint}/on_user_message`, {
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
            let messageContent = message.content
            .replace(/\\n/g, '<br>').replace(/\n/g, '<br>');
            
            appendMessage(
                message.name,
                "https://admissions.utah.edu/wp-content/themes/umctheme3/favicon-32x32.png",
                "left",
                markup(messageContent)
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
<div class="msg-bubble">
${imgHTML}
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

