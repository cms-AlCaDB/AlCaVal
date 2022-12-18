import React from 'react';
import { useTable, useSortBy } from 'react-table';
import ReactTable from '../components/Table';
import TableWrapper from '../components/TableWrapper';
import reducer, { initialState } from './reducer';

export const RelvalTable = () => {
  const [state, dispatch] = React.useReducer(reducer, initialState);

  const tableData = React.useMemo(() => {
    console.log("tableData useMemo executed")
    return [...state.data]},
  [state.data]);

  const columns = React.useMemo(() => 
    state.data[0]
    ? Object.keys(state.data[0])
        .filter((key) => typeof(state.data[0][key]) == "string")
        .map((key) => {
          const header = key.split("_").map(l=> l.charAt(0).toUpperCase()+l.slice(1)).join(' ')
          return { Header: header, accessor: key };
        })
    : [],
    [state.data]);

  const tableInstance = useTable(
    { columns: columns,
      data: tableData,
      manualPagination: true,
      autoResetSelectedRows: true,
      autoResetPage: false,
    },
    useSortBy,
  );

  React.useEffect(() => {
    let url = 'api/search?db_name=relvals';
    url += `&limit=${state.pageSize}&page=${state.currentPage}`;
    fetch(url)
    .then(res => res.json())
    .then(
      data => {
        console.log("Fetched data: ", data.response.results);
        dispatch({
          type: "SET_DATA", 
          data: data.response.results,
          totalRows: data.response.total_rows
        })
    })
    .catch(err => console.log('Error fetching data' + err));

  }, [state.currentPage, state.pageSize]);

  return (
    <TableWrapper>
      <ReactTable tableProps={tableInstance} />
    </TableWrapper>
  );
}