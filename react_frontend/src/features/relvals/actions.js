// Fetching column headers
export const fetchColumns = (fistColumn) => {
  return fistColumn
    ? Object.keys(fistColumn)
        .filter((key) => typeof(fistColumn[key]) == "string")
        .map((key) => {
          const header = key.split("_").map(l=> l.charAt(0).toUpperCase()+l.slice(1)).join(' ')
          return { Header: header, accessor: key };
        })
    : []
}

export const updateQueryString = (state, searchParams, setSearchParams) => {
  const query = Object.fromEntries(searchParams);
  query.limit = state.pageSize;
  query.page = state.currentPage;
  setSearchParams(query);
}

export const changePage = (page) => {
  return {type: "CHANGE_PAGE", payload: page};
}

export const setPageSize = (size) => {
  return {type: "SET_PAGE_SIZE", payload: size};
}