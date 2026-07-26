from __future__ import annotations

import argparse
import json
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import urljoin

from config import configure_logging
from pydantic import BaseModel
from requests import HTTPError, Session
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

BASE_DIR = Path(__file__).resolve().parent.parent
BASE_URL = "https://api.jolpi.ca/ergast/f1/"
SEASONS = [2022, 2023, 2024, 2025, 2026]


class Client(Session):
    """Client to fetch data from Jolpica F1 API.
    
    Additional functionality from Requests Session class, including retries and timeout handling.

    Attributes:
        host (str): Base URL for the Jolpica F1 API.
    """
    def __init__(
            self,
            timeout: int = 10,
            total: int = 3,
            backoff_factor: float = 30,
        ):

        super().__init__()

        self.host = BASE_URL

        adapter = TimeoutHTTPAdapter(
            timeout=timeout,
            max_retries=Retry(
                total=total,
                status_forcelist=[429, 500, 502, 503, 504],
                backoff_factor=backoff_factor,
            ),
        )
        self.mount(BASE_URL, adapter)

    def request(
            self, 
            method: str, 
            path: str, 
            *args, 
            **kwargs
        ) -> dict:
        """Override :obj:`Session` request method to add retries and output JSON.

        Args:
            method (str): Method for the new Request object.
            path (str): Path from host for the new Request object.

        Returns:
            dict: Response JSON
        """
        response = super().request(
            method=method, 
            url=urljoin(self.host, path), 
            *args,
            **kwargs
        )
        try:
            response.raise_for_status()
        except HTTPError as exc:
            code = exc.response.status_code
            logger.error(f"HTTP error occurred: {code} - {exc.response.text}")
            raise

        # Data is nested under 'MRData' key
        data = response.json()['MRData']

        return data


class TimeoutHTTPAdapter(HTTPAdapter):
    def __init__(self, timeout, *args, **kwargs):
        """TimeoutHTTPAdapter constructor.

        Args:
            timeout (int): How many seconds to wait for the server to send data before
                giving up.
        """
        self.timeout = timeout
        super().__init__(*args, **kwargs)

    def send(self, request, **kwargs):
        """Override :obj:`HTTPAdapter` send method to add a default timeout."""
        timeout = kwargs.get("timeout")
        if timeout is None:
            kwargs["timeout"] = self.timeout

        return super().send(request, **kwargs)


class PaginationParams(BaseModel):
    """Hold pagination parameters for API requests.

    Controls the flow of data retrieval. Each request will return a max of `limit` items, 
    and the `offset` determines how many items to skip before starting to collect the result set.
    This moves through the dataset in chunks.

    Attributes:
        limit (int): The maximum number of items to return per request.
        offset (int): The number of items to skip before starting to collect the result set.
    """
    limit: int = 30
    offset: int = 0


def save_data(
        data: dict, 
        season_id: str, 
        endpoint: str
    ) -> None:
    """Save data as JSON file."""
    path = BASE_DIR / 'data' / 'raw' / endpoint / season_id
    timestamp = datetime.now().strftime('%Y%m%d%H%M%S')
    output = path / (endpoint + '_' + timestamp + '.json')

    # Create directory if does not exist
    path.mkdir(parents=True, exist_ok=True)
    logger.info(f"Directory created: {path}")

    # Save
    logger.info(f"Saved to: {output}")
    with open(output, 'w') as w:
        json.dump(data, w, indent=4)


def paginate_data(
        client: Client,
        seasons: list[int],
        endpoint: str,
        params: PaginationParams,
    ) -> None:
    """Paginate through data from Jolpica F1 API and save to file."""
    updated_params = params.__dict__.copy()
    pagination_incomplete = True

    for season in seasons:
        updated_params['offset'] = 0

        while pagination_incomplete:
            logger.info(f'Fetching for season: {season}, offset: {updated_params["offset"]}')

            # Fetch data from API
            response = client.request("GET", f"{season}/{endpoint}", params=updated_params)
            # Save to file
            save_data(response, season_id=str(season), endpoint=endpoint)
        
            # Pagination
            updated_params['offset'] += updated_params['limit']
        
            # If offest is greater than or equal to total, all data has been fetched
            if int(updated_params['offset']) >= int(response['total']):
                logger.info(f'Nothing left to fetch for {season} season')
                # break
                pagination_incomplete = False
        
            time.sleep(1)


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

    logger.info(f"==== FETCHING FOR ENDPOINT: {args['Endpoint']} ====")

    fetcher = Client()
    paginate_data(
        client=fetcher,
        seasons=[args['Seasons']] if isinstance(args['Seasons'], int) else args['Seasons'],
        endpoint=args['Endpoint'],
        params=PaginationParams()
    )

if __name__ == "__main__":
    # Set up logging to both console and file
    log_filename = BASE_DIR / 'logs' / f'jolpica_fetcher_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    log_filename.parent.mkdir(parents=True, exist_ok=True)

    logger = configure_logging(log_filename)

    main()
