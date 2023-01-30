
  // Need query params for setting first data request
  var urlParams = new URLSearchParams(window.location.search);
  const shown = urlParams.get('shown')? urlParams.get('shown'): 1111111100000000;
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
  shown: shown,
  loadingData: false,
  refreshData: false,
  dialog: {
    visible: false,
    title: 'Test title',
    description: '',
    cancel: undefined,
    ok: undefined,
  }
};

function reducer(state=initialState, action) {
  switch(action.type){
    case "SET_DATA":
      return {
        ...state,
        data: action.data,
        totalRows: action.totalRows
      };
    case "REFRESH_DATA":
      return {...state, refreshData: action.payload}
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
    case "TOGGLE_LOADING_STATE":
      return {...state, loadingData: action.payload};
    case "TOGGLE_MODAL_DIALOG":
      return {...state, dialog: {...state.dialog, ...action.payload}};
    default:
      throw new Error();
  }
};

export default reducer;