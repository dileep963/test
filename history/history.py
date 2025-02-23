import os
import requests
import json
from datetime import datetime, timedelta
import re

# Read environment variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
RUNS_API = os.getenv("RUNS_API")
JOBS_API = os.getenv("JOBS_API")
OUTPUT_FILE = os.getenv("OUTPUT_FILE", "final.json")
DURATION = os.getenv("DURATION", "1w")

# Function to calculate the date range based on the duration
def calculate_date_range(duration):
    today = datetime.today()
    
    # Use regular expression to identify the duration type
    match = re.match(r"(\d+)([a-zA-Z]+)", duration)
    if not match:
        print(f"Invalid duration format: {duration}. Defaulting to 1 week.")
        # Default to 1 week if format is not recognized
        start_date = today - timedelta(weeks=1)
        return start_date.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
    
    # Extract the number and the unit from the input duration
    number = int(match.group(1))
    unit = match.group(2).lower()

    # Calculate the date range based on the unit (weeks, months, days)
    if unit == "w" or unit == "week":
        start_date = today - timedelta(weeks=number)
    elif unit == "d" or unit == "day":
        start_date = today - timedelta(days=number)
    elif unit == "m" or unit == "month":
        start_date = today - timedelta(days=30 * number)  # Approximate 30 days per month
    else:
        print(f"Unknown unit: {unit}. Defaulting to 1 week.")
        start_date = today - timedelta(weeks=1)
    
    return start_date.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")

# Get the start and end date based on the duration
START_DATE, END_DATE = calculate_date_range(DURATION)

# Print the date range being used
print(f"Fetching workflow runs from {START_DATE} to {END_DATE}")

headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def fetch_workflow_runs():
    """Fetch workflow runs within the specified date range."""
    runs_url = f"{RUNS_API}?created[gte]={START_DATE}&created[lte]={END_DATE}"
    response = requests.get(runs_url, headers=headers)
    
    # Debugging prints
    print(f"Querying URL: {runs_url}")
    print(f"Response Status: {response.status_code}")
    
    if response.status_code == 200:
        data = response.json()
        print(f"Fetched Workflow Runs: {data}")
        return data.get("workflow_runs", [])
    else:
        print(f"Error fetching workflow runs: {response.status_code} {response.text}")
        return []

def fetch_jobs_for_run(run_id):
    """Fetch jobs for a given workflow run ID."""
    response = requests.get(f"{JOBS_API}/{run_id}/jobs", headers=headers)
    
    # Debugging prints
    print(f"Fetching jobs for run ID: {run_id}")
    print(f"Response Status: {response.status_code}")
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching jobs for run {run_id}: {response.status_code} {response.text}")
        return {}

def main():
    """Main function to fetch jobs from workflow runs."""
    workflow_runs = fetch_workflow_runs()
    run_ids = [run["id"] for run in workflow_runs]

    all_jobs = []
    for index, run_id in enumerate(run_ids):
        print(f"Fetching jobs for run ID: {run_id}")
        jobs_data = fetch_jobs_for_run(run_id)
        all_jobs.append(jobs_data)

    # Save the output in the specified file
    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_jobs, f, indent=4)

    print(f"All job data stored in {OUTPUT_FILE} successfully.")

if __name__ == "__main__":
    main()
