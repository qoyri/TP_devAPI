// scala
package siren

import siren.SirenLogger.info

import java.util.Properties

object feedDB {

  def createSirenDB(url: String): Unit = {
    val sqlRequest: String =
      """
      CREATE DATABASE IF NOT EXISTS siren;
      """
    runRequest(sqlRequest, url, "")
  }

  def grantPrivileges(
                       url: String,
                     ): Unit = {
    val sirenuserGrantSqlRequest: String =
      """
      GRANT ALL PRIVILEGES ON siren.* TO 'sirenuser'@'%';
      """
    runRequest(sirenuserGrantSqlRequest, url, "")
    val flushSQLRequest: String =
      """
      FLUSH PRIVILEGES;
      """
    runRequest(flushSQLRequest, url, "")
  }

  def createUniteLegaleTable(
                              url: String,
                            ): Unit = {
    val sqlRequest: String =
      """
      CREATE TABLE IF NOT EXISTS unite_legale (
        siren                            CHAR(9)     NOT NULL,
        denomination_unite_legale        VARCHAR(100) NULL,
        activite_principale_unite_legale CHAR(6)     NULL,
        nomenclature_activite_principale_unite_legale VARCHAR(8) NULL,
        PRIMARY KEY (siren),
        INDEX idx_denomination_unite_legale (denomination_unite_legale),
        INDEX idx_activite_principale_unite_legale (activite_principale_unite_legale)
      ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
      """
    runRequest(sqlRequest, url, "siren")
  }

  def insertUniteLegaleFile(
                             url: String,
                           ): Unit = {
    val sqlRequest: String =
      """
    LOAD DATA LOCAL INFILE './data/StockUniteLegale_utf8.csv'
    INTO TABLE unite_legale
    FIELDS TERMINATED BY ','
    LINES TERMINATED BY '\n'
    IGNORE 1 LINES
    (
      siren,
      @skip_statutDiffusionUniteLegale,
      @skip_unitePurgeeUniteLegale,
      @skip_dateCreationUniteLegale,
      @skip_sigleUniteLegale,
      @skip_sexeUniteLegale,
      @skip_prenom1UniteLegale,
      @skip_prenom2UniteLegale,
      @skip_prenom3UniteLegale,
      @skip_prenom4UniteLegale,
      @skip_prenomUsuelUniteLegale,
      @skip_pseudonymeUniteLegale,
      @skip_identifiantAssociationUniteLegale,
      @skip_trancheEffectifsUniteLegale,
      @skip_anneeEffectifsUniteLegale,
      @skip_dateDernierTraitementUniteLegale,
      @skip_nombrePeriodesUniteLegale,
      @skip_categorieEntreprise,
      @skip_anneeCategorieEntreprise,
      @skip_dateDebut,
      @skip_etatAdministratifUniteLegale,
      @skip_nomUniteLegale,
      @skip_nomUsageUniteLegale,
      denomination_unite_legale,
      @skip_denominationUsuelle1UniteLegale,
      @skip_denominationUsuelle2UniteLegale,
      @skip_denominationUsuelle3UniteLegale,
      @skip_categorieJuridiqueUniteLegale,
      activite_principale_unite_legale,
      nomenclature_activite_principale_unite_legale,
      @skip_nicSiegeUniteLegale,
      @skip_economieSocialeSolidaireUniteLegale,
      @skip_societeMissionUniteLegale,
      @skip_caractereEmployeurUniteLegale
    );
    """
    runRequest(sqlRequest, url, "siren")
  }

  private def runRequest(
                          sqlRequest: String,
                          url: String,
                          base: String
                        ): Unit = {
    try {
      Class.forName("com.mysql.cj.jdbc.Driver")

      val props = new Properties()
      props.setProperty("user", "sirenuser")
      props.setProperty("password", "12345678")
      props.setProperty("allowLoadLocalInfile", "true")

      // timeouts (ms)
      props.setProperty("connectTimeout", "60000")
      props.setProperty("socketTimeout", "0") // 0 = infinite (good for big loads)
      props.setProperty("useSSL", "false")
      props.setProperty("allowPublicKeyRetrieval", "true")

      val conn = java.sql.DriverManager.getConnection(
        s"$url$base",
        props
      )
      try {
        val stmt = conn.createStatement()
        stmt.execute(sqlRequest)
        info(s"Successful SQL request:\n$sqlRequest")
        stmt.close()
      } finally if (conn != null) conn.close()
    } catch {
      case e: Throwable =>
        println(s"Error: ${e.getMessage}")
        e.printStackTrace()
        sys.exit(2)
    }
  }
}
