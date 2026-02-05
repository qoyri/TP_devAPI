defmodule ExUnit.HTMLFormatter do
  @moduledoc """
  Custom ExUnit formatter that generates an HTML test report.
  """
  use GenServer

  def init(_opts) do
    output_path = Application.get_env(:ex_unit_html, :output_path, "./test-results/report.html")
    {:ok, %{
      tests: [],
      failures: [],
      skipped: [],
      start_time: nil,
      end_time: nil,
      output_path: output_path
    }}
  end

  def handle_cast({:suite_started, _opts}, state) do
    {:noreply, %{state | start_time: DateTime.utc_now()}}
  end

  def handle_cast({:test_finished, %ExUnit.Test{} = test}, state) do
    test_data = %{
      name: test.name,
      module: inspect(test.module),
      time: test.time,
      state: test.state,
      tags: test.tags
    }

    state = case test.state do
      nil -> %{state | tests: [test_data | state.tests]}
      {:failed, _} -> %{state | tests: [test_data | state.tests], failures: [test_data | state.failures]}
      {:skipped, _} -> %{state | tests: [test_data | state.tests], skipped: [test_data | state.skipped]}
      _ -> %{state | tests: [test_data | state.tests]}
    end

    {:noreply, state}
  end

  def handle_cast({:suite_finished, _times}, state) do
    state = %{state | end_time: DateTime.utc_now()}
    generate_html_report(state)
    {:noreply, state}
  end

  def handle_cast(_event, state), do: {:noreply, state}

  defp generate_html_report(state) do
    total = length(state.tests)
    failed = length(state.failures)
    skipped = length(state.skipped)
    passed = total - failed - skipped
    duration = if state.start_time && state.end_time do
      DateTime.diff(state.end_time, state.start_time, :millisecond)
    else
      0
    end

    html = """
    <!DOCTYPE html>
    <html lang="en">
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>ExUnit Test Report</title>
      <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif; background: #1a1a2e; color: #eee; padding: 20px; }
        .container { max-width: 1200px; margin: 0 auto; }
        h1 { color: #9d4edd; margin-bottom: 20px; display: flex; align-items: center; gap: 10px; }
        h1::before { content: ''; display: inline-block; width: 40px; height: 40px; background: linear-gradient(135deg, #9d4edd, #c77dff); border-radius: 8px; }
        .summary { display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin-bottom: 30px; }
        .stat { background: #16213e; border-radius: 12px; padding: 20px; text-align: center; border: 1px solid #0f3460; }
        .stat-value { font-size: 2.5rem; font-weight: bold; }
        .stat-label { color: #888; font-size: 0.9rem; margin-top: 5px; }
        .stat.passed .stat-value { color: #4ade80; }
        .stat.failed .stat-value { color: #f87171; }
        .stat.skipped .stat-value { color: #fbbf24; }
        .stat.total .stat-value { color: #60a5fa; }
        .stat.time .stat-value { color: #c084fc; font-size: 1.8rem; }
        .progress-bar { height: 8px; background: #0f3460; border-radius: 4px; overflow: hidden; margin-bottom: 30px; }
        .progress-fill { height: 100%; display: flex; }
        .progress-passed { background: #4ade80; }
        .progress-failed { background: #f87171; }
        .progress-skipped { background: #fbbf24; }
        .tests { background: #16213e; border-radius: 12px; border: 1px solid #0f3460; overflow: hidden; }
        .tests-header { padding: 15px 20px; border-bottom: 1px solid #0f3460; font-weight: 600; color: #9d4edd; }
        .test { padding: 12px 20px; border-bottom: 1px solid #0f3460; display: flex; align-items: center; gap: 12px; }
        .test:last-child { border-bottom: none; }
        .test:hover { background: #1a2744; }
        .test-icon { width: 24px; height: 24px; border-radius: 50%; display: flex; align-items: center; justify-content: center; font-size: 12px; flex-shrink: 0; }
        .test-icon.passed { background: #065f46; color: #4ade80; }
        .test-icon.failed { background: #7f1d1d; color: #f87171; }
        .test-icon.skipped { background: #78350f; color: #fbbf24; }
        .test-name { flex: 1; }
        .test-module { color: #888; font-size: 0.85rem; }
        .test-time { color: #888; font-size: 0.85rem; min-width: 80px; text-align: right; }
        .filter-buttons { display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }
        .filter-btn { padding: 8px 16px; border: none; border-radius: 20px; cursor: pointer; font-size: 0.9rem; transition: all 0.2s; }
        .filter-btn { background: #16213e; color: #888; border: 1px solid #0f3460; }
        .filter-btn:hover, .filter-btn.active { background: #9d4edd; color: white; border-color: #9d4edd; }
        .timestamp { color: #666; font-size: 0.85rem; margin-bottom: 20px; }
      </style>
    </head>
    <body>
      <div class="container">
        <h1>ExUnit Test Report</h1>
        <p class="timestamp">Generated: #{DateTime.to_string(state.end_time || DateTime.utc_now())}</p>

        <div class="summary">
          <div class="stat total">
            <div class="stat-value">#{total}</div>
            <div class="stat-label">Total Tests</div>
          </div>
          <div class="stat passed">
            <div class="stat-value">#{passed}</div>
            <div class="stat-label">Passed</div>
          </div>
          <div class="stat failed">
            <div class="stat-value">#{failed}</div>
            <div class="stat-label">Failed</div>
          </div>
          <div class="stat skipped">
            <div class="stat-value">#{skipped}</div>
            <div class="stat-label">Skipped</div>
          </div>
          <div class="stat time">
            <div class="stat-value">#{format_duration(duration)}</div>
            <div class="stat-label">Duration</div>
          </div>
        </div>

        <div class="progress-bar">
          <div class="progress-fill">
            <div class="progress-passed" style="width: #{if total > 0, do: passed / total * 100, else: 0}%"></div>
            <div class="progress-failed" style="width: #{if total > 0, do: failed / total * 100, else: 0}%"></div>
            <div class="progress-skipped" style="width: #{if total > 0, do: skipped / total * 100, else: 0}%"></div>
          </div>
        </div>

        <div class="filter-buttons">
          <button class="filter-btn active" onclick="filterTests('all')">All (#{total})</button>
          <button class="filter-btn" onclick="filterTests('passed')">Passed (#{passed})</button>
          <button class="filter-btn" onclick="filterTests('failed')">Failed (#{failed})</button>
          <button class="filter-btn" onclick="filterTests('skipped')">Skipped (#{skipped})</button>
        </div>

        <div class="tests">
          <div class="tests-header">Test Results</div>
          #{generate_test_rows(Enum.reverse(state.tests))}
        </div>
      </div>

      <script>
        function filterTests(status) {
          document.querySelectorAll('.filter-btn').forEach(btn => btn.classList.remove('active'));
          event.target.classList.add('active');
          document.querySelectorAll('.test').forEach(test => {
            if (status === 'all' || test.dataset.status === status) {
              test.style.display = 'flex';
            } else {
              test.style.display = 'none';
            }
          });
        }
      </script>
    </body>
    </html>
    """

    File.mkdir_p!(Path.dirname(state.output_path))
    File.write!(state.output_path, html)
  end

  defp generate_test_rows(tests) do
    Enum.map(tests, fn test ->
      {status, icon} = case test.state do
        nil -> {"passed", "✓"}
        {:failed, _} -> {"failed", "✗"}
        {:skipped, _} -> {"skipped", "○"}
        _ -> {"passed", "✓"}
      end

      time_ms = div(test.time, 1000)

      """
      <div class="test" data-status="#{status}">
        <div class="test-icon #{status}">#{icon}</div>
        <div class="test-name">
          <div>#{format_test_name(test.name)}</div>
          <div class="test-module">#{test.module}</div>
        </div>
        <div class="test-time">#{time_ms}ms</div>
      </div>
      """
    end)
    |> Enum.join("")
  end

  defp format_test_name(name) when is_atom(name) do
    name
    |> Atom.to_string()
    |> String.replace("test ", "")
    |> String.replace("_", " ")
  end

  defp format_duration(ms) when ms < 1000, do: "#{ms}ms"
  defp format_duration(ms), do: "#{Float.round(ms / 1000, 2)}s"
end
