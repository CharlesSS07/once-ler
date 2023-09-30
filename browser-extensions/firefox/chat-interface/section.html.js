const view = document.createElement('div');
view.style.position = 'fixed';
view.style.top = '50%';
view.style.left = '60%';
view.style.zIndex = '999999';

// bad way to insert the html but I couldn't figure out a better method with the browser extension loading

view.innerHTML = `<section class="msger">
  <header class="msger-header">
    <div class="msger-header-title">
      <i class="fas fa-comment-alt"></i> UU-Ai
    </div>
    <div class="msger-header-options">
      <span><i class="fas fa-cog"></i></span>
    </div>
  </header>

  <main class="msger-chat">
    <div class="msg left-msg">
      <div
       class="msg-img"
       style="background-image: url(https://admissions.utah.edu/wp-content/themes/umctheme3/favicon-32x32.png)"
      ></div>

      <div class="msg-bubble">
        <div class="msg-info">
          <div class="msg-info-name">UU-Ai</div>
          <div class="msg-info-time">--:--</div>
        </div>

        <div class="msg-text">
          Hi, I'm the UU's chat AI, here to direct you around this website. Try me before emailing admissions (I'm faster...).
        </div>
      </div>
    </div>
  </main>

  <form class="msger-inputarea">
    <input type="text" class="msger-input" placeholder="How do I gain residency status as a international student?" id="messageCompositionBox">
    <button type="submit" class="msger-send-btn">Send</button>
  </form>

</section>`;

view.classList.add('chatinterface');
view.id = 'chatinterface';
document.body.appendChild(view);

function messageCompositionBoxPlaceHolderChangeEffect() {
    
    const messageCompositionBox = document.getElementById('messageCompositionBox');
    const messageCompositionBoxPlaceHolderContent = [
        "How do I gain residency status as an international student?",
        "I'm looking for scholarships.",
        "I want to check my application status.",
        "How do I get residency as an out-of-state student?",
        "Can I gain residency while on an Eccles Global study abroad?",
        "Tell me about research at the U.",
        "I'm looking for information on Early Admission.",
        "What are you looking for?"
    ];
    let i = 0;
    
    setInterval(change, 5000);

    function change() {
        if (messageCompositionBox.value!='') {
            return;
        }
        messageCompositionBox.classList.remove("text-show");
        messageCompositionBox.classList.add("text-fade");

        setTimeout(() => {
            messageCompositionBox.placeholder = messageCompositionBoxPlaceHolderContent[  i % messageCompositionBoxPlaceHolderContent.length ];
            
            messageCompositionBox.classList.remove("text-fade");
            messageCompositionBox.classList.add("text-show");
            
        }, 1000);
        
        i++;
    }
}

messageCompositionBoxPlaceHolderChangeEffect();
