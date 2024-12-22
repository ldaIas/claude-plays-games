class ConversationCache:
    def __init__(self, max_size=10):
        self.max_size = max_size
        self.messages = []

    def add_message(self, message):
        self.messages.append(message)  # Add to the end
        if len(self.messages) > self.max_size:
            self.messages.pop(0)  # Remove the oldest message

    def get_messages(self):
        return self.messages
