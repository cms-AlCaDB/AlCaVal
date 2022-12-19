import React from "react";
import * as actions from "../relvals/actions";

const Pagination = (props) => {
  const [state, dispatch] = props.reducer;
  const { 
    totalRows,
    currentPage, 
    pageSize, 
  } = state;

  // Calculating max number of pages
  const noOfPages = Math.ceil(totalRows / pageSize);

  // Navigation arrows enable/disable state
  const [canGoBack, setCanGoBack] = React.useState(false);
  const [canGoNext, setCanGoNext] = React.useState(true);

  // Onclick handlers for the butons
  const onNextPage = () => dispatch(actions.changePage(currentPage + 1));
  const onPrevPage = () => dispatch(actions.changePage(currentPage - 1));

  const pageStart = totalRows == 0 ? 0 : currentPage * pageSize + 1;
  const pageEnd = Math.min(totalRows, currentPage * pageSize + pageSize); 

  // Disable previous and next buttons in the first and last page
  // respectively
  React.useEffect(() => {
    (noOfPages <= currentPage+1)? setCanGoNext(false): setCanGoNext(true);
    (currentPage === 0)?setCanGoBack(false): setCanGoBack(true);
  }, [noOfPages, currentPage, pageSize]);

  return (
    <>
      {noOfPages > 1 ? (
        <div className="pagination" style={{float: "right"}}>
          <div className="" style={{alignSelf: 'center', marginRight: '5px'}}>
            Showing {pageStart} - {pageEnd} of {totalRows}
          </div>
          <div className="" style={{alignSelf: 'center'}}>
            Page size:
          </div>
          <ul className="pagination" key="1" style={{marginRight: '5px'}}>
            {
              [50, 100, 200].map(limit => (
              <li className={`page-item ${limit==pageSize?'active': ''}`}
                key={limit}
              >
                <button className="page-link" onClick={()=>dispatch(actions.setPageSize(limit))}>{limit}</button>
              </li>
              ))
            }
          </ul>

          <ul className="pagination" key="2" style={{border: '2px'}}>
            {
              !canGoBack?'': (
                <li className="page-item" key="Previous">
                  <button className="page-link"
                    onClick={onPrevPage}
                  >
                    Previous
                  </button>
                </li>
              )
            }
            <li className="page-item" key="CurrentButton">
              <span className="page-link">Page {currentPage}</span>
            </li>
            {
              !canGoNext?'': (
                <li className="page-item" key="Next">
                  <button className="page-link"
                    onClick={onNextPage}
                  >
                    Next
                  </button>
                </li>
              )
            }
          </ul>
        </div>
      ) : null}
    </>
  );
};

export default Pagination;