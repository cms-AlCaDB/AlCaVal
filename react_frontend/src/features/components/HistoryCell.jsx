import React from 'react';
import dateFormat from 'dateformat';
import './HistoryCell.css';

const niceDate = (time) => {
  return dateFormat(new Date(time * 1000), 'yyyy-mm-dd HH:MM:ss');
}

const historyValue = (entry) => {
  let value = entry.value;
  if (typeof value === 'string' || value instanceof String) {
    return value;
  }
  let action = entry.action;
  if ((action === 'update' || action == 'created_relvals') && value instanceof Array) {
    return '<pre>' + value.join(',\n') + '</pre>';
  }
  if (action === 'rename' && value instanceof Array) {
    return value.join(' -> ');
  }
  return '<pre>' + JSON.stringify(value, null, 2) + '</pre>';
}

const HistoryCell = (props) => {
  return (
    <table className="history">
      <thead>
        <tr>
          <th>Time</th>
          <th>User</th>
          <th>Action</th>
          <th>Value</th>
        </tr>
      </thead>
      <tbody>
      {
        React.Children.toArray(
          props.row.history.map((entry) => {
            return (
              <tr>
                <td>{niceDate(entry.time)}</td>
                <td>{entry.user}</td>
                <td>{entry.action}</td>
                <td dangerouslySetInnerHTML={{__html: historyValue(entry)}}></td>
              </tr>
            );
          })
        )
      }
      </tbody>
    </table>
  );
}

export default HistoryCell;