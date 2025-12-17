ThisBuild / version := "0.1.0-SNAPSHOT"
ThisBuild / scalaVersion := "2.12.17"

libraryDependencies ++= Seq(
  "mysql" % "mysql-connector-java" % "8.0.33",
  "com.github.scopt" %% "scopt" % "4.1.0", "io.github.cdimascio" % "dotenv-java" % "3.0.0",
  "org.apache.spark" %% "spark-core" % "3.4.4", "org.apache.spark" %% "spark-sql" % "3.4.4",
  "org.apache.spark" %% "spark-connect" % "3.4.4"
)

lazy val root = (project in file(".")).settings(name := "devAPI")