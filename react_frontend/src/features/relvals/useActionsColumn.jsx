import HistoryCell from "../components/HistoryCell";
import './RelvalTable.css';

export const columnsProps = [
  {'dbName': 'prepid', 'displayName': 'PrepID', 'visible': 1, 'sortable': true,
   title: 'Show only this relval',
   href: '/relvals?prepid=KEYNAME'
  },
  {'dbName': '_actions', 'displayName': 'Actions', 'visible': 1},
  {'dbName': 'status', 'displayName': 'Status', 'visible': 1, 'sortable': true,
   title: 'Show all relval with status KEY_NAME',
   href: '/relvals?status=KEYNAME'
  },
  {'dbName': 'batch_name', 'displayName': 'Batch Name', 'visible': 1, 'sortable': true,
   title: 'Show all relvals with KEY_NAME batch name',
   href: '/relvals?batch_name=KEYNAME'
  },
  {'dbName': 'cmssw_release', 'displayName': 'CMSSW Release', 'visible': 1, 'sortable': true,
   title: 'Show all relvals with KEY_NAME release',
   href: '/relvals?cmssw_release=KEYNAME'
  },
  {'dbName': 'cpu_cores', 'displayName': 'CPU Cores', 'visible': 1, 'sortable': true, title: ''},
  {'dbName': 'matrix', 'displayName': 'Matrix', 'visible': 1, 'sortable': true, title: ''},
  {'dbName': 'memory', 'displayName': 'Memory', 'visible': 1, 'sortable': true, title: ''},
  {'dbName': 'notes', 'displayName': 'Notes', 'visible': 1, title: ''},
  {'dbName': '_workflow', 'displayName': 'Workflow', 'visible': 1, 'sortable': true, title: ''},
  {'dbName': 'campaign_timestamp', 'displayName': 'Campaign', 'visible': 0, 'sortable': true, title: 'Show relvals with this campaign ID'},
  {'dbName': 'fragment', 'displayName': 'Fragment', 'visible': 0, title: ''},
  {'dbName': '_gpu', 'displayName': 'GPU', 'visible': 0, title: ''},
  {'dbName': 'history', 'displayName': 'History', 'visible': 0, 'sortable': true, title: ''},
  {'dbName': 'label', 'displayName': 'Label', 'visible': 0, 'sortable': true, title: ''},
  {'dbName': 'output_datasets', 'displayName': 'Output Datasets', 'visible': 0, title: ''},
  {'dbName': 'sample_tag', 'displayName': 'Sample Tag', 'visible': 0, 'sortable': true, title: ''},
  {'dbName': 'size_per_event', 'displayName': 'Size per Event', 'visible': 0, 'sortable': true, title: ''},
  {'dbName': 'steps', 'displayName': 'Steps', 'visible': 0, title: ''},
  {'dbName': 'time_per_event', 'displayName': 'Time per Event', 'visible': 0, 'sortable': true, title: ''},
  {'dbName': 'workflows', 'displayName': 'Workflows (jobs in ReqMgr2)', 'visible': 0, title: ''},
];

const nonStringColumns = [
  // '_actions',
  '_workflow',
  '_gpu',
  // 'history',
  'output_datasets',
  'steps',
  'workflows'
];

