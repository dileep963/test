import os
import requests
import json
from datetime import datetime, timedelta
import re
import argparse

def get_headers(github_token):
    return {
        "Authorization": f"Bearer {github_token}",
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

def fetch_all_workflow_runs(runs_api, start_date, end_date, github_token):
    all_runs = []
    page = 1
    while True:
        runs_url = f"{runs_api}?created={start_date}..{end_date}&page={page}"
        response = requests.get(runs_url, headers=get_headers(github_token))
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

def fetch_jobs_for_run(jobs_api, run_id, github_token):
    jobs_url = jobs_api.format(run_id=run_id)
    response = requests.get(jobs_url, headers=get_headers(github_token))
    if response.status_code == 200:
        return response.json()
    print(f"Error fetching jobs for run {run_id}: {response.status_code} - {response.text}")
    return {}

def main():
    parser = argparse.ArgumentParser(description="Fetch GitHub workflow run history.")
    parser.add_argument("--github_token", required=True, help="GitHub token for authentication")
    parser.add_argument("--workflow_name", required=True, help="Name of the GitHub workflow")
    parser.add_argument("--repo", required=True, help="GitHub repository (e.g., owner/repo)")
    parser.add_argument("--output_file", default="final.json", help="Output file name (default: final.json)")
    parser.add_argument("--duration", default="1w", help="Duration for the query (e.g., '1w', '5d', '2m')")
    # parser.add_argument("--exclude_statuses", default="", help="Comma-separated list of statuses to exclude (e.g., 'success,failure')")


    # # Debugging output to confirm exclusion list
    # print(f"Excluding statuses: {exclude_statuses}")

    parser.add_argument("--exclude_statuses", default="", help="Comma-separated list of statuses to exclude (e.g., 'success,failure')")

   # Parse arguments
    args = parser.parse_args()
    exclude_statuses = args.exclude_statuses.split(',') if args.exclude_statuses else []

    # If `exclude_statuses` is provided as an empty string, convert it to an empty list
    #exclude_statuses = args.exclude_statuses.split(',') if args.exclude_statuses else []
    print(f"Excluding statuses: {exclude_statuses}")

    
    jobs_api = f"https://api.github.com/repos/{args.repo}/actions/runs/{{run_id}}/jobs"
    runs_api = f"https://api.github.com/repos/{args.repo}/actions/workflows/{args.workflow_name}/runs"

    start_date, end_date = calculate_date_range(args.duration)

    print(f"Fetching workflow runs from {start_date} to {end_date}")

    workflow_runs = fetch_all_workflow_runs(runs_api, start_date, end_date, args.github_token)
    if not workflow_runs:
        return

    total_runs = 0
    total_failed = 0
    total_in_progress = 0
    total_success = 0
    total_cancelled = 0
    total_queued = 0
    all_jobs = []

    exclude_statuses = args.exclude_statuses.lower().split(',')

    for run in workflow_runs:
        run_id = run["id"]
        run_status = run.get("status", "").lower()
        run_conclusion = run.get("conclusion", "")
        if run_conclusion:
            run_conclusion = run_conclusion.lower()
        created_at = run.get("created_at", "")

        if run_conclusion in exclude_statuses:
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

        jobs_data = fetch_jobs_for_run(jobs_api, run_id, args.github_token)
        all_jobs.append({"run_id": run_id, "jobs_data": jobs_data})

    print("\nSummary of Workflow Runs:")
    if "success" not in exclude_statuses:
        print(f"Total Success: {total_success}")
    if "failure" not in exclude_statuses:
        print(f"Total Failed: {total_failed}")
    if "in_progress" not in exclude_statuses:
        print(f"Total In Progress: {total_in_progress}")
    if "cancelled" not in exclude_statuses:
        print(f"Total Cancelled: {total_cancelled}")
    if "queued" not in exclude_statuses:
        print(f"Total Queued: {total_queued}")
    print(f"Total Runs: {total_runs}")

    with open(args.output_file, "w") as f:
        json.dump(all_jobs, f, indent=4)

if __name__ == "__main__":
    main()
