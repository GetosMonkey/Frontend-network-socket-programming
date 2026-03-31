import { useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import './ChatView.css';

// Mock messages for UI visualization
const mockMessages = [
  { id: 1, sender: 'Saiyantha', content: 'Hey, are we still doing the demo?', time: '10:00 AM', isMe: false },
  { id: 2, sender: 'You', content: 'Yes! Im just fixing the Vite integration.', time: '10:05 AM', isMe: true },
  { id: 3, sender: 'Saiyantha', content: 'Awesome, looks amazing so far.', time: '10:06 AM', isMe: false },
];

export default function ChatView() {
  const { id } = useParams();
  const navigate = useNavigate();
  const [message, setMessage] = useState('');
  const [messages, setMessages] = useState(mockMessages);

  const handleSend = (e: React.FormEvent) => {
    e.preventDefault();
    if (!message.trim()) return;

    const newMessage = {
      id: messages.length + 1,
      sender: 'You',
      content: message,
      time: 'Just now',
      isMe: true,
    };

    setMessages([...messages, newMessage]);
    setMessage('');
  };

  return (
    <div className="chat-view-container">
      <div className="chat-panel glass-panel">
        
        {/* Header */}
        <div className="chat-header">
          <button className="back-btn" onClick={() => navigate('/history')}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="19" y1="12" x2="5" y2="12"></line>
              <polyline points="12 19 5 12 12 5"></polyline>
            </svg>
          </button>
          
          <div className="chat-header-info">
            <div className="chat-avatar small">
              {id === '2' ? 'S' : 'V'}
            </div>
            <div>
              <h3>{id === '2' ? 'Saiyantha' : `Chat Group ${id}`}</h3>
              <span className="status online">Online</span>
            </div>
          </div>
        </div>

        {/* Message Area */}
        <div className="messages-area">
          {messages.map(msg => (
            <div key={msg.id} className={`message-wrapper ${msg.isMe ? 'me' : 'them'}`}>
              <div className="message-bubble">
                {!msg.isMe && <span className="sender-name">{msg.sender}</span>}
                <p>{msg.content}</p>
                <span className="msg-time">{msg.time}</span>
              </div>
            </div>
          ))}
        </div>

        {/* Input Area */}
        <form className="chat-input-area" onSubmit={handleSend}>
          <button type="button" className="attach-btn">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <path d="M21.44 11.05l-9.19 9.19a6 6 0 0 1-8.49-8.49l9.19-9.19a4 4 0 0 1 5.66 5.66l-9.2 9.19a2 2 0 0 1-2.83-2.83l8.49-8.48"></path>
            </svg>
          </button>
          <input 
            type="text" 
            placeholder="Type a message..." 
            value={message}
            onChange={(e) => setMessage(e.target.value)}
          />
          <button type="submit" className="send-btn" disabled={!message.trim()}>
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="22" y1="2" x2="11" y2="13"></line>
              <polygon points="22 2 15 22 11 13 2 9 22 2"></polygon>
            </svg>
          </button>
        </form>

      </div>
    </div>
  );
}
