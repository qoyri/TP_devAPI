defmodule Oauth2Server.MixProject do
  use Mix.Project

  def project do
    [
      app: :oauth2_server,
      version: "1.0.0",
      elixir: "~> 1.14",
      elixirc_paths: elixirc_paths(Mix.env()),
      start_permanent: Mix.env() == :prod,
      aliases: aliases(),
      deps: deps()
    ]
  end

  def application do
    [
      mod: {Oauth2Server.Application, []},
      extra_applications: [:logger, :runtime_tools, :crypto]
    ]
  end

  defp elixirc_paths(:test), do: ["lib", "test/support"]
  defp elixirc_paths(_), do: ["lib"]

  defp deps do
    [
      {:phoenix, "~> 1.7.10"},
      {:phoenix_ecto, "~> 4.4"},
      {:ecto_sql, "~> 3.10"},
      {:myxql, "~> 0.6.0"},
      {:phoenix_html, "~> 3.3"},
      {:jason, "~> 1.2"},
      {:plug_cowboy, "~> 2.5"},
      {:bcrypt_elixir, "~> 3.0"},
      {:cors_plug, "~> 3.0"},
      {:open_api_spex, "~> 3.18"},
      {:joken, "~> 2.6"},
      # Test reporting
      {:junit_formatter, "~> 3.3", only: :test}
    ]
  end

  defp aliases do
    [
      setup: ["deps.get", "ecto.setup"],
      "ecto.setup": ["ecto.create", "ecto.migrate", "run priv/repo/seeds.exs"],
      "ecto.reset": ["ecto.drop", "ecto.setup"],
      # Note: removed ecto.create/migrate from test alias - tests don't require DB
      test: ["test"]
    ]
  end
end
