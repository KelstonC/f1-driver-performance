import os
import json
from datetime import datetime
import logging
import argparse
import pandas as pd


BASE_DIR = "/Users/kelstonchen/GitRepos/predicting_race_winners"
RAW_DATA = os.path.join(BASE_DIR, 'data', 'raw')

logging.basicConfig(
        level=logging.INFO,
        format="{asctime} - {levelname} - {message}",
        style="{",
        datefmt="%Y-%m-%d %H:%M"
        )

def save_data(df: pd.DataFrame, endpoint: str) -> None:
    """Export data"""
    path = os.path.join(BASE_DIR, 'data', 'intermediate', endpoint)
    output = os.path.join(path, endpoint + '.csv')
    
    os.makedirs(path, exist_ok=True)
    df.to_csv(output, index=False)
    
    logging.info(f'Data saved to: {output}')

def build_data(endpoint: str, key: str) -> pd.DataFrame:
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
                    season_id = int(race_data[d]['season'])
                    round_id = int(race_data[d]['round'])
                    circuit_id = str(race_data[d]['Circuit']['circuitId'])
                    race_df = pd.json_normalize(race_data[d][key])
                    race_df['season'] = season_id
                    race_df['round'] = round_id
                    race_df['circuit'] = circuit_id

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
        help="The endpoint key used to parse JSON files. This should be similar to the endpoint itself.",
        type=str,
        required=True
    )
    args = vars(parser.parse_args())

    df = build_data(endpoint=args['Endpoint'], key=args['Key'])
    save_data(df, endpoint=args['Endpoint'])

if __name__ == "__main__":
    main()

