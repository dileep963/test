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
DURATION = os.getenv("DURATION", "1w")  # Default to 1 week if not provided

# Function to calculate the date range based on the duration
def calculate_date_range(duration):
    now = datetime.now()

    # Use regular expression to identify the duration type (e.g., "1d", "2w", "1m")
    match = re.match(r"(\d+)([a-zA-Z]+)", duration)
    if not match:
        print(f"Invalid duration format: {duration}. Defaulting to 1 day.")
        start_date = now - timedelta(days=1)
        return start_date.strftime("%Y-%m-%dT%H:%M:%SZ"), now.strftime("%Y-%m-%dT%H:%M:%SZ")

    # Extract the number and the unit from the input duration
    number = int(match.group(1))
    unit = match.group(2).lower()

    # Calculate the date range based on the unit (days, weeks, months)
    if unit in ["w", "week"]:
        start_date = now - timedelta(weeks=number)
    elif unit in ["d", "day"]:
        start_date = now - timedelta(days=number)
    elif unit in ["m", "month"]:
        start_date = now - timedelta(days=30 * number)  # Approximate 30 days per month
    else:
        print(f"Unknown unit: {unit}. Defaulting to 1 day.")
        start_date = now - timedelta(days=1)
    
    # Return start and end dates in GitHub API-compatible format (ISO 8601)
    return start_date.strftime("%Y-%m-%dT%H:%M:%SZ"), now.strftime("%Y-%m-%dT%H:%M:%SZ")

# Get the start and end date based on the duration input
START_DATE, END_DATE = calculate_date_range(DURATION)

# Print the date range being used for the API query
print(f"Fetching workflow runs from {START_DATE} to {END_DATE}")

headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def fetch_workflow_runs():
    """Fetch workflow runs within the specified date range."""
    runs_url = f"{RUNS_API}?created[gte]={START_DATE}&created[lte]={END_DATE}"
    response = requests.get(runs_url, headers=headers)
    if response.status_code == 200:
        return response.json().get("workflow_runs", [])
    else:
        print(f"Error fetching workflow runs: {response.status_code} {response.text}")
        return []

def fetch_jobs_for_run(run_id):
    """Fetch jobs for a given workflow run ID."""
    response = requests.get(f"{JOBS_API}/{run_id}/jobs", headers=headers)
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
        print(f"\nFetching jobs for run ID: {run_id}")
        
        # Fetch job details for each workflow run
        jobs_data = fetch_jobs_for_run(run_id)
        
        # Print the details of each workflow run
        print(f"Workflow Run ID: {run_id}")
        print(f"Status: {jobs_data.get('status', 'Unknown')}")
        print(f"Conclusion: {jobs_data.get('conclusion', 'Unknown')}")
        print(f"Created at: {jobs_data.get('created_at', 'N/A')}")
        
        # Add jobs data to the list
        all_jobs.append(jobs_data)

    # Save the output in the specified file
    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_jobs, f, indent=4)

    print(f"\nAll job data stored in {OUTPUT_FILE} successfully.")

if __name__ == "__main__":
    main()
