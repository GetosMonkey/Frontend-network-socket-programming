import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import './ChatHistory.css';

// Mock data to demonstrate UI
const mockChats = [
  { id: 1, name: 'Vite Creators', type: 'group', lastMessage: 'Let\'s release v8.0', time: '10:30 AM', unread: 2 },
  { id: 2, name: 'Saiyantha', type: 'private', lastMessage: 'Are we doing the presentation tomorrow?', time: 'Yesterday', unread: 0 },
  { id: 3, name: 'Global Chat', type: 'group', lastMessage: 'Hello everyone!', time: 'Monday', unread: 5 },
];

export default function ChatHistory() {
  const navigate = useNavigate();
  const [searchTerm, setSearchTerm] = useState('');

  const filteredChats = mockChats.filter(chat => 
    chat.name.toLowerCase().includes(searchTerm.toLowerCase())
  );

  return (
    <div className="history-container">
      <div className="history-sidebar glass-panel">
        <div className="history-header">
          <h2>Chats</h2>
          <button className="new-chat-btn">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
              <line x1="12" y1="5" x2="12" y2="19"></line>
              <line x1="5" y1="12" x2="19" y2="12"></line>
            </svg>
          </button>
        </div>
        
        <div className="search-bar">
          <input 
            type="text" 
            placeholder="Search chats..." 
            value={searchTerm}
            onChange={(e) => setSearchTerm(e.target.value)}
          />
        </div>

        <div className="chat-list">
          {filteredChats.map(chat => (
            <div 
              key={chat.id} 
              className="chat-item"
              onClick={() => navigate(`/chat/${chat.id}`)}
            >
              <div className="chat-avatar">
                {chat.name.charAt(0)}
              </div>
              <div className="chat-info">
                <div className="chat-row-top">
                  <h4>{chat.name}</h4>
                  <span className="time">{chat.time}</span>
                </div>
                <div className="chat-row-bottom">
                  <p>{chat.lastMessage}</p>
                  {chat.unread > 0 && <span className="unread-badge">{chat.unread}</span>}
                </div>
              </div>
            </div>
          ))}
          {filteredChats.length === 0 && (
            <div className="no-chats">No chats found.</div>
          )}
        </div>
      </div>
    </div>
  );
}
