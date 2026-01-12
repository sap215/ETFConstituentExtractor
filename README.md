# ETF Constituent/Holding Extractor

This project is a Python-based tool for extracting Exchange-Traded Funds (ETFs) holding/constituent data from the U.S. Securities and Exchange Commission (SEC) EDGAR's database. This tool works by extracting, processing, and saving holdings data from NPORT-P filings. These NPORT-P quarterly filings provide detailed information about a given fund's portfolio holdings, including: Issuer name, Number of shares held, Market value (USD), and Percentage allocation in the portfolio.

Using this tool, users can fetch all of the NPORT-P filings (over the past five years) associated with any ETF by providing its 10-digit CIK number, scrape the fund's holding data from the filings, and save the data into CSV files that are easy to use for further data analysis. This tool uses the SEC's EDGAR API for fetching filing metadata and web scraping for parsing important holdings data from the filings.

## Features

- **Resumable Processing**: Automatically tracks progress and can resume from where it left off if interrupted
- **Error Handling & Retry Logic**: Built-in retry mechanism with exponential backoff for network errors and SSL issues
- **Organized Output**: Creates a structured output directory (`output/{CIK}/`) for each ETF
- **Command-line & Interactive Modes**: Supports both command-line arguments and interactive input

## How to Use

### Installation

Clone the repository to your local machine:

```bash
git clone https://github.com/sap215/ETFConstituentExtractor.git
cd ETFConstituentExtractor
```

Install the required dependencies:

```bash
pip install -r requirements.txt
```

### Running the Script

**Option 1: Command-line argument (recommended)**

```bash
./ETFQuarterlyHoldingsExtractor.py 0000707823
```

**Option 2: Interactive mode**

```bash
./ETFQuarterlyHoldingsExtractor.py
```

When prompted, enter the 10-digit CIK number of the ETF you want to extract holdings data for.

### Output

The tool will:
1. Fetch all relevant NPORT-P filings for the specified CIK
2. Extract the holdings data from each filing
3. Save each filing's data into a separate CSV file named `{YYYY-MM-DD}_NPORT-P_HOLDINGS.csv`
4. Store all files in the `output/{CIK}/` directory
5. Track progress in `output/{CIK}/progress.json` for resumability

### Resuming Interrupted Runs

If the script is interrupted or encounters errors, simply run it again with the same CIK number. It will automatically skip already-processed filings and continue from where it left off.

## Finding CIK Numbers

You can find an ETF's CIK number by searching for the fund on the [SEC EDGAR website](https://www.sec.gov/edgar/searchedgar/companysearch.html). The CIK is a 10-digit identifier (pad with leading zeros if necessary).
