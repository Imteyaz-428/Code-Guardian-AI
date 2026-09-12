import { useMemo } from "react";

const NODE_WIDTH = 250;
const NODE_HEIGHT = 72;
const COLUMN_GAP = 90;
const ROW_GAP = 110;
const PADDING = 70;

function formatFunctionId(functionId) {
  const parts = functionId.split("::");

  return {
    file: parts[0],
    functionName: parts.slice(1).join("::"),
  };
}

/*
 * Create visual levels for the CFG.
 *
 * Normal forward edges move downward.
 * Backward edges (typically loop edges) are rendered
 * separately as curved edges.
 */
function buildLayout(nodes, edges) {
  const nodeMap = new Map(
    nodes.map((node) => [node.id, node])
  );

  const outgoing = new Map();

  nodes.forEach((node) => {
    outgoing.set(node.id, []);
  });

  edges.forEach(([source, destination]) => {
    if (outgoing.has(source)) {
      outgoing.get(source).push(destination);
    }
  });

  const entry =
    nodes.find((node) => node.type === "entry") ||
    nodes[0];

  const exit =
    nodes.find((node) => node.type === "exit");

  const rank = new Map();

  if (entry) {
    rank.set(entry.id, 0);

    const queue = [entry.id];

    while (queue.length) {
      const current = queue.shift();
      const currentRank = rank.get(current);

      for (const next of outgoing.get(current) || []) {
        /*
         * Don't use already-ranked nodes for level expansion.
         * This naturally treats loop-back edges separately.
         */
        if (!rank.has(next)) {
          rank.set(next, currentRank + 1);
          queue.push(next);
        }
      }
    }
  }

  // Put disconnected nodes somewhere sensible.
  let fallbackRank = 0;

  nodes.forEach((node) => {
    if (!rank.has(node.id)) {
      rank.set(node.id, fallbackRank);
      fallbackRank += 1;
    }
  });

  /*
   * EXIT should always appear at the bottom.
   */
  if (exit) {
    const maxRank = Math.max(...rank.values());

    rank.set(exit.id, maxRank + 1);
  }

  const levels = new Map();

  nodes.forEach((node) => {
    const level = rank.get(node.id);

    if (!levels.has(level)) {
      levels.set(level, []);
    }

    levels.get(level).push(node);
  });

  const positions = new Map();

  const sortedLevels = [...levels.keys()].sort(
    (a, b) => a - b
  );

  let maxColumns = 1;

  sortedLevels.forEach((level) => {
    const levelNodes = levels.get(level);

    maxColumns = Math.max(
      maxColumns,
      levelNodes.length
    );

    levelNodes.forEach((node, index) => {
      const total = levelNodes.length;

      const x =
        PADDING +
        (index - (total - 1) / 2) *
          (NODE_WIDTH + COLUMN_GAP) +
        (maxColumns * (NODE_WIDTH + COLUMN_GAP)) / 2;

      const y =
        PADDING +
        level * ROW_GAP;

      positions.set(node.id, {
        x,
        y,
        rank: level,
      });
    });
  });

  const width =
    Math.max(
      700,
      maxColumns * (NODE_WIDTH + COLUMN_GAP) +
        PADDING * 2
    );

  const height =
    Math.max(
      420,
      (sortedLevels.length - 1) * ROW_GAP +
        NODE_HEIGHT +
        PADDING * 2
    );

  return {
    positions,
    width,
    height,
    nodeMap,
  };
}

function getNodeClass(type) {
  return `cfg-graph-node cfg-graph-node-${type}`;
}

