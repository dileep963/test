import os
import requests
import json

# Read variables from environment
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
RUNS_API = os.getenv("RUNS_API")
JOBS_API = os.getenv("JOBS_API")
PER_PAGE = os.getenv("PER_PAGE", "5")  # Default to 5 if not provided
OUTPUT_FILE = os.getenv("OUTPUT_FILE", "final.json")  # Default to final.json if not provided

headers = {
    "Authorization": f"Bearer {GITHUB_TOKEN}",
    "Accept": "application/vnd.github.v3+json"
}

def fetch_workflow_runs():
    """Fetch the latest workflow runs."""
    # Modify the API URL to include the per_page parameter
    runs_url = f"{RUNS_API}&per_page={PER_PAGE}"
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
        print(f"Fetching jobs for run ID: {run_id}")
        jobs_data = fetch_jobs_for_run(run_id)
        all_jobs.append(jobs_data)

    # Save the output in the file specified by OUTPUT_FILE
    with open(OUTPUT_FILE, "w") as f:
        json.dump(all_jobs, f, indent=4)

    print(f"All job data stored in {OUTPUT_FILE} successfully.")

if __name__ == "__main__":
    main()
