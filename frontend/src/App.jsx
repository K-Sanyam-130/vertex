import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import LoginPage from './pages/LoginPage';
import Dashboard from './pages/Dashboard';
import './index.css';

const API_URL = 'http://localhost:3001';

function App() {
  return (
    <Router>
      <Routes>
        <Route path="/" element={<Navigate to="/login" replace />} />
        <Route path="/login" element={<LoginPage apiUrl={API_URL} />} />
        <Route path="/dashboard" element={<Dashboard apiUrl={API_URL} />} />
      </Routes>
    </Router>
  );
}

export default App;
