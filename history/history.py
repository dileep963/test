import os
import requests
import json
from datetime import datetime, timedelta
import re

GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
WORKFLOW_NAME = os.getenv("WORKFLOW_NAME")
REPO = os.getenv("REPO")
OUTPUT_FILE = os.getenv("OUTPUT_FILE", "final.json")
DURATION = os.getenv("DURATION", "1 week")
EXCLUDE_STATUSES = os.getenv("EXCLUDE_STATUSES", "").lower().split(',')

JOBS_API = f"https://api.github.com/repos/{REPO}/actions/runs/{{run_id}}/jobs"
RUNS_API = f"https://api.github.com/repos/{REPO}/actions/workflows/{WORKFLOW_NAME}/runs"

def get_headers():
    return {
        "Authorization": f"Bearer {os.getenv('GITHUB_TOKEN')}",
        "Accept": "application/vnd.github.v3+json"
    }

def calculate_date_range(duration):
    today = datetime.today()
    match = re.match(r"^(\d+)([a-zA-Z]+)$", duration)
    if not match:
        print(f"Error: Invalid duration format '{duration}'. Expected formats: '1w', '5d', '2m'.")
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
        print(f"Error: Unknown unit '{unit}'. Expected 'w' (weeks), 'd' (days), 'm' (months).")
        exit(1)

    return start_date.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")

START_DATE, END_DATE = calculate_date_range(DURATION)

def fetch_all_workflow_runs():
    all_runs = []
    page = 1
    while True:
        runs_url = f"{RUNS_API}?created={START_DATE}..{END_DATE}&page={page}"
        response = requests.get(runs_url, headers=get_headers())
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
            print(f"Error fetching workflow runs: {response.status_code} - {response.text}")
            break
    return all_runs

def fetch_jobs_for_run(run_id):
    jobs_url = JOBS_API.format(run_id=run_id)
    response = requests.get(jobs_url, headers=get_headers())
    if response.status_code == 200:
        return response.json()
    print(f"Error fetching jobs for run {run_id}: {response.status_code} - {response.text}")
    return {}

def main():
    workflow_runs = fetch_all_workflow_runs()
    if not workflow_runs:
        return

    total_runs = 0
    total_failed = 0
    total_in_progress = 0
    total_success = 0
    total_cancelled = 0
    total_queued = 0
    all_jobs = []

    for run in workflow_runs:
        run_id = run["id"]
        run_status = run.get("status", "").lower()
        run_conclusion = run.get("conclusion", "")
        if run_conclusion:
            run_conclusion = run_conclusion.lower()
        created_at = run.get("created_at", "")

        if run_conclusion in EXCLUDE_STATUSES:
            continue

        print(f"Workflow Run ID: {run_id}")
        print(f"Status: {run_conclusion.capitalize() if run_conclusion else run_status.capitalize()}")
        print(f"Created at: {created_at}\n")

        if run_conclusion == "failure":
            total_failed += 1
        elif run_status == "in_progress":
            total_in_progress += 1
        elif run_conclusion == "cancelled":
            total_cancelled += 1
        elif run_status == "queued":
            total_queued += 1
        else:
            total_success += 1
        
        total_runs += 1

        jobs_data = fetch_jobs_for_run(run_id)
        all_jobs.append({"run_id": run_id, "jobs_data": jobs_data})

    print("\nSummary of Workflow Runs:")
    if "success" not in EXCLUDE_STATUSES:
        print(f"Total Success: {total_success}")
    if "failure" not in EXCLUDE_STATUSES:
        print(f"Total Failed: {total_failed}")
    if "in_progress" not in EXCLUDE_STATUSES:
        print(f"Total In Progress: {total_in_progress}")
    if "cancelled" not in EXCLUDE_STATUSES:
        print(f"Total Cancelled: {total_cancelled}")
    if "queued" not in EXCLUDE_STATUSES:
        print(f"Total Queued: {total_queued}")
    print(f"Total Runs: {total_runs}")

    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_jobs, f, indent=4)

if __name__ == "__main__":
    main()
