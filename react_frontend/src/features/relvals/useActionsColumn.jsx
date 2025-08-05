import HistoryCell from "../components/HistoryCell";
import StepCell from "../components/StepCell";
import './RelvalTable.css';
import axios from "axios";
import timeSince from "../utils/timeSince";
import { Button } from "react-bootstrap";

export const getHiddenColumns = (Shown, tableColumns) => {
  let shown = Shown.toString()
  return tableColumns
  .filter((item, idx) => {
    if (shown[idx] === "0"){
      return true;
    } else {
      return false;
    }
  }).map(item => item.accessor);
}

const makeDASLink = (dataset) => (`https://cmsweb.cern.ch/das/request?view=list&limit=50&instance=prod/global&input=dataset=${dataset}`);

// Fetching column headers also returning formatted cells alongwith handle methods
export const useColumns = (state, role, dispatch) => {
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
    dialog.description = "Are you sure you want to move "+ (itemsTobeDeleted.length>1?("selected "+itemsTobeDeleted.length+ " relvals"): itemsTobeDeleted+ " relval")+" to previous status?";
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
    dialog.description = "Are you sure you want to move "+ (itemsTobeDeleted.length>1?("selected "+itemsTobeDeleted.length+ " relvals"): itemsTobeDeleted+ " relval")+" to next status?";
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

  const updateWorkflows = (e, data) => {
    e.preventDefault();
    axios.post('api/relvals/update_workflows', data)
    .then(res => console.log('workflows updated'))
    .catch(err => console.log('Error updating workflows: ', err))
  }

  var tableColumns = [
    {
      Header: 'Prep ID',
      accessor: 'prepid',
      visible: 1,
      Cell: ({row}) => {
        let name = 'prepid';
        return (
          <a
            href={`/relvals?${name}=${row.values[name]}`}
            title={`Show all relvals with Batch Name: ${row.values[name]}`}
          >
            {row.values[name]}
          </a>
        );
      },
      aggregate: 'uniqueCount',
      Aggregated: ({ value }) => `${value} Brands`,
    },
    {
      Header: 'Actions',
      accessor: '_actions',
      visible: 1,
      Cell: ({row}) => 
        <ActionsCell
          row={row}
          handlePrevious={handlePrevious}
          handleDelete={handleDelete}
          handleNext={handleNext}
          updateWorkflows={updateWorkflows}
          role={role}
        />
    },
    {
      Header: 'Status',
      accessor: 'status',
      visible: 1,
      Cell: ({row}) =>
        <span>
          <a
            href={`/relvals?status=${row.values['status']}`}
            title={`Show all relval with status ${row.values['status']}`}
          >
            {row.values['status']}
          </a>
          <a style={{marginLeft: '2px'}} href={`/relvals/local_test_result/${row.id}`} rel="noreferrer noopener" target="_blank"><i className="bi bi-link-45deg"></i></a>
        </span>
    },
    {
      Header: 'Jira ticket',
      accessor: 'jira_ticket',
      visible: 1,
      Cell: ({row}) => 
        <span>
          <a
            href={`/relvals?jira_ticket=${row.values['jira_ticket']}`}
            title={`Show all relval with jira ticket- ${row.values['jira_ticket']}`}
          >
            {row.values['jira_ticket']!='None'? row.values['jira_ticket']: 'None'}
          </a>
          {row.values['jira_ticket']!='None'?
            <a style={{paddingLeft: '4px'}} href={`https://its.cern.ch/jira/browse/${row.values['jira_ticket']}`} rel="noreferrer noopener" target="_blank"><i className="bi bi-box-arrow-up-right"/></a>
            : null
          }
        </span>
    },
    {
      Header: 'Batch Name',
      accessor: 'batch_name',
      visible: 1,
      Cell: ({row}) => {
        let name = 'batch_name';
        return (
          <a
            href={`/relvals?${name}=${row.values[name]}`}
            title={`Show all relvals with Batch Name: ${row.values[name]}`}
          >
            {row.values[name]}
          </a>
        );
      }
    },
    {
      Header: 'Campaign',
      accessor: 'campaign_timestamp',
      visible: 1,
      Cell: ({row}) => {
        let name = 'campaign_timestamp';
        return (
          !row.values[name]? <span>Not set</span>
          :<a
            href={`/relvals?campaign_timestamp=${row.values[name]}&cmssw_release=${row.values.cmssw_release}&batch_name=${row.values.batch_name}`}
            title={`Show relvals with campaign`}
          >
            {row.values.prepid+'-'+row.values[name]}
          </a>
        );
      }
    },
    {
      Header: 'Notes',
      accessor: 'notes',
      visible: 0,
      Cell: ({row}) => 
        <pre>
          {row.values['notes']}
        </pre>
    },
    {
      Header: 'Workflow',
      accessor: 'workflow_id',
      visible: 0,
      Cell: ({row}) => (
      <span>
        <a
          href={`/relvals?workflow_id=${row.values['workflow_id']}`}
          title={`Show all relvals with memory: ${row.values['workflow_id']}`}
        >
          {`${row.values['workflow_id']} `}
        </a>
        ({row.original.workflow_name})
      </span>)
    },
    {
      Header: 'CMSSW Release',
      accessor: 'cmssw_release',
      visible: 0,
      Cell: ({row}) => {
        let name = 'cmssw_release';
        return (
          <a
            href={`/relvals?${name}=${row.values[name]}`}
            title={`Show all relvals with release: ${row.values[name]}`}
          >
            {row.values[name]}
          </a>
        );
      }
    },
    {
      Header: 'Cores',
      accessor: 'cpu_cores',
      visible: 1,
      Cell: ({row}) => row.values['cpu_cores']
    },
    {
      Header: 'Memory',
      accessor: 'memory',
      visible: 1,
      Cell: ({row}) => {
        let name = 'memory';
        return (
          <a
            href={`/relvals?${name}=${row.values[name]}`}
            title={`Show all relvals with memory: ${row.values[name]}`}
          >
            {row.values[name]}
          </a>
        );
      }
    },
    {
      Header: 'Matrix',
      accessor: 'matrix',
      visible: 1,
      Cell: ({row}) => row.values['matrix']
    },
    {
      Header: 'Fragment',
      accessor: 'fragment',
      visible: 0,
      Cell: ({row}) => row.values['fragment']
    },
    {
      Header: 'History',
      accessor: 'history',
      visible: 0,
      Cell: ({row}) => (<HistoryCell row={row.original}></HistoryCell>),
      aggregate: 'uniqueCount',
      Aggregated: ({ value }) => `${value} Brands`,
    },
    {
      Header: 'Label',
      accessor: 'label',
      visible: 0,
      Cell: ({row}) => row.values['label']
    },
    {
      Header: 'Size per Event',
      accessor: 'size_per_event',
      visible: 0,
      Cell: ({row}) => row.values['size_per_event']
    },
    {
      Header: 'Time per Event',
      accessor: 'time_per_event',
      visible: 0,
      Cell: ({row}) => row.values['time_per_event']
    },
    {
      Header: 'Output datasets',
      accessor: 'output_datasets',
      visible: 0,
      Cell: ({row}) => (
        <ul>
          {
          row.original.output_datasets.map(dataset=> (
            <li key={dataset}>
              <a target="_blank" title="Open dataset in DAS" href={makeDASLink(dataset)}>{dataset}</a>
            </li>
          ))
          }
        </ul>
      ),
    },
    {
      Header: 'Steps',
      accessor: 'steps',
      visible: 0,
      Cell: ({row}) => <StepCell row={row}/>,
    },
    {
      Header: 'Workflows (jobs in ReqMgr2)',
      accessor: 'workflows',
      visible: 1,
      Cell: ({row}) => {
        return (
          <ol>
          {
            row.original.workflows.map(workflow => 
              <li key={workflow.name}>
                <a target="_blank" title="Open workflow in ReqMgr2" href={`https://cmsweb.cern.ch/reqmgr2/fetch?rid=${workflow.name}`}>{workflow.name}</a>
                <small style={{color: 'gray'}}> open in:</small> <a target="_blank" title="Open workflow in Stats2" href={`https://cms-pdmv.cern.ch/stats?workflow_name=${workflow.name}`}>Stats2</a>
		if (typeof workflow.output_datasets !== "undefined")
			{
	                  workflow.output_datasets.map(dataset =>
	                    <li key={dataset.name}>
	                      <div>
	                        <small style={{color: 'gray'}}>datatier: </small> {dataset.name.split('/').pop()}
	                        <small style={{letterSpacing: "-0.1px"}}><a target="_blank" title="Open dataset in DAS" href={()=>makeDASLink(dataset.name)}>{dataset.name}</a></small>
	                      </div>
	                    </li>
	                  )
	                }
                <br/>
                <small style={{color: 'gray'}}>Last status: </small> <span style={{color: 'brown'}}>{workflow.status_history[workflow.status_history.length - 1].status}</span>
                <small style={{color: 'gray'}}> was set </small> { timeSince(new Date(workflow.status_history[workflow.status_history.length - 1].time*1000 ))}
                <small style={{color: 'gray'}}> ({ new Date( workflow.status_history[workflow.status_history.length - 1].time*1000 ).toLocaleString()}) </small>
              </li>
            )
          }
          </ol>
        )}
    },
    {
      Header: 'DQM Links',
      accessor: 'test',
      visible: 0,
      Cell: ({row}) => (
        <ul>
          {
          row.original.output_datasets.map(dataset=> (
            <li key={dataset}>
              <a target="_blank" title="Open dataset in DAS" href={makeDASLink(dataset)}>{dataset}</a>
            </li>
          ))
          }
        </ul>
      ),
    },
    {
      Header: 'Steps',
      accessor: 'steps',
      visible: 0,
      Cell: ({row}) => <StepCell row={row}/>,
    },
  ]

  return {tableColumns, handleDelete, handleNext, handlePrevious, updateWorkflows};
}

