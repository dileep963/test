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
DURATION = os.getenv("DURATION", "1w")  # Default to 1 week if not set
EXCLUDE_STATUSES = os.getenv("EXCLUDE_STATUSES", "").lower().split(',')

# Construct API URLs
JOBS_API = f"https://api.github.com/repos/{REPO}/actions/runs/{{run_id}}/jobs"
RUNS_API = f"https://api.github.com/repos/{REPO}/actions/workflows/{WORKFLOW_NAME}/runs"

def calculate_date_range(duration):
    today = datetime.today()
    match = re.match(r"^(\d+)([a-zA-Z]+)$", duration)
    if not match:
        print(f"Error: Invalid duration format '{duration}'. Expected formats: eg '1w', '5d', '2m'.")
        exit(1)
    
    number = int(match.group(1))
    unit = match.group(2).lower()

    if unit in ["w", "week"]:
        start_date = today - timedelta(weeks=number)
    elif unit in ["d", "day"]:
        start_date = today - timedelta(days=number)
    elif unit in ["m", "month"]:
        start_date = today - timedelta(days=30 * number)
    else:
        print(f"Error: Unknown unit '{unit}'. Supported units: 'w' (week), 'd' (day), 'm' (month).")
        exit(1)
    
    return start_date.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")

START_DATE, END_DATE = calculate_date_range(DURATION)

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
            print("Error fetching workflow runs.")
            exit(1)
    return all_runs

def fetch_jobs_for_run(run_id):
    jobs_url = JOBS_API.format(run_id=run_id)
    response = requests.get(jobs_url, headers=headers)
    if response.status_code == 200:
        return response.json()
    print(f"Error fetching jobs for run ID {run_id}.")
    return {}

def main():
    workflow_runs = fetch_all_workflow_runs()
    if not workflow_runs:
        print("No workflow runs found.")
        return

    total_runs = 0
    status_counts = {"success": 0, "failure": 0, "in_progress": 0, "cancelled": 0, "queued": 0}
    all_jobs = []

    for run in workflow_runs:
        run_id = run["id"]
        run_status = run.get("status", "").lower()
        run_conclusion = run.get("conclusion", "").lower() if run.get("conclusion") else ""
        created_at = run.get("created_at", "")

        if run_conclusion in EXCLUDE_STATUSES:
            continue

        print(f"Workflow Run ID: {run_id}\nStatus: {run_conclusion.capitalize() if run_conclusion else run_status.capitalize()}\nCreated at: {created_at}\n")

        status_counts[run_conclusion or run_status] += 1
        total_runs += 1
        jobs_data = fetch_jobs_for_run(run_id)
        all_jobs.append({"run_id": run_id, "jobs_data": jobs_data})

    print("\nSummary of Workflow Runs:")
    for status, count in status_counts.items():
        if status not in EXCLUDE_STATUSES:
            print(f"Total {status.capitalize()}: {count}")
    print(f"Total Runs: {total_runs}")

    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_jobs, f, indent=4)

if __name__ == "__main__":
    main()
