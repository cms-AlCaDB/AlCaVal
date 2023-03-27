import React from 'react';
import { Nav, Form } from 'react-bootstrap';

// Define a default UI for filtering
function GlobalFilter({
    preGlobalFilteredRows,
    globalFilter,
    setGlobalFilter,
  }) {
  const count = preGlobalFilteredRows.length
  const [value, setValue] = React.useState(globalFilter)

  const handleKeyDown = (e) => {
    if(e.key==='Enter'){
      setGlobalFilter(e.target.value);
    }
  }

  return (
    <Nav className="ms-auto me-1">
      <Form.Control
        type="search"
        value={value || ""}
        onChange={e => setValue(e.target.value)}
        onKeyDown={e=>handleKeyDown(e)}
        placeholder='Search here...'
        onBlur={e=>setGlobalFilter(e.target.value)}
      />
    </Nav>
  )
}

export default GlobalFilter;