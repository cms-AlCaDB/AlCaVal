import React from 'react';
import Container from 'react-bootstrap/Container';
import Nav from 'react-bootstrap/Nav';
import Navbar from 'react-bootstrap/Navbar';
import './NavBar.css';
import useUserRole from '../utils/UserRole';

const NavBar = () => {
  const userUtil = useUserRole();
  // const [userInfo, setUserInfo] = React.useState({'fullname': 'loading'});
  // React.useEffect(() => {setUserInfo(userUtil.getUserInfo); console.log('NavBar UseState used')}, [userUtil]);
  console.log('NAVBAR rendered')
  return (
    <>
    <Navbar bg="light" expand="lg">
      <Container fluid>
        <Navbar.Brand href="#home" title="Home" style={{alignContent: 'left'}}><img src="Test" height="24"/><font face = "Wildwest"><strong>AlCa</strong>Val</font></Navbar.Brand>
        <Navbar.Toggle aria-controls="basic-navbar-nav" />
        <Navbar.Collapse id="basic-navbar-nav">
          <Nav className="me-auto">
            <Nav.Link href="/tickets" title="List of tickets">Tickets</Nav.Link>
            <Nav.Link href="/relvals" title="List of relvals">Relvals</Nav.Link>
            <Nav.Link href="/dqm" title="DQM plots comparison">DQM</Nav.Link>
            <Nav.Link href="/dashboard" title='Show dashboard'>Dashboard</Nav.Link>
          </Nav>
        </Navbar.Collapse>
        <Navbar.Collapse>
              <Navbar.Text style={{marginLeft: 'auto'}}>
                Signed in as: <a href="/api/get/user_info">'userInfo.fullname'</a>
              </Navbar.Text>
        </Navbar.Collapse>
      </Container>
    </Navbar>
    </>
  );
}

export default NavBar;
