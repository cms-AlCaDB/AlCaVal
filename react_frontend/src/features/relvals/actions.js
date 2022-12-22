import HistoryCell from "../components/HistoryCell";

export const columnsProps = [
  {'dbName': 'prepid', 'displayName': 'PrepID', 'visible': 1, 'sortable': true, 'title': 'Show only this relval '},
  {'dbName': '_actions', 'displayName': 'Actions', 'visible': 1},
  {'dbName': 'status', 'displayName': 'Status', 'visible': 1, 'sortable': true, 'title': 'Show all relval with status '},
  {'dbName': 'batch_name', 'displayName': 'Batch Name', 'visible': 1, 'sortable': true},
  {'dbName': 'cmssw_release', 'displayName': 'CMSSW Release', 'visible': 1, 'sortable': true},
  {'dbName': 'cpu_cores', 'displayName': 'CPU Cores', 'visible': 1, 'sortable': true},
  {'dbName': 'matrix', 'displayName': 'Matrix', 'visible': 1, 'sortable': true},
  {'dbName': 'memory', 'displayName': 'Memory', 'visible': 1, 'sortable': true},
  {'dbName': 'notes', 'displayName': 'Notes', 'visible': 1},
  {'dbName': '_workflow', 'displayName': 'Workflow', 'visible': 1, 'sortable': true},
  {'dbName': 'campaign_timestamp', 'displayName': 'Campaign', 'visible': 0, 'sortable': true},
  {'dbName': 'fragment', 'displayName': 'Fragment', 'visible': 0},
  {'dbName': '_gpu', 'displayName': 'GPU', 'visible': 0},
  {'dbName': 'history', 'displayName': 'History', 'visible': 0, 'sortable': true},
  {'dbName': 'label', 'displayName': 'Label', 'visible': 0, 'sortable': true},
  {'dbName': 'output_datasets', 'displayName': 'Output Datasets', 'visible': 0},
  {'dbName': 'sample_tag', 'displayName': 'Sample Tag', 'visible': 0, 'sortable': true},
  {'dbName': 'size_per_event', 'displayName': 'Size per Event', 'visible': 0, 'sortable': true},
  {'dbName': 'steps', 'displayName': 'Steps', 'visible': 0},
  {'dbName': 'time_per_event', 'displayName': 'Time per Event', 'visible': 0, 'sortable': true},
  {'dbName': 'workflows', 'displayName': 'Workflows (jobs in ReqMgr2)', 'visible': 0},
];

const nonStringColumns = [
  '_actions',
  '_workflow',
  '_gpu',
  // 'history',
  'output_datasets',
  'steps',
  'workflows'
];

export const getHiddenColumns = (Shown) => {
  let shown = Number(Shown).toString(2);
  return columnsProps
  .filter(column => !nonStringColumns.includes(column.dbName))
  .filter((item, idx) => {
    if (shown[idx] === "0"){
      return true;
    } else if (!item.dbName === 'prepid') {
      return false;
    } else {
      return false;
    }
  }).map(item => item.dbName);
}

// Fetching column headers
export const fetchColumns = () => {
  return columnsProps.filter(column => !nonStringColumns.includes(column.dbName))
  .map((item) => {
      if (item.dbName === 'history') {
        return { Header: item.displayName,
                 accessor: item.dbName,
                 Cell: ({ row }) => {
                  return (<HistoryCell row={row.original}></HistoryCell>);
                 }
               };
      } else {
        return {
          Header: item.displayName,
          accessor: item.dbName,
          Cell: ({row}) => <a href="test" title={item.title? item.title + row.original[item.dbName]: 'test'}>{row.original[item.dbName]}</a>,
          visible: item.visible
        };
      }
    }
  );
}

export const changePage = (page) => {
  return {type: "CHANGE_PAGE", payload: page};
}

export const setPageSize = (size) => {
  return {type: "SET_PAGE_SIZE", payload: size};
}

export const setSelectedItems = (state, selectedFlatRows) => {
  const newSelectedItems = {...state.selectedItems};
  newSelectedItems[state.currentPage] = [...selectedFlatRows];
  return {type: "SET_SELECTED_ITEMS", payload: newSelectedItems};
}

export const updateQueryString = (state, tableInstance, searchParams, setSearchParams) => {
  searchParams.set('limit', state.pageSize);
  searchParams.set('page', state.currentPage);
  const query = Object.fromEntries(searchParams);
  if (!('shown' in query)) {
    const shown = updateShownFromVisible(tableInstance.columns);
    query['shown'] = parseInt(shown, 2);
  }
  setSearchParams(query);
  return {type: "UPDATE_SHOWN", payload: query.shown }
}

export const updateShownFromVisible = (columns) => {
  let shown = "1";
  columns.filter(col => !['prepid', 'selection'].includes(col.id)).forEach(entry => {
    if (entry.isVisible) {
      shown = shown.concat("1");
    } else {
      shown = shown.concat("0");
    }
  });
  return shown;
}