import os
import requests
import json
from datetime import datetime, timedelta
import pytz

# Read environment variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
RUNS_API = os.getenv("RUNS_API")
JOBS_API = os.getenv("JOBS_API")
OUTPUT_FILE = os.getenv("OUTPUT_FILE", "final.json")

# Define the timezone for MST (Mountain Standard Time)
MST = pytz.timezone('US/Mountain')

# Function to fetch workflow runs
def fetch_workflow_runs():
    """Fetch workflow runs using the system's current date and time."""
    current_time = datetime.now(MST)
    start_date = current_time - timedelta(days=1)  # Last 1 day
    end_date = current_time  # Current time

    # Format the dates as YYYY-MM-DD
    start_date_str = start_date.strftime("%Y-%m-%d")
    end_date_str = end_date.strftime("%Y-%m-%d")

    print(f"Fetching workflow runs from {start_date_str} to {end_date_str}")

    # API call to get workflow runs
    runs_url = f"{RUNS_API}?per_page=5&created={start_date_str}..{end_date_str}"
    print(f"Querying URL: {runs_url}")
    response = requests.get(runs_url, headers={"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"})
    
    if response.status_code == 200:
        return response.json().get("workflow_runs", [])
    else:
        print(f"Error fetching workflow runs: {response.status_code} {response.text}")
        return []

def fetch_jobs_for_run(run_id):
    """Fetch jobs for a given workflow run ID."""
    response = requests.get(f"{JOBS_API}/{run_id}/jobs", headers={"Authorization": f"Bearer {GITHUB_TOKEN}", "Accept": "application/vnd.github.v3+json"})
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Error fetching jobs for run {run_id}: {response.status_code} {response.text}")
        return {}

def convert_to_mst(time_str):
    """Convert UTC time to MST."""
    try:
        utc_time = datetime.strptime(time_str, "%Y-%m-%dT%H:%M:%SZ")
        utc_time = pytz.utc.localize(utc_time)
        mst_time = utc_time.astimezone(MST)
        return mst_time.strftime("%Y-%m-%d %H:%M:%S")
    except Exception as e:
        print(f"Error converting time: {e}")
        return time_str

def main():
    """Main function to fetch jobs from workflow runs."""
    workflow_runs = fetch_workflow_runs()
    if not workflow_runs:
        print("No workflow runs found.")
        return

    total_runs = len(workflow_runs)
    total_failed = 0
    total_in_progress = 0
    all_jobs = []

    for index, run in enumerate(workflow_runs):
        run_id = run["id"]
        print(f"Fetching jobs for run ID: {run_id}")
        jobs_data = fetch_jobs_for_run(run_id)
        
        # Calculate the status counts
        status = jobs_data.get('status', 'Unknown')
        conclusion = jobs_data.get('conclusion', 'Unknown')

        if status == 'in_progress':
            total_in_progress += 1
        if conclusion == 'failure':
            total_failed += 1

        # Print the details of each workflow run
        created_at = jobs_data.get('created_at', 'N/A')
        print(f"Workflow Run ID: {run_id}")
        print(f"Status: {status}")
        print(f"Conclusion: {conclusion}")
        print(f"Created at: {convert_to_mst(created_at)}")

        all_jobs.append(jobs_data)

    # Print summary of the workflow runs
    print(f"\nSummary of Workflow Runs:")
    print(f"Total Runs: {total_runs}")
    print(f"Total Failed: {total_failed}")
    print(f"Total In Progress: {total_in_progress}")

    # Save the output in the specified file
    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_jobs, f, indent=4)

    print(f"All job data stored in {OUTPUT_FILE} successfully.")

if __name__ == "__main__":
    main()
