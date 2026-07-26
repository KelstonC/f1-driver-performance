from __future__ import annotations

import argparse
import json
import os
from collections.abc import Callable
from datetime import datetime
from pathlib import Path

import pandas as pd
from config import configure_logging
from pydantic import BaseModel, ValidationError

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DATA = BASE_DIR / 'data' / 'raw'
OUTPUT_DIR = BASE_DIR / 'data' / 'intermediate'


def save_data(df: pd.DataFrame, endpoint: str) -> None:
    """Export data"""
    path = OUTPUT_DIR / endpoint
    output = path / (endpoint + '.csv')

    path.mkdir(parents=True, exist_ok=True)
    df.to_csv(output, index=False)
    
    logger.info(f'Data saved to: {output}')


class JolpicaData(BaseModel):
    """Base class for Jolpica data.
    
    Included are key data fields that are common across all Jolpica data endpoints.

    Attributes:
        season (int): The season year of the race.
        round (int): Enumeration of the race within season.
        circuit (str): The circuit ID of the race.
        locality (str): The locality of the race.
        country (str): The country of the race.
        lat (str): The latitude of the race location.
        long (str): The longitude of the race location.
    """
    season: int
    round: int
    circuit: str
    locality: str
    country: str
    lat: str
    long: str


def build_data(
        endpoint: str, 
        key: str,
        jolpica_data: BaseModel = JolpicaData
        ) -> pd.DataFrame:
    """Build data from endpoint into a DataFrame"""
    data_list = []

    # Walk through directories to get JSON files
    for root, dirs, files in os.walk(os.path.join(RAW_DATA, endpoint)):
        for name in files:
            if name.endswith('.json'):
                filepath = os.path.join(root, name)

                with open(filepath, 'r') as reader:
                    data = json.load(reader)

                race_data = data['RaceTable']['Races']

                # Some parsed data may contain more than one race
                for d in range(len(race_data)):
                    # Build DataFrame
                    try:
                        _data = jolpica_data(
                            season=race_data[d]['season'],
                            round=race_data[d]['round'],
                            circuit=race_data[d]['Circuit']['circuitId'],
                            locality=race_data[d]['Circuit']['Location']['locality'],
                            country=race_data[d]['Circuit']['Location']['country'],
                            lat=race_data[d]['Circuit']['Location']['lat'],
                            long=race_data[d]['Circuit']['Location']['long']
                        )
                    except ValidationError as e:
                        logger.error(f"Validation error for race data: {e}")
                        continue

                    race_df = pd.json_normalize(race_data[d][key])
                    race_df['season'] = _data.season
                    race_df['round'] = _data.round
                    race_df['circuit'] = _data.circuit
                    race_df['locality'] = _data.locality
                    race_df['country'] = _data.country
                    race_df['lat'] = _data.lat
                    race_df['long'] = _data.long

                    data_list.append(race_df)

    # Stack into a single DataFrame
    stacked = pd.concat(data_list).sort_values(by=['season', 'round'], ascending=True)
    stacked = stacked.drop_duplicates(subset=['season', 'round', 'Driver.driverId'])
    
    return stacked


def main():
    parser = argparse.ArgumentParser(description="Build the data from Jolpica API")
    parser.add_argument(
        "-e", 
        "--Endpoint", 
        help="Endpoint for API, see Jolpica documentation for list of endpoints (e.g., 'results')",
        type=str,
        required=True
        )
    parser.add_argument(
        "-k",
        "--Key",
        help="The endpoint key used to parse JSON files. This should be similar to the endpoint itself. (e.g., for the 'results' endpoint, the key is 'Results')",
        type=str,
        required=True
    )
    args = vars(parser.parse_args())

    df = build_data(endpoint=args['Endpoint'], key=args['Key'], jolpica_data=JolpicaData)
    save_data(df, endpoint=args['Endpoint'])


if __name__ == "__main__":
    # Set up logging to both console and file
    log_filename = BASE_DIR / 'logs' / f'data_build_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    log_filename.parent.mkdir(parents=True, exist_ok=True)

    logger = configure_logging(log_filename)

    main()