export const getHiddenColumns = (Shown) => {
  let shown = Shown.toString();
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

// Fetching column headers also returning formatted cells alongwith handle methods
export const useColumns = (userUtil, dispatch) => {
  let dialog = {
    visible: false,
    title: '',
    description: '',
    cancel: undefined,
    ok: undefined,
  };

  const showError = (title, description) => {
    let ddd = {
      visible: true,
      title: title,
      description: description,
      cancel: undefined,
      ok: undefined,
    };
    dispatch({type: "TOGGLE_MODAL_DIALOG", payload: ddd});
  }

  const handleDelete = (itemsTobeDeleted) => {
    dialog.visible = true;
    dialog.title = `Delete ${itemsTobeDeleted.length}`+(itemsTobeDeleted.length>1? " relvals?": " relval?");
    dialog.description = "Are you sure you want to delete " + (itemsTobeDeleted.length>1?("selected "+itemsTobeDeleted.length+ " relvals?"): itemsTobeDeleted+ " relval?");
    dialog.ok = function() {
        fetch('api/relvals/delete', {
          method: 'DELETE', 
          headers: {'Content-Type': 'application/x-www-form-urlencoded'},
          body: itemsTobeDeleted
        })
        .then(res => res.json())
        .then(data => {
          dispatch({type: "REFRESH_DATA", payload: true});
        })
        .catch(err => {
          showError('Error deleting relvals', err.toString());
        });
        dispatch({type: "TOGGLE_MODAL_DIALOG", payload: {visible: false}});
      };
    dispatch({type: "TOGGLE_MODAL_DIALOG", payload: dialog});
  }

  const handlePrevious = (itemsTobeDeleted) => {
    dialog.visible = true;
    dialog.title = `Move ${itemsTobeDeleted.length}`+(itemsTobeDeleted.length>1? " relvals": " relval")+" to previous state?";
    dialog.description = "Are you sure you want to move "+ (itemsTobeDeleted.length>1?("selected "+itemsTobeDeleted.length+ " relvals"): itemsTobeDeleted+ " relval?")+" to previous status?";
    dialog.ok = function() {
        fetch('api/relvals/previous_status', {
          method: 'POST', 
          body: JSON.stringify(itemsTobeDeleted)
        })
        .then(res => res.json())
        .then(data => dispatch({type: "REFRESH_DATA", payload: true}))
        .catch(err => showError('Error moving relvals to previous status', err.toString())); 
        dispatch({type: "TOGGLE_MODAL_DIALOG", payload: {visible: false}});
      };
    dispatch({type: "TOGGLE_MODAL_DIALOG", payload: dialog});
  }

  const handleNext = (itemsTobeDeleted) => {
    dialog.visible = true;
    dialog.title = `Move ${itemsTobeDeleted.length}` +(itemsTobeDeleted.length>1? " relvals": " relval")+ " to next state?";
    dialog.description = "Are you sure you want to move "+ (itemsTobeDeleted.length>1?("selected "+itemsTobeDeleted.length+ " relvals"): itemsTobeDeleted+ " relval")+" relval to next status?";
    dialog.ok = function() {
        fetch('api/relvals/next_status', {
          method: 'POST',
          headers: {'Content-Type': 'application/x-www-form-urlencoded'},
          body: itemsTobeDeleted
        })
        .then(res => res.json())
        .then(data => dispatch({type: "REFRESH_DATA", payload: true}))
        .catch(err => showError('Error moving relvals to next status', err.toString())); 
        dispatch({type: "TOGGLE_MODAL_DIALOG", payload: {visible: false}});
      };
    dispatch({type: "TOGGLE_MODAL_DIALOG", payload: dialog});
  }

  const tableColumns = columnsProps.filter(column => !nonStringColumns.includes(column.dbName))
  .map((item) => {
      if (item.dbName === 'history') {
        return { Header: item.displayName,
                 accessor: item.dbName,
                 Cell: ({ row }) => {
                  return (<HistoryCell row={row.original}></HistoryCell>);
                 }
               };
      } else if(item.dbName === '_actions') {
        return { Header: item.displayName,
                 accessor: item.dbName,
                 Cell: ({row}) => <ActionsCell 
                                    row={row}
                                    handlePrevious={handlePrevious}
                                    handleDelete={handleDelete}
                                    handleNext={handleNext}
                                    userUtil={userUtil}/>
               }
      } else if(item.dbName === 'status'){
        return { Header: item.displayName,
                 accessor: item.dbName,
                 Cell: ({row}) => 
                  <span>
                    <a
                      href={item.href?item.href.replace('KEYNAME', row.original[item.dbName]):''}
                      title={item.title.replace("KEY_NAME", row.original[item.dbName])}
                    >
                    {row.original[item.dbName]}
                    </a>
                    <a style={{marginLeft: '2px'}} href={`/relvals/local_test_result/${row.id}`} rel="noreferrer noopener" target="_blank"><i className="bi bi-link-45deg"></i></a>
                  </span>
               }
      } else {
        return {
          Header: item.displayName,
          accessor: item.dbName,
          Cell: ({row}) =>
          <a
            href={item.href?item.href.replace('KEYNAME', row.original[item.dbName]):''}
            title={item.title.replace("KEY_NAME", row.original[item.dbName])}
          >
            {row.original[item.dbName]}
          </a>,
          visible: item.visible
        };
      }
    }
  );

  return {tableColumns, handleDelete, handleNext, handlePrevious};
}

const ActionsCell = (props) => {
  const {row, handleDelete, handleNext, handlePrevious, userUtil} = props;
  return (
    <div className="actions">
      {userUtil.role('manager')?<a href={`relvals/edit?prepid=${row.original.prepid}`}>Edit</a>: null}
      {(row.original.status === 'new' && userUtil.role('manager'))?<a className="action-button" role="button" onClick={()=>handleDelete([row.original.prepid])}>Delete</a>:null}
      {userUtil.role('manager')?<a href={`relvals/edit?clone=${row.original.prepid}`} title="Clone RelVal">Clone</a>: null}
      <a href={`api/relvals/get_cmsdriver/${row.original.prepid}`} title="Show cmsDriver.py command for this RelVal">cmsDriver</a>
      <a href={`api/relvals/get_dict/${row.original.prepid}`} title="Show JSON dictionary for ReqMgr2">Job dict</a>
      {userUtil.role('manager')?<a className="action-button" role="button" onClick={()=>handlePrevious([row.original.prepid])} title="Move to previous status">Previous</a>: null}
      {userUtil.role('manager')?<a className="action-button" role="button" onClick={()=>handleNext([row.original.prepid])} title="Move to next status">Next</a>: null}
      {(row.original.status === 'submitted' || row.original.status === 'done' || row.original.status === 'archived')?<a target={'_blank'} href={`https://cms-pdmv.cern.ch/stats?prepid=${row.original.prepid}`} title="Show workflows of this RelVal in Stats2">Stats2</a>: null}
      <a href={`tickets?created_relvals=${row.original.prepid}`} title="Show ticket that was used to create this RelVal">Ticket</a>
    </div>
  );
}