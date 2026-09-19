import json
import re
import secrets
from pathlib import Path


WORKSPACE_FILE = Path(
    "documind_workspaces.json"
)


def load_workspaces():

    if not WORKSPACE_FILE.exists():
        return {}

    try:

        with open(
            WORKSPACE_FILE,
            "r",
            encoding="utf-8",
        ) as file:

            return json.load(file)

    except Exception:

        return {}


def save_workspaces(workspaces):

    with open(
        WORKSPACE_FILE,
        "w",
        encoding="utf-8",
    ) as file:

        json.dump(
            workspaces,
            file,
            indent=2,
            ensure_ascii=False,
        )


def clean_workspace_id(value):

    value = value.strip().lower()

    value = re.sub(
        r"[^a-z0-9_-]",
        "-",
        value,
    )

    value = re.sub(
        r"-+",
        "-",
        value,
    )

    return value.strip("-_")


def workspace_exists(workspace_id):

    workspaces = load_workspaces()

    return workspace_id in workspaces


def create_workspace(
    name,
    workspace_id,
):

    workspaces = load_workspaces()

    workspace_id = clean_workspace_id(
        workspace_id
    )

    if not workspace_id:
        raise ValueError(
            "Workspace ID cannot be empty."
        )

    if workspace_id in workspaces:
        raise ValueError(
            "That Workspace ID already exists."
        )

    workspaces[workspace_id] = {
        "name": name.strip(),
        "workspace_id": workspace_id,
    }

    save_workspaces(workspaces)

    return workspace_id


def generate_workspace_id():

    return (
        "dm-"
        + secrets.token_hex(4)
    )


def get_workspace(
    workspace_id,
):

    workspaces = load_workspaces()

    return workspaces.get(
        workspace_id
    )