import React from 'react';
import { useTable, useSortBy } from 'react-table';
import ReactTable from '../components/Table';
import TableWrapper from '../components/TableWrapper';

export const RelvalTable = () => {
  const [data, setData] = React.useState([]);
  const [totalRows, setTotalRows] = React.useState([]);
  const [currentPage, setCurrentPage] = React.useState(1);
  const [pageSize, setPageSize] = React.useState(100);

  const tableData = React.useMemo(() => {
    console.log("tableData useMemo executed")
    return [...data]},
  [data]);

  const columns = React.useMemo(() => 
    data[0]
    ? Object.keys(data[0])
        .filter((key) => typeof(data[0][key]) == "string")
        .map((key) => {
          const header = key.split("_").map(l=> l.charAt(0).toUpperCase()+l.slice(1)).join(' ')
          return { Header: header, accessor: key };
        })
    : [],
    [data]);

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
    url += `&limit=${pageSize}&page=${currentPage}`
    fetch(url)
    .then(res => res.json())
    .then(
      data => {
        console.log("Fetched data: ", data.response.results);
        setData(data.response.results);
        setTotalRows(data.response.total_rows);
    })
    .catch(err => console.log('Error fetching data' + err));
  }, [currentPage, pageSize]);

  return (
    <TableWrapper>
      <ReactTable tableProps={tableInstance} />
    </TableWrapper>
  );
}