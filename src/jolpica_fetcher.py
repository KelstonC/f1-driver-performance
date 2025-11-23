import os
import requests
import json
from datetime import datetime
import time
import logging
import argparse


BASE_DIR = "/Users/kelstonchen/GitRepos/predicting_race_winners"
BASE_URL = "https://api.jolpi.ca/ergast/f1"
SEASONS = [2022, 2023, 2024, 2025]

logging.basicConfig(
    level=logging.INFO,
    format="{asctime} - {levelname} - {message}",
    style="{",
    datefmt="%Y-%m-%d %H:%M"
    )

class JolpicaFetcher:
    def __init__(
            self, 
            base_url: str, 
            params: dict, 
            seasons: list[int], 
            endpoint: str,
            filepath: str
            ):
        self.base_url = base_url
        self.params = params
        self.seasons = seasons
        self.endpoint = endpoint
        self.filepath = filepath
    
    def _save(
            self, 
            data: json,
            season_id: str,
            file_id: str
            ) -> None:
        """Save JSON file"""
        path = os.path.join(self.filepath, self.endpoint, season_id)
        time = datetime.now().strftime('%Y%m%d%H%M%S')
        output = os.path.join(path, (file_id + '_' + time + '.json'))

        # Create directory if does not exist
        if not os.path.exists(path):
            logging.info(f"Directory created: {path}")
            os.makedirs(path, exist_ok=True)
        # Save
        logging.info(f"Saved to: {output}")
        with open(output, 'w') as w:
            json.dump(data, w, indent=4)

    def _retries(self, url: str, params: dict) -> requests.Response:
        """Retry GET request after pulling too fast"""
        for i in range(3):
            r = requests.get(url, params=params)

            if r.status_code == 429:
                logging.warning('Too fast, sleep and try again')
                logging.info(f'Retry: {i + 1}')
                time.sleep(3)
                continue
            
            elif r.status_code == 200:
                logging.info(f'Successful pull after {i + 1} tries')
                return r
        
        raise Exception(f"Failed to fetch data after 3 retries. Status code: {r.status_code}")

    def fetch(self) -> None:
        """Grab data from Jolpica F1 API"""
        updated_params = self.params.copy()

        for season in self.seasons:
            updated_params['offset'] = 0
            logging.info(f'Fetching for season: {season}')

            while True:
                try:
                    url = os.path.join(
                        self.base_url, 
                        f'{season}',
                        self.endpoint
                        )
                    r = requests.get(url, params=updated_params)

                    # If too fast
                    if r.status_code == 429:
                        r = self._retries(url, params=updated_params)
                    
                    # Save data
                    data = r.json()['MRData']
                    self._save(
                        data,
                        season_id=str(season),
                        file_id=self.endpoint
                        )
                    
                    # Pagination
                    updated_params['offset'] += updated_params['limit']

                    # If offest is greater than or equal to total, all data has been fetched
                    if int(updated_params['offset']) >= int(data['total']):
                        logging.info(f'Nothing left to fetch for {season} season')
                        break

                    time.sleep(0.5)

                except requests.exceptions.RequestException as e:
                    raise e

def main():
    parser = argparse.ArgumentParser(description="Fetch data from Jolpica F1 API")
    parser.add_argument(
        "-e", 
        "--Endpoint", 
        help="Endpoint for API, see Jolpica documentation for list of endpoints (e.g., 'results')",
        type=str,
        required=True
        )
    parser.add_argument(
        "-s", 
        "--Seasons", 
        help="Season(s) to fetch data for. If not specified, will fetch for all seasons (i.e., 2022-2025).",
        type=int,
        default=SEASONS,
        required=False
        )
    args = vars(parser.parse_args())

    logging.info(f"==== FETCHING FOR ENDPOINT: {args['Endpoint']} ====")

    fetcher = JolpicaFetcher(
        BASE_URL, 
        params={'limit': 30, 'offset': 0},
        seasons=[args['Seasons']] if isinstance(args['Seasons'], int) else args['Seasons'],
        endpoint=args['Endpoint'],
        filepath=os.path.join(BASE_DIR, 'data', 'raw')
        )
    fetcher.fetch()

if __name__ == "__main__":
    main()
