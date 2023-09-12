const view = document.createElement('div');
view.style.position = 'fixed';
view.style.top = '0';
view.style.zIndex = '999999';

// bad way to insert the html but I couldn't figure out a better method with the browser extension loading

view.innerHTML = `<section class="msger">
  <header class="msger-header">
    <div class="msger-header-title">
      <i class="fas fa-comment-alt"></i> once-ler
    </div>
    <div class="msger-header-options">
      <span><i class="fas fa-cog"></i></span>
    </div>
  </header>

  <main class="msger-chat">
    <div class="msg left-msg">
      <div
       class="msg-img"
       style="background-image: url(https://i0.wp.com/bane-tech.com/wp-content/uploads/2015/10/google-font-b.jpg)"
      ></div>

      <div class="msg-bubble">
        <div class="msg-info">
          <div class="msg-info-name">once-ler-BOT</div>
          <div class="msg-info-time">12:45</div>
        </div>

        <div class="msg-text">
          Hi, I'm once-ler! Go ahead and send me a message. 😄 I can help you understand this page in record time.
        </div>
      </div>
    </div>
  </main>

  <form class="msger-inputarea">
    <input type="text" class="msger-input" placeholder="Enter your message...">
    <button type="submit" class="msger-send-btn">Send</button>
  </form>
</section>`;

view.classList.add('chatinterface');
view.id = 'chatinterface';
document.body.appendChild(view);