const ActionsCell = (props) => {
  const {row, handleDelete, handleNext, handlePrevious, updateWorkflows, role} = props;
  return (
    <div className="actions">
      {role('manager')?
        <a href={`relvals/edit?prepid=${row.original.prepid}`}>Edit</a>
        : null
      }
      {(row.original.status === 'new' && role('manager'))?
        <a className="action-button" role="button" onClick={()=>handleDelete([row.original.prepid])}>Delete</a>
        :null
      }
      {role('manager')?
        <a href={`relvals/edit?clone=${row.original.prepid}`} title="Clone RelVal">Clone</a>
        : null
      }
      <a href={`api/relvals/get_cmsdriver/${row.original.prepid}`} title="Show cmsDriver.py command for this RelVal">cmsDriver</a>
      <a href={`api/relvals/get_dict/${row.original.prepid}`} title="Show JSON dictionary for ReqMgr2">Job dict</a>
      {role('manager')?
        <a className="action-button" role="button" onClick={()=>handlePrevious([row.original.prepid])} title="Move to previous status">Previous</a>
        : null
      }
      {role('manager')?
        <a className="action-button" role="button" onClick={()=>handleNext([row.original.prepid])} title="Move to next status">Next</a>
        : null
      }
      {(row.original.status === 'submitted' || row.original.status === 'done' || row.original.status === 'archived')?
        <a target={'_blank'} href={`https://cms-pdmv.cern.ch/stats?prepid=${row.original.prepid}`} title="Show workflows of this RelVal in Stats2">Stats2</a>
        : null
      }
      <a href={`tickets?created_relvals=${row.original.prepid}`} title="Show ticket that was used to create this RelVal">Ticket</a>
      {(row.original.status === 'submitted' && role('manager'))?
        <a onClick={(e)=>updateWorkflows(e, [row.original.prepid])} href="#" title='Update RelVal information from ReqMgr2'>
          Update Workflows
        </a>
        : null
      }
    </div>
  );
}
