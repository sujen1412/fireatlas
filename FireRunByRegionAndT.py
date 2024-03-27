import json
import argparse
import os

from utils import timed
from FireTypes import TimeStep, Region


def validate_json(s):
    try:
        return json.loads(s)
    except ValueError:
        raise argparse.ArgumentTypeError("Not a valid JSON string")


@timed
def Run(region: Region, t: TimeStep):
    from FireRunDaskCoordinator import job_preprocess_region_t
    import FireConsts
    from FireLog import logger

    logger.info(f"Running preprocessing code for {region[0]} at {t=} with source {FireConsts.firesrc}")
    job_preprocess_region_t(None, None, region, t)


if __name__ == "__main__":
    """ The main code to run preprocessing for a region and time period. It writes to a dedicated directory on s3.
    
    Example:
    python3 FireRunByRegionAndT.py --regnm="WesternUS" --t="[2023,6,1,\"AM\"]"
    """
    
    parser = argparse.ArgumentParser()
    parser.add_argument("--regnm", type=str)
    parser.add_argument("--t", type=validate_json)
    args = parser.parse_args()
    Run([args.regnm, None], args.t)
