
  // Need query params for setting first data request
  var urlParams = new URLSearchParams(window.location.search);
  const shown = urlParams.get('shown')? urlParams.get('shown'): 111111110000000;
  const pageValid =  Number(urlParams.get('page')) >= 0
  const pageSizeValid = Number(urlParams.get('limit')) > 0
  const initPageNumber = pageValid? Number(urlParams.get('page')): 0
  const initPageSize = pageSizeValid? Number(urlParams.get('limit')): 50


export const initialState = {
  data: [],
  totalRows: "",
  currentPage: initPageNumber,
  pageSize: initPageSize,
  selectedItems: {},
  shown: shown
};

function reducer(state=initialState, action) {
  switch(action.type){
    case "SET_DATA":
      return {
        ...state,
        data: action.data,
        totalRows: action.totalRows
      };
    case "DO_NOTHING":
      return {...state};
    case "CHANGE_PAGE":
      return {...state, currentPage: action.payload};
    case "SET_PAGE_SIZE":
      return {...state, pageSize: action.payload};
    case "SET_SELECTED_ITEMS":
      return {...state, selectedItems: action.payload};
    case "UPDATE_SHOWN":
      return {...state, shown: action.payload};
    default:
      throw new Error();
  }
};

export default reducer;