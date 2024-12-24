class Chatbox {
  constructor() {
    this.args = {
      openButton: document.querySelector(".chatbox_button"),
      chatBox: document.querySelector(".chatbox"),
      sendButton: document.querySelector(".send_button"),
    };
    this.state = false;
    this.messages = [];
  }

  display() {
    const { openButton, chatBox, sendButton } = this.args;
    openButton.addEventListener("click", () => this.toggleState(chatBox));
    sendButton.addEventListener("click", () => this.onSendButton(chatBox));
    const node = chatBox.querySelector("input");
    node.addEventListener("keyup", ({ key }) => {
      if (key === "Enter") {
        this.onSendButton(chatBox);
      }
    });
  }

  toggleState(chatBox) {
    this.state = !this.state;
    if (this.state) {
      chatBox.classList.add("chatbox-active");
    } else {
      chatBox.classList.remove("chatbox-active");
    }
  }

  async recordUnknownQuery(query) {
    try {
      const response = await fetch($SCRIPT_ROOT + "/api/unknown-queries", {
        method: "POST",
        body: JSON.stringify({ query }),
        headers: {
          "Content-Type": "application/json",
        },
      });
      const data = await response.json();
      console.log("Unknown query recorded:", data);
    } catch (error) {
      console.error("Error recording unknown query:", error);
    }
  }

  onSendButton(chatBox) {
    var textField = chatBox.querySelector("input");
    let query = textField.value;
    if (query === "") {
      return;
    }
    let msg1 = { name: "User", message: query };
    this.messages.push(msg1);
    fetch($SCRIPT_ROOT + "/predict", {
      method: "POST",
      body: JSON.stringify({ message: query }),
      mode: "cors",
      headers: {
        "Content-Type": "application/json",
      },
    })
      .then((r) => r.json())
      .then((r) => {
        let msg2 = { name: "DWIT Chatbot", message: r.answer };
        this.messages.push(msg2);

        // If bot doesn't understand, record the query
        if (r.answer === "I do not understand...") {
          this.recordUnknownQuery(query);
        }

        this.updateChatText(chatBox);
        textField.value = "";
      })
      .catch((error) => {
        console.error("Error:", error);
        this.updateChatText(chatBox);
        textField.value = "";
      });
  }

  updateChatText(chatBox) {
    var html = "";
    this.messages
      .slice()
      .reverse()
      .forEach(function (item) {
        if (item.name === "DWIT Chatbot") {
          html +=
            '<div class="message_item message_item-operator">' +
            item.message +
            "</div>";
        } else {
          html +=
            '<div class="message_item message_item-visitor">' +
            item.message +
            "</div>";
        }
      });
    const chatMessage = chatBox.querySelector(".chatbox_messages");
    chatMessage.innerHTML = html;
  }
}

const chatbox = new Chatbox();
chatbox.display();
