import React from 'react';
import {Nav, Container, Navbar} from 'react-bootstrap';
import useUserRole from '../utils/UserRole';

const NavBar = () => {
  const {userInfo} = useUserRole();
  return (
    <Navbar bg="light" expand="lg" fixed='top' style={{boxShadow: '0px 5px 5px -5px gray'}}>
      <Container fluid>
        <Navbar.Brand href="#home" title="Home" style={{alignContent: 'left'}}><img src="Test" height="24"/><font face = "Wildwest"><strong>AlCa</strong>Val</font></Navbar.Brand>
        <Navbar.Toggle aria-controls="basic-navbar-nav" />
        <Navbar.Collapse id="basic-navbar-nav">
          <Nav className="me-2">
            <Nav.Link href="/tickets" title="List of tickets">Tickets</Nav.Link>
          </Nav>
          <Nav className="me-2">
            <Nav.Link href="/relvals" title="List of relvals">Relvals</Nav.Link>
          </Nav>
          <Nav className="me-2">
            <Nav.Link href="/dqm" title="DQM plots comparison">DQM</Nav.Link>
          </Nav>
          <Nav className="me-2">
            <Nav.Link href="/dashboard" title='Show dashboard'>Dashboard</Nav.Link>
          </Nav>

          <Navbar.Text className='ms-auto'>
            Signed in as: <a href="/api/system/user_info">{userInfo.fullname}</a>
          </Navbar.Text>
        </Navbar.Collapse>
      </Container>
    </Navbar>
  );
}

export default NavBar;