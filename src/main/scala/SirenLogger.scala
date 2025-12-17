package siren
import java.util.logging.{ConsoleHandler, Level, Logger, SimpleFormatter}

object SirenLogger extends Logger("SirenLogger", null) {
  private val consoleHandler = new ConsoleHandler
  consoleHandler.setLevel(Level.INFO)
  consoleHandler.setFormatter(new SimpleFormatter)

  setUseParentHandlers(false)
  addHandler(consoleHandler)
  setLevel(Level.INFO)

  override def info(message: String): Unit = log(Level.INFO, message)
}
