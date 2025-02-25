import os
import requests
import json
from datetime import datetime, timedelta
import re
import argparse

class GitHubFetcher:
    """
    A class to fetch GitHub workflow runs and jobs.
    """

    def __init__(self, token: str, runs_api: str, jobs_api: str, output_file: str = "final.json", duration: str = "1 week", exclude_status: list = None):
        """
        Initializes the GitHubFetcher class with API details and configuration.

        Args:
            token (str): GitHub token for authentication.
            runs_api (str): API endpoint for workflow runs.
            jobs_api (str): API endpoint for job details.
            output_file (str, optional): Output file to store job data. Defaults to "final.json".
            duration (str, optional): Time range for fetching workflow runs. Defaults to "1 week".
            exclude_status (list, optional): List of statuses to exclude (e.g., ['queued', 'failure']).
        """
        self.token = token
        self.runs_api = runs_api
        self.jobs_api = jobs_api
        self.output_file = output_file
        self.duration = duration
        self.exclude_status = exclude_status if exclude_status else []

    # Function to calculate the date range based on the duration
    def calculate_date_range(self, duration):
        today = datetime.today()
        match = re.match(r"(\d+)([a-zA-Z]+)", duration)
        if not match:
            print(f"Invalid duration format: {duration}. Exiting.")
            exit(1)  # Exit with status 1 if input does not match requirements

        number = int(match.group(1))
        unit = match.group(2).lower()
        if unit in ["w", "week"]:
            start_date = today - timedelta(weeks=number)
        elif unit in ["d", "day"]:
            start_date = today - timedelta(days=number)
        elif unit in ["m", "month"]:
            start_date = today - timedelta(days=30 * number)
        else:
            print(f"Unknown unit: {unit}. Exiting.")
            exit(1)  # Exit with status 1 if input does not match requirements

        return start_date.strftime("%Y-%m-%d"), today.strftime("%Y-%m-%d")

    def fetch_all_workflow_runs(self, start_date, end_date):
        all_runs = []
        page = 1
        while True:
            runs_url = f"{self.runs_api}?created={start_date}..{end_date}&page={page}"
            headers = {
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github.v3+json"
            }
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

    def fetch_jobs_for_run(self, run_id):
        headers = {
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json"
        }
        response = requests.get(f"{self.jobs_api}/{run_id}/jobs", headers=headers)
        if response.status_code == 200:
            return response.json()
        else:
            print(f"Error fetching jobs for run {run_id}: {response.status_code} {response.text}")
            return {}

    def fetch_workflow_data(self):
        # Read environment variables inside the method
        GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
        RUNS_API = os.getenv("RUNS_API")
        JOBS_API = os.getenv("JOBS_API")
        OUTPUT_FILE = os.getenv("OUTPUT_FILE", "final.json")
        DURATION = os.getenv("DURATION", "1 week")

        # Calculate date range
        start_date, end_date = self.calculate_date_range(self.duration)
        print(f"Fetching workflow runs from {start_date} to {end_date}")

        workflow_runs = self.fetch_all_workflow_runs(start_date, end_date)
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
            jobs_data = self.fetch_jobs_for_run(run_id)

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
                        elif job_conclusion == 'failure':
                            run_failed = True
                        elif job_conclusion == 'cancelled':
                            run_cancelled = True
                        if 'steps' in job:
                            for step in job['steps']:
                                if step.get('conclusion') == 'failure':
                                    run_failed = True

            # Apply the exclusion filter
            if self.exclude_status:
                if 'queued' in self.exclude_status and (run_in_progress or run_failed or run_cancelled):
                    continue
                elif 'failure' in self.exclude_status and run_failed:
                    continue
                elif 'success' in self.exclude_status and not (run_failed or run_cancelled or run_in_progress):
                    continue
                elif 'cancelled' in self.exclude_status and run_cancelled:
                    continue
                elif 'in_progress' in self.exclude_status and run_in_progress:
                    continue

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

        with open(self.output_file, "w") as f:
            json.dump(all_jobs, f, indent=4)

        print(f"All job data stored in {self.output_file} successfully.")

if __name__ == "__main__":
    argument = argparse.ArgumentParser(description="GitHub Workflow Data Fetcher")
    argument.add_argument("--token", required=True, help="GitHub Token for authentication.")
    argument.add_argument("--repo", required=True, help="GitHub repository in the format owner/repo.")
    argument.add_argument("--workflow_name", required=True, help="GitHub workflow file name (e.g., manual-trigger.yml).")
    argument.add_argument("--output_file", default="final.json", help="The output file to store job data.")
    argument.add_argument("--duration", default="1 week", help="Duration for fetching workflow runs (e.g., 1 week, 2 days).")
    argument.add_argument("--exclude_overall_status", nargs='*', choices=["queued", "success", "failure", "cancelled", "in_progress"],
                           help="Exclude workflow runs based on the overall status. You can pass multiple status values (e.g., --exclude_overall_status queued failure).")
    
    args = argument.parse_args()

    # Build the API endpoints dynamically based on repo and workflow_name
    runs_api = f"https://api.github.com/repos/{args.repo}/actions/workflows/{args.workflow_name}/runs"
    jobs_api = f"https://api.github.com/repos/{args.repo}/actions/runs"

    fetcher = GitHubFetcher(
        token=args.token,
        runs_api=runs_api,
        jobs_api=jobs_api,
        output_file=args.output_file,
        duration=args.duration,
        exclude_status=args.exclude_overall_status
    )

    # Fetch the start and end date within the main method as requested
    START_DATE, END_DATE = fetcher.calculate_date_range(fetcher.duration)
    print(f"Fetching workflow runs from {START_DATE} to {END_DATE}")
    
    fetcher.fetch_workflow_data()
