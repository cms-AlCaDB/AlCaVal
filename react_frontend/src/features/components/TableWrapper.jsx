
export default function TableWrapper(props){
  return (
    <div style={{height: 'calc(100vh - 52px)', overflow: 'auto'}}>
      <div style={{display: 'flex'}}>
        <div style={{flex: '1 1 auto'}}>
          {props.children}
        </div>
      </div>
    </div>
  );
}