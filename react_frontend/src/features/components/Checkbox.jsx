import React from 'react';

export const IndeterminateCheckbox = React.forwardRef(
  ({ indeterminate, ...rest }, ref) => {
    const defaultRef = React.useRef()
    const resolvedRef = ref || defaultRef

    React.useEffect(() => {
      resolvedRef.current.indeterminate = indeterminate
    }, [resolvedRef, indeterminate])

    return (
      <React.Fragment>
        <input type="checkbox" ref={resolvedRef} {...rest} />
      </React.Fragment>
    )
  }
)

const checkboxHook = hooks => (
  hooks.visibleColumns.push(columns => [
    {
      id: 'selection',
      Header: ({ getToggleAllRowsSelectedProps }) => (
        <div>
          <IndeterminateCheckbox {...getToggleAllRowsSelectedProps()} />
        </div>
      ),
      Cell: ({ row }) => (
        <div>
          <IndeterminateCheckbox {...row.getToggleRowSelectedProps()} />
        </div>
      ),
    },
    ...columns,
  ])
);

export const ColumnSelector = (props) => {
  const {allColumns, getToggleHideAllColumnsProps} = props.tableProps;

  return (
    <div className="row" style={{margin: '5px', boxShadow: '0 3px 1px -2px rgba(0,0,0,.2),0 2px 2px 0 rgba(0,0,0,.14),0 1px 5px 0 rgba(0,0,0,.12)'}}>
      <h4>Columns</h4>
      <div className="col-sm-6 col-md-3 col-lg-2 col-12">
        <IndeterminateCheckbox {...getToggleHideAllColumnsProps()} /> Toggle All
      </div>
      {allColumns.filter(m => typeof(m.Header) == "string" && m.id !== "prepid").map(column => (
        <div key={column.id} className="col-sm-6 col-md-3 col-lg-2 col-12">
          <label>
            <input type="checkbox" {...column.getToggleHiddenProps()}/>{' '}
            {column.Header}
          </label>
        </div>
        ))}
      <br />
    </div>
  );
}

export default checkboxHook;