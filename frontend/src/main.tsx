import React from 'react'
import ReactDOM from 'react-dom/client'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import App from './App'
import AppBuilder from './AppBuilder'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <BrowserRouter>
      <Routes>
        {/* App Builder as default */}
        <Route path="/" element={<AppBuilder />} />
        <Route path="/builder" element={<AppBuilder />} />

        {/* Streamlit launcher */}
        <Route path="/streamlit" element={<App />} />

        {/* Catch all - redirect to builder */}
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  </React.StrictMode>,
)
