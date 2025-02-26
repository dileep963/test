import os
import requests
import json
from datetime import datetime, timedelta
import re

# Read environment variables
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
WORKFLOW_NAME = os.getenv("WORKFLOW_NAME")  # e.g., manual-trigger.yml
REPO = os.getenv("REPO")  # e.g., dileep963/repo
OUTPUT_FILE = os.getenv("OUTPUT_FILE", "final.json")
DURATION = os.getenv("DURATION", "1 week")
EXCLUDE_STATUSES = os.getenv("EXCLUDE_STATUSES", "").lower().split(',')

# Construct API URLs
RUNS_API = f"https://api.github.com/repos/{REPO}/actions/workflows/{WORKFLOW_NAME}/runs"
JOBS_API = "https://api.github.com/repos/{repo}/actions/runs/{run_id}/jobs"

headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

# Function to calculate date range based on duration
def calculate_date_range(duration):
    today = datetime.today()
    match = re.match(r"(\d+)([a-zA-Z]+)", duration)
    if not match:
        print(f"Invalid duration format: {duration}. Defaulting to 1 week.")
        start_date = today - timedelta(weeks=1)
        return start_date.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")
    
    number = int(match.group(1))
    unit = match.group(2).lower()
    if unit in ["w", "week"]:
        start_date = today - timedelta(weeks=number)
    elif unit in ["d", "day"]:
        start_date = today - timedelta(days=number)
    elif unit in ["m", "month"]:
        start_date = today - timedelta(days=30 * number)
    else:
        print(f"Unknown unit: {unit}. Defaulting to 1 week.")
        start_date = today - timedelta(weeks=1)
    
    return start_date.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")

START_DATE, END_DATE = calculate_date_range(DURATION)
print(f"Fetching workflow runs from {START_DATE} to {END_DATE}")

def fetch_all_workflow_runs():
    all_runs = []
    page = 1
    while True:
        runs_url = f"{RUNS_API}?created={START_DATE}..{END_DATE}&page={page}"
        response = requests.get(runs_url, headers=headers)
        if response.status_code == 200:
            data = response.json()
            workflow_runs = data.get("workflow_runs", [])
            if not workflow_runs:
                break
            all_runs.extend(workflow_runs)
            if "next" not in response.links:
                break
            page += 1
        else:
            print(f"Error fetching workflow runs: {response.status_code} {response.text}")
            break
    return all_runs

def fetch_jobs_for_run(run_id):
    jobs_url = JOBS_API.format(repo=REPO, run_id=run_id)  # Using formatted JOBS_API
    response = requests.get(jobs_url, headers=headers)
    if response.status_code == 200:
        jobs_data = response.json()
        jobs = jobs_data.get("jobs", [])
        job_statuses = {job["name"]: job.get("conclusion", "unknown") for job in jobs}
        return job_statuses
    else:
        print(f"Error fetching jobs for run {run_id}: {response.status_code} {response.text}")
        return {}

def main():
    workflow_runs = fetch_all_workflow_runs()
    if not workflow_runs:
        print("No workflow runs found.")
        return

    total_runs = 0
    total_failed = 0
    total_success = 0
    total_cancelled = 0
    total_in_progress = 0
    total_queued = 0
    all_jobs_data = []

    for run in workflow_runs:
        run_id = run["id"]
        workflow_status = run.get('conclusion', '').lower()

        # Skip this run if its status is in the excluded statuses
        if workflow_status in EXCLUDE_STATUSES:
            print(f"Skipping run {run_id} due to excluded status {workflow_status}")
            continue

        jobs_data = fetch_jobs_for_run(run_id)  # Fetch job statuses for this run
        all_jobs_data.append({"run_id": run_id, "jobs": jobs_data})

        # Count the workflow status
        if workflow_status == "failure":
            total_failed += 1
        elif workflow_status == "success":
            total_success += 1
        elif workflow_status == "cancelled":
            total_cancelled += 1
        elif workflow_status == "in_progress":
            total_in_progress += 1
        elif workflow_status == "queued":
            total_queued += 1

        total_runs += 1  # Increment only for included runs

    # Print summary
    print(f"\nSummary of Workflow Runs:")
    print(f"Total Success: {total_success}")
    print(f"Total Failed: {total_failed}")
    print(f"Total Cancelled: {total_cancelled}")
    print(f"Total In Progress: {total_in_progress}")
    print(f"Total Queued: {total_queued}")
    print(f"Total Runs: {total_runs}")

    # Save jobs data to output file
    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_jobs_data, f, indent=4)

    print(f"All job data stored in {OUTPUT_FILE} successfully.")

if __name__ == "__main__":
    main()
