import Table from 'react-bootstrap/Table';

const ReactTable = (props) => {
  const {
    getTableProps,
    headerGroups,
    getTableBodyProps,
    rows,
    prepareRow
  } = props.tableProps;

  return (
    <Table hover size="sm" {...getTableProps({style: {whiteSpace: 'nowrap', overflow: 'auto'}})}>
      <thead>
        {headerGroups.map(headerGroup => (
          <tr {...headerGroup.getHeaderGroupProps()}>
            {headerGroup.headers.map(column => (
              <th {...column.getHeaderProps(column.getSortByToggleProps())}>
                {column.render('Header')}
                <span>
                  {column.isSorted ?
                    column.isSortedDesc? ' ⬇': ' ⬆'
                    : ''
                  }
                </span>
              </th>
            ))}
          </tr>
        ))}
      </thead>
      <tbody {...getTableBodyProps()}>
        {rows.length
        ? rows.map((row, i) => {
          prepareRow(row)
          return (
            <tr {...row.getRowProps()}>
              {row.cells.map(cell => {
                return <td {...cell.getCellProps()}>{cell.render('Cell')}</td>
              })}
            </tr>
          )
        })
        : <tr>
            <td colSpan={props.tableProps.columns.length}
             style={{textAlign: 'center', color: 'rgba(0, 0, 0, 0.38)'}}
            >
              {props.loading? 'Loading items...': 'No data available'}
            </td>
          </tr>
        }
      </tbody>
    </Table>
  );
}

export default ReactTable;