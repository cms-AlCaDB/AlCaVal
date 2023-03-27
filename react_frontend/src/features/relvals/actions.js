export const setPageSize = (size) => {
  return {type: "SET_PAGE_SIZE", payload: size};
}

export const setSelectedItems = (state, selectedFlatRows) => {
  const newSelectedItems = {...state.selectedItems};
  newSelectedItems[state.currentPage] = [...selectedFlatRows];
  return {type: "SET_SELECTED_ITEMS", payload: newSelectedItems};
}

export const updateSortState = (sortState) => ({type: "UPDATE_SORT_STATE", payload: {...sortState}});

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

export const getQueryString = (state, forData=false) => {
  // If forData is true then queryString is returned for fetching data, 
  // If forData is false then it returns queryString for setting query in the URL

  var params = new URLSearchParams(window.location.search);
  const query = Object.fromEntries(params);
  const object = {
                  shown: state.shown,
                  limit: state.pageSize,
                  page: state.currentPage,
                  sort: state.sort,
                  sort_asc: state.sort_asc,
                  filter: state.filterData
                };
  let queryString = '';
  Object.entries({...query, ...object}).forEach(([k, value]) => {
    // ignore shown param when fetching data
    if (forData && k==='shown') return;
    // ignore sort or sort_asc param when it is null
    if (k.includes('sort') && value===null) return;
    queryString += '&' + k + '=' + value;
  });
  return queryString;
}

export const changePage = (page) => {
  return {type: "CHANGE_PAGE", payload: page};
}