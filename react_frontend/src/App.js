import logo from './logo.svg';
import './App.css';
import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { RelvalTable } from './features/relvals/RelvalTable';

function App() {
  React.useEffect(() =>{
    fetch('/api/search?db_name=tickets', 
      { mode: 'cors',
        headers: {"Access-Control-Allow-Origin": "*"}
      }
    )
    .then(res => res.json())
    .then(data => console.log(data))
  }, []);

  return (
    <BrowserRouter>
      <Routes>
        <Route path="relvals" element={<RelvalTable />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
