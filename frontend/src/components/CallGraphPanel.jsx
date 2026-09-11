function formatNode(node) {
    const parts = node.split("::");
  
    const file = parts[0];
    const functionParts = parts.slice(1);
  
    return {
      file,
      functionName: functionParts.join("::"),
    };
  }
  
  function CallGraphPanel({ callGraph }) {
    if (!callGraph || !callGraph.edges?.length) {
      return (
        <section className="call-graph-panel">
          <div className="panel-header">
            <h2>Call Graph</h2>
            <span>0 calls</span>
          </div>
  
          <div className="call-graph-empty">
            No internal function calls detected.
          </div>
        </section>
      );
    }
  
    return (
      <section className="call-graph-panel">
        <div className="panel-header">
          <h2>Call Graph</h2>
          <span>
            {callGraph.edges.length}{" "}
            {callGraph.edges.length === 1 ? "call" : "calls"}
          </span>
        </div>
  
        <div className="call-graph-list">
          {callGraph.edges.map((edge, index) => {
            const caller = formatNode(edge.caller);
            const callee = formatNode(edge.callee);
  
            return (
              <div className="call-edge" key={`${edge.caller}-${edge.callee}-${index}`}>
                <div className="call-node">
                  <span className="call-file">{caller.file}</span>
                  <span className="call-function">
                    {caller.functionName}
                  </span>
                </div>
  
                <div className="call-arrow" aria-hidden="true">
                  →
                </div>
  
                <div className="call-node">
                  <span className="call-file">{callee.file}</span>
                  <span className="call-function">
                    {callee.functionName}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </section>
    );
  }
  
  export default CallGraphPanel;