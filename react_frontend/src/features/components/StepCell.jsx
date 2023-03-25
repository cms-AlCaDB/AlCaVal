const StepCell = ({row}) => {
  return (
    <ul>
    {
      row.original.steps.map(item => (
        <li key={item.name}>{item.name}
          <ul key={item.name}>
          {
            item.driver.data?
              Object.keys(item.driver).map(key => 
                item.driver[key]? 
                  <li key={key} style={{fontFamily: "monospace", fontSize: "smaller"}}>
                    {`--${key} ${item.driver[key]}`}
                  </li>
                : null
              )
            : Object.keys(item.input).map(key => 
                item.input[key]? 
                  <li key={key} style={{fontFamily: "monospace", fontSize: "smaller"}}>
                    {
                      typeof(item.input[key])==="object"? `${key}: ${JSON.stringify(item.input[key])}`
                      : `${key}: ${item.input[key]}`
                    }
                  </li>
                : null 
            )
          }
          </ul>
        </li>
      ))
    }
    </ul>
  );
};

export default StepCell;