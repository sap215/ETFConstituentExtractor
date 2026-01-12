#!/usr/bin/env python3
import requests
import pandas as pd
from bs4 import BeautifulSoup
import json
import os
import time
from requests.exceptions import SSLError, ConnectionError, Timeout, RequestException

class NPORTPScraper:
    def __init__(self, etf_cik):
        self.etf_cik = etf_cik
        self.base_url = f"https://data.sec.gov/submissions/CIK{self.etf_cik}.json"

        # Headers for the base API request
        self.base_headers = {
            "User-Agent": "Sam Pass samalam66@gmail.com", # REPLACE WITH YOUR OWN INFORMATION
            "Accept-Encoding": "gzip, deflate",
            "Host": "data.sec.gov"
        }

        # Headers for individual NPORT-P filings
        self.nportp_headers = {
            "User-Agent": "Sam Pass samalam66@gmail.com", # REPLACE WITH YOUR OWN INFORMATION
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "application/xml",
            "Priority": "u=0, i",
            "Accept-Encoding": "gzip, deflate",
            "sec-ch-ua": 'Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"'
        }

        self.master_df_list = {}
        self.output_dir = os.path.join("output", self.etf_cik)
        os.makedirs(self.output_dir, exist_ok=True)
        self.progress_file = os.path.join(self.output_dir, "progress.json")
        self.processed_filings = self.load_progress()

    def load_progress(self):
        """ FUNCTION DESCRIPTION:
        Load the list of already processed filings from the progress file.
        """
        if os.path.exists(self.progress_file):
            try:
                with open(self.progress_file, 'r') as f:
                    data = json.load(f)
                    print(f"Loaded progress: {len(data.get('processed', []))} filings already processed")
                    return set(data.get('processed', []))
            except Exception as e:
                print(f"Error loading progress file: {e}")
                return set()
        return set()

    def save_progress(self, accession_number):
        """ FUNCTION DESCRIPTION:
        Save a processed filing accession number to the progress file.
        """
        self.processed_filings.add(accession_number)
        try:
            with open(self.progress_file, 'w') as f:
                json.dump({'processed': list(self.processed_filings)}, f, indent=2)
        except Exception as e:
            print(f"Error saving progress: {e}")

    def fetch_submission_data(self):
        """ FUNCTION DESCRIPTION:
        Fetch the original submission data from the SEC API.
        """
        print(f"Fetching data from {self.base_url}")

        # Retry logic
        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = requests.get(self.base_url, headers=self.base_headers, timeout=30)
                if response.status_code != 200:
                    print(f"Failed to fetch submission data: {response.status_code}")
                    return None
                return response.json()
            except (SSLError, ConnectionError, Timeout) as e:
                if attempt < max_retries - 1:
                    wait_time = 2 * (2 ** attempt)
                    print(f"Network error (attempt {attempt + 1}/{max_retries}): {type(e).__name__}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"Failed to fetch submission data after {max_retries} attempts: {type(e).__name__}")
                    return None
            except RequestException as e:
                print(f"Request error: {type(e).__name__}: {str(e)}")
                return None

    def filter_nport_p_filings(self, data):
        """ FUNCTION DESCRIPTION:
        Filter for NPORT-P filings.
        """
        filings = data.get("filings", {}).get("recent", {})
        df = pd.DataFrame({
            "Accession Number": filings.get("accessionNumber", []),
            "Filing Date": filings.get("filingDate", []),
            "Form Type": filings.get("form", []),
            "Primary Document": filings.get("primaryDocument", [])
        })
        return df[df["Form Type"] == "NPORT-P"]

    def scrape_filing(self, accession_number, primary_document):
        """ FUNCTION DESCRIPTION:
        Scrape holdings data from an individual NPORT-P filing, given the accession number and primary document URL.
        """
        url = f"https://www.sec.gov/Archives/edgar/data/{self.etf_cik}/{accession_number.replace('-', '')}/{primary_document}"
        print(f"Fetching filing from: {url}")

        # Retry logic with exponential backoff
        max_retries = 5
        retry_delay = 2  # seconds

        for attempt in range(max_retries):
            try:
                response = requests.get(url, headers=self.nportp_headers, timeout=30)
                if response.status_code != 200:
                    print(f"Failed to fetch filing: {response.status_code}")
                    return None, None
                break  # Success, exit retry loop
            except (SSLError, ConnectionError, Timeout) as e:
                if attempt < max_retries - 1:
                    wait_time = retry_delay * (2 ** attempt)  # Exponential backoff
                    print(f"Network error (attempt {attempt + 1}/{max_retries}): {type(e).__name__}. Retrying in {wait_time}s...")
                    time.sleep(wait_time)
                else:
                    print(f"Failed after {max_retries} attempts: {type(e).__name__}: {str(e)}")
                    return None, None
            except RequestException as e:
                print(f"Request error: {type(e).__name__}: {str(e)}")
                return None, None

        soup = BeautifulSoup(response.content, 'html.parser')

        # Extract the reporting date from the filing
        reporting_date = None
        reporting_sections = soup.find_all('h1', string=lambda text: text and 'NPORT-P: Part A: General Information' in text)
        for reporting_section in reporting_sections:
            reporting_table = reporting_section.find_next('h4', string=lambda text: text and 'Item A.3. Reporting period' in text)
            if reporting_table is not None:
                table = reporting_table.find_next('table')
                if table is not None:
                    date_section = table.find('td', string=lambda text: text and 'b. Date as of which information is reported' in text)
                    if date_section is not None:
                        reporting_date = date_section.find_next_sibling('td').get_text(strip=True)
                        break

        # If the reporting date is not found, return None
        if not reporting_date:
            print("Failed to extract reporting date from the filing.")
            return None, None

        holdings_data = []

        # Extract the investment sections (each section represents a different holding)
        investment_sections = soup.find_all('h1', string=lambda text: text and 'NPORT-P: Part C: Schedule of Portfolio Investments' in text)

        # Iterate through each investment section and extract the holdings data
        for investment in investment_sections:
            investment_data = {}

            # Extract the 'Item C.1. Identification of investment' table to find the issuer name and CUSIP
            c1 = investment.find_next('h4', string=lambda text: text and 'Item C.1. Identification of investment' in text)
            if c1 is not None:
                c1_table = c1.find_next('table')
                if c1_table is not None:

                    # Extract the name of the issuer
                    issuer_name = c1_table.find('td', string=lambda text: text and 'a. Name of issuer (if any)' in text)
                    if issuer_name is not None:
                        investment_data["Name of Issuer"] = issuer_name.find_next_sibling('td').get_text(strip=True)

                    # Extract the CUSIP for the issuer
                    # cusip = c1_table.find('td', string=lambda text: text and 'd. CUSIP (if any)' in text)
                    # if cusip is not None:
                    #     investment_data["CUSIP"] = cusip.find_next_sibling('td').get_text(strip=True)

            # Extract the 'Item C.2. Amount of each investment' table to find the number of shares (balance), value in USD, and percentage of net assets
            c2 = investment.find_next('h4', string=lambda text: text and 'Item C.2. Amount of each investment' in text)
            c2_table = c2.find_next('table')
            if c2_table is not None:

                # Extract the number of shares (balance)
                num_shares = c2_table.find('td', string=lambda text: text and 'Balance' in text)
                if num_shares is not None:
                    investment_data["Number of Shares"] = num_shares.find_next_sibling('td').get_text(strip=True)

                # Extract the value in USD
                value_usd = c2_table.find('td', string=lambda text: text and 'Report values in U.S. dollars' in text)
                if value_usd is not None:
                    investment_data["Value (USD)"] = value_usd.find_next_sibling('td').get_text(strip=True)

                # Extract the percentage of net assets
                percent_net_assets = c2_table.find('td', string=lambda text: text and 'Percentage value compared to net assets of the Fund' in text)
                if percent_net_assets is not None:
                    investment_data["Percentage of Net Assets"] = percent_net_assets.find_next_sibling('td').get_text(strip=True)

            if investment_data:
                holdings_data.append(investment_data)
        holdings_df = pd.DataFrame(holdings_data)
        return holdings_df, reporting_date



    def run(self):
        """ FUNCTION DESCRIPTION:
        Main execution flow of the scraper.
        """
        data = self.fetch_submission_data()
        if not data:
            return
        nport_p_filings = self.filter_nport_p_filings(data)
        total_filings = len(nport_p_filings)
        print(f"Found {total_filings} NPORT-P filings")

        for idx, row in nport_p_filings.iterrows():
            accession_number = row["Accession Number"]
            primary_document = row["Primary Document"]

            # Skip if already processed
            if accession_number in self.processed_filings:
                print(f"Skipping already processed filing: {accession_number}")
                continue

            print(f"Processing filing {len(self.processed_filings) + 1}/{total_filings}: {accession_number}")
            holdings_df, reporting_date = self.scrape_filing(accession_number, primary_document)
            if holdings_df is not None and reporting_date is not None:
                self.master_df_list[reporting_date] = holdings_df
                # Save this filing immediately
                filename = f"{reporting_date}_NPORT-P_HOLDINGS.csv"
                filepath = os.path.join(self.output_dir, filename)
                print(f"Saving {filepath}")
                holdings_df.to_csv(filepath, index=False)
                # Mark as processed
                self.save_progress(accession_number)
            else:
                print(f"Failed to process filing {accession_number}, will retry on next run")

        print("\nProcessing complete!")
        if len(self.processed_filings) == total_filings:
            print("All filings have been processed.")
        else:
            print(f"Processed {len(self.processed_filings)}/{total_filings} filings. Run again to retry failed filings.")

def main():
    etf_cik = input("Enter the 10-digit CIK number for the ETF: ").strip()
    if not etf_cik.isdigit() or len(etf_cik) != 10:
        print("Invalid CIK number. Please enter a 10-digit numeric CIK.")
        return
    scraper = NPORTPScraper(etf_cik)
    scraper.run()

if __name__ == "__main__":
    main()