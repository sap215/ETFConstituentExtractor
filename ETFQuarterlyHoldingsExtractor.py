# Imports
import requests
import pandas as pd
from bs4 import BeautifulSoup

class NPORTPScraper:
    def __init__(self, etf_cik):
        self.etf_cik = etf_cik
        self.base_url = f"https://data.sec.gov/submissions/CIK{self.etf_cik}.json"

        # Headers for the base API request
        self.base_headers = {
            "User-Agent": "Firstname Lastname your_email@example.com", # REPLACE WITH YOUR OWN INFORMATION
            "Accept-Encoding": "gzip, deflate",
            "Host": "data.sec.gov"
        }
        
        # Headers for individual NPORT-P filings
        self.nportp_headers = {
            "User-Agent": "Firstname Lastname your_email@example.com", # REPLACE WITH YOUR OWN INFORMATION
            "Accept-Language": "en-US,en;q=0.9",
            "Accept": "application/xml",
            "Priority": "u=0, i",
            "Accept-Encoding": "gzip, deflate",
            "sec-ch-ua": 'Google Chrome";v="129", "Not=A?Brand";v="8", "Chromium";v="129"'
        }

        self.master_df_list = {}

    def fetch_submission_data(self):
        """ FUNCTION DESCRIPTION:
        Fetch the original submission data from the SEC API.
        """
        print(f"Fetching data from {self.base_url}")
        response = requests.get(self.base_url, headers=self.base_headers)
        if response.status_code != 200:
            print(f"Failed to fetch submission data: {response.status_code}")
            return None
        return response.json()
    
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
        response = requests.get(url, headers=self.nportp_headers)
        if response.status_code != 200:
            print(f"Failed to fetch filing: {response.status_code}")
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
                    cusip = c1_table.find('td', string=lambda text: text and 'd. CUSIP (if any)' in text)
                    if cusip is not None:
                        investment_data["CUSIP"] = cusip.find_next_sibling('td').get_text(strip=True)
            
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
        


    def save_holdings(self):
        """ FUNCTION DESCRIPTION:
        Save all of the extracted holdings to CSV files (each file corresponds to a NPORT-P filing).
        """
        for date, df in self.master_df_list.items():
            filename = f"{date}_NPORT-P_HOLDINGS.csv"
            print(f"Saving {filename}")
            df.to_csv(filename, index=False)

    def run(self):
        """ FUNCTION DESCRIPTION:
        Main execution flow of the scraper.
        """
        data = self.fetch_submission_data()
        if not data:
            return
        nport_p_filings = self.filter_nport_p_filings(data)
        for _, row in nport_p_filings.iterrows():
            accession_number = row["Accession Number"]
            primary_document = row["Primary Document"]
            holdings_df, reporting_date = self.scrape_filing(accession_number, primary_document)
            if holdings_df is not None:
                self.master_df_list[reporting_date] = holdings_df
        self.save_holdings()

def main():
    etf_cik = input("Enter the 10-digit CIK number for the ETF: ").strip()
    if not etf_cik.isdigit() or len(etf_cik) != 10:
        print("Invalid CIK number. Please enter a 10-digit numeric CIK.")
        return
    scraper = NPORTPScraper(etf_cik)
    scraper.run()

if __name__ == "__main__":
    main()