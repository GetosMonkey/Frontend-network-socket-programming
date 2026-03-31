import threading
import queue

class ChatQueue:
    """
    Manages a message queue for a single chat (chatID).
    Ensures message ordering and deduplication at the server level.
    """
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.queue = queue.Queue()
        self.lock = threading.Lock()
        self.next_sequence = self._get_initial_sequence()
        self.worker_thread = threading.Thread(target=self._process_queue, daemon=True)
        self.worker_thread.start()

    def _get_initial_sequence(self):
        from .database import get_last_sequence
        return get_last_sequence(self.chat_id) + 1

    def push(self, sender_id, content, message_type="text"):
        """
        Pushes a message into the logical queue.
        Logical ordering is preserved here before database insertion.
        """
        with self.lock:
            seq = self.next_sequence
            self.next_sequence += 1
            self.queue.put((sender_id, content, message_type, seq))
            return seq

    def _process_queue(self):
        """
        Worker thread that drains the queue and performs database insertions.
        Ensures that heavy write activity doesn't block the main server threads.
        """
        from .database import save_message
        while True:
            sender_id, content, message_type, seq = self.queue.get()
            try:
                save_message(self.chat_id, sender_id, content, seq, message_type)
            except Exception as e:
                print(f"[ERROR] Failed to save message in chat {self.chat_id}: {e}")
            finally:
                self.queue.task_done()

class QueueManager:
    """
    Manages multiple ChatQueues, one for each unique chatID.
    Maximizes throughput by processing different chats in parallel.
    """
    def __init__(self):
        self.queues = {}
        self.lock = threading.Lock()

    def get_queue(self, chat_id):
        with self.lock:
            if chat_id not in self.queues:
                self.queues[chat_id] = ChatQueue(chat_id)
            return self.queues[chat_id]

    def queue_message(self, chat_id, sender_id, content, message_type="text"):
        chat_queue = self.get_queue(chat_id)
        return chat_queue.push(sender_id, content, message_type)

# Global Manager Instance
manager = QueueManager()
