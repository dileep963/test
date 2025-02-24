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
        print(f"Querying URL: {runs_url}")
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

    total_runs = len(workflow_runs)
    total_failed = 0
    total_in_progress = 0
    total_success = 0
    total_cancelled = 0
    all_jobs = []

    for index, run in enumerate(workflow_runs):
        run_id = run["id"]
        print(f"Fetching jobs for run ID: {run_id}")
        jobs_data = fetch_jobs_for_run(run_id)
        
        run_failed = False
        run_in_progress = False
        run_cancelled = False
        
        if 'jobs' in jobs_data:
            if jobs_data.get("total_count", 0) == 0:
                run_failed = True
            else:
                for job in jobs_data['jobs']:
                    job_status = job.get('status', 'Unknown')
                    job_conclusion = job.get('conclusion', 'Unknown')
                    if job_status in ['in_progress', 'queued']:
                        run_in_progress = True
                        print(f"In Progress/Queued Job: {job_status}")
                    elif job_conclusion == 'failure':
                        run_failed = True
                    elif job_conclusion == 'cancelled':
                        run_cancelled = True
                        print(f"Cancelled Job Status: {job_conclusion}")
                    if 'steps' in job:
                        for step in job['steps']:
                            if step.get('conclusion') == 'failure':
                                run_failed = True

        if run_failed:
            total_failed += 1
        elif run_in_progress:
            total_in_progress += 1
        elif run_cancelled:
            total_cancelled += 1
        else:
            total_success += 1

        created_at = run.get('created_at', 'N/A')
        print(f"Workflow Run ID: {run_id}")
        print(f"Status: {'Success' if not run_failed and not run_in_progress and not run_cancelled else 'Failure' if run_failed else 'Cancelled' if run_cancelled else 'In Progress'}")
        print(f"Created at: {created_at}")

        all_jobs.append(jobs_data)

    print(f"\nSummary of Workflow Runs:")
    print(f"Total Runs: {total_runs}")
    print(f"Total Success: {total_success}")
    print(f"Total Failed: {total_failed}")
    print(f"Total In Progress: {total_in_progress}")
    print(f"Total Cancelled: {total_cancelled}")

    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_jobs, f, indent=4)

    print(f"All job data stored in {OUTPUT_FILE} successfully.")

if __name__ == "__main__":
    main()
