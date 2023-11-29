import os
import sys
from time import sleep
from dataclasses import dataclass
from typing import AnyStr

import httpx


wf_id = AnyStr
wf_conclusion = AnyStr


@dataclass(frozen=True)
class Config:
    github_token: str
    workspace: str
    repository: str
    workflow: str
    github_api_path: str = "https://api.github.com/repos"
    github_default_workflows_path: str = "actions/workflows"
    github_default_runs_path: str = "actions/runs"


def get_headers(config: Config) -> dict:
    return {
        'Accept': 'application/vnd.github+json',
        'Authorization': f'Bearer {config.github_token}',
        'Content-Type': 'application/json'
    }


def dispatch_workflow(config: Config) -> None:
    default_branch = "master"
    data = {"ref": default_branch}
    dispatch_uri = (
        f'{config.github_api_path}/'
        f'{config.workspace}/'
        f'{config.repository}/'
        f'{config.github_default_workflows_path}/'
        f'{config.workflow}/'
        f'dispatches'
    )

    print(f"dispatch url:{dispatch_uri}")

    r = httpx.post(
        dispatch_uri,
        json=data,
        headers=get_headers(config)
    )

    if r.is_error:
        raise Exception(f"{r.content}")


def disable_workflow(config: Config) -> None:
    disable_uri = (
        f'{config.github_api_path}/'
        f'{config.workspace}/'
        f'{config.repository}/'
        f'{config.github_default_workflows_path}/'
        f'{config.workflow}/'
        f'disable'
    )
    r = httpx.put(
        disable_uri,
        headers=get_headers(config)
    )

    if r.is_error:
        raise Exception(f"{r.content}")


def get_running_workflow_id(config: Config) -> wf_id:
    params = {'status': 'in_progress'}
    get_runs_uri = (
        f'{config.github_api_path}/'
        f'{config.workspace}/'
        f'{config.repository}/'
        f'{config.github_default_runs_path}'
    )

    r = httpx.get(
        get_runs_uri,
        params=params,
        headers=get_headers(config)
    )

    if r.is_error:
        raise Exception(f"{r.content}")

    data = r.json()

    print(f"Running workflow data:{data}")

    runs = data.get("workflow_runs")
    related_runs = list(filter(lambda workflow: config.workflow in workflow.get("path"), runs))

    if len(related_runs) != 1:
        raise Exception()

    return data.get("workflow_runs").pop().get("id")


def get_workflow_conclusion_when_complete(
        workflow_id: wf_id,
        config: Config,
        sleeping_seconds: int = 10
) -> wf_conclusion:
    get_run_uri = (
        f'{config.github_api_path}/'
        f'{config.workspace}/'
        f'{config.repository}/'
        f'{config.github_default_runs_path}/'
        f'{workflow_id}'
    )

    data = {}

    while data.get("status") != "completed":
        sleep(sleeping_seconds)
        r = httpx.get(
            get_run_uri,
            headers=get_headers(config)
        )
        if r.is_error:
            raise Exception(f"{r.content}")
        data = r.json()

    return data.get("conclusion", "failure")


def main():
    conf = Config(
        github_token=os.environ["INPUT_GITHUBTOKEN"],
        workspace=os.environ["INPUT_WORKSPACE"],
        repository=os.environ["INPUT_REPOSITORY"],
        workflow=os.environ["INPUT_WORKFLOW"],
    )

    dispatch_workflow(conf)
    # disable_workflow(conf)
    sleep(10)
    workflow_id = get_running_workflow_id(conf)
    conclusion = get_workflow_conclusion_when_complete(workflow_id, conf)

    if conclusion == "failure":
        sys.exit(13)

    sys.exit()


if __name__ == "__main__":
    main()
