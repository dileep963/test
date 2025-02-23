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
DURATION = os.getenv("DURATION", "1 week")

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

def fetch_all_workflow_runs():
    """Fetch all workflow runs within the specified date range, handling pagination."""
    all_runs = []
    page = 1
    while True:
        runs_url = f"{RUNS_API}?created={START_DATE}..{END_DATE}&page={page}"
        print(f"Querying URL: {runs_url}")
        response = requests.get(runs_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            workflow_runs = data.get("workflow_runs", [])
            if not workflow_runs:
                break  # Exit loop if no more results
            all_runs.extend(workflow_runs)
            # Check if there is another page
            if "next" not in response.links:
                break  # Exit if no next page
            page += 1
        else:
            print(f"Error fetching workflow runs: {response.status_code} {response.text}")
            break
    return all_runs

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
    workflow_runs = fetch_all_workflow_runs()  # Now this will fetch all runs
    if not workflow_runs:
        print("No workflow runs found.")
        return

    total_runs = len(workflow_runs)
    total_success = 0
    total_failed = 0
    total_in_progress = 0
    all_jobs = []

    for index, run in enumerate(workflow_runs):
        run_id = run["id"]
        print(f"Fetching jobs for run ID: {run_id}")
        jobs_data = fetch_jobs_for_run(run_id)
        
        # Get the status and conclusion
        status = run.get('status', 'Unknown')
        conclusion = run.get('conclusion', 'Unknown')

        if status == 'in_progress':
            total_in_progress += 1
        if conclusion == 'failure':
            total_failed += 1
        if conclusion == 'success':
            total_success += 1

        # Get the created_at field
        created_at = run.get('created_at', 'N/A')

        # Print the details of each workflow run
        print(f"Workflow Run ID: {run_id}")
        print(f"Status: {status}")
        print(f"Conclusion: {conclusion}")
        print(f"Created at: {created_at}")

        all_jobs.append({
            'run_id': run_id,
            'status': status,
            'conclusion': conclusion,
            'created_at': created_at
        })

    # Print summary of the workflow runs
    print(f"\nSummary of Workflow Runs:")
    print(f"Total Runs: {total_runs}")
    print(f"Total Success: {total_success}")
    print(f"Total Failed: {total_failed}")
    print(f"Total In Progress: {total_in_progress}")

    # Save the output in the specified file
    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_jobs, f, indent=4)

    print(f"All job data stored in {OUTPUT_FILE} successfully.")

if __name__ == "__main__":
    main()