function CFGPanel({
  controlFlowGraphs = [],
  selectedFinding,
}) {
  if (!controlFlowGraphs.length) {
    return (
      <section className="cfg-panel">
        <div className="panel-header">
          <h2>Control Flow Graph</h2>
          <span>0 functions</span>
        </div>

        <div className="cfg-empty">
          No control flow graph data available.
        </div>
      </section>
    );
  }

  let selectedCFG = null;

  if (selectedFinding) {
    const exactId =
      `${selectedFinding.file}::${selectedFinding.function}`;

    selectedCFG = controlFlowGraphs.find(
      (cfg) => cfg.function === exactId
    );

    if (!selectedCFG) {
      selectedCFG = controlFlowGraphs.find(
        (cfg) =>
          cfg.function.startsWith(
            `${selectedFinding.file}::`
          ) &&
          cfg.function.endsWith(
            `::${selectedFinding.function}`
          )
      );
    }
  }

  if (!selectedCFG) {
    selectedCFG = controlFlowGraphs[0];
  }

  const formatted = formatFunctionId(
    selectedCFG.function
  );

  const layout = useMemo(
    () =>
      buildLayout(
        selectedCFG.nodes,
        selectedCFG.edges
      ),
    [selectedCFG]
  );

  const {
    positions,
    width,
    height,
    nodeMap,
  } = layout;

  return (
    <section className="cfg-panel">
      {/* -------------------------------------------------- */}
      {/* Header                                             */}
      {/* -------------------------------------------------- */}

      <div className="panel-header">
        <div>
          <h2>Control Flow Graph</h2>
        </div>

        <span>
          {selectedCFG.nodes.length} nodes ·{" "}
          {selectedCFG.edges.length} edges
        </span>
      </div>

      {/* -------------------------------------------------- */}
      {/* Selected function                                  */}
      {/* -------------------------------------------------- */}

      <div className="cfg-function">
        <span className="cfg-file">
          {formatted.file}
        </span>

        <span className="cfg-function-name">
          {formatted.functionName}()
        </span>
      </div>

      {/* -------------------------------------------------- */}
      {/* Graph                                              */}
      {/* -------------------------------------------------- */}

      <div className="cfg-graph-container">
        <svg
          className="cfg-graph-svg"
          width={width}
          height={height}
          viewBox={`0 0 ${width} ${height}`}
          role="img"
          aria-label={`Control flow graph for ${selectedCFG.function}`}
        >
          <defs>
            <marker
              id="cfg-arrow"
              markerWidth="8"
              markerHeight="8"
              refX="7"
              refY="4"
              orient="auto"
              markerUnits="strokeWidth"
            >
              <path
                d="M0,0 L8,4 L0,8 Z"
                fill="currentColor"
              />
            </marker>
          </defs>

          {/* ------------------------------------------------ */}
          {/* Edges                                             */}
          {/* ------------------------------------------------ */}

          <g className="cfg-graph-edges">
            {selectedCFG.edges.map(
              ([source, destination], index) => {
                const from = positions.get(source);
                const to = positions.get(destination);

                if (!from || !to) {
                  return null;
                }

                const sourceNode = nodeMap.get(source);
                const destinationNode =
                  nodeMap.get(destination);

                const isBackEdge =
                  to.rank <= from.rank;

                const sourceX =
                  from.x + NODE_WIDTH / 2;

                const sourceY =
                  from.y + NODE_HEIGHT;

                const destinationX =
                  to.x + NODE_WIDTH / 2;

                const destinationY =
                  to.y;

                let path;

                if (isBackEdge) {
                  /*
                   * Curve loop-back edges around the
                   * left/right side of the graph.
                   */
                  const side =
                    sourceX > destinationX
                      ? Math.max(
                          20,
                          Math.min(
                            sourceX,
                            destinationX
                          ) - 45
                        )
                      : Math.min(
                          width - 20,
                          Math.max(
                            sourceX,
                            destinationX
                          ) + 45
                        );

                  path = `
                    M ${sourceX} ${sourceY}
                    C ${side} ${sourceY + 25},
                      ${side} ${destinationY - 25},
                      ${destinationX} ${destinationY}
                  `;
                } else if (
                  Math.abs(
                    sourceX - destinationX
                  ) < 5
                ) {
                  path = `
                    M ${sourceX} ${sourceY}
                    L ${destinationX} ${destinationY}
                  `;
                } else {
                  /*
                   * Branching edge.
                   */
                  const middleY =
                    (sourceY + destinationY) / 2;

                  path = `
                    M ${sourceX} ${sourceY}
                    C ${sourceX} ${middleY},
                      ${destinationX} ${middleY},
                      ${destinationX} ${destinationY}
                  `;
                }

                return (
                  <path
                    key={`${source}-${destination}-${index}`}
                    className={
                      isBackEdge
                        ? "cfg-edge-path cfg-edge-back"
                        : "cfg-edge-path"
                    }
                    d={path}
                    markerEnd="url(#cfg-arrow)"
                  />
                );
              }
            )}
          </g>

          {/* ------------------------------------------------ */}
          {/* Nodes                                             */}
          {/* ------------------------------------------------ */}

          <g className="cfg-graph-nodes">
            {selectedCFG.nodes.map((node) => {
              const position =
                positions.get(node.id);

              if (!position) {
                return null;
              }

              return (
                <g
                  key={node.id}
                  transform={`translate(${position.x}, ${position.y})`}
                  className={getNodeClass(node.type)}
                >
                  <rect
                    width={NODE_WIDTH}
                    height={NODE_HEIGHT}
                    rx="10"
                  />

                  <text
                    x="16"
                    y="21"
                    className="cfg-svg-type"
                  >
                    {node.type}
                  </text>

                  {node.line !== null &&
                    node.line !== undefined && (
                      <text
                        x={NODE_WIDTH - 16}
                        y="21"
                        textAnchor="end"
                        className="cfg-svg-line"
                      >
                        line {node.line}
                      </text>
                    )}

                  <text
                    x="16"
                    y="48"
                    className="cfg-svg-label"
                  >
                    {node.label}
                  </text>
                </g>
              );
            })}
          </g>
        </svg>
      </div>

      {/* -------------------------------------------------- */}
      {/* Edge list                                           */}
      {/* -------------------------------------------------- */}

      <div className="cfg-edges">
        <div className="cfg-edges-header">
          <span>Graph Edges</span>
          <span>{selectedCFG.edges.length}</span>
        </div>

        {selectedCFG.edges.map(
          ([source, destination], index) => (
            <div
              className="cfg-edge"
              key={`${source}-${destination}-${index}`}
            >
              <span>Node {source}</span>

              <span className="cfg-edge-arrow">
                →
              </span>

              <span>Node {destination}</span>
            </div>
          )
        )}
      </div>
    </section>
  );
}

export default CFGPanel;