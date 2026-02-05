import Config

if config_env() == :prod do
  # Database configuration - support both DATABASE_URL and individual vars
  database_url = System.get_env("DATABASE_URL")

  if database_url do
    config :oauth2_server, Oauth2Server.Repo,
      url: database_url,
      pool_size: String.to_integer(System.get_env("POOL_SIZE") || "10")
  else
    config :oauth2_server, Oauth2Server.Repo,
      hostname: System.get_env("MYSQL_HOST") || "localhost",
      port: String.to_integer(System.get_env("MYSQL_PORT") || "3306"),
      username: System.get_env("MYSQL_USER") || "sirenuser",
      password: System.get_env("MYSQL_PASSWORD") || "12345678",
      database: System.get_env("MYSQL_DATABASE") || "siren",
      pool_size: String.to_integer(System.get_env("POOL_SIZE") || "10")
  end

  secret_key_base =
    System.get_env("SECRET_KEY_BASE") ||
      raise """
      environment variable SECRET_KEY_BASE is missing.
      """

  host = System.get_env("PHX_HOST") || "localhost"
  port = String.to_integer(System.get_env("PORT") || "4000")

  config :oauth2_server, Oauth2ServerWeb.Endpoint,
    url: [host: host, port: 443, scheme: "https"],
    http: [ip: {0, 0, 0, 0}, port: port],
    secret_key_base: secret_key_base,
    server: true

  # JWT Secret
  config :oauth2_server, :jwt,
    secret_key: System.get_env("SECRET_KEY") || "super-secret-key-for-jwt"
end
