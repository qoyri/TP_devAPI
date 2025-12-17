package siren

import io.github.cdimascio.dotenv.Dotenv
import scopt.OParser
import siren.feedDB._

import java.nio.file.Paths

case class Config(envPath: Option[String] = None)

object dbcli extends App {

  // Parse arguments
  val builder = OParser.builder[Config]
  val parser = {
    import builder._
    OParser.sequence(
      programName("cli"),
      head("cli", "0.1"),
      opt[String]('e', "env")
        .valueName("<file>")
        .action((x, c) => c.copy(envPath = Some(x)))
        .text("path to .env file (optional)"),
      help("help").text("prints this usage text")
    )
  }

  // Parse dotenv
  OParser.parse(parser, args, Config()) match {
    case Some(cfg) =>
      val dotenv = cfg.envPath match {
        case Some(p) =>
          val path = Paths.get(p)
          val dir = if (path.getParent != null) path.getParent.toString else "."
          val name = path.getFileName.toString
          Dotenv.configure().directory(dir).filename(name).load()
        case None =>
          Dotenv.load()
      }

      // Call SQL related functions
      val dbURL = Option(dotenv.get("MYSQL_URL")).getOrElse("jdbc:mysql://localhost:3366/")
      createSirenDB(dbURL: String)
      grantPrivileges(dbURL: String)
      createUniteLegaleTable(dbURL: String)
      insertUniteLegaleFile(dbURL: String)
    case _ => // parsing failure or help printed by scopt
  }
}