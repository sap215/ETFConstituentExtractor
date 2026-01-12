# ETF Constituent/Holding Extractor

This project is a Python based tool for extracting Exchange-Traded Funds (ETFs) holding/constituent data from the U.S. Securities and Exchange Commission (SEC) EDGAR's database. This tool works by extracting, processing, and saving holdings data from NPORT-P filings. These NPORT-P quarterly filings provide a lot of information about a given fund’s portfolio holdings, but the information of interest is as follows: Issuer name, CUSIP, Number of shares held, Market value (USD), Percentage allocation in the portfolio.

Using this tool, users can fetch all of the NPORT-P filings (over the past five years) associated with any ETF by providing its 10-digit CIK number, scrape fund's holding data from the filings, and save the data into CSV files that are easy to use for further data analysis. This tool uses the SEC’s EDGAR API for fetching filing metadata and web scraping for parsing important holdings data from the filings.

## How to Use

Clone the repository to your local machine:

```bash
git clone https://github.com/yourusername/ETFConstituentExtractor.git
cd ETFConstituentExtractor
```

```bash
pip install -r requirements.txt
```

```bash
python main.py
```

When prompted, enter the 10-digit CIK number of the ETF you want to extract holdings data for. The tool will fetch all relevant NPORT-P filings, extract the holdings data, and save it into CSV files in the `output` directory.
