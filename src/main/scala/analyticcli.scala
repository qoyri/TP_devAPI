package siren

import org.apache.spark.sql.SparkSession
import siren.SirenLogger.info

object analyticcli extends App {
  val mysqlHost = sys.env.getOrElse("MYSQL_HOST", "db")
  val mysqlPort = sys.env.getOrElse("MYSQL_PORT", "3306")
  val jdbcUrl = s"jdbc:mysql://$mysqlHost:$mysqlPort/siren"

  val spark = SparkSession.builder()
    .appName("spark-connect-server")
    .master("local[*]")
    .config("spark.connect.grpc.binding.port", "15002")
    .config("spark.connect.grpc.binding.address", "0.0.0.0")
    .getOrCreate()

  // Lecture de la table pré-calculée (2000 lignes au lieu de 29M)
  val activityCounts = spark.read
    .format("jdbc")
    .option("url", jdbcUrl)
    .option("dbtable", "stats_activite")
    .option("user", "sirenuser")
    .option("password", "12345678")
    .option("driver", "com.mysql.cj.jdbc.Driver")
    .load()
    .withColumnRenamed("activitePrincipaleUniteLegale", "activite_principale_unite_legale")

  activityCounts.createOrReplaceGlobalTempView("activity")

  info("Spark session started on port 15002.")
  info("Views: global_temp.activity, global_temp.zone")

  sys.addShutdownHook {
    spark.stop()
  }

  Thread.currentThread().join()
}