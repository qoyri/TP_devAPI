# Create test-results directory
File.mkdir_p!("./test-results")

# JUnit formatter config
Application.put_env(:junit_formatter, :report_dir, "./test-results")
Application.put_env(:junit_formatter, :report_file, "results.xml")

# HTML formatter config
Application.put_env(:ex_unit_html, :output_path, "./test-results/report.html")

# Configure formatters for CI
ExUnit.configure(
  formatters: [
    JUnitFormatter,
    ExUnit.CLIFormatter,
    ExUnit.HTMLFormatter
  ]
)

ExUnit.start()
