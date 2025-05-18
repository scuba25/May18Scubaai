import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Route, Switch, Redirect } from 'react-router-dom';
import { ToastContainer, toast } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

// Components
import Login from './components/Login';
import Chat from './components/Chat';
import Sidebar from './components/Sidebar';
import Settings from './components/Settings';

// Services
import { getUser, checkTokenExpiry } from './services/authService';

function App() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [sidebarOpen, setSidebarOpen] = useState(true);
  
  // Check authentication status on app load
  useEffect(() => {
    const checkAuth = async () => {
      const token = localStorage.getItem('accessToken');
      
      if (!token) {
        setLoading(false);
        return;
      }
      
      // Check if token is expired
      if (checkTokenExpiry()) {
        setLoading(false);
        return;
      }
      
      try {
        const userData = await getUser();
        setUser(userData);
      } catch (error) {
        console.error('Error fetching user data:', error);
        localStorage.removeItem('accessToken');
        localStorage.removeItem('refreshToken');
      } finally {
        setLoading(false);
      }
    };
    
    checkAuth();
  }, []);
  
  // Handle login success
  const handleLoginSuccess = (userData) => {
    setUser(userData);
    toast.success('Login successful!');
  };
  
  // Handle logout
  const handleLogout = () => {
    localStorage.removeItem('accessToken');
    localStorage.removeItem('refreshToken');
    setUser(null);
    toast.info('Logged out successfully');
  };
  
  // Toggle sidebar
  const toggleSidebar = () => {
    setSidebarOpen(!sidebarOpen);
  };
  
  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-gray-100">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      </div>
    );
  }
  
  return (
    <Router>
      <div className="app bg-gray-100 min-h-screen">
        <ToastContainer position="top-right" autoClose={3000} />
        
        {user ? (
          // Authenticated layout
          <div className="flex h-screen">
            {sidebarOpen && (
              <div className="w-64 bg-white shadow-md">
                <Sidebar user={user} onLogout={handleLogout} />
              </div>
            )}
            
            <div className="flex-1 flex flex-col">
              <header className="bg-white shadow-sm p-4 flex items-center">
                <button 
                  onClick={toggleSidebar} 
                  className="mr-4 focus:outline-none"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
                  </svg>
                </button>
                <h1 className="text-xl font-semibold text-gray-800">ScubaAI</h1>
              </header>
              
              <main className="flex-1 overflow-auto p-4">
                <Switch>
                  <Route path="/chat/:conversationId?">
                    <Chat user={user} />
                  </Route>
                  <Route path="/settings">
                    <Settings user={user} />
                  </Route>
                  <Route exact path="/">
                    <Redirect to="/chat" />
                  </Route>
                </Switch>
              </main>
            </div>
          </div>
        ) : (
          // Unauthenticated layout
          <Switch>
            <Route path="/login">
              <Login onLoginSuccess={handleLoginSuccess} />
            </Route>
            <Route path="*">
              <Redirect to="/login" />
            </Route>
          </Switch>
        )}
      </div>
    </Router>
  );
}

export default App;
