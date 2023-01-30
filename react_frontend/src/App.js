import logo from './logo.svg';
import './App.css';
import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { RelvalTable } from './features/relvals/RelvalTable';

function App() {

  return (
    <BrowserRouter>
      <Routes>
        <Route path="relvals" element={<RelvalTable />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
