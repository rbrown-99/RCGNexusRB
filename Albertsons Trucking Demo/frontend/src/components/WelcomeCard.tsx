/**
 * Welcome card shown when no optimization has been run yet. Walks the
 * dispatcher through the three things they need to do.
 */
export default function WelcomeCard() {
  return (
    <div className="welcome">
      <h2>Welcome, dispatcher</h2>
      <p className="welcome-lead">
        This tool plans cost-optimal truckloads from the Salt Lake City DC across
        Utah, Idaho, Wyoming, Montana, and Colorado — respecting cold-chain rules,
        trailer mix, weight caps, and delivery windows.
      </p>
      <ol className="welcome-steps">
        <li>
          <span className="step-num">1</span>
          <div>
            <strong>Bring your data</strong>
            <p>Upload tomorrow's orders, store list, and your trailer constraints — or grab the sample files to see the format.</p>
          </div>
        </li>
        <li>
          <span className="step-num">2</span>
          <div>
            <strong>Run the optimizer</strong>
            <p>Click <em>Try it with sample data</em> (or <em>Parse + Optimize</em> on your own files). The solver typically finishes in under 30 seconds.</p>
          </div>
        </li>
        <li>
          <span className="step-num">3</span>
          <div>
            <strong>Review and adjust</strong>
            <p>Check the route map, KPI cards, and exception list. Ask the assistant to drop a trailer config or relax a constraint and re-optimize.</p>
          </div>
        </li>
      </ol>
    </div>
  );
}
