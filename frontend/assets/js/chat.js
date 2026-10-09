var checkout = {};

$(document).ready(function () {
  var $messages = $('.messages-content'),
    d, h, m,
    i = 0;

  // Keep the same Lex session throughout the conversation
  var sessionId = null;

  $(window).on('load', function () {
    $messages.mCustomScrollbar();
    insertResponseMessage(
      "Hi there, I'm your personal Concierge. How can I help?"
    );
  });

  function updateScrollbar() {
    $messages.mCustomScrollbar("update").mCustomScrollbar(
      'scrollTo',
      'bottom',
      {
        scrollInertia: 10,
        timeout: 0
      }
    );
  }

  function setDate() {
    d = new Date();

    if (m != d.getMinutes()) {
      m = d.getMinutes();

      $('<div class="timestamp">' +
        d.getHours() + ':' + m +
        '</div>').appendTo($('.message:last'));
    }
  }

  // Send the message to LF0, reusing the same Lex session ID
  function callChatbotApi(message) {
    var requestBody = {
      messages: [
        {
          type: 'unstructured',
          unstructured: {
            text: message
          }
        }
      ]
    };

    if (sessionId) {
      requestBody.sessionId = sessionId;
    }

    console.log('Sending message:', message);
    console.log('Session ID being sent:', sessionId);

    return sdk.chatbotPost({}, requestBody, {});
  }

  function insertMessage() {
    var msg = $('.message-input').val();

    if ($.trim(msg) === '') {
      return false;
    }

    $('<div class="message message-personal"></div>')
      .text(msg)
      .appendTo($('.mCSB_container'))
      .addClass('new');

    setDate();

    $('.message-input').val(null);
    updateScrollbar();

    callChatbotApi(msg)
      .then(function (response) {
        console.log('Full API response:', response);

        // API Gateway response body may be a JSON string
        var data = response.data.body;

        if (typeof data === 'string') {
          data = JSON.parse(data);
        }

        // Save the session ID returned by LF0.
        // Subsequent user messages reuse this ID.
        if (data.sessionId) {
          sessionId = data.sessionId;
        }

        console.log('Current Lex session ID:', sessionId);

        if (data.messages && data.messages.length > 0) {
          console.log(
            'Received ' + data.messages.length + ' messages'
          );

          data.messages.forEach(function (message) {
            if (message.type === 'unstructured') {
              insertResponseMessage(
                message.unstructured.text
              );

            } else if (
              message.type === 'structured' &&
              message.structured.type === 'product'
            ) {
              var product = message.structured;

              insertResponseMessage(product.text);

              setTimeout(function () {
                var payload = product.payload;

                var html =
                  '<img src="' + payload.imageUrl +
                  '" width="200" height="240" class="thumbnail" />' +
                  '<b>' + payload.name +
                  '<br>$' + payload.price +
                  '</b><br><a href="#" onclick="' +
                  payload.clickAction + '()">' +
                  payload.buttonLabel + '</a>';

                insertResponseMessage(html);
              }, 1100);

            } else {
              console.log(
                'Unsupported message type:',
                message.type
              );
            }
          });

        } else {
          insertResponseMessage(
            'Sorry, I did not receive a response. Please try again.'
          );
        }
      })
      .catch(function (error) {
        console.error('Chatbot API error:', error);

        insertResponseMessage(
          'Oops, something went wrong. Please try again.'
        );
      });

    return false;
  }

  $('.message-submit').on('click', function () {
    insertMessage();
  });

  $(window).on('keydown', function (e) {
    if (e.which === 13) {
      // Prevent Enter from submitting twice
      e.preventDefault();
      insertMessage();
      return false;
    }
  });

  function insertResponseMessage(content) {
    var $loading = $(
      '<div class="message loading new">' +
        '<figure class="avatar">' +
          '<img src="https://media.tenor.com/images/4c347ea7198af12fd0a66790515f958f/tenor.gif" />' +
        '</figure>' +
        '<span></span>' +
      '</div>'
    );

    $messages.find('.mCSB_container').append($loading);
    updateScrollbar();

    setTimeout(function () {
      $loading.remove();

      // Preserve the existing chat message styling
      var $response = $(
        '<div class="message new">' +
          '<figure class="avatar">' +
            '<img src="https://media.tenor.com/images/4c347ea7198af12fd0a66790515f958f/tenor.gif" />' +
          '</figure>' +
        '</div>'
      );

      // Insert text safely; allow HTML only for existing product cards
      $response.append(document.createTextNode(content));

      $messages.find('.mCSB_container').append($response);

      setDate();
      updateScrollbar();
      i++;
    }, 500);
  }
});