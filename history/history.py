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

# Define constant for JOBS_API
JOBS_API = f"https://api.github.com/repos/{REPO}/actions/runs"

# Construct the RUNS_API dynamically using WORKFLOW_NAME and REPO
RUNS_API = f"https://api.github.com/repos/{REPO}/actions/workflows/{WORKFLOW_NAME}/runs"

# Function to calculate the date range based on the duration
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

headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

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
    response = requests.get(f"{JOBS_API}/{run_id}/jobs", headers=headers)
    if response.status_code == 200:
        return response.json()
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
    total_in_progress = 0
    total_success = 0
    total_cancelled = 0
    total_queued = 0
    all_jobs = []

    for index, run in enumerate(workflow_runs):
        run_id = run["id"]
        jobs_data = fetch_jobs_for_run(run_id)
        
        run_failed = False
        run_in_progress = False
        run_cancelled = False
        run_queued = False

        # Debugging: Print the status of the workflow run
        print(f"Run ID: {run_id} - Status: {run.get('status')} - Conclusion: {run.get('conclusion')}")

        # Skip this run if its status is in the excluded statuses
        if run.get('status', '').lower() in EXCLUDE_STATUSES:
            print(f"Skipping run {run_id} due to excluded status {run.get('status')}")
            continue

        if 'jobs' in jobs_data:
            if jobs_data.get("total_count", 0) == 0:
                run_failed = True
            else:
                for job in jobs_data['jobs']:
                    job_status = job.get('status', 'Unknown')
                    job_conclusion = job.get('conclusion', 'Unknown')

                    # Debugging: Print the job status and conclusion
                    print(f"Job ID: {job.get('id')} - Status: {job_status} - Conclusion: {job_conclusion}")

                    if job_status == 'in_progress' and 'in_progress' not in EXCLUDE_STATUSES:
                        run_in_progress = True
                    elif job_conclusion == 'failure' and 'failure' not in EXCLUDE_STATUSES:
                        run_failed = True
                    elif job_conclusion == 'cancelled' and 'cancelled' not in EXCLUDE_STATUSES:
                        run_cancelled = True
                    elif job_status == 'queued' and 'queued' not in EXCLUDE_STATUSES:
                        run_queued = True

        # Count this run if its status is not excluded
        if run_failed and 'failure' not in EXCLUDE_STATUSES:
            total_failed += 1
        elif run_in_progress and 'in_progress' not in EXCLUDE_STATUSES:
            total_in_progress += 1
        elif run_cancelled and 'cancelled' not in EXCLUDE_STATUSES:
            total_cancelled += 1
        elif run_queued and 'queued' not in EXCLUDE_STATUSES:
            total_queued += 1
        else:
            total_success += 1

        # If no exclusions were found, count the run
        if not any(run.get('status', '').lower() in EXCLUDE_STATUSES for status in ['failure', 'in_progress', 'cancelled', 'queued']):
            total_runs += 1

        created_at = run.get('created_at', 'N/A')
        status = "Success" if not run_failed and not run_in_progress and not run_cancelled else (
            "Failure" if run_failed else (
                "Cancelled" if run_cancelled else (
                    "In Progress" if run_in_progress else "Unknown"
                )
            )
        )

        # Print status only if it's not in excluded statuses
        if status.lower() not in EXCLUDE_STATUSES:
            print(f"Workflow Run ID: {run_id}")
            print(f"Status: {status}")
            print(f"Created at: {created_at}")

        # Store jobs in the output file if not excluded
        all_jobs.append(jobs_data)

    # Print summary with excluded statuses in mind
    print(f"\nSummary of Workflow Runs:")
    if 'success' not in EXCLUDE_STATUSES:
        print(f"Total Success: {total_success}")
    if 'failure' not in EXCLUDE_STATUSES:
        print(f"Total Failed: {total_failed}")
    if 'in_progress' not in EXCLUDE_STATUSES:
        print(f"Total In Progress: {total_in_progress}")
    if 'cancelled' not in EXCLUDE_STATUSES:
        print(f"Total Cancelled: {total_cancelled}")
    if 'queued' not in EXCLUDE_STATUSES:
        print(f"Total Queued: {total_queued}")
    print(f"Total Runs: {total_runs}")

    # Save all job data
    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_jobs, f, indent=4)

    print(f"All job data stored in {OUTPUT_FILE} successfully.")

if __name__ == "__main__":
    main()
