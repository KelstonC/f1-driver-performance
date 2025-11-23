import os
import logging
import pandas as pd
import numpy as np


BASE_DIR = "/Users/kelstonchen/GitRepos/predicting_race_winners"

logging.basicConfig(
    level=logging.INFO,
    format="{asctime} - {levelname} - {message}",
    style="{",
    datefmt="%Y-%m-%d %H:%M"
    )

COLUMNS = [
    'position', 
    # 'points', 
    'grid', 
    'status', 
    'Driver.driverId', 
    'Constructor.constructorId', 
    'Time.millis', 
    'season', 
    'round', 
    'circuit'
    ]

def create_points_time(results):

    by_race = results.groupby(['season', 'round'])

    # Standardize time (z-score)
    results['std_time'] = (results['Time.millis'] - by_race['Time.millis'].transform('mean')) / by_race['Time.millis'].transform('std')

    # Scale points by standardized time, square it to keep it > 0
    results['points_time'] = results['points'] * results['std_time']

    return results

def main():
    
    results = pd.read_csv(os.path.join(BASE_DIR, 'data', 'intermediate', 'results', 'results.csv'))
    results = results.loc[:, COLUMNS]

    # Redefine points system, every place get at least 1 point
    # add/subtract points based on difference between start and end position (grid - position)
    finished = (results['status'] == 'Finished' )
    results['points'] = (
        (np.abs(results['position'] - results['position'].max()) + 1) 
        + (results['grid'] - results['position'])
        ) * finished

    results = create_points_time(results)
    print(results)

main()