import React from 'react';
import { useTable, useSortBy, useRowSelect } from 'react-table';
import reducer, { initialState } from './reducer';
import * as actions from './actions';
import ReactTable from '../components/Table';
import checkboxHook, {ColumnSelector} from '../components/Checkbox';
import Pagination from '../components/Paginator';
import './RelvalTable.css';

export const RelvalTable = () => {
  const [state, dispatch] = React.useReducer(reducer, initialState);

  const tableData = React.useMemo(() => {
    console.log("tableData useMemo executed")
    return [...state.data]},
  [state.data]);

  const columns = React.useMemo(() => actions.fetchColumns(), []);

  const getRowId = React.useCallback(row => {
    return row._id
  }, []);

  const tableInstance = useTable(
    { columns: columns,
      data: tableData,
      initialState: { hiddenColumns: actions.getHiddenColumns(state.shown) },
      manualPagination: true,
      autoResetSelectedRows: true,
      autoResetPage: false,
      getRowId,
    },
    useSortBy,
    useRowSelect,
    checkboxHook,
  );

  React.useEffect(() => {
    let url = 'api/search?db_name=relvals';
    url += actions.getQueryString(state, true);
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

  // Retain selected rows when page changes
  React.useEffect(() => {
    if (state.selectedItems[state.currentPage]){
      console.log('Toggle rows')
      state.selectedItems[state.currentPage].map(
        rowid =>
        tableInstance.toggleRowSelected(rowid.id, true)
        );
    }
  }, [state.data]);

  // Update selectedItems when row is checked/unchecked
  React.useEffect(() => {
    dispatch(actions.setSelectedItems(state, tableInstance.selectedFlatRows));
  }, [tableInstance.selectedFlatRows]);

  // Reset selectedItems when page-size changes
  React.useEffect(() => {
    console.log('PageSize changed')
    dispatch({type: "SET_SELECTED_ITEMS", payload: {}});
  }, [state.pageSize]);

  React.useEffect(() => {
    const shown = actions.updateShownFromVisible(tableInstance.columns);
    dispatch({type: "UPDATE_SHOWN", payload: shown});
    console.log('handleChange UPDATED');
  }, [tableInstance.visibleColumns]);

  // Update query string
  React.useEffect(() => {
    const queryString = actions.getQueryString(state);
    window.history.replaceState({}, '', `/relvals?${queryString.slice(1)}`);
  }, [state.shown, state.currentPage, state.pageSize]);

  return (
    <div style={{height: 'calc(100vh - 52px)', overflow: 'auto'}}>
      <div style={{display: 'flex'}}>
        <div style={{flex: '1 1 auto'}}>

          <div style={{width: 'calc(100vw - 32px)', position: 'sticky', left: '16px'}}>
            <h1 className='page-title'>RelVals</h1>
            <ColumnSelector
              tableProps={tableInstance}
              ></ColumnSelector>
          </div>

          <ReactTable tableProps={tableInstance} />
          <button className='btn btn-secondary' onClick={()=>dispatch(actions.changePage(2))}>Change Page</button>
          <pre>
            <code>
              {
                JSON.stringify({
                  Selected: Object.values(state.selectedItems).flat()
                            .map(el => el.id),
                }, null, 2)
              }
            </code>
          </pre>
        </div>
      </div>
      <footer
        className="footer fixed-bottom badge-light"
        style={{height: '52px'}}
        >
        {
        Object.values(state.selectedItems).flat().length > 0
        ? <div className='footer-item'>Selected ({Object.values(state.selectedItems).flat().length }) items</div>
        : <div className='footer-item'><a href="relvals/edit">New Relval</a></div>
        }
        <Pagination tableProps={tableInstance} reducer={[state, dispatch]}/>
      </footer>
    </div>
  );
}