export const setPageSize = (size) => {
  return {type: "SET_PAGE_SIZE", payload: size};
}

export const setSelectedItems = (state, selectedFlatRows) => {
  const newSelectedItems = {...state.selectedItems};
  newSelectedItems[state.currentPage] = [...selectedFlatRows];
  return {type: "SET_SELECTED_ITEMS", payload: newSelectedItems};
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

export const getQueryString = (state, forData=false) => {
  var params = new URLSearchParams(window.location.search);
  const query = Object.fromEntries(params);
  const object = {shown: state.shown, limit: state.pageSize, page: state.currentPage};
  let queryString = '';
  Object.entries({...query, ...object}).forEach(([k, value]) => {
    if (forData && k==='shown') return;
    queryString += '&' + k + '=' + value;
  });
  return queryString;
}

export const changePage = (page) => {
  return {type: "CHANGE_PAGE", payload: page};
}