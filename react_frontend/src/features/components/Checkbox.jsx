import React from 'react';
import { Form } from 'react-bootstrap';

export const IndeterminateCheckbox = React.forwardRef(
  ({ indeterminate, ...rest }, ref) => {
    const defaultRef = React.useRef()
    const resolvedRef = ref || defaultRef

    React.useEffect(() => {
      resolvedRef.current.indeterminate = indeterminate
    }, [resolvedRef, indeterminate])

    return (
      <React.Fragment>
        <Form.Check type="checkbox" ref={resolvedRef} {...rest} />
      </React.Fragment>
    )
  }
)

const checkboxHook = hooks => (
  hooks.visibleColumns.push(columns => [
    {
      id: 'selection',
      Header: ({ getToggleAllRowsSelectedProps }) => (
        <div style={{textAlign: 'center'}}>
          <IndeterminateCheckbox {...getToggleAllRowsSelectedProps()} />
        </div>
      ),
      Cell: ({ row }) => (
        <div style={{textAlign: 'center'}}>
          <IndeterminateCheckbox {...row.getToggleRowSelectedProps()} />
        </div>
      ),
    },
    ...columns,
  ])
);

export const ColumnSelector = (props) => {
  const {allColumns, setHiddenColumns, getToggleHideAllColumnsProps} = props.tableProps;

  // Custom onChange method to make some column always visible
  const columnsToIgnoreToggle = ['selection', 'prepid'];
  const customHiddenColumnProps = getToggleHideAllColumnsProps({
    onChange: ()=>
      setHiddenColumns(
        oldcol => !oldcol.length
          ? allColumns.filter(m=>!columnsToIgnoreToggle.includes(m.id)).map(item=>item.id)
          : []
      )
  });

  return (
    <div className="row" style={{margin: '5px', boxShadow: '0 3px 1px -2px rgba(0,0,0,.2),0 2px 2px 0 rgba(0,0,0,.14),0 1px 5px 0 rgba(0,0,0,.12)'}}>
      <h4>Columns</h4>
      <div className="col-sm-6 col-md-3 col-lg-2 col-12">
        <IndeterminateCheckbox {...customHiddenColumnProps} label="Toggle All"/>
      </div>
      {allColumns.filter(m => !columnsToIgnoreToggle.includes(m.id)).map(column => (
        <div key={column.id} className="col-sm-6 col-md-3 col-lg-2 col-12">
          <IndeterminateCheckbox {...column.getToggleHiddenProps()} label={column.Header} />
        </div>
        ))}
      <br />
    </div>
  );
}

export default checkboxHook;