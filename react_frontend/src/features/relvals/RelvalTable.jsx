import React from 'react';
import { useTable, useSortBy, useRowSelect } from 'react-table';
import { useSearchParams } from 'react-router-dom'
import ReactTable from '../components/Table';
import TableWrapper from '../components/TableWrapper';
import reducer, { initialState } from './reducer';
import checkboxHook from '../components/Checkbox';
import * as actions from './actions';

export const RelvalTable = () => {
  const [state, dispatch] = React.useReducer(reducer, initialState);
  const [searchParams, setSearchParams] = useSearchParams();

  const tableData = React.useMemo(() => {
    console.log("tableData useMemo executed")
    return [...state.data]},
  [state.data]);

  const columns = React.useMemo(() => actions.fetchColumns(state.data[0]), [state.data]);

  const tableInstance = useTable(
    { columns: columns,
      data: tableData,
      manualPagination: true,
      autoResetSelectedRows: true,
      autoResetPage: false,
    },
    useSortBy,
    useRowSelect,
    checkboxHook,
  );

  React.useEffect(() => {
    actions.updateQueryString(state, searchParams, setSearchParams);

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
      <button className='btn btn-secondary' onClick={()=>dispatch(actions.changePage(2))}>Change Page</button>
      <pre>
        <code>
          {
            JSON.stringify({
              Selected: Object.values(tableInstance.selectedFlatRows).flat()
                        .map(el => el.values._id),
            }, null, 2)
          }
        </code>
      </pre>
    </TableWrapper>
  );
}