export const initialState = {
  data: [],
  totalRows: "",
  currentPage: 0,
  pageSize: 100
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
    default:
      throw new Error();
  }
};

export default reducer;