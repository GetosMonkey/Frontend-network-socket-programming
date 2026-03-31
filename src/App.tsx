import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import LoginSignup from './pages/LoginSignup/LoginSignup';
import ChatHistory from './pages/ChatHistory/ChatHistory';
import ChatView from './pages/ChatView/ChatView';
import './App.css';

function App() {
  return (
    <Router>
      <div className="app-container">
        <Routes>
          <Route path="/" element={<Navigate to="/login" replace />} />
          <Route path="/login" element={<LoginSignup />} />
          <Route path="/history" element={<ChatHistory />} />
          <Route path="/chat/:id" element={<ChatView />} />
        </Routes>
      </div>
    </Router>
  )
}

export default App;
