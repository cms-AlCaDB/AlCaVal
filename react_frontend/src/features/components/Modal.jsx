import Button from 'react-bootstrap/Button';
import Modal from 'react-bootstrap/Modal';

function CustomModal(props) {
  const {show, onHide, dialog} = props;
  return (
    <Modal
      show={show}
      onHide={onHide}
      size="lg"
      aria-labelledby="contained-modal-title-vcenter"
      centered
    >
      <Modal.Header closeButton>
        <Modal.Title id="contained-modal-title-vcenter">
          {dialog.title}
        </Modal.Title>
      </Modal.Header>
      <Modal.Body>
        {/* <h4></h4> */}
        <p>
          {dialog.description}
        </p>
      </Modal.Body>
      <Modal.Footer>
        <Button onClick={onHide}>{dialog.ok? 'Close': 'Dismiss'}</Button>
        {dialog.ok? <Button variant="danger" onClick={dialog.ok}>Go Ahead</Button>: null}
      </Modal.Footer>
    </Modal>
  );
}

export default CustomModal;