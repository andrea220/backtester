# data/
#   corporate_actions/
#     events.csv       ← tutti gli eventi di tutti i ticker
#     splits.csv       ← solo split
#     dividends.csv    ← solo dividendi
#     … (altri tipi)

## dividends.csv
# | nome colonna    | descrizione                                               | tipo               |
# | --------------- | --------------------------------------------------------- | ------------------ |
# | `ticker`        | identificativo univoco del titolo                         | string             |
# | `ex_date`       | data “ex-dividend” (primo day senza diritto al pagamento) | YYYY-MM-DD         |
# | `record_date`   | data in cui si registrano gli azionisti per il dividendo  | YYYY-MM-DD         |
# | `pay_date`      | data di pagamento                                         | YYYY-MM-DD         |
# | `dividend`      | importo del dividendo per azione                          | float              |
# | `currency`      | valuta                                                    | string (es. “EUR”) |
# | `dividend_type` | es. “cash”, “stock”                                       | string             |


## splits.csv
# | nome colonna     | descrizione                                             | tipo       |
# | ---------------- | ------------------------------------------------------- | ---------- |
# | `ticker`         | identificativo univoco del titolo                       | string     |
# | `split_date`     | data in cui lo split entra in vigore                    | YYYY-MM-DD |
# | `factor_old`     | numero di azioni dopo lo split per ogni azione prima    | float      |
# | `factor_new`     | numero di azioni prima dello split per ogni azione dopo | float      |
# | `ratio`          | rapporto di split (`factor_old`/`factor_new`)           | float      |
# | `currency_ratio` | (opzionale) se vi è variazione di valuta                | float      |
