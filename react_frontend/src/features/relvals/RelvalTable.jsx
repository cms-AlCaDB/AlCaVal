import React from 'react';
import { useTable, useSortBy, useRowSelect } from 'react-table';
import reducer, { initialState } from './reducer';
import * as actions from './actions';
import ReactTable from '../components/Table';
import checkboxHook, {ColumnSelector} from '../components/Checkbox';
import Pagination from '../components/Paginator';
import './RelvalTable.css';
import CustomModal from '../components/Modal';
import useUserRole from '../utils/UserRole';
import { useColumns, getHiddenColumns } from './useActionsColumn';
import NavBar from '../components/NavBar';

export const RelvalTable = () => {
  const [state, dispatch] = React.useReducer(reducer, initialState);
  const {role, userInfo} = useUserRole();
  const {tableColumns, handleDelete, handleNext, handlePrevious, updateWorkflows} = useColumns(role, dispatch);

  const tableData = React.useMemo(() => {
    return [...state.data]},
  [state.data]);

  const columns = React.useMemo(() => tableColumns, [userInfo]);

  const getRowId = React.useCallback(row => {
    return row._id
  }, []);

  const tableInstance = useTable(
    { columns: columns,
      data: tableData,
      initialState: { hiddenColumns: getHiddenColumns(state.shown, tableColumns), sortBy: state.sort?[{id: state.sort, desc: state.sort_asc}]: [] },
      manualPagination: true,
      manualSortBy: true,
      autoResetSelectedRows: true,
      autoResetPage: false,
      getRowId,
    },
    useSortBy,
    useRowSelect,
    checkboxHook,
  );

  function fetchData(){
    dispatch({type: "TOGGLE_LOADING_STATE", payload: true});
    let url = 'api/search?db_name=relvals';
    url += actions.getQueryString(state, true);

    fetch(url)
    .then(res => res.json())
    .then(
      data => {
        dispatch({
          type: "SET_DATA",
          data: data.response.results,
          totalRows: data.response.total_rows
        });
        dispatch({type: "REFRESH_DATA", payload: false});
        dispatch({type: "TOGGLE_LOADING_STATE", payload: false});
    })
    .catch(err => {
      console.log('Error fetching data' + err);
      dispatch({type: "TOGGLE_LOADING_STATE", payload: false});
      let dialog = {
        visible: true,
        title: 'Error fetching data',
        description: `${err}`,
        cancel: undefined,
        ok: undefined,
      };
      dispatch({type: "TOGGLE_MODAL_DIALOG", payload: dialog})
    });
  }

  React.useEffect(() => {
    fetchData();
  }, [state.currentPage, state.pageSize, state.refreshData, state.sort, state.sort_asc]);

  // Retain selected rows when page changes
  React.useEffect(() => {
    if (state.selectedItems[state.currentPage]){
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
    dispatch({type: "SET_SELECTED_ITEMS", payload: {}});
  }, [state.pageSize]);

  React.useEffect(() => {
    const shown = actions.updateShownFromVisible(tableInstance.columns);
    dispatch({type: "UPDATE_SHOWN", payload: shown});
  }, [tableInstance.visibleColumns]);

  // Dispach action when sortBy state of the tableInstance changes
  React.useEffect(() => {
    if (tableInstance.state.sortBy.length){ 
      dispatch(
        actions.updateSortState({sort: tableInstance.state.sortBy[0].id, sort_asc: !tableInstance.state.sortBy[0].desc})
      );
    } else {
      dispatch(
        actions.updateSortState({sort: null, sort_asc: null})
      );
    }
  }, [tableInstance.state.sortBy]);

  // Update query string
  React.useEffect(() => {
    const queryString = actions.getQueryString({...state});
    window.history.replaceState({}, '', `${window.location.pathname}?${queryString.slice(1)}`);
  }, [state.shown, state.currentPage, state.pageSize, state.sort, state.sort_asc]);

  return (
    <>
    <NavBar/>
    <div style={{paddingBottom: '52px', overflow: 'auto'}}>
      <div style={{display: 'flex'}}>
        <div style={{flex: '1 1 auto'}}>

          <div style={{width: 'calc(100vw - 32px)', position: 'sticky', left: '16px'}}>
            <h1 className='page-title'>RelVals</h1>
            <ColumnSelector
              tableProps={tableInstance}
              ></ColumnSelector>
          </div>

          <ReactTable tableProps={tableInstance} loading={state.loadingData}/>
        </div>
      </div>
      <footer
        className="footer fixed-bottom badge-light"
        style={{height: '52px'}}
        >
        {
        Object.values(state.selectedItems).flat().length > 0
        ? <div className='footer-item'>
          <div>Selected ({Object.values(state.selectedItems).flat().length }) items: </div>
          <div className='actions' style={{paddingLeft: '5px'}}>
            {role('manager')?<a className="action-button" role="button" onClick={()=>handleDelete(Object.values(state.selectedItems).flat().map(item =>item.id))} title="Delete selected RelVals">Delete</a>: null}
            {role('manager')?<a className="action-button" role="button" onClick={()=>handlePrevious(Object.values(state.selectedItems).flat().map(item =>item.id))} title="Move to previous status">Previous</a>: null}
            {role('manager')?<a className="action-button" role="button" onClick={()=>handleNext(Object.values(state.selectedItems).flat().map(item =>item.id))} title="Move to next status">Next</a>: null}
            {role('manager')?<a className='action-button' role='button' onClick={(e)=>updateWorkflows(e, Object.values(state.selectedItems).flat().map(item =>item.id))}>Update Workflows</a>: null}
          </div>
        </div>
        : <div className='footer-item'><a href="relvals/edit">New Relval</a></div>
        }
        <Pagination tableProps={tableInstance} reducer={[state, dispatch]}/>
      </footer>
      <CustomModal
        show={state.dialog.visible}
        onHide={() => dispatch({type: "TOGGLE_MODAL_DIALOG", payload: {visible: false}})}
        dialog={state.dialog}
      />
    </div>
    </>
  );
}