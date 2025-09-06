import json
import os
from typing import List, Optional

import click
from google.auth import default, credentials, impersonated_credentials
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError


def get_credentials(
    scopes: List[str], target_principal: Optional[str] = None
) -> credentials.Credentials:
    """
    Get Google API credentials for given scopes, with optional impersonation.

    Args:
        scopes: List of OAuth2 scopes to request.
        target_principal: The service account to impersonate.

    Returns:
        A Google credentials object.
    """
    creds, _ = default(scopes=scopes)

    if target_principal:
        creds = impersonated_credentials.Credentials(
            source_credentials=creds,
            target_principal=target_principal,
            target_scopes=scopes,
        )

    return creds


@click.command()
@click.argument(
    "output_file", type=click.Path(dir_okay=False, writable=True, resolve_path=True)
)
def build_dataset(output_file: str):
    """
    Queries Google Drive for files in specified folders and builds a JSON dataset.

    Reads folder IDs from GDRIVE_SONG_SHEETS_FOLDER_IDS environment variable.
    Optionally impersonates a service account specified by GDRIVE_TARGET_PRINCIPAL.
    """
    folder_ids_str = os.environ.get("GDRIVE_SONG_SHEETS_FOLDER_IDS")
    if not folder_ids_str:
        click.echo(
            "Error: GDRIVE_SONG_SHEETS_FOLDER_IDS environment variable not set.",
            err=True,
        )
        raise click.Abort()

    folder_ids = [folder_id.strip() for folder_id in folder_ids_str.split(",")]
    target_principal = os.environ.get("GDRIVE_TARGET_PRINCIPAL")

    try:
        creds = get_credentials(
            scopes=["https://www.googleapis.com/auth/drive.readonly"],
            target_principal=target_principal,
        )
        service = build("drive", "v3", credentials=creds)

        all_files = []
        for folder_id in folder_ids:
            page_token = None
            while True:
                response = (
                    service.files()
                    .list(
                        q=f"'{folder_id}' in parents and trashed=false",
                        fields="nextPageToken, files(id, name, properties)",
                        pageToken=page_token,
                    )
                    .execute()
                )
                all_files.extend(response.get("files", []))
                page_token = response.get("nextPageToken")
                if not page_token:
                    break

        for file_data in all_files:
            if "properties" in file_data and file_data["properties"]:
                file_data["properties"] = dict(sorted(file_data["properties"].items()))

        all_files.sort(key=lambda item: item["name"])

        output_dir = os.path.dirname(output_file)
        if output_dir:
            os.makedirs(output_dir, exist_ok=True)

        with open(output_file, "w") as f:
            json.dump(all_files, f, indent=2)

        click.echo(
            f"Successfully built dataset with {len(all_files)} files at {output_file}"
        )

    except HttpError as error:
        click.echo(f"An error occurred: {error}", err=True)
        raise click.Abort()
    except Exception as e:
        click.echo(f"An unexpected error occurred: {e}", err=True)
        raise click.Abort()


if __name__ == "__main__":
    build_dataset()
